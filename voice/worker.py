"""The voice worker: reads JSON lines on stdin, writes JSON lines on stdout.

Commands in:  {"cmd":"say","id":N,"text":"..."}  {"cmd":"listen","id":N}  {"cmd":"quit"}
Events out:   ready, first_audio, spoken, heard, error (each a JSON object with "event").

Speech out: the cloned voice (VoxCPM2, one cached prompt made from RK's local
sample) is generated in small pieces and played as they are made. Speech in: the
microphone is open only while the push-to-talk key is held, and is closed while
JARVIS is speaking (ADR-0012 D3). Audio is held in memory and never stored.
The profile asset is refused if its SHA-256 differs from the record (ADR-0012 D5).
"""

import hashlib
import json
import os
import queue
import sys
import threading
import time

PREBUFFER_S = 0.5
LISTEN_WAIT_S = 20.0
LISTEN_MAX_S = 30.0
MIN_SPEECH_S = 0.3
SILENT_PEAK = 330        # a piece whose loudest sample is below this (about 1% of full scale) counts as silence
FADE_IN_S = 0.015
FADE_OUT_S = 0.03
PAUSE_S = 0.12           # the deliberate gap left after each sentence


def emit(**obj) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Worker:
    def __init__(self, root: str):
        self.root = root
        with open(os.path.join(root, "voice_settings.json"), encoding="utf-8-sig") as fh:
            self.cfg = json.load(fh)
        self.jobs = queue.Queue()
        self.stt = None
        self.stt_problem = ""
        self.tts = None
        self.player = None

    def load(self) -> None:
        os.environ.setdefault("HF_HOME", os.path.join(self.root, "hf-cache"))
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        sample = os.path.join(self.root, "samples", self.cfg["voice"])
        want = self.cfg.get("sample_sha256", "")
        if not want or sha256(sample) != want:
            raise RuntimeError("the voice asset does not match its record; refusing to speak")
        import numpy as np
        import torch
        from voxcpm import VoxCPM
        self.np, self.torch = np, torch
        model = VoxCPM.from_pretrained(os.path.join(self.root, "models", "voxcpm2"), load_denoiser=False,
                                       local_files_only=True, optimize=False)
        self.tts = model.tts_model
        self.sr = self.tts.sample_rate
        if self.cfg.get("mode") == "ref+continuation" and self.cfg.get("reference_text"):
            # the sample is both the voice reference and a spoken lead-in with its own transcript:
            # measured steadier and closer to the sample than reference-only (evidence note, voice section)
            self.cache = self.tts.build_prompt_cache(prompt_text=self.cfg["reference_text"], prompt_wav_path=sample,
                                                     reference_wav_path=sample)
        else:
            self.cache = self.tts.build_prompt_cache(prompt_text=None, prompt_wav_path=None, reference_wav_path=sample)
        from voice.winaudio import Player
        self.player = Player(int(self.sr * float(self.cfg.get("playback_factor", 1.0))))  # below 1.0: slower and lower
        for _ in self._pieces("Good evening, sir."):  # warm-up; discarded
            pass
        # Speech in is optional: if its libraries cannot load (for example Windows Smart App Control blocks a
        # compiled file), the voice still speaks and the keyboard still works.
        try:
            from faster_whisper import WhisperModel
            self.stt = WhisperModel(os.path.join(self.root, "models", "whisper", "small.en"), device="cpu", compute_type="int8")
            self.stt_problem = ""
        except Exception as exc:
            self.stt = None
            self.stt_problem = type(exc).__name__ + ": " + str(exc)[:160]

    def _pieces(self, text):
        steps = int(self.cfg.get("inference_timesteps", 4))
        cfg = float(self.cfg.get("cfg_value", 2.0))
        for ch in self.tts.generate_with_prompt_cache_streaming(target_text=text, prompt_cache=self.cache,
                                                                inference_timesteps=steps, cfg_value=cfg):
            a = ch[0] if isinstance(ch, tuple) else ch
            a = a.detach().float().cpu().numpy().reshape(-1)
            yield (self.np.clip(a, -1.0, 1.0) * 32767).astype(self.np.int16)

    def _clean(self, pieces):
        """Trim the model's leading silence, keep internal pauses, drop the trailing tail, and fade the
        first and last pieces so a sentence neither pops in nor trails off; then leave a short fixed pause."""
        np = self.np
        started = False
        held = []   # [last loud piece, then any silent pieces after it]
        for a in pieces:
            loud = int(np.abs(a).max()) >= SILENT_PEAK
            if not started:
                if not loud:
                    continue
                started = True
                a = a.copy()
                n = min(len(a), int(FADE_IN_S * self.sr))
                a[:n] = (a[:n] * np.linspace(0.0, 1.0, n)).astype(np.int16)
            if loud:
                for h in held:
                    yield h
                held = [a]
            else:
                held.append(a)
        if held:
            last = held[0].copy()
            n = min(len(last), int(FADE_OUT_S * self.sr))
            last[-n:] = (last[-n:] * np.linspace(1.0, 0.0, n)).astype(np.int16)
            yield last
            yield np.zeros(int(PAUSE_S * self.sr), dtype=np.int16)

    def say(self, job_id: int, text: str, received_at: float) -> None:
        t0 = time.monotonic()
        started = False
        held = []
        held_s = 0.0
        made_s = 0.0
        gaps = 0
        need = max(0.0, PREBUFFER_S - self.player.queued_seconds())  # earlier speech still playing counts as buffer
        for arr in self._clean(self._pieces(text)):
            pcm = arr.tobytes()
            made_s += len(pcm) / (2.0 * self.sr)
            if not started:
                held.append(pcm)
                held_s += len(pcm) / (2.0 * self.sr)
                if held_s >= need:
                    for p in held:
                        self.player.write(p)
                    started = True
                    emit(event="first_audio", id=job_id, at=time.time(), after_received_s=round(time.time() - received_at, 3),
                         after_start_s=round(time.monotonic() - t0, 3), still_playing_s=round(self.player.queued_seconds(), 2))
                continue
            if self.player.queued_seconds() <= 0.0:
                gaps += 1
            self.player.write(pcm)
        if not started and held:
            for p in held:
                self.player.write(p)
            emit(event="first_audio", id=job_id, at=time.time(), after_received_s=round(time.time() - received_at, 3),
                 after_start_s=round(time.monotonic() - t0, 3))
        # the next sentence may follow at once; the mic stays closed until playback ends
        emit(event="generated", id=job_id, audio_s=round(made_s, 2), took_s=round(time.monotonic() - t0, 2), gaps=gaps)

    def listen(self, job_id: int) -> None:
        from voice import winaudio
        if self.stt is None:
            emit(event="heard", id=job_id, text="", reason="speech recognition unavailable")
            return
        self.player.drain()
        end = time.monotonic() + LISTEN_WAIT_S
        while not winaudio.key_down():
            if time.monotonic() > end:
                emit(event="heard", id=job_id, text="", reason="no key press")
                return
            time.sleep(0.02)
        rec = winaudio.Recorder()
        rec.start()
        try:
            t_end = time.monotonic() + LISTEN_MAX_S
            while winaudio.key_down() and time.monotonic() < t_end:
                rec.poll()
                time.sleep(0.02)
        finally:
            pcm = rec.stop()
        seconds = len(pcm) / (2.0 * rec.RATE)
        if seconds < MIN_SPEECH_S:
            emit(event="heard", id=job_id, text="", reason="too short", audio_s=round(seconds, 2))
            return
        audio = self.np.frombuffer(pcm, dtype=self.np.int16).astype(self.np.float32) / 32768.0
        self.transcribe(job_id, audio, seconds)

    def transcribe(self, job_id: int, audio, seconds: float) -> None:
        t0 = time.monotonic()
        segments, _ = self.stt.transcribe(audio, language="en", beam_size=1, vad_filter=False, condition_on_previous_text=False)
        text = " ".join(s.text.strip() for s in segments).strip()
        emit(event="heard", id=job_id, text=text, audio_s=round(seconds, 2), stt_s=round(time.monotonic() - t0, 2))

    def run_jobs(self) -> None:
        while True:
            job = self.jobs.get()
            try:
                cmd = job["cmd"]
                if cmd == "quit":
                    self.player.drain()
                    return
                if cmd == "say":
                    self.say(job["id"], str(job["text"])[:2000], job["received_at"])
                elif cmd == "listen":
                    self.listen(job["id"])
                elif cmd == "wait":
                    self.player.drain()
                    emit(event="spoken", id=job["id"])
                elif cmd == "hear_file" and self.stt is None:
                    emit(event="heard", id=job["id"], text="", reason="speech recognition unavailable")
                elif cmd == "hear_file":  # test hook: transcribe a WAV file given by path (no microphone)
                    import soundfile
                    data, rate = soundfile.read(job["path"], dtype="float32")
                    if data.ndim > 1:
                        data = data.mean(axis=1)
                    if rate != 16000:
                        import scipy.signal
                        data = scipy.signal.resample_poly(data, 16000, rate).astype("float32")
                    self.transcribe(job["id"], data, len(data) / 16000.0)
            except Exception as exc:  # report, keep running
                emit(event="error", id=job.get("id"), error=type(exc).__name__ + ": " + str(exc)[:200])

    def main(self) -> int:
        try:
            self.load()
        except Exception as exc:
            emit(event="error", id=None, error="load failed: " + type(exc).__name__ + ": " + str(exc)[:200])
            return 2
        emit(event="ready", sample_rate=self.sr, stt=self.stt is not None, stt_problem=self.stt_problem)
        t = threading.Thread(target=self.run_jobs, daemon=True)
        t.start()
        for line in sys.stdin:
            try:
                job = json.loads(line)
                if not isinstance(job, dict) or job.get("cmd") not in ("say", "listen", "quit", "wait", "hear_file"):
                    raise ValueError("unknown command")
                job["received_at"] = time.time()
                self.jobs.put(job)
                if job["cmd"] == "quit":
                    break
            except ValueError as exc:
                emit(event="error", id=None, error=str(exc))
        t.join(timeout=120)
        self.player.close()
        return 0

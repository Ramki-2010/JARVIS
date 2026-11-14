"""The voice worker: reads JSON lines on stdin, writes JSON lines on stdout.

Commands in:  {"cmd":"say","id":N,"text":"..."}  {"cmd":"listen","id":N}  {"cmd":"quit"}
              {"cmd":"listen","id":N,"hold":"button"}  {"cmd":"mic_stop","target":N}   (a dashboard button instead of the key; ADR-0011 Amendment 3)
Events out:   ready, first_audio, spoken, heard, error (each a JSON object with "event").

Speech out: the cloned voice (VoxCPM2, one cached prompt made from RK's local
sample) is generated in small pieces and played as they are made. Speech in: the
microphone is open only while the push-to-talk key (or, for a button-held listen, the button) is held, and is closed while
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

from voice.holds import Holds

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
        self.holds = Holds()
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
        from voice.livestate import LiveState
        self.live = LiveState(self.root)
        self.live.start()
        for _ in self._pieces("Good evening, sir."):  # warm-up; discarded
            pass
        # Speech in is optional: if its libraries cannot load (for example Windows Smart App Control blocks a
        # compiled file), the voice still speaks and the keyboard still works.
        # The engine built on torch is preferred: it adds no compiled library of its own, so Smart App Control
        # has nothing new to block. The older engine (ctranslate2) is only a fallback.
        problems = []
        for loader in (self._load_torch_stt, self._load_ct2_stt):
            try:
                self.stt = loader()
                self.stt_problem = ""
                return
            except Exception as exc:
                self.stt = None
                root = exc
                while (root.__cause__ or root.__context__) is not None:  # report the deepest cause, not the wrapper
                    root = root.__cause__ or root.__context__
                problems.append(type(root).__name__ + ": " + str(root)[:160])
        self.stt_problem = " | ".join(problems)

    def _load_torch_stt(self):
        """Whisper through transformers and torch. The model file must match its recorded SHA-256."""
        spec = self.cfg.get("stt") or {}
        if not spec.get("dir") or not spec.get("sha256"):
            raise RuntimeError("no speech-recognition model is recorded in voice_settings.json")
        path = os.path.join(self.root, spec["dir"])
        if sha256(os.path.join(path, "model.safetensors")) != spec["sha256"]:
            raise RuntimeError("the speech-recognition model does not match its record; not loading it")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
        torch = self.torch
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        proc = WhisperProcessor.from_pretrained(path, local_files_only=True)
        model = WhisperForConditionalGeneration.from_pretrained(
            path, local_files_only=True, torch_dtype=torch.float16 if dev == "cuda" else torch.float32).to(dev).eval()

        def run(audio) -> str:
            feats = proc(audio, sampling_rate=16000, return_tensors="pt").input_features.to(dev, model.dtype)
            with torch.no_grad():
                ids = model.generate(feats, max_new_tokens=128)
            return proc.batch_decode(ids, skip_special_tokens=True)[0].strip()

        run(self.np.zeros(16000, dtype=self.np.float32))  # warm-up; discarded
        return run

    def _load_ct2_stt(self):
        from faster_whisper import WhisperModel
        model = WhisperModel(os.path.join(self.root, "models", "whisper", "small.en"), device="cpu", compute_type="int8")

        def run(audio) -> str:
            segments, _ = model.transcribe(audio, language="en", beam_size=1, vad_filter=False, condition_on_previous_text=False)
            return " ".join(s.text.strip() for s in segments).strip()

        return run

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

    def _play(self, pcm: bytes) -> None:
        self.player.write(pcm)
        self.live.audio_queued(self.player.queued_seconds())   # the speaker really has this audio queued now

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
                        self._play(p)
                    started = True
                    emit(event="first_audio", id=job_id, at=time.time(), after_received_s=round(time.time() - received_at, 3),
                         after_start_s=round(time.monotonic() - t0, 3), still_playing_s=round(self.player.queued_seconds(), 2))
                continue
            if self.player.queued_seconds() <= 0.0:
                gaps += 1
            self._play(pcm)
        if not started and held:
            for p in held:
                self._play(p)
            emit(event="first_audio", id=job_id, at=time.time(), after_received_s=round(time.time() - received_at, 3),
                 after_start_s=round(time.monotonic() - t0, 3))
        # the next sentence may follow at once; the mic stays closed until playback ends
        emit(event="generated", id=job_id, audio_s=round(made_s, 2), took_s=round(time.monotonic() - t0, 2), gaps=gaps)

    def listen(self, job_id: int, hold: str = "key") -> None:
        from voice import winaudio
        if self.stt is None:
            emit(event="heard", id=job_id, text="", reason="speech recognition unavailable")
            return
        self.player.drain()
        if hold == "button":   # the dashboard button is the key: held until "mic_stop" names this job
            held = lambda: not self.holds.released(job_id)
            if not held():     # released before the microphone was ever opened: it is not opened
                emit(event="heard", id=job_id, text="", reason="released before listening")
                return
        else:
            held = winaudio.key_down
            end = time.monotonic() + LISTEN_WAIT_S
            while not held():
                if time.monotonic() > end:
                    emit(event="heard", id=job_id, text="", reason="no key press")
                    return
                time.sleep(0.02)
        rec = winaudio.Recorder()
        rec.start()
        self.live.mic_open(True)   # the microphone really is open now
        try:
            t_end = time.monotonic() + LISTEN_MAX_S
            while held() and time.monotonic() < t_end:
                rec.poll()
                time.sleep(0.02)
        finally:
            pcm = rec.stop()
            self.live.mic_open(False)
        seconds = len(pcm) / (2.0 * rec.RATE)
        if seconds < MIN_SPEECH_S:
            emit(event="heard", id=job_id, text="", reason="too short", audio_s=round(seconds, 2))
            return
        audio = self.np.frombuffer(pcm, dtype=self.np.int16).astype(self.np.float32) / 32768.0
        self.transcribe(job_id, audio, seconds)

    def transcribe(self, job_id: int, audio, seconds: float) -> None:
        t0 = time.monotonic()
        text = self.stt(audio)
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
                    self.listen(job["id"], job.get("hold", "key"))
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
                if not isinstance(job, dict) or job.get("cmd") not in ("say", "listen", "quit", "wait", "hear_file", "mic_stop"):
                    raise ValueError("unknown command")
                if job["cmd"] == "mic_stop":   # handled at once, never queued behind the listen it ends
                    if isinstance(job.get("target"), int):
                        self.holds.release(job["target"])
                    continue
                if job.get("hold", "key") not in ("key", "button"):
                    raise ValueError("unknown hold")
                job["received_at"] = time.time()
                self.jobs.put(job)
                if job["cmd"] == "quit":
                    break
            except ValueError as exc:
                emit(event="error", id=None, error=str(exc))
        t.join(timeout=120)
        self.player.close()
        self.live.stop()
        return 0

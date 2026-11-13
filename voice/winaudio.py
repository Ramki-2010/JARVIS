"""Local audio through Windows' own winmm library (ctypes). No third-party audio package.

`Player` plays 16-bit mono PCM as a gapless queue of small buffers, so speech can
start while later pieces are still being made. `Recorder` captures 16 kHz mono
audio from the default microphone only while it is open. `key_down` reads a
key's state for push-to-talk. Windows only.
"""

import ctypes
import time
from ctypes import wintypes
from typing import List, Tuple

WAVE_MAPPER = 0xFFFFFFFF
WHDR_DONE = 0x1
WAVE_FORMAT_PCM = 1
VK_RCONTROL = 0xA3

winmm = ctypes.WinDLL("winmm")
user32 = ctypes.WinDLL("user32")


class WAVEFORMATEX(ctypes.Structure):
    _fields_ = [("wFormatTag", wintypes.WORD), ("nChannels", wintypes.WORD), ("nSamplesPerSec", wintypes.DWORD),
                ("nAvgBytesPerSec", wintypes.DWORD), ("nBlockAlign", wintypes.WORD),
                ("wBitsPerSample", wintypes.WORD), ("cbSize", wintypes.WORD)]


class WAVEHDR(ctypes.Structure):
    pass


WAVEHDR._fields_ = [("lpData", ctypes.c_void_p), ("dwBufferLength", wintypes.DWORD), ("dwBytesRecorded", wintypes.DWORD),
                    ("dwUser", ctypes.c_size_t), ("dwFlags", wintypes.DWORD), ("dwLoops", wintypes.DWORD),
                    ("lpNext", ctypes.c_void_p), ("reserved", ctypes.c_size_t)]

_HDR_SIZE = ctypes.sizeof(WAVEHDR)
_P_HDR = ctypes.POINTER(WAVEHDR)
_P_FMT = ctypes.POINTER(WAVEFORMATEX)
_P_H = ctypes.POINTER(ctypes.c_void_p)

for _name in ("waveOutOpen", "waveInOpen"):
    _f = getattr(winmm, _name)
    _f.argtypes = [_P_H, ctypes.c_uint, _P_FMT, ctypes.c_size_t, ctypes.c_size_t, wintypes.DWORD]
    _f.restype = ctypes.c_uint
for _name in ("waveOutPrepareHeader", "waveOutUnprepareHeader", "waveOutWrite",
              "waveInPrepareHeader", "waveInUnprepareHeader", "waveInAddBuffer"):
    _f = getattr(winmm, _name)
    _f.argtypes = [ctypes.c_void_p, _P_HDR, ctypes.c_uint]
    _f.restype = ctypes.c_uint
for _name in ("waveOutReset", "waveOutClose", "waveInStart", "waveInStop", "waveInReset", "waveInClose"):
    _f = getattr(winmm, _name)
    _f.argtypes = [ctypes.c_void_p]
    _f.restype = ctypes.c_uint
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short


class AudioError(Exception):
    pass


def _check(code: int, what: str) -> None:
    if code != 0:
        raise AudioError("%s failed (winmm code %d)" % (what, code))


def _format(rate: int) -> WAVEFORMATEX:
    return WAVEFORMATEX(WAVE_FORMAT_PCM, 1, rate, rate * 2, 2, 16, 0)


def key_down(vk: int = VK_RCONTROL) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


class Player:
    def __init__(self, rate: int):
        self.rate = rate
        self._h = ctypes.c_void_p()
        self._fmt = _format(rate)
        _check(winmm.waveOutOpen(ctypes.byref(self._h), WAVE_MAPPER, ctypes.byref(self._fmt), 0, 0, 0), "open the speaker")
        self._live: List[Tuple[ctypes.Array, WAVEHDR]] = []

    def _reap(self) -> None:
        keep = []
        for buf, hdr in self._live:
            if hdr.dwFlags & WHDR_DONE:
                winmm.waveOutUnprepareHeader(self._h, ctypes.byref(hdr), _HDR_SIZE)
            else:
                keep.append((buf, hdr))
        self._live = keep

    def write(self, pcm16: bytes) -> None:
        if not pcm16:
            return
        self._reap()
        buf = ctypes.create_string_buffer(pcm16, len(pcm16))
        hdr = WAVEHDR()
        hdr.lpData = ctypes.cast(buf, ctypes.c_void_p).value
        hdr.dwBufferLength = len(pcm16)
        _check(winmm.waveOutPrepareHeader(self._h, ctypes.byref(hdr), _HDR_SIZE), "prepare audio")
        _check(winmm.waveOutWrite(self._h, ctypes.byref(hdr), _HDR_SIZE), "play audio")
        self._live.append((buf, hdr))

    def queued_seconds(self) -> float:
        self._reap()
        return sum(h.dwBufferLength for _, h in self._live) / (2.0 * self.rate)

    def drain(self, timeout: float = 60.0) -> None:
        end = time.monotonic() + timeout
        while self.queued_seconds() > 0 and time.monotonic() < end:
            time.sleep(0.02)

    def close(self) -> None:
        winmm.waveOutReset(self._h)
        self._reap()
        winmm.waveOutClose(self._h)


class Recorder:
    """Records from the default microphone between `start()` and `stop()`; keeps audio in memory only."""
    RATE = 16000
    BUFFERS = 8
    BUF_MS = 100

    def __init__(self):
        self._h = ctypes.c_void_p()
        self._fmt = _format(self.RATE)
        self._size = self.RATE * 2 * self.BUF_MS // 1000
        self._bufs = []
        self._chunks: List[bytes] = []
        self._open = False

    def start(self) -> None:
        _check(winmm.waveInOpen(ctypes.byref(self._h), WAVE_MAPPER, ctypes.byref(self._fmt), 0, 0, 0), "open the microphone")
        self._open = True
        for _ in range(self.BUFFERS):
            buf = ctypes.create_string_buffer(self._size)
            hdr = WAVEHDR()
            hdr.lpData = ctypes.cast(buf, ctypes.c_void_p).value
            hdr.dwBufferLength = self._size
            _check(winmm.waveInPrepareHeader(self._h, ctypes.byref(hdr), _HDR_SIZE), "prepare the microphone")
            _check(winmm.waveInAddBuffer(self._h, ctypes.byref(hdr), _HDR_SIZE), "queue the microphone")
            self._bufs.append((buf, hdr))
        _check(winmm.waveInStart(self._h), "start the microphone")

    def poll(self) -> None:
        """Collect finished buffers in the order they were queued, and queue them again."""
        while self._bufs and self._bufs[0][1].dwFlags & WHDR_DONE:
            buf, hdr = self._bufs.pop(0)
            self._chunks.append(buf.raw[:hdr.dwBytesRecorded])
            winmm.waveInUnprepareHeader(self._h, ctypes.byref(hdr), _HDR_SIZE)
            hdr.dwFlags = 0
            hdr.dwBytesRecorded = 0
            winmm.waveInPrepareHeader(self._h, ctypes.byref(hdr), _HDR_SIZE)
            winmm.waveInAddBuffer(self._h, ctypes.byref(hdr), _HDR_SIZE)
            self._bufs.append((buf, hdr))

    def stop(self) -> bytes:
        if not self._open:
            return b""
        winmm.waveInStop(self._h)
        winmm.waveInReset(self._h)  # returns every queued buffer, with what it holds so far
        for buf, hdr in self._bufs:
            if hdr.dwFlags & WHDR_DONE:
                self._chunks.append(buf.raw[:hdr.dwBytesRecorded])
            winmm.waveInUnprepareHeader(self._h, ctypes.byref(hdr), _HDR_SIZE)
        winmm.waveInClose(self._h)
        self._open = False
        data = b"".join(self._chunks)
        self._chunks, self._bufs = [], []
        return data

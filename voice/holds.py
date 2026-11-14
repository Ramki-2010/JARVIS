"""Which button-held listens have been released (ADR-0011 Amendment 3).

A dashboard microphone button asks the worker to listen on a job id and later says "release job N". The release
can arrive before the worker has even started that job (a quick tap), so it is remembered by job id and checked
before the microphone is opened as well as while it is open. Plain data: no audio, no text, bounded.
"""

import threading

KEEP = 64


class Holds:
    def __init__(self):
        self._lock = threading.Lock()
        self._released = []

    def release(self, job_id) -> None:
        with self._lock:
            if job_id not in self._released:
                self._released.append(job_id)
                del self._released[:-KEEP]

    def released(self, job_id) -> bool:
        with self._lock:
            return job_id in self._released

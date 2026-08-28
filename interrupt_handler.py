import queue
import threading
from shared_types import Command


class InterruptHandler:
    def __init__(self,
                 in_queue: queue.Queue,
                 out_queue: queue.Queue,
                 priority_queue: queue.Queue,
                 restart_queue: queue.Queue,
                 stop_words: list[str],
                 restart_words: list[str]):
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.priority_queue = priority_queue
        self.restart_queue = restart_queue
        self.stop_words = stop_words
        self.restart_words = restart_words
        self._running = threading.Event()
        self._thread = None

    def start(self):
        self._running.set()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _loop(self):
        while self._running.is_set():
            try:
                phrase = self.in_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            text = phrase.text.lower().strip()
            if any(word in text for word in self.stop_words):
                cmd = Command(action="EMERGENCY_STOP", params={}, source="interrupt")
                self.priority_queue.put(cmd)
                continue
            if any(word in text for word in self.restart_words):
                cmd = Command(action="RESTART_LEVEL", params={}, source="interrupt")
                self.restart_queue.put(cmd)
                continue
            self.out_queue.put(phrase)
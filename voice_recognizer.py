import json
import time
import queue
import threading
import sounddevice as sd

from shared_types import RecognizedPhrase
from vosk import Model, KaldiRecognizer, SetLogLevel
SetLogLevel(-1)


class VoiceRecognizer:
    def __init__(self, out_queue: queue.Queue,
                 model_path: str = "vosk-model-small-ru-0.22",
                 sample_rate: int = 16000, device: int = None,
                 blocksize: int = 4000):
        self.out_queue = out_queue
        self.sample_rate = sample_rate
        self.device = device
        self.blocksize = blocksize
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
        self.recognizer.SetWords(False)
        self._listening = threading.Event()
        self._running = threading.Event()
        self._lock = threading.Lock()
        self._stream = None
        self._thread = None

    def start(self):
        self._running.set()
        self._stream = sd.RawInputStream(
            device=self.device,
            samplerate=self.sample_rate,
            channels=1,
            dtype='int16',
            blocksize=self.blocksize,
            callback=self._audio_callback
        )
        self._stream.start()
        self._thread = threading.Thread(target=self._keep_alive, daemon=True)
        self._thread.start()

    def stop(self):
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._stream:
            self._stream.stop()
            self._stream.close()

    def enable(self):
        with self._lock:
            self.recognizer.Reset()
        self._listening.set()

    def disable(self):
        self._listening.clear()
        with self._lock:
            final = json.loads(self.recognizer.FinalResult())
            text = final.get("text", "").strip()
            if text:
                phrase = RecognizedPhrase(text=text, timestamp=time.time())
                self.out_queue.put(phrase)

    def _audio_callback(self, indata, _frames, _time_info, status):
        if status or not self._listening.is_set():
            return
        with self._lock:
            if self.recognizer.AcceptWaveform(bytes(indata)):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    phrase = RecognizedPhrase(text=text, timestamp=time.time())
                    self.out_queue.put(phrase)

    def _keep_alive(self):
        while self._running.is_set():
            time.sleep(0.1)
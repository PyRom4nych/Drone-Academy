import base64
import io

import mss
from PIL import Image


class ScreenCapture:
    def __init__(self, monitor: int = 0, quality: int = 80):
        self.monitor = monitor
        self.quality = quality
        self._sct = mss.mss()

    def capture(self) -> str:
        monitor = self._sct.monitors[self.monitor]
        screenshot = self._sct.grab(monitor)
        image = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=self.quality)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
import asyncio
import queue
import threading
import logging
import time

from voice_recognizer import VoiceRecognizer
from interrupt_handler import InterruptHandler
from intent_parser import IntentParser
from screen_capture import ScreenCapture
from ai_client import AIClient
from command_mapper import CommandMapper
from control_layer import ControlLayer
from text_corrector import TextCorrector
from shared_types import RecognizedPhrase, Command

logger = logging.getLogger("Orchestrator")


class Orchestrator:
    def __init__(self,
                 recognizer: VoiceRecognizer,
                 interrupt_handler: InterruptHandler,
                 intent_parser: IntentParser,
                 screen_capture: ScreenCapture,
                 ai_client: AIClient,
                 command_mapper: CommandMapper,
                 control_layer: ControlLayer,
                 dispatch_queue: queue.Queue,
                 priority_queue: queue.Queue,
                 restart_queue: queue.Queue,
                 text_corrector: TextCorrector):
        self.recognizer = recognizer
        self.interrupt_handler = interrupt_handler
        self.intent_parser = intent_parser
        self.screen_capture = screen_capture
        self.ai_client = ai_client
        self.command_mapper = command_mapper
        self.control_layer = control_layer
        self.dispatch_queue = dispatch_queue
        self.priority_queue = priority_queue
        self.restart_queue = restart_queue
        self.text_corrector = text_corrector
        self._running = threading.Event()

    def run(self):
        self._running.set()
        self.recognizer.start()
        self.interrupt_handler.start()
        self.control_layer.start()
        logger.info("All modules started")

        while self._running.is_set():
            try:
                raw_phrase = self.dispatch_queue.get(timeout=0.2)
            except queue.Empty:
                self._check_restart()
                continue

            corrected_text = self.text_corrector.correct(raw_phrase.text)
            if corrected_text != raw_phrase.text:
                print(f"Corrected: '{raw_phrase.text}' -> '{corrected_text}'")
                phrase = RecognizedPhrase(text=corrected_text, timestamp=raw_phrase.timestamp)
            else:
                phrase = raw_phrase

            print(f"Recognized: {phrase.text}")
            cmd = self.intent_parser.parse(phrase)
            if cmd:
                print(f"Action: {cmd.action} {cmd.params}")
                button_cmd = self.command_mapper.map_button(cmd)
                if button_cmd:
                    self.control_layer.press_button(button_cmd.button, button_cmd.duration)
                else:
                    state = self.command_mapper.map(cmd)
                    self.control_layer.set_target(state)
            else:
                print("Not recognized locally, querying AI...")
                screenshot = self.screen_capture.capture()
                try:
                    ai_commands = asyncio.run(self.ai_client.query(phrase.text, screenshot))
                except Exception as e:
                    logger.error(f"AI query failed: {e}")
                    ai_commands = None

                if ai_commands:
                    print(f"AI returned {len(ai_commands)} command(s)")
                    self._execute_sequence(ai_commands)
                else:
                    print("AI failed, falling back to HOVER")
                    hover = Command(action="HOVER", params={}, source="fallback")
                    state = self.command_mapper.map(hover)
                    self.control_layer.set_target(state)

    def stop(self):
        self._running.clear()
        self.interrupt_handler.stop()
        self.control_layer.stop()
        self.recognizer.stop()
        logger.info("All modules stopped")

    def _check_restart(self):
        try:
            cmd = self.restart_queue.get_nowait()
            if cmd.action == "RESTART_LEVEL":
                logger.info("Restart command received")
                self.control_layer.emergency_stop()
        except queue.Empty:
            pass

    def _execute_sequence(self, commands: list):
        for cmd in commands:
            if not self._running.is_set():
                break
            if self._check_priority_abort():
                print("Sequence aborted by EMERGENCY_STOP")
                break

            print(f"Step: {cmd.action} {cmd.params}")

            button_cmd = self.command_mapper.map_button(cmd)
            if button_cmd:
                self.control_layer.press_button(button_cmd.button, button_cmd.duration)
                time.sleep(button_cmd.duration)
                continue

            state = self.command_mapper.map(cmd)
            duration = state.duration

            if duration <= 0 and cmd.action not in ("HOVER", "EMERGENCY_STOP"):
                duration = 2.0
                state.duration = duration

            self.control_layer.set_target(state)

            if duration > 0:
                deadline = time.monotonic() + duration
                while time.monotonic() < deadline:
                    if self._check_priority_abort():
                        self.control_layer.emergency_stop()
                        return
                    time.sleep(0.05)
            else:
                time.sleep(0.1)

    def _check_priority_abort(self) -> bool:
        try:
            prio_cmd = self.priority_queue.get_nowait()
            if prio_cmd.action == "EMERGENCY_STOP":
                self.control_layer.emergency_stop()
                return True
        except queue.Empty:
            pass
        return False
import sys
import threading
import queue
import logging

import keyboard

from config import Config
from voice_recognizer import VoiceRecognizer
from interrupt_handler import InterruptHandler
from intent_parser import IntentParser
from screen_capture import ScreenCapture
from ai_client import AIClient
from command_mapper import CommandMapper
from control_layer import ControlLayer
from orchestrator import Orchestrator
from text_corrector import TextCorrector

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger("Main")


def main():
    try:
        config = Config("config.yaml")
    except Exception as e:
        logger.error(f"Не удалось загрузить конфиг: {e}")
        sys.exit(1)

    phrase_queue = queue.Queue()
    dispatch_queue = queue.Queue()
    priority_queue = queue.Queue()
    restart_queue = queue.Queue()

    recognizer = VoiceRecognizer(
        out_queue=phrase_queue,
        model_path="vosk-model-small-ru-0.22"
    )
    interrupt_handler = InterruptHandler(
        in_queue=phrase_queue,
        out_queue=dispatch_queue,
        priority_queue=priority_queue,
        restart_queue=restart_queue,
        stop_words=config.stop_words,
        restart_words=config.restart_words
    )
    intent_parser = IntentParser(
        intent_phrases=config.intent_phrases,
        threshold=config.intent_threshold,
        default_params=config.default_params
    )
    screen_capture = ScreenCapture()
    ai_client = AIClient(
        url=config.ai_url,
        model=config.ai_model,
        system_prompt=config.ai_system_prompt
    )
    command_mapper = CommandMapper(config.command_map)
    control_layer = ControlLayer(config, priority_queue)
    text_corrector = TextCorrector(config)

    orchestrator = Orchestrator(
        recognizer=recognizer,
        interrupt_handler=interrupt_handler,
        intent_parser=intent_parser,
        screen_capture=screen_capture,
        ai_client=ai_client,
        command_mapper=command_mapper,
        control_layer=control_layer,
        dispatch_queue=dispatch_queue,
        priority_queue=priority_queue,
        restart_queue=restart_queue,
        text_corrector=text_corrector
    )

    recognizer.start()
    recognizer.enable()
    print("Микрофон включён. Говорите команды.")
    control_layer.start()
    orch_thread = threading.Thread(target=orchestrator.run, daemon=True)
    orch_thread.start()

    muted = False

    def toggle_mute():
        nonlocal muted
        muted = not muted
        if muted:
            recognizer.disable()
            print("Микрофон выключен.")
        else:
            recognizer.enable()
            print("Микрофон включён.")

    keyboard.on_press_key('f8', lambda _: toggle_mute(), suppress=False)
    print("F8 — заглушить/включить микрофон. F10 — выход.")

    try:
        keyboard.wait('f10')
    except KeyboardInterrupt:
        pass
    finally:
        print("Завершение работы...")
        keyboard.unhook_all()
        orchestrator.stop()
        orch_thread.join(timeout=2.0)
        control_layer.stop()
        recognizer.stop()
        print("Программа остановлена.")


if __name__ == "__main__":
    main()
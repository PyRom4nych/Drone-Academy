import yaml
from pathlib import Path


class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self._path = Path(config_path)
        if not self._path.exists():
            raise FileNotFoundError(f"Config file not found: {self._path}")
        with open(self._path, 'r', encoding='utf-8') as f:
            self._data = yaml.safe_load(f)
        self._validate()
        self._build()

    def _validate(self):
        required_top = [
            'stop_words',
            'restart_words',
            'intent_phrases',
            'intent_threshold',
            'control_loop_hz',
            'command_map',
            'ai'
        ]
        for key in required_top:
            if key not in self._data:
                raise KeyError(f"Missing required config key: {key}")
        if not isinstance(self._data['stop_words'], list):
            raise TypeError("stop_words must be a list")
        if not isinstance(self._data['restart_words'], list):
            raise TypeError("restart_words must be a list")
        if not isinstance(self._data['intent_phrases'], dict):
            raise TypeError("intent_phrases must be a dict")
        for action, phrases in self._data['intent_phrases'].items():
            if not isinstance(phrases, list):
                raise TypeError(f"intent_phrases.{action} must be a list")
        if not isinstance(self._data['intent_threshold'], (int, float)):
            raise TypeError("intent_threshold must be a number")
        if not isinstance(self._data['control_loop_hz'], int):
            raise TypeError("control_loop_hz must be an integer")
        if not isinstance(self._data['command_map'], dict):
            raise TypeError("command_map must be a dict")
        ai_keys = ['url', 'model', 'system_prompt']
        if not all(k in self._data['ai'] for k in ai_keys):
            raise KeyError(f"ai section must contain {ai_keys}")

    def _build(self):
        self.stop_words = self._data['stop_words']
        self.restart_words = self._data['restart_words']
        self.intent_phrases = self._data['intent_phrases']
        self.intent_threshold = self._data['intent_threshold']
        self.control_loop_hz = self._data['control_loop_hz']
        self.command_map = self._data['command_map']
        self.ai_url = self._data['ai']['url']
        self.ai_model = self._data['ai']['model']
        self.ai_system_prompt = self._data['ai']['system_prompt']

    @property
    def default_params(self) -> dict[str, dict]:
        params = {}
        for action, mapping in self.command_map.items():
            params[action] = dict(mapping)
        return params
import re
from typing import Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from shared_types import RecognizedPhrase, Command


class IntentParser:
    _NUM_WORDS = {
        "ноль": 0, "один": 1, "одна": 1, "одну": 1, "два": 2, "две": 2,
        "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7,
        "восемь": 8, "девять": 9, "десять": 10, "одиннадцать": 11,
        "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14,
        "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17,
        "восемнадцать": 18, "девятнадцать": 19, "двадцать": 20,
        "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60,
        "семьдесят": 70, "восемьдесят": 80, "девяносто": 90,
        "сто": 100, "полторы": 1.5, "полтора": 1.5, "полсекунды": 0.5
    }

    def __init__(self,
                 intent_phrases: dict[str, list[str]],
                 threshold: float = 0.75,
                 default_params: dict[str, dict] = None):
        self.intent_phrases = intent_phrases
        self.threshold = threshold
        self.default_params = default_params or {}
        self._model = SentenceTransformer('all-MiniLM-L6-v2')
        self._embeddings, self._actions = self._build_index()

    def _build_index(self):
        embeddings = []
        actions = []
        for action, phrases in self.intent_phrases.items():
            for phrase in phrases:
                emb = self._model.encode(phrase, normalize_embeddings=True)
                embeddings.append(emb)
                actions.append(action)
        return np.stack(embeddings), actions

    def parse(self, phrase: RecognizedPhrase) -> Optional[Command]:
        text = phrase.text.lower().strip()
        emb = self._model.encode(text, normalize_embeddings=True)
        scores = np.dot(self._embeddings, emb)
        max_idx = int(np.argmax(scores))
        max_score = float(scores[max_idx])
        if max_score < self.threshold:
            return None
        action = self._actions[max_idx]
        params = self._extract_params(text, action)
        return Command(action=action, params=params, source="intent_parser")

    def _extract_params(self, text: str, action: str) -> dict:
        defaults = self.default_params.get(action, {}).copy()

        duration = self._extract_duration(text)
        if duration is not None:
            defaults['duration'] = duration

        angle = self._extract_angle(text)
        if angle is not None:
            defaults['angle'] = angle

        distance = self._extract_distance(text)
        if distance is not None:
            defaults['distance'] = distance

        intensity = self._extract_intensity(text)
        if intensity is not None:
            defaults['intensity'] = intensity

        return defaults

    @classmethod
    def _words_to_int(cls, phrase: str) -> Optional[float]:
        num_match = re.search(r'(\d+[.,]?\d*)', phrase)
        if num_match:
            return float(num_match.group(1).replace(',', '.'))

        words = phrase.split()
        total = 0
        current = 0
        for word in words:
            if word in cls._NUM_WORDS:
                val = cls._NUM_WORDS[word]
                if val in (100, ):  # сотни
                    if current == 0:
                        current = 1
                    current *= val
                elif val >= 20:
                    total += current
                    current = val
                else:
                    if current >= 20:
                        total += current + val
                        current = 0
                    else:
                        current += val
            else:
                if current:
                    total += current
                    current = 0
        total += current
        if total > 0:
            return float(total)
        return None

    @classmethod
    def _extract_duration(cls, text: str) -> Optional[float]:
        patterns = [
            r'(\d+[\.,]?\d*)\s*секунд',
            r'(\d+[\.,]?\d*)\s*сек',
            r'(\d+[\.,]?\d*)\s*с\b',
            r'на\s+(\d+[\.,]?\d*)\s*секунд',
            r'((?:[а-яё]+\s+){0,3}секунд)',
            r'полсекунды'
        ]
        for pat in patterns:
            match = re.search(pat, text)
            if match:
                group = match.group(1)
                if group.isdigit():
                    return float(group)
                num = cls._words_to_int(group)
                if num is not None:
                    return num
        if 'полторы секунды' in text or 'полтора секунды' in text:
            return 1.5
        return None

    @classmethod
    def _extract_angle(cls, text: str) -> Optional[float]:
        patterns = [
            r'на\s+(\d+[\.,]?\d*)\s*градус',
            r'(\d+[\.,]?\d*)\s*градус',
            r'((?:[а-яё]+\s+){0,2}градус)',
        ]
        for pat in patterns:
            match = re.search(pat, text)
            if match:
                group = match.group(1)
                if group.isdigit():
                    return float(group)
                num = cls._words_to_int(group)
                if num is not None:
                    return num
        return None

    @staticmethod
    def _extract_distance(text: str) -> Optional[float]:
        patterns = [
            r'на\s+(\d+[\.,]?\d*)\s*метр',
            r'(\d+[\.,]?\d*)\s*м\b',
            r'(\d+[\.,]?\d*)\s*метр',
        ]
        for pat in patterns:
            match = re.search(pat, text)
            if match:
                return float(match.group(1).replace(',', '.'))
        return None

    @staticmethod
    def _extract_intensity(text: str) -> Optional[float]:
        patterns = [
            r'на\s+(\d+[\.,]?\d*)\s*процент',
            r'(\d+[\.,]?\d*)\s*%',
            r'силу\s+(\d+[\.,]?\d*)',
            r'мощность\s+(\d+[\.,]?\d*)',
        ]
        for pat in patterns:
            match = re.search(pat, text)
            if match:
                val = float(match.group(1).replace(',', '.'))
                return val / 100.0 if val > 1 else val
        return None
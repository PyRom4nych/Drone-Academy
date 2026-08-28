class TextCorrector:
    def __init__(self, config):
        self.reference_phrases = []
        for phrases in config.intent_phrases.values():
            self.reference_phrases.extend(phrases)
        self.reference_phrases.extend(config.stop_words)
        self.reference_phrases.extend(config.restart_words)
        self.reference_phrases = sorted(set(self.reference_phrases), key=len, reverse=True)

    def correct(self, text: str) -> str:
        if not text:
            return text
        text_lower = text.lower().strip()
        if text_lower in self.reference_phrases:
            return text_lower

        best_match = None
        best_score = 0.0
        for phrase in self.reference_phrases:
            score = self._similarity(text_lower, phrase)
            if score > best_score:
                best_score = score
                best_match = phrase
        if best_score > 0.7 and best_match:
            return best_match
        return text

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        def get_bigrams(s):
            return set(s[i:i+2] for i in range(len(s)-1))
        a_bigrams = get_bigrams(a)
        b_bigrams = get_bigrams(b)
        if not a_bigrams or not b_bigrams:
            return 0.0
        intersection = a_bigrams & b_bigrams
        return 2.0 * len(intersection) / (len(a_bigrams) + len(b_bigrams))
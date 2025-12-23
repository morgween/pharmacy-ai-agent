"""lightweight safety guard for detecting policy violations in responses"""
import re
from typing import List, Optional, Tuple


class SafetyGuard:
    """Detects potential medical advice, diagnosis, promotional language, or upselling."""

    def __init__(self) -> None:
        # Medical advice patterns - designed to catch personal advice, not label information
        # ALLOWED: "The recommended dose is 500mg" (label info)
        # BLOCKED: "I recommend you take 500mg" (personal advice)
        self._medical_patterns: List[Tuple[re.Pattern[str], str]] = [
            (re.compile(r"\bdiagnos(e|is)\b", re.IGNORECASE), "diagnosis"),
            (re.compile(r"\b(should (I|you) take|you should take|I should take)\b", re.IGNORECASE), "direct advice"),
            # Only catch personal dose recommendations, not label info
            (re.compile(r"\bI recommend( a| your)? dose\b", re.IGNORECASE), "dose recommendation"),
            (re.compile(r"\bincrease (your|the) dose\b", re.IGNORECASE), "dose adjustment"),
            (re.compile(r"\bdouble (your|the) dose\b", re.IGNORECASE), "dose adjustment"),
            # Only catch drug interaction ADVICE, not general info
            (re.compile(r"\b(avoid|don't take).*(interaction|with)\b", re.IGNORECASE), "drug interaction advice"),
            # These patterns catch personal suitability advice
            (re.compile(r"\b(you can|you may|it's safe to)\s+take\b.*\bpregnan(t|cy)\b", re.IGNORECASE), "pregnancy advice"),
            (re.compile(r"\bpregnan(t|cy)\b.*(you can|you may|it's safe to)\s+take\b", re.IGNORECASE), "pregnancy advice"),
            (re.compile(r"\b(you can|you may|it's safe to)\s+take\b.*\bbreastfeed(ing)?\b", re.IGNORECASE), "breastfeeding advice"),
            (re.compile(r"\bbreastfeed(ing)?\b.*(you can|you may|it's safe to)\s+take\b", re.IGNORECASE), "breastfeeding advice"),
            (re.compile(r"\ballerg(y|ies)?\b.*(you can|you may|it's safe to)\s+take\b", re.IGNORECASE), "allergy advice"),
            (re.compile(r"\b(you can|you may|it's safe to)\s+take\b.*\ballerg(y|ies)?\b", re.IGNORECASE), "allergy advice"),
            (re.compile(r"\bsafe for (me|you)\b", re.IGNORECASE), "suitability judgment"),
            (re.compile(r"\b(this|that|it) is better (than|for)\b", re.IGNORECASE), "comparative recommendation"),
            (re.compile(r"\bI recommend( this| that| the)? (medication|medicine)\b", re.IGNORECASE), "medication recommendation"),
            (re.compile(r"\byou (should|need to|must) (start|stop|continue)\b", re.IGNORECASE), "treatment advice"),
            (re.compile(r"\byou (should|can|may) (skip|miss) (a |your )?dose\b", re.IGNORECASE), "dose modification advice"),
        ]

        # Upselling and promotional patterns
        self._upsell_patterns: List[Tuple[re.Pattern[str], str]] = [
            (re.compile(r"\byou should (buy|purchase|get)\b", re.IGNORECASE), "purchase encouragement"),
            (re.compile(r"\bI recommend (buying|purchasing|getting)\b", re.IGNORECASE), "purchase recommendation"),
            (re.compile(r"\b(great|good|best|excellent) (deal|value|price|buy)\b", re.IGNORECASE), "promotional language"),
            (re.compile(r"\b(on sale|limited time|special offer|discount)\b", re.IGNORECASE), "promotional language"),
            (re.compile(r"\b(hurry|act now|don't miss|while supplies last)\b", re.IGNORECASE), "urgency marketing"),
            (re.compile(r"\b(cheaper|more affordable|better value) than\b", re.IGNORECASE), "price comparison"),
            (re.compile(r"\bwhy not (try|get|buy)\b", re.IGNORECASE), "purchase suggestion"),
            (re.compile(r"\byou('ll| will) (love|like|enjoy)\b", re.IGNORECASE), "promotional endorsement"),
        ]

        # Combine all patterns
        self._patterns = self._medical_patterns + self._upsell_patterns

    def check_text(self, text: str) -> Optional[str]:
        """Return the violation reason if any prohibited pattern is detected."""
        for regex, reason in self._patterns:
            if regex.search(text):
                return reason
        return None

    @staticmethod
    def refusal_message(reason: str) -> str:
        """Standard refusal message for safety violations."""
        return (
            "I can't provide medical advice, diagnosis, or recommendations. "
            "Please consult a licensed pharmacist or doctor. "
            f"(request blocked: {reason})."
        )
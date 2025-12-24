"""lightweight safety guard for detecting policy violations in responses"""
import re
from typing import List, Optional, Tuple

from backend.domain.messages import Messages


class SafetyGuard:
    """detects potential medical advice, diagnosis, promotional language, or upselling."""

    def __init__(self) -> None:
        # medical advice patterns - designed to catch personal advice, not label information
        # allowed: "the recommended dose is 500mg" (label info)
        # blocked: "i recommend you take 500mg" (personal advice)
        self._medical_patterns: List[Tuple[re.Pattern[str], str]] = [
            (re.compile(r"\bdiagnos(e|is)\b", re.IGNORECASE), "diagnosis"),
            (re.compile(r"\b(should (I|you) take|you should take|I should take)\b", re.IGNORECASE), "direct advice"),
            # only catch personal dose recommendations, not label info
            (re.compile(r"\bI recommend( a| your)? dose\b", re.IGNORECASE), "dose recommendation"),
            (re.compile(r"\bincrease (your|the) dose\b", re.IGNORECASE), "dose adjustment"),
            (re.compile(r"\bdouble (your|the) dose\b", re.IGNORECASE), "dose adjustment"),
            # only catch drug interaction advice, not general info or label warnings
            (re.compile(r"\b(avoid|don't take).*(interaction)\b", re.IGNORECASE), "drug interaction advice"),
            # these patterns catch personal suitability advice
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
            # hebrew direct advice
            (re.compile(r"(?:אני|אתה|את)\s*(?:ממליץ(?:ה)?|מומלץ|צריך|צריכה|חייב|חייבת)\s*(?:לקחת|ליטול|להשתמש|להתחיל|להפסיק)", re.IGNORECASE), "direct advice"),
            (re.compile(r"(?:ממליץ(?:ה)?|מומלץ)\s*(?:על\s*)?(?:תרופה|תרופות)", re.IGNORECASE), "medication recommendation"),
            (re.compile(r"(?:זה|התרופה)\s*מתאים(?:ה)?\s*(?:לך|לכם)", re.IGNORECASE), "suitability judgment"),
            # russian direct advice
            (re.compile(r"(?:вам|тебе|ты)\s*(?:нужно|следует|стоит|рекомендую|рекомендуется)\s*(?:принимать|использовать|начать|прекратить)", re.IGNORECASE), "direct advice"),
            (re.compile(r"(?:можно|нельзя)\s*(?:принимать|использовать)", re.IGNORECASE), "suitability judgment"),
            (re.compile(r"(?:рекомендую|советую)\s*(?:этот|это)\s*(?:препарат|лекарство)", re.IGNORECASE), "medication recommendation"),
            # arabic direct advice
            (re.compile(r"(?:ينبغي|يجب|أنصح(?:ك)?|من\s+الأفضل)\s*(?:أن\s*)?(?:تأخذ|تتناول|تستخدم|تبدأ|توقف)", re.IGNORECASE), "direct advice"),
            (re.compile(r"(?:هذا|هذه)\s*(?:مناسب|آمن)\s*(?:لك|لكم)", re.IGNORECASE), "suitability judgment"),
            (re.compile(r"(?:أنصح(?:ك)?|أوصي)\s*(?:بهذا|بهذه)\s*(?:الدواء|العلاج)", re.IGNORECASE), "medication recommendation"),
        ]

        # upselling and promotional patterns
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

        # combine all patterns
        self._patterns = self._medical_patterns + self._upsell_patterns
        self._refusal_patterns: List[re.Pattern[str]] = [
            re.compile(r"\b(i can'?t|i cannot) provide medical advice\b", re.IGNORECASE),
            re.compile(r"\bplease consult (a|your) (doctor|pharmacist)\b", re.IGNORECASE),
            re.compile(r"\bconsult (a|your) (doctor|pharmacist)\b", re.IGNORECASE),
            re.compile(r"אני\s*(?:לא\s*)?יכול(?:ה)?\s*(?:לתת|לספק)\s*ייעוץ\s*רפואי", re.IGNORECASE),
            re.compile(r"פנה(?:י)?\s*(?:ל|אל)\s*(?:רופא|רוקח)", re.IGNORECASE),
            re.compile(r"не могу\s*(?:давать|предоставлять)\s*медицинские\s*(?:советы|рекомендации)", re.IGNORECASE),
            re.compile(r"обратитесь\s*к\s*(?:врачу|фармацевту)", re.IGNORECASE),
            re.compile(r"لا\s*أستطيع\s*تقديم\s*نصيحة\s*طبية", re.IGNORECASE),
            re.compile(r"يرجى\s*استشارة\s*(?:طبيب|صيدلي)", re.IGNORECASE),
        ]

    def check_text(self, text: str) -> Optional[str]:
        """return the violation reason if any prohibited pattern is detected."""
        if self._is_refusal(text):
            return None
        for regex, reason in self._patterns:
            if regex.search(text):
                return reason
        return None

    def _is_refusal(self, text: str) -> bool:
        """return true when the text is a refusal that should not be blocked."""
        if not text:
            return False
        for regex in self._refusal_patterns:
            if regex.search(text):
                return True
        return False

    @staticmethod
    def refusal_message(reason: str, language: str = "en") -> str:
        """standard refusal message for safety violations."""
        base = Messages.get("SAFETY", "refusal_base", language)
        tail = Messages.get("SAFETY", "refusal_suffix", language, reason=reason)
        return f"{base} {tail}"

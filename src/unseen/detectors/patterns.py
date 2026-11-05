"""Shared heuristics: does a piece of text look like instructions aimed at an AI model?"""

from __future__ import annotations

import re
import unicodedata

# Zero-width, bidi-control, soft-hyphen, BOM and Unicode tag characters.
INVISIBLE = re.compile(
    "[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u00ad\ufeff"
    "\U000e0000-\U000e007f]"
)

_SOURCES = [
    # Override earlier instructions: "ignore all previous instructions"
    (
        r"\b(?:ignore|disregard|forget|override|bypass)\b(?:\s+\w+){0,3}?\s+"
        r"(?:previous|prior|above|earlier|preceding|system|original)\s+"
        r"(?:instructions?|prompts?|rules?|context|messages?|guidelines?|directions?)"
    ),
    # Persona or mode switch: "you are now in developer mode"
    (
        r"\byou\s+are\s+now\s+(?:in\s+(?:\w+\s+){0,2}mode\b"
        r"|(?:an?\s+)?(?:unrestricted|unfiltered|jailbroken|evil)\b"
        r"|(?:acting|playing|roleplaying)\b|going\s+to\b)"
    ),
    r"\b(?:developer|admin|debug|god|sudo|dan|jailbreak)\s+mode\b",
    r"\bpretend\s+(?:to\s+be|you\s+are|that\s+you)\b",
    # Addressing the model directly: "note to AI assistants"
    (
        r"\b(?:note|message|attention|notice|instructions?)\s+(?:to|for)\s+(?:the\s+)?"
        r"(?:ai|llm|language\s+model|chat\s?bot|assistant|agent|bot|model)s?"
        r"(?:\s+(?:assistant|agent|model|system)s?)?\b"
    ),
    (
        r"\bif\s+you(?:'re|\s+are)\s+(?:an?\s+)?"
        r"(?:ai|llm|language\s+model|chat\s?bot|artificial\s+intelligence)\b"
    ),
    # Secrecy: "do not tell the user"
    (
        r"\b(?:do\s+not|don't|never)\s+(?:tell|inform|mention|reveal|disclose|alert|notify)"
        r"\s+(?:this\s+to\s+)?(?:the\s+)?(?:user|human|person)\b"
    ),
    # Prompt extraction
    (
        r"\b(?:reveal|print|repeat|output|show|disclose|leak)\b[^.\n]{0,30}?"
        r"\b(?:system\s+prompt|hidden\s+prompt|your\s+instructions)\b"
    ),
    # Fake prompt structure
    r"\bnew\s+(?:instructions?|system\s+prompt|rules)\s*[:\-]",
    r"\bsystem\s*(?:prompt|message)\s*[:\-]",
    r"<\|?(?:im_start|im_end|system|endoftext)\|?>|\[/?inst\]|<<sys>>",
    # Exfiltration: a verb, then something sensitive, then an address or URL
    (
        r"\b(?:send|forward|email|post|upload|leak|transmit|exfiltrate)\b[^.\n]{0,60}?"
        r"\b(?:conversations?|chats?|history|data|credentials?|passwords?|cookies?|tokens?"
        r"|secrets?|files?|contents?|information|details)\b[^.\n]{0,60}?"
        r"(?:https?://\S+|[\w.+-]+@[\w-]+\.[\w.-]+)"
    ),
    # --- French ---
    # "ignorez les instructions précédentes"
    (
        r"\b(?:ignor(?:e|ez|er)|oubli(?:e|ez|er)|n[ée]glige[zr]?|d[ée]sob[ée]i\w*)\b"
        r"(?:\s+\w+){0,3}?\s+"
        r"(?:instructions?|consignes?|directives?|r[èe]gles?|ordres?|prompts?|messages?)\s+"
        r"(?:pr[ée]c[ée]dent\w*|ant[ée]rieur\w*|ci-dessus|initial\w*|original\w*|syst[èe]me)"
    ),
    # "ne dis pas à l'utilisateur"
    (
        r"\bne\s+(?:le\s+|lui\s+)?(?:dis|dites|r[ée]v[èée]le[z]?|mentionne[z]?)\s+pas\s+"
        r"(?:[àa]\s+)?l['’]\s?utilisateur"
    ),
    # --- Spanish ---
    # "ignora todas las instrucciones anteriores"
    (
        r"\b(?:ignor(?:a|as|e|ar)|olvid(?:a|e|ar)|omit(?:e|ir)|descart(?:a|e|ar))\b"
        r"(?:\s+\w+){0,3}?\s+"
        r"(?:instrucciones|indicaciones|reglas|directrices|directivas|[óo]rdenes|mensajes)\s+"
        r"(?:anteriores|previas|previos|precedentes|originales)"
    ),
    # "no le digas al usuario"
    (
        r"\bno\s+(?:le\s+)?(?:digas|cuentes|reveles|menciones|informes|muestres)\s+"
        r"(?:esto\s+)?(?:al|a\s+la|a\s+el)\s+(?:usuario|persona|humano)"
    ),
    # --- German ---
    # "ignoriere alle vorherigen Anweisungen"
    (
        r"\b(?:ignorier\w*|vergiss\w*|vergessen|missachte\w*)\b(?:\s+\w+){0,3}?\s+"
        r"(?:vorherig|vorig|fr[üu]her|bisherig|obig|vorangegangen|urspr[üu]nglich)\w*\s+"
        r"(?:anweisung|instruktion|regel|befehl|vorgabe|anleitung|eingabe)\w*"
    ),
    # "sage dem Benutzer nicht"
    (
        r"\b(?:sage|sag|erz[äa]hle|verrate|teile)\s+(?:es\s+|dies\s+)?(?:dem|der)\s+"
        r"(?:benutzer|nutzer|anwender|person)\w*\s+nicht\b"
    ),
    # --- Turkish ---
    # "önceki talimatları yoksay"
    (
        r"\b[öo]ncek[iıİ]\s+(?:\w+\s+){0,2}?"
        r"(?:talimat|komut|y[öo]nerge|kural|istem|y[öo]nlendirme)\w*\s+(?:\w+\s+){0,2}?"
        r"(?:yoksay|unut|g[öo]rmezden|dikkate\s+alma|iptal)\w*"
    ),
    # "kullanıcıya söyleme"
    r"\bkullan[ıi]c[ıi]ya\s+(?:\w+\s+){0,2}?(?:s[öo]yleme|bildirme|g[öo]sterme)\w*",
]

PATTERNS = [re.compile(source, re.IGNORECASE) for source in _SOURCES]
NON_ENGLISH_PATTERNS = PATTERNS[-8:]


def normalize(text: str) -> str:
    """Fold lookalike characters, drop invisible ones, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text)
    text = INVISIBLE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def find_instruction(text: str) -> str | None:
    """Return the earliest instruction-like phrase in text, or None."""
    text = normalize(text)
    matches = [m for pattern in PATTERNS if (m := pattern.search(text))]
    if not matches:
        return None
    best = min(matches, key=lambda m: (m.start(), -len(m.group(0))))
    return best.group(0)


def looks_like_instruction(text: str) -> bool:
    return find_instruction(text) is not None
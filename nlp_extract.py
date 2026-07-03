"""
Rule-based medical entity extraction using plain Python (no spaCy).

We deliberately avoid spaCy/thinc/blis here — those pull in compiled
BLAS extensions that frequently fail to build on hosts running a very new
Python version (no prebuilt wheels yet), which is exactly what happened on
Streamlit Community Cloud. Since our extraction is rule-based (a curated
drug list + regex for dosage/frequency/duration), plain Python regex does
the same job with zero compiled dependencies and installs instantly
anywhere.

For production / clinical use, swap the drug list for a real database
(e.g. RxNorm, WHO ATC) and consider a trained clinical NER model
(e.g. med7, scispaCy en_core_sci_md) for higher recall/precision — those
do need spaCy, so only add that back if you control the host's Python
version.
"""

import re
from pathlib import Path

DRUG_LIST_PATH = Path(__file__).resolve().parent.parent / "data" / "drugs.txt"

# --- Regex patterns -----------------------------------------------------
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

DOSAGE_RE = re.compile(
    r"""
    (\d+(\.\d+)?\s?(mg|mcg|g|ml|milligrams?|micrograms?|grams?|units?|iu)\b)
    |
    (\b(one|two|three|1|2|3)\s+(tablet|tablets|capsule|capsules|drop|drops|puff|puffs|teaspoon|teaspoons)\b)
    """,
    re.IGNORECASE | re.VERBOSE,
)

FREQUENCY_PATTERNS = [
    (r"\bonce a day\b|\bonce daily\b|\bod\b", "Once daily (OD)"),
    (r"\btwice a day\b|\btwice daily\b|\bbid\b|\bbd\b", "Twice daily (BD)"),
    (r"\bthree times a day\b|\bthrice daily\b|\btds\b|\btid\b", "Three times daily (TDS)"),
    (r"\bfour times a day\b|\bqid\b", "Four times daily (QID)"),
    (r"\bevery (\d+) hours?\b", "Every {0} hours"),
    (r"\bat bedtime\b|\bhs\b|\bbefore sleeping\b|\bat night\b", "At bedtime (HS)"),
    (r"\bin the morning\b", "Morning"),
    (r"\bas needed\b|\bsos\b|\bwhen required\b", "As needed (SOS)"),
    (r"\bstat\b|\bimmediately\b", "Immediately (STAT)"),
    (r"\bbefore food\b|\bbefore meals\b", "Before food"),
    (r"\bafter food\b|\bafter meals\b", "After food"),
]

DURATION_RE = re.compile(
    r"\bfor\s+(\d+|one|two|three|four|five|six|seven|\d+)\s*(day|days|week|weeks|month|months)\b",
    re.IGNORECASE,
)


def load_nlp_pipeline():
    """
    Loads the curated drug list and compiles a case-insensitive,
    word-boundary regex pattern per drug name for fast matching.
    Returns a list of (compiled_pattern, display_name) tuples.
    """
    drug_names = [
        line.strip() for line in DRUG_LIST_PATH.read_text().splitlines() if line.strip()
    ]
    # Longer names first, so e.g. "augmentin duo" matches before "augmentin"
    drug_names.sort(key=len, reverse=True)

    patterns = []
    for name in drug_names:
        pattern = re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE)
        patterns.append((pattern, name.title()))
    return patterns


def _split_sentences(text: str):
    parts = SENTENCE_SPLIT_RE.split(text.strip())
    return [p for p in parts if p]


def _extract_frequency(sentence: str):
    for pattern, label in FREQUENCY_PATTERNS:
        m = re.search(pattern, sentence, re.IGNORECASE)
        if m:
            if "{0}" in label:
                return label.format(m.group(1))
            return label
    return ""


def _extract_dosage(sentence: str):
    m = DOSAGE_RE.search(sentence)
    return m.group(0).strip() if m else ""


def _extract_duration(sentence: str):
    m = DURATION_RE.search(sentence)
    return m.group(0).strip() if m else ""


def extract_prescription_info(pipeline, transcript: str):
    """
    Given the raw transcript, return a list of dicts:
        {"medicine": ..., "dosage": ..., "frequency": ..., "duration": ..., "notes": ""}

    Strategy: split into sentences, find drug mentions per sentence via the
    compiled drug-name patterns, and pull dosage/frequency/duration from
    that same sentence (this is where doctors naturally group the info when
    dictating, e.g. "Give Paracetamol 500 mg twice a day for 5 days").
    """
    results = []
    seen = set()

    for sentence in _split_sentences(transcript):
        matched_drug = None
        for pattern, display_name in pipeline:
            if pattern.search(sentence):
                matched_drug = display_name
                break  # longest match wins (list is sorted longest-first)

        if not matched_drug:
            continue

        dosage = _extract_dosage(sentence)
        frequency = _extract_frequency(sentence)
        duration = _extract_duration(sentence)

        dedupe_key = (matched_drug.lower(), dosage, frequency, duration)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        results.append(
            {
                "medicine": matched_drug,
                "dosage": dosage,
                "frequency": frequency,
                "duration": duration,
                "notes": "",
            }
        )

    return results

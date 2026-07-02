"""
Rule-based medical entity extraction using spaCy.

We deliberately avoid requiring a heavyweight scispaCy/med7 model so the app
stays free and installable on Streamlit Cloud's free tier. Instead we use:
  - a PhraseMatcher over a curated drug-name list (data/drugs.txt) to find
    medicine mentions, and
  - regex over each sentence to pull dosage / frequency / duration that
    appears near the drug mention.

For production / clinical use, swap the drug list for a real database
(e.g. RxNorm, WHO ATC) and consider a trained clinical NER model
(e.g. med7, scispaCy en_core_sci_md) for higher recall/precision.
"""

import re
from pathlib import Path

import spacy
from spacy.matcher import PhraseMatcher

DRUG_LIST_PATH = Path(__file__).resolve().parent.parent / "data" / "drugs.txt"

# --- Regex patterns -----------------------------------------------------
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
    Loads a small spaCy English pipeline (for sentence segmentation) and
    attaches a PhraseMatcher for drug-name recognition.
    """
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        # Fallback: blank English pipeline + rule-based sentence splitter.
        # (Happens if the small model wasn't downloaded — see README.)
        nlp = spacy.blank("en")
        nlp.add_pipe("sentencizer")

    drug_names = [
        line.strip() for line in DRUG_LIST_PATH.read_text().splitlines() if line.strip()
    ]
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(name) for name in drug_names]
    matcher.add("DRUG", patterns)

    return {"nlp": nlp, "matcher": matcher}


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


def extract_prescription_info(pipeline: dict, transcript: str):
    """
    Given the raw transcript, return a list of dicts:
        {"medicine": ..., "dosage": ..., "frequency": ..., "duration": ..., "notes": ""}

    Strategy: split into sentences, find drug mentions per sentence via the
    PhraseMatcher, and pull dosage/frequency/duration from that same
    sentence (this is where doctors naturally group the info when dictating,
    e.g. "Give Paracetamol 500 mg twice a day for 5 days").
    """
    nlp = pipeline["nlp"]
    matcher = pipeline["matcher"]

    doc = nlp(transcript)
    results = []
    seen = set()

    for sent in doc.sents:
        matches = matcher(sent.as_doc())
        if not matches:
            continue
        sent_text = sent.text
        for match_id, start, end in matches:
            drug_span = sent.as_doc()[start:end].text
            key = drug_span.lower()
            dosage = _extract_dosage(sent_text)
            frequency = _extract_frequency(sent_text)
            duration = _extract_duration(sent_text)

            # Merge duplicate drug mentions in the same transcript
            dedupe_key = (key, dosage, frequency, duration)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            results.append(
                {
                    "medicine": drug_span.title(),
                    "dosage": dosage,
                    "frequency": frequency,
                    "duration": duration,
                    "notes": "",
                }
            )

    return results

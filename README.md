# 🩺 Voice Prescription Generator

Doctor records **three separate clips** — Tests, Medicines, and Notes/Advice
— each transcribed offline by **faster-whisper**. Medicines are parsed into
structured drug/dosage/frequency/duration with plain-Python regex; Tests
become a clean bullet list; Notes are used as-is. Everything is assembled
into a letterhead-style, downloadable **PDF prescription**.

100% free stack: no API keys, no cloud costs, no compiled dependencies that
can fail to build. Runs on Streamlit Cloud's free tier.

```
prescription-generator/
├── app.py                 # Streamlit UI
├── utils/
│   ├── audio_transcribe.py  # Whisper wrapper
│   ├── nlp_extract.py       # spaCy PhraseMatcher + regex extraction
│   └── pdf_generator.py     # reportlab PDF builder
├── data/
│   └── drugs.txt            # sample drug name list (expand for production)
├── requirements.txt
├── packages.txt            # ffmpeg (apt dependency for Streamlit Cloud)
└── README.md
```

## 1. Run it locally

Requires Python 3.10+ and `ffmpeg` installed on your system.

```bash
# Install ffmpeg (once)
#   Mac:      brew install ffmpeg
#   Ubuntu:   sudo apt install ffmpeg
#   Windows:  choco install ffmpeg   (or download from ffmpeg.org)

cd prescription-generator
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows

pip install -r requirements.txt

streamlit run app.py
```

Your browser will open at `http://localhost:8501`. Click the **Record**
tab to speak directly into your mic, or **Upload a file** to use an
existing recording.

> First run will download the faster-whisper "base" model (~140 MB) — this
> is a one-time download, cached afterwards.

## 2. Host it for free on Streamlit Community Cloud

1. **Push this folder to GitHub**
   ```bash
   cd prescription-generator
   git init
   git add .
   git commit -m "Voice prescription generator"
   git branch -M main
   git remote add origin https://github.com/<your-username>/prescription-generator.git
   git push -u origin main
   ```

2. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in
   with GitHub.

3. Click **"New app"** → select your repo, branch `main`, and main file
   path `app.py`.

4. Click **Deploy**. Streamlit Cloud will automatically:
   - install everything in `requirements.txt`
   - install `ffmpeg` from `packages.txt`
   - start the app and give you a public URL like
     `https://your-app-name.streamlit.app`

   First deploy takes a few minutes (downloading model files). Subsequent
   redeploys (after a `git push`) are much faster.

   **Python version:** This project deliberately avoids any dependency
   that needs compiling from source (`faster-whisper`, `reportlab`, and
   `streamlit` all ship prebuilt wheels), so it should install cleanly on
   whatever Python version Streamlit Cloud uses. If you ever add a package
   that fails to build, check whether it has a prebuilt wheel for the
   platform's current Python version before assuming `runtime.txt` will
   help — Streamlit Cloud has a known bug where it sometimes ignores it.

> **Free-tier note:** Streamlit Community Cloud gives ~1 GB RAM. The app is
> configured to use faster-whisper's **"base"** model with `int8` compute,
> which fits comfortably. If you need higher accuracy and have access to a
> paid host, switch to `"small"` or `"medium"` in `app.py`
> (`get_whisper()` function).

## 3. How the NLP extraction works

`utils/nlp_extract.py` uses plain Python (no spaCy — see note below) with:
- a **word-boundary regex per drug name** from `data/drugs.txt` to spot
  medicine mentions
- **regex patterns** to grab dosage (`500 mg`, `2 tablets`), frequency
  (`twice a day`, `BD`, `every 8 hours`), and duration (`for 5 days`) from
  the same sentence as the medicine mention

This is intentionally simple, free to run (no external API, no GPU), and
has **zero compiled dependencies** — important for reliably deploying on
hosts like Streamlit Community Cloud, where packages that need compiling
from source (like spaCy's `blis`) can fail if the host's Python version is
newer than what that package has prebuilt wheels for.

For a production/clinical-grade system, consider:
- Replacing `data/drugs.txt` with a real drug database (RxNorm, WHO ATC,
  or your local formulary)
- Adding a trained clinical NER model such as **med7** or **scispaCy**
  (`en_core_sci_md`) for higher recall on drug/dosage entities — only do
  this if you control (or can pin) the host's Python version, since these
  pull in spaCy/thinc/blis
- Adding a spell-correction pass on the transcript for drug names the
  speech model may mis-hear (medical vocabulary isn't in its training data
  by default)

## 4. Editing before generating the PDF

The app is designed to keep a human in the loop:
- The raw transcript is shown and **editable** before extraction
- The extracted medicine table is shown in an **editable data grid** (add/
  remove rows, fix any mis-extracted field) before the PDF is generated

This matters for a prescription tool — the doctor should always review and
confirm before it's finalized.

## 5. Known limitations / next steps

- Whisper's `"base"` model is optimized for general speech, not medical
  terminology — expect occasional drug-name transcription errors,
  especially for longer/less common drug names. Editing the transcript
  before extraction is the safety net.
- The drug list in `data/drugs.txt` is a small sample for demonstration.
  Add your commonly prescribed medicines to it, one per line.
- No patient data is stored anywhere — everything lives in the browser
  session and is discarded when the tab closes. If you need persistence
  (patient history, past prescriptions), you'll need to add a database
  and handle patient data privacy/compliance (e.g. HIPAA) accordingly —
  that is out of scope of this starter project.

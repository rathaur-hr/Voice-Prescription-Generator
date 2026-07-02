"""
Voice-to-Prescription Generator
--------------------------------
Doctor speaks -> Whisper transcribes -> spaCy extracts drug/dosage/frequency/
duration -> a clean, printable PDF prescription is generated.

Run locally:    streamlit run app.py
Deploy:         push this folder to GitHub, then deploy on Streamlit Cloud
                 (see README.md for step-by-step instructions)
"""

import io
import tempfile
from datetime import date

import streamlit as st

from utils.audio_transcribe import load_whisper_model, transcribe_audio
from utils.nlp_extract import load_nlp_pipeline, extract_prescription_info
from utils.pdf_generator import build_prescription_pdf

st.set_page_config(page_title="Voice Prescription Generator", page_icon="🩺", layout="centered")

# ----------------------------------------------------------------------
# Cached, expensive resources (loaded once per server, not per request)
# ----------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading speech-to-text model (first run only)...")
def get_whisper():
    # "tiny" or "base" recommended for free-tier hosting (low RAM/CPU).
    # Swap to "small"/"medium" locally if you have more compute.
    return load_whisper_model("base")


@st.cache_resource(show_spinner="Loading medical NLP pipeline (first run only)...")
def get_nlp():
    return load_nlp_pipeline()


# ----------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "medicines" not in st.session_state:
    st.session_state.medicines = []

# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
st.title("🩺 Voice Prescription Generator")
st.caption("Speak or upload the consultation audio → get a structured, editable, printable prescription.")

with st.sidebar:
    st.header("Doctor & Patient Details")
    doctor_name = st.text_input("Doctor's Name", "Dr. ")
    doctor_reg = st.text_input("Registration / License No.", "")
    clinic_name = st.text_input("Clinic / Hospital Name", "")
    st.divider()
    patient_name = st.text_input("Patient's Name", "")
    patient_age = st.text_input("Age", "")
    patient_sex = st.selectbox("Sex", ["", "Male", "Female", "Other"])
    presc_date = st.date_input("Date", value=date.today())

st.subheader("1. Capture audio")
tab_record, tab_upload = st.tabs(["🎙️ Record", "📁 Upload a file"])

audio_bytes = None
with tab_record:
    mic_input = st.audio_input("Record the doctor's dictation")
    if mic_input is not None:
        audio_bytes = mic_input.read()

with tab_upload:
    uploaded = st.file_uploader("Upload audio (wav, mp3, m4a, ogg)", type=["wav", "mp3", "m4a", "ogg"])
    if uploaded is not None:
        audio_bytes = uploaded.read()

if audio_bytes:
    st.audio(audio_bytes)

    if st.button("Transcribe & Extract", type="primary"):
        with st.spinner("Transcribing audio..."):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            model = get_whisper()
            transcript = transcribe_audio(model, tmp_path)
            st.session_state.transcript = transcript

        with st.spinner("Extracting medicines, dosage, frequency..."):
            nlp = get_nlp()
            st.session_state.medicines = extract_prescription_info(nlp, transcript)

        st.success("Done! Review and edit the results below.")

# ----------------------------------------------------------------------
# Transcript (editable, in case Whisper mis-heard something)
# ----------------------------------------------------------------------
if st.session_state.transcript:
    st.subheader("2. Transcript")
    st.session_state.transcript = st.text_area(
        "You can correct the raw transcript here, then click 'Re-extract' below.",
        st.session_state.transcript,
        height=140,
    )
    if st.button("Re-extract from edited transcript"):
        nlp = get_nlp()
        st.session_state.medicines = extract_prescription_info(nlp, st.session_state.transcript)

# ----------------------------------------------------------------------
# Structured, editable medicine table
# ----------------------------------------------------------------------
if st.session_state.medicines:
    st.subheader("3. Prescription details")
    st.caption("Auto-extracted from speech — please verify before printing. Add/remove rows as needed.")

    edited = st.data_editor(
        st.session_state.medicines,
        num_rows="dynamic",
        column_config={
            "medicine": st.column_config.TextColumn("Medicine"),
            "dosage": st.column_config.TextColumn("Dosage"),
            "frequency": st.column_config.TextColumn("Frequency"),
            "duration": st.column_config.TextColumn("Duration"),
            "notes": st.column_config.TextColumn("Notes"),
        },
        use_container_width=True,
        key="medicine_editor",
    )
    st.session_state.medicines = edited

    st.subheader("4. Generate prescription")
    extra_notes = st.text_area("Additional notes / advice (optional)", "")

    if st.button("📄 Generate PDF", type="primary"):
        if not patient_name or not doctor_name.strip("Dr. "):
            st.warning("Please fill in doctor and patient name in the sidebar first.")
        else:
            pdf_bytes = build_prescription_pdf(
                doctor_name=doctor_name,
                doctor_reg=doctor_reg,
                clinic_name=clinic_name,
                patient_name=patient_name,
                patient_age=patient_age,
                patient_sex=patient_sex,
                presc_date=presc_date.strftime("%d-%m-%Y"),
                medicines=st.session_state.medicines,
                extra_notes=extra_notes,
            )
            st.download_button(
                "⬇️ Download Prescription PDF",
                data=pdf_bytes,
                file_name=f"prescription_{patient_name.replace(' ', '_')}_{presc_date}.pdf",
                mime="application/pdf",
            )
else:
    st.info("Record or upload audio above, then click **Transcribe & Extract** to begin.")

st.divider()
st.caption(
    "⚠️ This tool assists drafting only. The prescribing doctor is responsible for reviewing "
    "and verifying all medicine names, dosages, and instructions before signing/issuing."
)

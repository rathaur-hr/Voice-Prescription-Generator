"""
Voice-to-Prescription Generator
--------------------------------
Doctor records separate audio clips for Tests, Medicines, and Notes/Advice
-> each is transcribed offline (faster-whisper) -> Medicines are parsed
into structured drug/dosage/frequency/duration, Tests into a clean list ->
everything is assembled into a letterhead-style, downloadable PDF.

Run locally:    streamlit run app.py
Deploy:         push this folder to GitHub, then deploy on Streamlit Cloud
                 (see README.md for step-by-step instructions)
"""

import tempfile
from datetime import date

import streamlit as st

from utils.audio_transcribe import load_whisper_model, transcribe_audio
from utils.nlp_extract import load_nlp_pipeline, extract_prescription_info, extract_list_items
from utils.pdf_generator import build_prescription_pdf

st.set_page_config(page_title="Voice Prescription Generator", page_icon="🩺", layout="centered")


# ----------------------------------------------------------------------
# Cached, expensive resources (loaded once per server, not per request)
# ----------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading speech-to-text model (first run only)...")
def get_whisper():
    return load_whisper_model("base")


@st.cache_resource(show_spinner="Loading medicine-matching pipeline...")
def get_nlp():
    return load_nlp_pipeline()


def transcribe(audio_bytes):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    model = get_whisper()
    return transcribe_audio(model, tmp_path)


# ----------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------
defaults = {
    "tests_transcript": "",
    "tests_list": [],
    "meds_transcript": "",
    "medicines": [],
    "notes_transcript": "",
    "advice_text": "",
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ----------------------------------------------------------------------
# Sidebar: doctor, clinic, patient details
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("Doctor & Clinic")
    doctor_name = st.text_input("Doctor's Name", "Dr. ")
    doctor_qualification = st.text_input("Qualification", "MBBS")
    doctor_reg = st.text_input("Registration / License No.", "")
    clinic_name = st.text_input("Clinic / Hospital Name", "")
    clinic_slogan = st.text_input("Slogan / Tagline", "")
    clinic_phone1 = st.text_input("Phone 1", "")
    clinic_phone2 = st.text_input("Phone 2 (optional)", "")
    clinic_email = st.text_input("Email", "")
    clinic_website = st.text_input("Website", "")

    st.divider()
    st.header("Patient")
    patient_name = st.text_input("Patient's Name", "")
    patient_address = st.text_input("Address", "")
    patient_age = st.text_input("Age", "")
    presc_date = st.date_input("Date", value=date.today())
    diagnosis = st.text_input("Diagnosis", "")

st.title("🩺 Voice Prescription Generator")
st.caption("Record each section separately, review the results, then generate a printable PDF.")


def audio_section(section_key, label, help_text):
    """Renders a record/upload widget and returns raw audio bytes, or None."""
    st.write(f"**{label}**")
    st.caption(help_text)
    tab_record, tab_upload = st.tabs(["🎙️ Record", "📁 Upload"])
    audio_bytes = None
    with tab_record:
        mic_input = st.audio_input("Record", key=f"{section_key}_mic", label_visibility="collapsed")
        if mic_input is not None:
            audio_bytes = mic_input.read()
    with tab_upload:
        uploaded = st.file_uploader(
            "Upload", type=["wav", "mp3", "m4a", "ogg"], key=f"{section_key}_upload", label_visibility="collapsed"
        )
        if uploaded is not None:
            audio_bytes = uploaded.read()
    if audio_bytes:
        st.audio(audio_bytes)
    return audio_bytes


# ----------------------------------------------------------------------
# Section 1: Tests
# ----------------------------------------------------------------------
st.subheader("1. 🧪 Tests")
tests_audio = audio_section(
    "tests", "Dictate tests advised", "e.g. \"Complete blood count, blood sugar fasting, chest X-ray\""
)
if tests_audio and st.button("Transcribe Tests", key="btn_tests"):
    with st.spinner("Transcribing..."):
        st.session_state.tests_transcript = transcribe(tests_audio)
        st.session_state.tests_list = extract_list_items(st.session_state.tests_transcript)

if st.session_state.tests_transcript:
    st.session_state.tests_transcript = st.text_area(
        "Transcript (edit if needed)", st.session_state.tests_transcript, key="tests_ta", height=80
    )
    if st.button("Re-extract test list", key="btn_tests_reextract"):
        st.session_state.tests_list = extract_list_items(st.session_state.tests_transcript)

    tests_text_block = st.text_area(
        "Tests (one per line — add/remove/edit freely)",
        "\n".join(st.session_state.tests_list),
        key="tests_list_ta",
        height=100,
    )
    st.session_state.tests_list = [line.strip() for line in tests_text_block.split("\n") if line.strip()]

st.divider()

# ----------------------------------------------------------------------
# Section 2: Medicines
# ----------------------------------------------------------------------
st.subheader("2. 💊 Medicines")
meds_audio = audio_section(
    "meds", "Dictate medicines", "e.g. \"Paracetamol 500 mg twice a day for 5 days after food\""
)
if meds_audio and st.button("Transcribe Medicines", key="btn_meds"):
    with st.spinner("Transcribing..."):
        st.session_state.meds_transcript = transcribe(meds_audio)
    with st.spinner("Extracting medicines..."):
        nlp = get_nlp()
        st.session_state.medicines = extract_prescription_info(nlp, st.session_state.meds_transcript)

if st.session_state.meds_transcript:
    st.session_state.meds_transcript = st.text_area(
        "Transcript (edit if needed)", st.session_state.meds_transcript, key="meds_ta", height=80
    )
    if st.button("Re-extract medicines", key="btn_meds_reextract"):
        nlp = get_nlp()
        st.session_state.medicines = extract_prescription_info(nlp, st.session_state.meds_transcript)

    st.caption("Review/edit the extracted table — add or remove rows as needed.")
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

st.divider()

# ----------------------------------------------------------------------
# Section 3: Other notes / advice
# ----------------------------------------------------------------------
st.subheader("3. 📝 Other Notes / Advice")
notes_audio = audio_section(
    "notes", "Dictate any additional advice", "e.g. \"Drink plenty of fluids, follow up after 5 days\""
)
if notes_audio and st.button("Transcribe Notes", key="btn_notes"):
    with st.spinner("Transcribing..."):
        st.session_state.notes_transcript = transcribe(notes_audio)
        st.session_state.advice_text = st.session_state.notes_transcript

if st.session_state.notes_transcript:
    st.session_state.advice_text = st.text_area(
        "Advice / notes (edit freely — this goes on the prescription as-is)",
        st.session_state.advice_text,
        key="advice_ta",
        height=100,
    )

st.divider()

# ----------------------------------------------------------------------
# Generate PDF
# ----------------------------------------------------------------------
st.subheader("4. Generate Prescription")

has_any_content = bool(st.session_state.tests_list or len(st.session_state.medicines) or st.session_state.advice_text)

if st.button("📄 Generate PDF", type="primary"):
    if not patient_name or not doctor_name.strip("Dr. "):
        st.warning("Please fill in doctor and patient name in the sidebar first.")
    elif not has_any_content:
        st.warning("Record or fill in at least one section (Tests, Medicines, or Notes) first.")
    else:
        pdf_bytes = build_prescription_pdf(
            doctor_name=doctor_name,
            doctor_qualification=doctor_qualification,
            doctor_reg=doctor_reg,
            clinic_name=clinic_name,
            clinic_slogan=clinic_slogan,
            clinic_phone1=clinic_phone1,
            clinic_phone2=clinic_phone2,
            clinic_email=clinic_email,
            clinic_website=clinic_website,
            patient_name=patient_name,
            patient_address=patient_address,
            patient_age=patient_age,
            presc_date=presc_date.strftime("%d-%m-%Y"),
            diagnosis=diagnosis,
            tests=st.session_state.tests_list,
            medicines=st.session_state.medicines,
            advice_notes=st.session_state.advice_text,
        )
        st.success("Prescription generated!")
        st.download_button(
            "⬇️ Download Prescription PDF",
            data=pdf_bytes,
            file_name=f"prescription_{patient_name.replace(' ', '_')}_{presc_date}.pdf",
            mime="application/pdf",
        )

st.divider()
st.caption(
    "⚠️ This tool assists drafting only. The prescribing doctor is responsible for reviewing "
    "and verifying all tests, medicines, dosages, and instructions before signing/issuing."
)
st.caption("© 2026 Harshit Rathaur — Portfolio: [contactharshit.netlify.app](https://contactharshit.netlify.app)")

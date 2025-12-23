import streamlit as st
import os
import time
import tempfile
import re
import qrcode
from dotenv import load_dotenv
from google import genai
from tools.report_generator import create_pdf, TRANSLATIONS

# 1. Load Environment Variables
load_dotenv()

# --- CONFIGURATION & TRANSLATIONS ---

# --- PDF CLASS ---


def create_pdf(text, name, level, lang, r_type, video_link):
    pdf = ProReport(name, level, lang, r_type)
    pdf.create_cover_page()
    pdf.chapter_body(text, video_link)
    return pdf.output(dest='S')

# --- MAIN APP ---
st.set_page_config(page_title="Tennis AI Lab", page_icon="🎾", layout="wide")

if "lang" not in st.session_state:
    st.session_state.lang = "English"

with st.sidebar:
    st.title("⚙️ Config")
    selected_lang = st.selectbox("Language / Idioma", ["English", "Portuguese"])
    
    st.divider()
    t = TRANSLATIONS[selected_lang]
    report_type = st.radio(t["ui_mode_label"], t["ui_mode_options"])
    
    st.divider()
    creator_mode = st.checkbox("Creator Mode (Social Media)", value=False)
    if creator_mode:
        st.caption("✅ Reports will include Instagram/Reels suggestions.")

st.title(t["ui_title"])
st.markdown(t["ui_subtitle"])

video_content = None
uploaded_file = st.file_uploader(t["ui_upload_label"], type=["mp4", "mov"])

if uploaded_file:
    st.video(uploaded_file)
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    video_content = tfile.name
    tfile.close()

with st.sidebar:
    st.header(t["ui_sec_player"])
    player_description = st.text_input(t["ui_desc_label"], placeholder="e.g. 'Red Shirt'")
    st.divider()
    st.header(t["ui_sec_context"])
    player_level = st.selectbox(t["ui_level_label"], t["levels"])
    player_notes = st.text_area(t["ui_notes_label"])
    analysis_focus = st.multiselect(t["ui_focus_label"], t["focus_areas"], default=[t["focus_areas"][0]])

if st.button(t["ui_btn_analyze"], type="primary", use_container_width=True):
    if not video_content or not player_description:
        st.warning(t["ui_warning_video"] if not video_content else t["ui_warning_desc"])
        st.stop()

    try:
        # API & CLIENT
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            api_key = st.secrets["GOOGLE_API_KEY"]
        client = genai.Client(api_key=api_key)
        
        # UPLOAD (Spinner 1)
        with st.spinner("Uploading video to Google AI..."):
            video_file = client.files.upload(file=video_content)
        
        # PROCESSING (Spinner 2 - FIXED to match style)
        msg_processing = "⏳ AI is watching the video... (This usually takes 10-20 seconds)" if "English" in selected_lang else "⏳ A IA está assistindo ao vídeo... (Isso leva 10-20 segundos)"
        
        with st.spinner(msg_processing):
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = client.files.get(name=video_file.name)
        
        if video_file.state.name == "FAILED":
            st.error("Video processing failed.")
            st.stop()

        # PROMPT SETUP
        social_add_on = ""
        if creator_mode:
            social_add_on = """
            --- SOCIAL MEDIA PACK ---
            Identify 2 "Viral Moments" with Timestamps, Hooks, and Captions.
            """

        search_instruction = """
        FINAL STEP:
        At the very end of your response, on a new line, output a YouTube Search Query for the specific drill you recommended.
        Format it exactly like this:
        SEARCH_QUERY: [Tennis Drill for X]
        (Keep it short, e.g., "Tennis Drill Topspin Forehand")
        """

        if "Quick" in report_type or "Rápida" in report_type:
            full_prompt = f"""
            You are an elite tennis performance coach (ATP/WTA level).
            TARGET: {player_description}
            DECLARED LEVEL: {player_level}
            NOTES: {player_notes}
            FOCUS: {', '.join(analysis_focus)}
            LANGUAGE: {t['prompt_instruction']}
            
            REPORT TYPE: QUICK FIX (Actionable, Short, Precise).
            
            STRUCTURE:
            1. **THE MAIN ISSUE:** Identify the ONE technical flaw.
            2. **THE FIX (Drill):** Give one specific drill.
            3. **THE CUE:** A 3-word mental trigger.
            
            {search_instruction}
            {social_add_on}
            """
        else:
            full_prompt = f"""
            You are an elite tennis performance coach (ATP/WTA level).
            TARGET: {player_description}
            DECLARED LEVEL: {player_level}
            NOTES: {player_notes}
            FOCUS: {', '.join(analysis_focus)}
            LANGUAGE: {t['prompt_instruction']}
            
            REPORT TYPE: FULL PROFESSIONAL AUDIT (Comprehensive).
            
            STRUCTURE:
            ## SECTION 0: REALITY CHECK
            Estimate REAL-WORLD level vs Declared Level.
            
            ## SECTION 1: COMPREHENSIVE AUDIT
            List 4-5 distinct areas of inefficiency.
            
            ## SECTION 2: BIOMECHANICAL ARCHETYPE
            Match to Pro Archetype (Federer, Sinner, Nadal, Djokovic) and explain why.
            
            ## SECTION 3: THE PRIORITY FIX
            Identify #1 priority.
            
            ## SECTION 4: DIDACTIC LESSON PLAN
            - **The Concept:** Physics.
            - **The Drill:** Specific drill.
            - **The Cue:** Mental phrase.
            
            {search_instruction}
            {social_add_on}
            """
        
        # GENERATE (Spinner 3)
        with st.spinner("🤖 Analyzing biomechanics & generating drill link..." if "English" in selected_lang else "🤖 Analisando biomecânica..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[video_file, full_prompt]
            )

        st.success(t["ui_success"])
        st.markdown(response.text)
        
        # EXTRACT LINK & CREATE PDF
        video_link = None
        match = re.search(r"SEARCH_QUERY:\s*(.*)", response.text, re.IGNORECASE)
        if match:
            query = match.group(1).strip()
            clean_query = query.replace(" ", "+")
            video_link = f"https://www.youtube.com/results?search_query={clean_query}"
        else:
            video_link = "https://www.youtube.com/results?search_query=tennis+training+drills"

        try:
            pdf_bytes = create_pdf(response.text, player_description, player_level, selected_lang, report_type, video_link)
            st.download_button(t["ui_download_btn"], data=bytes(pdf_bytes), file_name="analysis_report.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"PDF Error: {e}")

    finally:
        if video_content and os.path.exists(video_content):
            os.unlink(video_content)
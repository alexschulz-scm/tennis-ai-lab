import streamlit as st
import os
import time
import tempfile
import re
import qrcode
from dotenv import load_dotenv
from google import genai
from tools.report_generator import create_pdf, TRANSLATIONS
from tools.video_editor import create_viral_clip
from tools.report_generator import create_pdf
import json # We need this to parse the AI's data


# 1. Load Environment Variables
load_dotenv(override=True)

# Initialize Session State
if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None
if "video_path" not in st.session_state:
    st.session_state["video_path"] = None


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

# --- LOGIC: ANALYZE BUTTON (Fetches & Saves to Memory) ---
if st.button(t["ui_btn_analyze"], type="primary", use_container_width=True):
    if not video_content or not player_description:
        st.warning(t["ui_warning_video"] if not video_content else t["ui_warning_desc"])
        st.stop()

    try:
        # API & CLIENT
        api_key = os.environ.get("GOOGLE_API_KEY")
        if api_key: api_key = api_key.strip() # Safety strip
        
        if not api_key:
            api_key = st.secrets.get("GOOGLE_API_KEY") # Use .get() to avoid errors if missing
            
        if not api_key:
            st.error("❌ API Key missing.")
            st.stop()

        client = genai.Client(api_key=api_key)
        
        # UPLOAD
        with st.spinner("Uploading video to Google AI..."):
            video_file = client.files.upload(file=video_content)
        
        # WAIT FOR PROCESSING
        msg_processing = "⏳ AI is watching... (10-20s)" if "English" in selected_lang else "⏳ A IA está assistindo... (10-20s)"
        with st.spinner(msg_processing):
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = client.files.get(name=video_file.name)
        
        if video_file.state.name == "FAILED":
            st.error("Video processing failed.")
            st.stop()

        # PROMPT SETUP (Same logic as before)
        social_add_on = ""
        if creator_mode:
            social_add_on = """
            --- SOCIAL MEDIA PACK ---
            Identify 2 "Viral Moments" with Timestamps, Hooks, and Captions.
            """

        search_instruction = """
        FINAL STEP:
        At the very end, output a YouTube Search Query on a new line:
        SEARCH_QUERY: [Tennis Drill for X]
        """

        # Build Prompt based on Report Type
        report_label = "QUICK FIX" if ("Quick" in report_type or "Rápida" in report_type) else "FULL AUDIT"
        full_prompt = f"""
        You are an elite tennis performance coach.
        TARGET: {player_description} | LEVEL: {player_level}
        REPORT TYPE: {report_label}
        
        Analyze the video and provide a structured report.
        {social_add_on}
        {search_instruction}

        BONUS: Identify TWO specific moments in the video:
        1. "best_shot": The single best execution (good form/result).
        2. "fix_shot": The clearest example of the MAIN ISSUE you identified in the report.

        Return the timestamps in this exact JSON format at the very end:
        JSON_DATA: {{
            "best_shot": {{"start": 12, "end": 18, "reason": "Great extension"}},
            "fix_shot": {{"start": 45, "end": 50, "reason": "Late preparation example"}}
        }}
        """

        # GENERATE
        with st.spinner("🤖 Analyzing biomechanics..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[video_file, full_prompt]
            )

        # --- CRITICAL CHANGE: SAVE TO SESSION STATE ---
        st.session_state["analysis_result"] = response.text
        st.session_state["video_path"] = video_content  # Save path so we can edit it later
        
        # Force a rerun so the "Display Logic" below picks it up immediately
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")


# --- LOGIC: DISPLAY RESULTS (Reads from Memory) ---
if st.session_state["analysis_result"]:
    raw_text = st.session_state["analysis_result"]
    saved_video_path = st.session_state["video_path"]
    
    # 🧹 CLEANING STEP: Remove technical data
    clean_text = raw_text
    
    # 1. Remove JSON Block (and any surrounding stars/newlines)
    clean_text = re.sub(r"\**JSON_DATA:?.*", "", clean_text, flags=re.DOTALL)
    
    # 2. Remove Search Query Line (Catching the leading stars too!)
    clean_text = re.sub(r"\**SEARCH_QUERY:?.*", "", clean_text, flags=re.IGNORECASE)
    
    # 3. Final Polish (Remove extra newlines left behind)
    clean_text = clean_text.strip()

    st.success(t["ui_success"])
    st.markdown(clean_text)
    
    # 1. PDF GENERATION
    video_link = "https://www.youtube.com/results?search_query=tennis+drills"
    match = re.search(r"SEARCH_QUERY:\s*(.*)", raw_text, re.IGNORECASE)
    if match:
        clean_query = match.group(1).strip().replace(" ", "+")
        video_link = f"https://www.youtube.com/results?search_query={clean_query}"

    try:
        pdf_bytes = create_pdf(clean_text, player_description, player_level, selected_lang, report_type, video_link)
        st.download_button(
            label=t["ui_download_btn"], 
            data=bytes(pdf_bytes), 
            file_name="analysis_report.pdf", 
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"PDF Error: {e}")

    # 2. SMART VIDEO ANALYSIS (Side-by-Side Reels)
    match_json = re.search(r"JSON_DATA:\s*({.*})", raw_text, re.DOTALL)
    if match_json:
        try:
            data = json.loads(match_json.group(1))
            st.divider()
            st.subheader("🎬 Smart Video Analysis")
            
            col1, col2 = st.columns(2)
            
            # Highlight (Best Shot)
            with col1:
                if "best_shot" in data:
                    shot = data["best_shot"]
                    st.success(f"✅ **Best Shot:** {shot.get('reason', 'N/A')}")
                    if st.button("✂️ Create Highlight Reel"):
                        if saved_video_path and os.path.exists(saved_video_path):
                            with st.spinner("Creating Highlight..."):
                                try:
                                    path = create_viral_clip(saved_video_path, shot['start'], shot['end'])
                                    if path:
                                        st.video(path)
                                        with open(path, "rb") as f:
                                            st.download_button("Download Highlight", f, file_name="best_shot.mp4")
                                except Exception as e:
                                    st.error(f"Edit Error: {e}")
            
            # Analysis (Fix Shot)
            with col2:
                if "fix_shot" in data:
                    shot = data["fix_shot"]
                    st.error(f"⚠️ **Needs Work:** {shot.get('reason', 'N/A')}")
                    if st.button("✂️ Create Analysis Clip"):
                        if saved_video_path and os.path.exists(saved_video_path):
                            with st.spinner("Isolating Mistake..."):
                                try:
                                    path = create_viral_clip(saved_video_path, shot['start'], shot['end'])
                                    if path:
                                        st.video(path)
                                        with open(path, "rb") as f:
                                            st.download_button("Download Analysis", f, file_name="fix_shot.mp4")
                                except Exception as e:
                                    st.error(f"Edit Error: {e}")

        except Exception as e:
            st.error(f"Could not parse video data: {e}")
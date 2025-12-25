import streamlit as st
import os
import time
import tempfile
import re
import json
from dotenv import load_dotenv
from tools.report_generator import create_pdf, TRANSLATIONS
from tools.video_editor import create_viral_clip

# --- NEW IMPORT: THE AGENT ---
try:
    from agent.graph import app_graph
except ImportError:
    st.error("⚠️ Could not find the Agent! Make sure you created the 'agent' folder with 'graph.py' inside.")
    st.stop()

# 1. Load Environment Variables
load_dotenv(override=True)

# Initialize Session State
if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None
if "video_path" not in st.session_state:
    st.session_state["video_path"] = None
if "email_draft" not in st.session_state:     # <--- NEW: Init Email State
    st.session_state["email_draft"] = None

# --- MAIN APP ---
st.set_page_config(page_title="Court Lens AI", page_icon="🎾", layout="wide")


# --- 🔒 GATEKEEPER LOGIC (Insert after st.set_page_config) ---
# --- 🔒 GATEKEEPER LOGIC (Upgraded for Roles) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = "user" # Default is standard user

def check_password():
    """Checks password and assigns role (User vs Creator)."""
    if st.session_state.authenticated:
        return True

    st.title("🔒 Court Lens AI")
    st.markdown("### Private Beta Access")
    
    password_input = st.text_input("Access Code", type="password")
    
    if st.button("Login"):
        # 1. Get Secrets (Support both Cloud and Local)
        # Standard Access
        std_code = os.environ.get("ACCESS_CODE") 
        if not std_code: std_code = st.secrets.get("ACCESS_CODE", "tennis2025")
        
        # Creator Access (New Secret)
        creator_code = os.environ.get("CREATOR_CODE")
        if not creator_code: creator_code = st.secrets.get("CREATOR_CODE", "admin123")

        # 2. Check Input
        if password_input == std_code:
            st.session_state.authenticated = True
            st.session_state.user_role = "user"
            st.success("✅ Welcome, Player!")
            time.sleep(1)
            st.rerun()
            
        elif password_input == creator_code:
            st.session_state.authenticated = True
            st.session_state.user_role = "creator" # <--- The Magic Flag
            st.success("✅ Welcome, Creator! (Advanced Mode Unlocked)")
            time.sleep(1)
            st.rerun()
            
        else:
            st.error("❌ Invalid Code.")
            
    return False

if not check_password():
    st.stop()
# -----------------------------------------------------------

if "lang" not in st.session_state:
    st.session_state.lang = "English"

with st.sidebar:
    st.title("⚙️ Config")
    selected_lang = st.selectbox("Language / Idioma", ["English", "Portuguese"])
    
    st.divider()
    t = TRANSLATIONS[selected_lang]
    report_type = st.radio(t["ui_mode_label"], t["ui_mode_options"])
    
    st.divider()
    # Only show this toggle if logged in with the MASTER PASSWORD
    creator_mode = False 
    if st.session_state.user_role == "creator":
        st.markdown("### 🎬 Creator Studio")
        creator_mode = st.checkbox("Enable Social Media Pack", value=True)
        if creator_mode:
            st.caption("✅ Viral Hooks, Captions & Reel Edits enabled.")
    else:
        # Standard users never see this, and it defaults to False
        creator_mode = False

# UPDATE: Hardcoded Brand Header (Overrides translation file for now)
st.title("COURT LENS AI")
st.caption("Powered by Schulz Creative Media") # Optional: Keep the agency link subtle
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

# --- LOGIC: ANALYZE BUTTON ---
if st.button(t["ui_btn_analyze"], type="primary", use_container_width=True):
    if not video_content or not player_description:
        st.warning(t["ui_warning_video"] if not video_content else t["ui_warning_desc"])
        st.stop()

    try:
        # 1. Check API Key
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key: api_key = st.secrets.get("GOOGLE_API_KEY")
        if not api_key:
            st.error("❌ API Key missing.")
            st.stop()
        
        # 2. Prepare Inputs
        agent_inputs = {
            "video_path": video_content,
            "player_description": player_description,
            "player_level": player_level,
            "player_notes": player_notes,
            "focus_areas": analysis_focus,
            "report_type": report_type,
            "language": selected_lang,
            "creator_mode": creator_mode
        }

        # 3. RUN THE AGENT
        with st.spinner("🤖 Agent is working... (Uploading & Analyzing)"):
            result_state = app_graph.invoke(agent_inputs)
            
        # 4. Extract Results
        final_text = result_state.get("analysis_text", "")
        final_email = result_state.get("email_draft", "")  # <--- NEW: Get Email
        
        if not final_text:
            st.error("Agent finished but returned no text.")
            st.stop()
            
        if "Error:" in final_text:
            st.error(final_text)
            st.stop()

        # 5. Save to Session State
        st.session_state["analysis_result"] = final_text
        st.session_state["email_draft"] = final_email      # <--- NEW: Save Email
        st.session_state["video_path"] = video_content
        
        st.rerun()

    except Exception as e:
        st.error(f"Agent Error: {e}")


# --- LOGIC: DISPLAY RESULTS ---
if st.session_state["analysis_result"]:
    raw_text = st.session_state["analysis_result"]
    saved_video_path = st.session_state["video_path"]
    
    # 🧹 CLEANING
    clean_text = raw_text
    clean_text = re.sub(r"\**JSON_DATA:?.*", "", clean_text, flags=re.DOTALL)
    clean_text = re.sub(r"\**SEARCH_QUERY:?.*", "", clean_text, flags=re.IGNORECASE)
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

    # 📧 EMAIL ASSISTANT (Placed after PDF button)
    if st.session_state.get("email_draft"):
        with st.expander("📧 Email Draft (Copy & Paste)", expanded=False):
            # We add a dynamic key based on text length to FORCE Streamlit to refresh the widget
            # whenever the text changes.
            st.text_area(
                "Client Email", 
                value=st.session_state["email_draft"], 
                height=300,
                key=f"email_output_{len(raw_text)}" 
            )
            st.caption("Tip: Copy this into your mail app and attach the PDF + Video.")

    # 2. SMART VIDEO ANALYSIS
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
import streamlit as st
import os
import time
import tempfile
import re
import json
from dotenv import load_dotenv
from tools.report_generator import create_pdf, TRANSLATIONS
from tools.video_editor import create_viral_clip, extract_frame, normalize_input_video

# --- KEEPING THE MODULAR ARCHITECTURE ---
from agent.state import AgentState

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

# --- HELPER: ROBUST JSON EXTRACTOR ---
def extract_clean_json(text):
    """
    Hunts for JSON data even if the LLM messes up the formatting
    or forgets the 'JSON_DATA:' label.
    """
    json_str = ""
    
    # 1. Try finding the standard label
    match = re.search(r"JSON_DATA:\s*(.*)", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # 2. If label missing, find the last large {...} block
        # We assume the JSON is at the end of the response
        matches = list(re.finditer(r"(\{.*\})", text, re.DOTALL))
        if matches:
            json_str = matches[-1].group(1)
    
    if not json_str:
        return {}

    # 3. Clean up LLM artifacts
    # Remove markdown code blocks
    json_str = re.sub(r"```json", "", json_str, flags=re.IGNORECASE)
    json_str = re.sub(r"```", "", json_str)
    # Remove the specific "json" keyword inside braces hallucination
    json_str = re.sub(r"^{\s*json\s*", "{", json_str.strip(), flags=re.IGNORECASE)
    
    try:
        return json.loads(json_str)
    except Exception:
        # 4. Last ditch: Extract substring from first { to last }
        try:
            start = json_str.find('{')
            end = json_str.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(json_str[start:end])
        except:
            pass
    return {}

# --- MAIN APP ---
st.set_page_config(page_title="Court Lens AI", page_icon="🎾", layout="wide")


# --- 🔒 GATEKEEPER LOGIC (Insert after st.set_page_config) ---
# --- 🔒 GATEKEEPER LOGIC (Upgraded for Roles) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = "user" # Default is standard user
if "dev_mode" not in st.session_state:   # <--- NEW
    st.session_state.dev_mode = False

def check_password():
    """Checks password and assigns role (User vs Creator)."""
    if st.session_state.authenticated:
        return True

    st.title("🔒 Court Lens AI")
    st.markdown("### Private Beta Access")
    
    password_input = st.text_input("Access Code", type="password")
    
    if st.button("Login"):
        # 1. Get Secrets (Support both Cloud and Local)
        std_code = os.environ.get("ACCESS_CODE", st.secrets.get("ACCESS_CODE"))
        creator_code = os.environ.get("CREATOR_CODE", st.secrets.get("CREATOR_CODE"))
        dev_code = os.environ.get("DEV_CODE", st.secrets.get("DEV_CODE")) # <--- NEW SECRET

        # 2. Check Input
        if password_input == std_code:
            st.session_state.authenticated = True
            st.session_state.user_role = "user"
            st.session_state.dev_mode = False
            st.success("✅ Welcome, Player!")
            time.sleep(1); st.rerun()
            
        elif password_input == creator_code:
            st.session_state.authenticated = True
            st.session_state.user_role = "creator"
            st.session_state.dev_mode = False
            st.success("✅ Welcome, Creator!")
            time.sleep(1); st.rerun()
            
        elif password_input == dev_code:  # <--- NEW LOGIC
            st.session_state.authenticated = True
            st.session_state.user_role = "creator" # Devs get creator features too
            st.session_state.dev_mode = True       # The Magic Flag
            st.success("🛠️ DEV MODE ACTIVE: AI Bypassed.")
            time.sleep(1); st.rerun()
            
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
    # 1. Determine correct extension (.mov or .mp4)
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    if file_ext not in [".mp4", ".mov"]:
        file_ext = ".mp4" # Default fallback
        
    # 2. Save with correct extension
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    tfile.write(uploaded_file.read())
    raw_video_path = tfile.name
    tfile.close()
    
    # 3. Normalize (Compress & Fix Codec)
    with st.spinner("🔄 Optimizing video for AI (Compressing)..."):
        # This will now convert MOV -> MP4 and 4K -> 720p
        video_content = normalize_input_video(raw_video_path)
    
    # 4. Show the result
    st.video(video_content)

with st.sidebar:
    st.header(t["ui_sec_player"])
    player_description = st.text_input(t["ui_desc_label"], placeholder="e.g. 'Red Shirt'")
    st.divider()
    st.header(t["ui_sec_context"])
    # 1. Player Level (Existing)
    player_level = st.selectbox(t["ui_level_label"], t["ui_level_options"])
    
    # 2. Handedness (NEW FIX)
    handedness = st.radio("Dominant Hand / Mão Dominante", ["Right (Destro)", "Left (Canhoto)"])
    player_notes = st.text_area(t["ui_notes_label"])
    analysis_focus = st.multiselect(t["ui_focus_label"], t["focus_areas"], default=[t["focus_areas"][0]])

    # 3. Stroke Type (NEW FORCE FIX)
    stroke_type = st.selectbox(
        "Primary Stroke / Golpe Principal", 
        ["Match Play / Rally (Mixed)", "Forehand", "Backhand", "Serve", "Volley", "Overhead"]
    )

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
            "handedness": handedness,
            "stroke_type": stroke_type,
            "report_type": report_type,
            "language": selected_lang,
            "creator_mode": creator_mode,
            "dev_mode": st.session_state.dev_mode # <--- PASS THIS
        }

        # 🔍 LOGGING: Check your terminal
        print(f"\n🚀 SENDING TO AGENT -> Dev Mode: {st.session_state.dev_mode}")

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

    # --- 1. ROBUST DATA EXTRACTION (The Fix) ---
    json_data = extract_clean_json(raw_text)
    
    # 🧹 CLEANING
    # Remove the JSON block from the text display so it looks clean
    clean_text = raw_text
    if json_data:
        # Strip out the last {} block if we successfully parsed data
        clean_text = re.sub(r"\{.*\}$", "", clean_text, flags=re.DOTALL).strip()

    # Fallback cleaning for standard labels
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

    # --- NEW: VISUAL EVIDENCE EXTRACTION ---
    image_assets = {}
    
    # --- IMAGE EXTRACTION ---
    image_assets = {}
        
    if saved_video_path and os.path.exists(saved_video_path):
        with st.spinner("📸 Extracting frames for PDF..."):
            # 1. Cover
            cover_path = extract_frame(saved_video_path, 1.0, "temp_cover.jpg")
            if cover_path: image_assets["cover"] = cover_path
            
           # 2. Best Shot (Smart Extraction)
            if "best_shot" in json_data:
                shot = json_data["best_shot"]
                # Look for the Smart Timestamp
                capture_point = shot.get('key_moment')
                
                # FALLBACK: If AI didn't give a key_moment, DO NOT SHOW IMAGE (Cleaner Report)
                if capture_point is not None:
                    path = extract_frame(saved_video_path, int(capture_point), "temp_best.jpg")
                    if path: 
                        image_assets["best"] = path
                        image_assets["best_reason"] = shot.get("reason", "Good execution")
            
            # 3. Fix Shot (Smart Extraction)
            if "fix_shot" in json_data:
                shot = json_data["fix_shot"]
                capture_point = shot.get('key_moment')
                
                # FALLBACK: If AI didn't give a key_moment, DO NOT SHOW IMAGE
                if capture_point is not None:
                    path = extract_frame(saved_video_path, int(capture_point), "temp_fix.jpg")
                    if path: 
                        image_assets["fix"] = path
                        image_assets["fix_reason"] = shot.get("reason", "Needs correction")

    try:
        # Pass the new image_assets dictionary to the PDF generator
        pdf_bytes = create_pdf(
            clean_text, 
            player_description, 
            player_level, 
            selected_lang, 
            report_type, 
            video_link,
            images=image_assets,
            confidence_data=json_data.get("confidence_log", [])
        )
        
        st.download_button(
            label=t["ui_download_btn"], 
            data=bytes(pdf_bytes), 
            file_name="CourtLens_Analysis.pdf", 
            mime="application/pdf"
        )
        
        # Cleanup temp images
        for key in ["cover", "best", "fix"]:
            if key in image_assets and os.path.exists(image_assets[key]):
                os.remove(image_assets[key])
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

    # 2. SMART VIDEO ANALYSIS (UI Display)
    if json_data and st.session_state.user_role == "creator":
        st.divider()
        st.subheader("🎬 Smart Video Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if "best_shot" in json_data:
                shot = json_data["best_shot"]
                st.success(f"✅ **Best Shot:** {shot.get('reason', 'N/A')}")
                if st.button("✂️ Create Highlight Reel"):
                    if saved_video_path:
                        path = create_viral_clip(saved_video_path, shot['start'], shot['end'])
                        if path: st.video(path)

        with col2:
            if "fix_shot" in json_data:
                shot = json_data["fix_shot"]
                st.error(f"⚠️ **Needs Work:** {shot.get('reason', 'N/A')}")
                if st.button("✂️ Create Analysis Clip"):
                    if saved_video_path:
                        path = create_viral_clip(saved_video_path, shot['start'], shot['end'])
                        if path: st.video(path)

    # 3. AI CONFIDENCE AUDIT (New Feature)
    if "confidence_log" in json_data:
        with st.expander("🤖 AI Confidence Audit (Beta)", expanded=False):
            st.caption("The AI self-evaluates the visibility of its observations.")
            
            for log in json_data["confidence_log"]:
                claim = log.get("claim", "Unknown Claim")
                score = float(log.get("confidence_score", 0))
                evidence = log.get("evidence", "No evidence cited")
                
                # Dynamic Color based on score
                color = "green" if score >= 8.5 else "orange"
                if score < 8.0: color = "red"
                
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**Claim:** {claim}")
                    st.caption(f"*Evidence: {evidence}*")
                with col_b:
                    st.progress(score / 10)
                    st.markdown(f":{color}[**{score}/10**]")
                st.divider()
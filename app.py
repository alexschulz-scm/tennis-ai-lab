import streamlit as st
import os
import time
import tempfile
import requests
import yt_dlp
from dotenv import load_dotenv
from google import genai
from google.genai import types
from fpdf import FPDF
from urllib.parse import urlparse

# 1. Load Environment Variables
load_dotenv()

# --- DEBUGGING: PRINT THE KEY IDENTITY (Remove this after it works) ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    # st.write(f"🔑 DEBUG: App is using key ending in: ...{api_key[-4:]}")
except Exception:
    st.error("❌ Google API Key not found in Secrets.")
    st.stop()

# --- TRANSLATIONS CONFIGURATION ---
TRANSLATIONS = {
    "English": {
        "pdf_title": "MATCH ANALYSIS",
        "pdf_subtitle": "AI-POWERED PERFORMANCE REVIEW",
        "pdf_header": "TENNIS AI LAB | Performance Report",
        "label_player": "Player",
        "label_level": "Level",
        "label_date": "Date",
        "label_coach": "Coach's Analysis:",
        "context_label": "Context & Notes:",
        "prompt_instruction": "Respond in English."
    },
    "Portuguese": {
        "pdf_title": "ANÁLISE TÉCNICA",
        "pdf_subtitle": "RELATÓRIO DE PERFORMANCE COM IA",
        "pdf_header": "TENNIS AI LAB | Relatório Técnico",
        "label_player": "Atleta",
        "label_level": "Nível",
        "label_date": "Data",
        "label_coach": "Análise do Treinador:",
        "context_label": "Contexto e Notas:",
        "prompt_instruction": "Responda em Português Brasileiro. Use termos técnicos de tênis adequados (ex: 'Topspin', 'Slice', 'Voleio')."
    }
}

# --- CONSTANTS ---
PRIMARY_COLOR = (0, 51, 102)    
ACCENT_COLOR = (102, 204, 0)    
TEXT_COLOR = (50, 50, 50)       
BG_COLOR = (245, 245, 245)      

# --- PDF CLASS ---
class ProReport(FPDF):
    def __init__(self, player_name, level, lang_key):
        super().__init__()
        self.player_name = player_name
        self.level = level
        self.labels = TRANSLATIONS[lang_key]
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=20, top=20, right=20)

    def header(self):
        if self.page_no() == 1: return
        self.set_fill_color(*PRIMARY_COLOR)
        self.rect(0, 0, 210, 15, 'F') 
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(255, 255, 255)
        self.set_xy(20, 4)
        self.cell(0, 8, clean_for_pdf(self.labels["pdf_header"]), align='L')
        self.set_xy(0, 4)
        self.cell(190, 8, clean_for_pdf(f"{self.player_name}"), align='R')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def create_cover_page(self, context_text):
        self.add_page()
        self.set_fill_color(*PRIMARY_COLOR)
        self.rect(0, 0, 210, 297, 'F')
        
        # Title
        self.set_y(80)
        self.set_font('Helvetica', 'B', 36)
        self.set_text_color(255, 255, 255) 
        self.cell(0, 20, clean_for_pdf(self.labels["pdf_title"]), align='C', new_x="LMARGIN", new_y="NEXT")
        
        # Subtitle
        self.set_font('Helvetica', '', 18)
        self.set_text_color(*ACCENT_COLOR) 
        self.cell(0, 10, clean_for_pdf(self.labels["pdf_subtitle"]), align='C', new_x="LMARGIN", new_y="NEXT")
        
        # Info Box
        box_x = 40
        box_y = 150
        box_w = 130
        
        self.ln(40)
        self.set_fill_color(255, 255, 255)
        self.rect(box_x, box_y, box_w, 60, 'F')
        
        self.set_xy(box_x + 5, box_y + 5)
        self.set_text_color(*TEXT_COLOR)
        
        # Player Info
        self.set_font('Helvetica', 'B', 14)
        self.multi_cell(box_w - 10, 8, clean_for_pdf(f"{self.labels['label_player']}: {self.player_name}"), align='C')
        
        self.set_x(box_x + 5) 
        self.set_font('Helvetica', '', 12)
        self.cell(box_w - 10, 8, clean_for_pdf(f"{self.labels['label_level']}: {self.level}"), align='C', new_x="LMARGIN", new_y="NEXT")
        
        self.set_x(box_x + 5)
        self.cell(box_w - 10, 8, f"{self.labels['label_date']}: {time.strftime('%d/%m/%Y')}", align='C', new_x="LMARGIN", new_y="NEXT")

    def chapter_body(self, text):
        self.add_page()
        self.set_text_color(*TEXT_COLOR)
        self.set_font('Helvetica', '', 11)
        
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, clean_for_pdf(self.labels["label_coach"]), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_font('Helvetica', '', 11)

        width = self.epw 
        lines = text.split('\n')
        
        for line in lines:
            safe_line = clean_for_pdf(line).strip()
            if not safe_line:
                self.ln(4)
                continue
            
            if safe_line.startswith('**') and safe_line.endswith('**'):
                self.ln(5)
                self.set_fill_color(240, 240, 240)
                self.set_font('Helvetica', 'B', 12)
                self.set_text_color(*PRIMARY_COLOR)
                self.cell(width, 8, safe_line.replace('**', ''), fill=True, new_x="LMARGIN", new_y="NEXT")
                self.set_font('Helvetica', '', 11)
                self.set_text_color(*TEXT_COLOR)
            elif safe_line.startswith('- ') or safe_line.startswith('* '):
                indent = 8
                self.set_x(self.l_margin + indent) 
                self.cell(5, 5, chr(149), align='R') 
                bullet_width = width - indent - 5
                self.multi_cell(bullet_width, 5, safe_line[1:].strip())
            else:
                self.set_x(self.l_margin) 
                self.multi_cell(width, 6, safe_line)

# --- HELPER FUNCTIONS ---

def download_youtube_video(url):
    """Downloads YouTube video to a local file so we can upload it to Gemini."""
    output_filename = "temp_video.mp4"
    
    # Remove old file if it exists
    if os.path.exists(output_filename):
        os.remove(output_filename)
    
    # Configuration to download a single MP4 file
    ydl_opts = {
        'format': 'best[ext=mp4]', 
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True,
    }
    
    status_msg = st.empty()
    status_msg.info("⏳ Downloading video from YouTube... (This may take 10-20 seconds)")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        status_msg.success("✅ Download complete! Sending to Gemini...")
        time.sleep(1) 
        status_msg.empty() 
        return output_filename
    except Exception as e:
        status_msg.error(f"❌ Download failed: {e}")
        return None

def clean_for_pdf(text):
    """Sanitizes text for PDF generation."""
    replacements = {
        "–": "-", "—": "--", "“": '"', "”": '"', 
        "‘": "'", "’": "'", "…": "...", "•": "-", 
        "✔": "[OK]", "❌": "[X]", "🎾": "[Tennis]" 
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')

def create_pdf(analysis_text, player_desc, context_text, level_text, lang_key):
    pdf = ProReport(player_desc, level_text, lang_key)
    pdf.create_cover_page(context_text)
    pdf.chapter_body(analysis_text)
    return pdf.output(dest='S')

def download_file_from_url(url):
    try:
        with st.spinner("Downloading video from URL..."):
            response = requests.get(url, stream=True)
            response.raise_for_status()
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            for chunk in response.iter_content(chunk_size=8192):
                tfile.write(chunk)
            tfile.close()
            return tfile.name
    except Exception as e:
        st.error(f"Download Error: {e}")
        return None

# --- MAIN PAGE LAYOUT ---
st.set_page_config(page_title="Tennis AI Lab", page_icon="🎾", layout="wide")

st.title("🎾 Tennis AI Lab")
st.markdown("AI Professional Video Analysis for Tennis Coaches & Players")

# Tabs
tab1, tab2 = st.tabs(["📂 Upload Video File", "🔗 Web Link (YouTube/OneDrive)"])

video_content = None # This will store the path to the LOCAL file (uploaded or downloaded)
is_youtube_link = False
youtube_url_str = None

# TAB 1: Local Upload
with tab1:
    uploaded_file = st.file_uploader("Drop a video here (MP4, MOV)", type=["mp4", "mov"])
    if uploaded_file:
        st.video(uploaded_file)
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_file.read())
        video_content = tfile.name
        tfile.close()

# TAB 2: Web Link
with tab2:
    web_url = st.text_input("Paste Video URL", placeholder="https://youtube.com/... or OneDrive direct link")
    if web_url:
        domain = urlparse(web_url).netloc
        if "youtube" in domain or "youtu.be" in domain:
            st.video(web_url)
            is_youtube_link = True
            youtube_url_str = web_url # Store URL to download later
        else:
            if st.button("Load Web Video"):
                downloaded_path = download_file_from_url(web_url)
                if downloaded_path:
                    st.video(downloaded_path)
                    video_content = downloaded_path

# --- SIDEBAR: CONFIGURATION ---
with st.sidebar:
    st.title("⚙️ Analysis Setup")
    language_choice = st.selectbox("Report Language", ["English", "Portuguese"])
    st.header("1. Target Player")
    st.info("💡 Critical if multiple people are visible.")
    player_description = st.text_input("Who should I watch?", placeholder="e.g. 'Player in red shirt'")
    st.divider()
    st.header("2. Context & Goals")
    player_level = st.selectbox("Player Level", ["Junior / Beginner", "High School / Club", "College / Advanced", "Professional"])
    player_notes = st.text_area("Specific Issues / Context:", placeholder="e.g. 'Recovering from wrist injury'")
    analysis_focus = st.multiselect("Focus Areas:", ["Biomechanics (Technique)", "Tactical Choices", "Footwork & Movement", "Mental Game"], default=["Biomechanics (Technique)"])
    st.divider()

# --- ACTION AREA ---
col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
        
        # Validation
        if not video_content and not is_youtube_link:
            st.warning("⚠️ Please upload a video first.")
            st.stop()
            
        if not player_description:
            st.warning("⚠️ Please describe WHO to watch in the sidebar.")
            st.stop()

        try:
            client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
            
            # --- CRITICAL FIX: UNIFIED UPLOAD PATH ---
            # If it's YouTube, we DOWNLOAD it first, then treat it as a local file.
            # We NO LONGER pass the URL to Gemini directly.
            
            final_file_path = video_content # Default to local file
            
            if is_youtube_link:
                # Run the downloader bypass
                final_file_path = download_youtube_video(youtube_url_str)
                if not final_file_path:
                    st.stop() # Download failed
            
            # Now we upload the physical file (whether from user or from YouTube)
            with st.spinner("Uploading video to AI Engine..."):
                video_file = client.files.upload(file=final_file_path)
            
            # Polling Loop
            status_text = st.empty()
            bar = st.progress(0)
            while video_file.state.name == "PROCESSING":
                status_text.caption("⏳ AI is processing video frames...")
                time.sleep(2)
                video_file = client.files.get(name=video_file.name)
                bar.progress(50)
            
            if video_file.state.name == "FAILED":
                st.error("Processing failed.")
                st.stop()
            
            bar.progress(100)
            status_text.empty()
            gemini_video_part = video_file

            # Build Prompt
            full_prompt = f"""
            You are an elite tennis performance coach (ATP/WTA level).
            
            TARGET PLAYER IDENTITY: {player_description}
            PLAYER LEVEL: {player_level}
            CONTEXT/NOTES: {player_notes}
            FOCUS AREAS: {', '.join(analysis_focus)}

            LANGUAGE INSTRUCTION: {TRANSLATIONS[language_choice]['prompt_instruction']}
            
            INSTRUCTIONS:
            1. Start with a "Quick Assessment" (2-3 sentences summary).
            2. Provide detailed observation based on the Focus Areas selected.
            3. End with 3 specific "Drills or Cues" to fix the main issue.
            
            Tone: Professional, encouraging, but technically precise.
            """
            
            # Generate
            with st.spinner("🤖 Analyzing biomechanics and tactics..."):
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[gemini_video_part, full_prompt]
                )

            # Display Results
            st.success("Analysis Complete!")
            st.markdown("### 📋 Coach's Report")
            st.markdown(response.text)
            
            # PDF Generation
            try:
                pdf_bytes = create_pdf(response.text, player_description, player_notes, player_level, language_choice)
                st.download_button(
                    label="📥 Download PDF Report",
                    data=bytes(pdf_bytes),
                    file_name="tennis_analysis.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"⚠️ PDF Generation Failed: {e}")
            
        finally:
            # Clean up temp files
            if is_youtube_link and final_file_path and os.path.exists(final_file_path):
                os.unlink(final_file_path)
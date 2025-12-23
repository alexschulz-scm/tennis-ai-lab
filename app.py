import streamlit as st
import os
import time
import tempfile
import re
import qrcode
from dotenv import load_dotenv
from google import genai
from fpdf import FPDF

# 1. Load Environment Variables
load_dotenv()

# --- CONFIGURATION & TRANSLATIONS ---
TRANSLATIONS = {
    "English": {
        "ui_title": "🎾 Tennis AI Lab",
        "ui_subtitle": "AI Professional Video Analysis for Tennis Coaches & Players",
        "ui_mode_label": "Report Type",
        "ui_mode_options": ["⚡ Quick Fix (1 Issue + Drill)", "📋 Full Professional Audit (Deep Dive)"],
        "prompt_instruction": "Respond in English.",
        "ui_upload_label": "📂 Upload Video (MP4, MOV)",
        "ui_btn_analyze": "🚀 Run Analysis",
        "ui_success": "Analysis Complete!",
        "ui_download_btn": "📥 Download PDF Report",
        "ui_warning_video": "⚠️ Please upload a video first.",
        "ui_warning_desc": "⚠️ Please describe WHO to watch in the sidebar.",
        "ui_sec_player": "1. Target Player",
        "ui_desc_label": "Who should I watch?",
        "ui_sec_context": "2. Context & Goals",
        "ui_level_label": "Player Level",
        "ui_notes_label": "Context / Notes:",
        "ui_focus_label": "Focus Areas:",
        "levels": ["Junior / Beginner", "High School / Club", "College / Advanced", "Professional"],
        "focus_areas": ["Biomechanics (Technique)", "Tactical Choices", "Footwork & Movement", "Mental Game"],
        # FIXED LINE BELOW (Removed Emoji):
        "pdf_watch_video": ">> WATCH DRILL VIDEO (Click Here)",
        "pdf_scan_qr": "Scan to watch on phone"
    },
    "Portuguese": {
        "ui_title": "🎾 Tennis AI Lab",
        "ui_subtitle": "Análise de Vídeo Profissional com IA",
        "ui_mode_label": "Tipo de Relatório",
        "ui_mode_options": ["⚡ Correção Rápida (1 Erro + Drill)", "📋 Auditoria Completa (Análise Profunda)"],
        "prompt_instruction": "Responda em Português Brasileiro. Use termos técnicos de tênis adequados.",
        "ui_upload_label": "📂 Enviar Vídeo (MP4, MOV)",
        "ui_btn_analyze": "🚀 Iniciar Análise",
        "ui_success": "Análise Concluída!",
        "ui_download_btn": "📥 Baixar Relatório PDF",
        "ui_warning_video": "⚠️ Por favor, envie um vídeo primeiro.",
        "ui_warning_desc": "⚠️ Por favor, descreva QUEM devo analisar.",
        "ui_sec_player": "1. Identificação",
        "ui_desc_label": "Quem devo analisar?",
        "ui_sec_context": "2. Contexto e Objetivos",
        "ui_level_label": "Nível do Atleta",
        "ui_notes_label": "Contexto / Notas:",
        "ui_focus_label": "Áreas de Foco:",
        "levels": ["Iniciante / Junior", "Clube / Amador", "Avançado / Universitário", "Profissional"],
        "focus_areas": ["Biomecânica (Técnica)", "Tática e Decisão", "Jogos de Perna (Footwork)", "Mental"],
        # FIXED LINE BELOW (Removed Emoji):
        "pdf_watch_video": ">> ASSISTIR VIDEO DO DRILL (Clique Aqui)",
        "pdf_scan_qr": "Escaneie para ver no celular"
    }
}

# --- PDF CLASS ---
class ProReport(FPDF):
    def __init__(self, player_name, level, lang_key, report_type):
        super().__init__()
        self.player_name = player_name
        self.level = level
        self.lang_key = lang_key
        self.labels = TRANSLATIONS[lang_key]
        self.report_type = report_type
        self.header_text = "TENNIS AI LAB | " + ("Quick Fix" if "Quick" in report_type or "Rápida" in report_type else "Full Audit")
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=20, top=20, right=20)

    def header(self):
        if self.page_no() == 1: return
        self.set_fill_color(0, 51, 102) 
        self.rect(0, 0, 210, 15, 'F') 
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(255, 255, 255)
        self.set_xy(20, 4)
        self.cell(0, 8, clean_for_pdf(self.header_text), align='L')
        self.ln(20)

    def create_cover_page(self):
        self.add_page()
        self.set_fill_color(0, 51, 102)
        self.rect(0, 0, 210, 297, 'F')
        
        self.set_y(80)
        self.set_font('Helvetica', 'B', 36)
        self.set_text_color(255, 255, 255) 
        title_text = "QUICK FIX" if "Quick" in self.report_type or "Rápida" in self.report_type else "FULL AUDIT"
        self.cell(0, 20, title_text, align='C', new_x="LMARGIN", new_y="NEXT")
        
        self.set_font('Helvetica', '', 18)
        self.set_text_color(102, 204, 0) 
        self.cell(0, 10, "AI COACH REPORT", align='C', new_x="LMARGIN", new_y="NEXT")
        
        self.ln(40)
        self.set_fill_color(255, 255, 255)
        self.rect(40, 150, 130, 60, 'F')
        self.set_xy(45, 155)
        self.set_text_color(50, 50, 50)
        self.set_font('Helvetica', 'B', 14)
        self.multi_cell(120, 8, clean_for_pdf(f"Player: {self.player_name}"), align='C')
        self.set_x(45)
        self.set_font('Helvetica', '', 12)
        self.cell(120, 8, clean_for_pdf(f"Level: {self.level}"), align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_x(45)
        self.cell(120, 8, f"Date: {time.strftime('%d/%m/%Y')}", align='C', new_x="LMARGIN", new_y="NEXT")

    def chapter_body(self, text, video_link=None):
        self.add_page()
        self.set_text_color(50, 50, 50)
        self.set_font('Helvetica', '', 11)
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, "Analysis:", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_font('Helvetica', '', 11)

        lines = text.split('\n')
        for line in lines:
            safe_line = clean_for_pdf(line).strip()
            # Skip the search query line in the printed text
            if "SEARCH_QUERY:" in safe_line:
                continue
                
            if not safe_line:
                self.ln(4)
                continue
            
            if safe_line.startswith('##') or (safe_line.startswith('**') and safe_line.endswith('**')):
                self.ln(5)
                self.set_fill_color(240, 240, 240)
                self.set_font('Helvetica', 'B', 12)
                self.set_text_color(0, 51, 102)
                content = safe_line.replace('**', '').replace('##', '').strip()
                self.cell(0, 8, content, fill=True, new_x="LMARGIN", new_y="NEXT")
                self.set_font('Helvetica', '', 11)
                self.set_text_color(50, 50, 50)
            elif safe_line.startswith('- ') or safe_line.startswith('* '):
                self.set_x(28)
                self.multi_cell(0, 5, chr(149) + " " + safe_line[1:].strip())
            else:
                self.set_x(20)
                self.multi_cell(0, 6, safe_line)

        # --- ADD VIDEO LINK & QR CODE SECTION ---
        if video_link:
            self.add_page()
            self.set_fill_color(0, 51, 102)
            self.rect(0, 0, 210, 297, 'F')
            
            # Title
            self.set_y(60)
            self.set_font('Helvetica', 'B', 24)
            self.set_text_color(255, 255, 255)
            self.cell(0, 10, "TRAINING RESOURCES", align='C', new_x="LMARGIN", new_y="NEXT")
            
            # 1. Clickable Link (Blue Button style)
            self.ln(20)
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(100, 200, 255) # Light Blue
            # Add Underline
            self.cell(0, 10, clean_for_pdf(self.labels["pdf_watch_video"]), align='C', link=video_link, new_x="LMARGIN", new_y="NEXT")
            
            # 2. QR Code Image
            self.ln(10)
            # Generate QR
            qr = qrcode.QRCode(box_size=10, border=4)
            qr.add_data(video_link)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')
            
            # Save temp QR
            img_path = "temp_qr.png"
            img.save(img_path)
            
            # Center the image (A4 width is 210mm. QR is roughly 80mm wide)
            x_pos = (210 - 80) / 2
            self.image(img_path, x=x_pos, w=80)
            
            # Caption
            self.ln(5)
            self.set_font('Helvetica', '', 12)
            self.set_text_color(200, 200, 200)
            self.cell(0, 10, clean_for_pdf(self.labels["pdf_scan_qr"]), align='C')
            
            # Cleanup
            if os.path.exists(img_path):
                os.remove(img_path)

def clean_for_pdf(text):
    replacements = {
        "–": "-", "—": "--", "“": '"', "”": '"', 
        "‘": "'", "’": "'", "…": "...", "•": "-", 
        "✔": "[OK]", "❌": "[X]", "🎾": "[Tennis]" 
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')

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
        
        # UPLOAD
        with st.spinner("Uploading video to Google AI..."):
            video_file = client.files.upload(file=video_content)
        
        # PROCESSING
        status_box = st.empty()
        while video_file.state.name == "PROCESSING":
            if "English" in selected_lang:
                status_box.info("⏳ AI is watching the video... (10-20s)")
            else:
                status_box.info("⏳ A IA está assistindo ao vídeo... (10-20s)")
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)
        
        if video_file.state.name == "FAILED":
            st.error("Video processing failed.")
            st.stop()
        status_box.empty()

        # PROMPT SETUP
        social_add_on = ""
        if creator_mode:
            social_add_on = """
            --- SOCIAL MEDIA PACK ---
            Identify 2 "Viral Moments" with Timestamps, Hooks, and Captions.
            """

        # INSTRUCTION FOR SEARCH TERM
        search_instruction = """
        FINAL STEP:
        At the very end of your response, on a new line, output a YouTube Search Query for the specific drill you recommended.
        Format it exactly like this:
        SEARCH_QUERY: [Tennis Drill for X]
        (Keep it short, e.g., "Tennis Drill Topspin Forehand" or "Tennis Split Step Drill")
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
        
        # GENERATE
        with st.spinner("🤖 Analyzing & Generating Drill Link..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[video_file, full_prompt]
            )

        st.success(t["ui_success"])
        st.markdown(response.text)
        
        # EXTRACT SEARCH TERM & CREATE LINK
        video_link = None
        match = re.search(r"SEARCH_QUERY:\s*(.*)", response.text, re.IGNORECASE)
        if match:
            query = match.group(1).strip()
            # Create a YouTube Search URL
            clean_query = query.replace(" ", "+")
            video_link = f"https://www.youtube.com/results?search_query={clean_query}"
        else:
            # Fallback if AI forgets
            video_link = "https://www.youtube.com/results?search_query=tennis+training+drills"

        # PDF GENERATION
        try:
            pdf_bytes = create_pdf(response.text, player_description, player_level, selected_lang, report_type, video_link)
            st.download_button(t["ui_download_btn"], data=bytes(pdf_bytes), file_name="analysis_report.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"PDF Error: {e}")

    finally:
        if video_content and os.path.exists(video_content):
            os.unlink(video_content)
import streamlit as st
import os
import time
import tempfile
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
        "focus_areas": ["Biomechanics (Technique)", "Tactical Choices", "Footwork & Movement", "Mental Game"]
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
        "focus_areas": ["Biomecânica (Técnica)", "Tática e Decisão", "Jogos de Perna (Footwork)", "Mental"]
    }
}

# --- PDF CLASS ---
class ProReport(FPDF):
    def __init__(self, player_name, level, lang_key, report_type):
        super().__init__()
        self.player_name = player_name
        self.level = level
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

    def chapter_body(self, text):
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

def clean_for_pdf(text):
    replacements = {
        "–": "-", "—": "--", "“": '"', "”": '"', 
        "‘": "'", "’": "'", "…": "...", "•": "-", 
        "✔": "[OK]", "❌": "[X]", "🎾": "[Tennis]" 
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')

def create_pdf(text, name, level, lang, r_type):
    pdf = ProReport(name, level, lang, r_type)
    pdf.create_cover_page()
    pdf.chapter_body(text)
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
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        
        with st.spinner("Uploading to AI..."):
            video_file = client.files.upload(file=video_content)
        
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)
        
        if video_file.state.name == "FAILED":
            st.error("Processing failed.")
            st.stop()

        # --- "SCHULZ ALGORITHM" PROMPTS ---
        
        social_add_on = ""
        if creator_mode:
            social_add_on = """
            --- SOCIAL MEDIA PACK ---
            Identify 2 "Viral Moments" with Timestamps, Hooks, and Captions.
            """

        # 1. QUICK FIX MODE
        if "Quick" in report_type or "Rápida" in report_type:
            full_prompt = f"""
            You are an elite tennis performance coach (ATP/WTA level).
            TARGET: {player_description}
            LEVEL: {player_level}
            NOTES: {player_notes}
            FOCUS: {', '.join(analysis_focus)}
            LANGUAGE: {t['prompt_instruction']}
            
            REPORT TYPE: QUICK FIX (Actionable, Short, Precise).
            
            STRUCTURE:
            1. **THE MAIN ISSUE:** Identify the ONE technical flaw causing the most trouble. Be direct.
            2. **THE FIX (Drill):** Give one specific drill to fix it today.
            3. **THE CUE:** A 3-word mental trigger to use on court.
            
            Keep it under 300 words. No fluff.
            {social_add_on}
            """
            
        # 2. FULL AUDIT MODE (With Hidden Pro Match)
        else:
            full_prompt = f"""
            You are an elite tennis performance coach (ATP/WTA level).
            TARGET: {player_description}
            LEVEL: {player_level}
            NOTES: {player_notes}
            FOCUS: {', '.join(analysis_focus)}
            LANGUAGE: {t['prompt_instruction']}
            
            REPORT TYPE: FULL PROFESSIONAL AUDIT (Comprehensive).
            
            STRUCTURE:
            ## SECTION 1: COMPREHENSIVE AUDIT
            List 4-5 distinct areas where the player is losing efficiency (Biomechanics, Footwork, Tactics).
            
            ## SECTION 2: BIOMECHANICAL ARCHETYPE (The Diagnosis)
            Analyze the player's Grip, Swing Path, and Stance.
            Match them to ONE of these Pro Archetypes and explain WHY:
            - **The Fluid Attacker (e.g., Federer):** Eastern/Semi-Western grip, smooth kinetic chain.
            - **The Modern Power Player (e.g., Sinner/Alcaraz):** Semi-Western, explosive hip rotation, open stance.
            - **The Spin Grinder (e.g., Nadal/Ruud):** Extreme Western, heavy topspin, high clearance.
            - **The Counter-Puncher (e.g., Djokovic/Medvedev):** Efficient redirection, incredible balance.
            
            Tell the user: "Your Biomechanical Archetype closest match is: [PRO NAME]" and explain the similarity.
            
            ## SECTION 3: THE PRIORITY FIX
            "Based on your archetype and the audit, your #1 priority to fix is..."
            
            ## SECTION 4: DIDACTIC LESSON PLAN
            Provide a detailed plan to fix that priority issue:
            - **The Concept:** Physics explanation.
            - **The Drill:** Specific drill (reps/sets).
            - **The Cue:** Mental phrase.
            
            {social_add_on}
            """
        
        with st.spinner("🤖 Analyzing biomechanics & diagnosing archetype..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[video_file, full_prompt]
            )

        st.success(t["ui_success"])
        st.markdown(response.text)
        
        try:
            pdf_bytes = create_pdf(response.text, player_description, player_level, selected_lang, report_type)
            st.download_button(t["ui_download_btn"], data=bytes(pdf_bytes), file_name="analysis_report.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"PDF Error: {e}")

    finally:
        if video_content and os.path.exists(video_content):
            os.unlink(video_content)
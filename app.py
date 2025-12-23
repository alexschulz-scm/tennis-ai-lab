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
        # PDF Content
        "pdf_title": "MATCH ANALYSIS",
        "pdf_subtitle": "AI-POWERED PERFORMANCE REVIEW",
        "pdf_header": "TENNIS AI LAB | Performance Report",
        "label_player": "Player",
        "label_level": "Level",
        "label_date": "Date",
        "label_coach": "Coach's Analysis:",
        "context_label": "Context & Notes:",
        "prompt_instruction": "Respond in English.",
        
        # UI Interface
        "ui_title": "🎾 Tennis AI Lab",
        "ui_subtitle": "AI Professional Video Analysis for Tennis Coaches & Players",
        "ui_upload_label": "📂 Upload Video (MP4, MOV)",
        "ui_sidebar_title": "⚙️ Analysis Setup",
        "ui_lang_label": "App Language / Idioma",
        "ui_sec_player": "1. Target Player",
        "ui_desc_placeholder": "e.g. 'Player in red shirt'",
        "ui_desc_label": "Who should I watch?",
        "ui_sec_context": "2. Context & Goals",
        "ui_level_label": "Player Level",
        "ui_notes_label": "Specific Issues / Context:",
        "ui_focus_label": "Focus Areas:",
        "ui_btn_analyze": "🚀 Run Analysis",
        "ui_success": "Analysis Complete!",
        "ui_download_btn": "📥 Download PDF Report",
        "ui_warning_video": "⚠️ Please upload a video first.",
        "ui_warning_desc": "⚠️ Please describe WHO to watch in the sidebar.",
        "levels": ["Junior / Beginner", "High School / Club", "College / Advanced", "Professional"],
        "focus_areas": ["Biomechanics (Technique)", "Tactical Choices", "Footwork & Movement", "Mental Game"]
    },
    "Portuguese": {
        # PDF Content
        "pdf_title": "ANÁLISE TÉCNICA",
        "pdf_subtitle": "RELATÓRIO DE PERFORMANCE COM IA",
        "pdf_header": "TENNIS AI LAB | Relatório Técnico",
        "label_player": "Atleta",
        "label_level": "Nível",
        "label_date": "Data",
        "label_coach": "Análise do Treinador:",
        "context_label": "Contexto e Notas:",
        "prompt_instruction": "Responda em Português Brasileiro. Use termos técnicos de tênis adequados (ex: 'Topspin', 'Slice', 'Voleio').",
        
        # UI Interface
        "ui_title": "🎾 Tennis AI Lab",
        "ui_subtitle": "Análise de Vídeo Profissional com IA",
        "ui_upload_label": "📂 Enviar Vídeo (MP4, MOV)",
        "ui_sidebar_title": "⚙️ Configuração",
        "ui_lang_label": "Idioma / Language",
        "ui_sec_player": "1. Identificação",
        "ui_desc_placeholder": "ex: 'Jogador de camisa vermelha'",
        "ui_desc_label": "Quem devo analisar?",
        "ui_sec_context": "2. Contexto e Objetivos",
        "ui_level_label": "Nível do Atleta",
        "ui_notes_label": "Notas / Histórico de Lesão:",
        "ui_focus_label": "Áreas de Foco:",
        "ui_btn_analyze": "🚀 Iniciar Análise",
        "ui_success": "Análise Concluída!",
        "ui_download_btn": "📥 Baixar Relatório PDF",
        "ui_warning_video": "⚠️ Por favor, envie um vídeo primeiro.",
        "ui_warning_desc": "⚠️ Por favor, descreva QUEM devo analisar na barra lateral.",
        "levels": ["Iniciante / Junior", "Clube / Amador", "Avançado / Universitário", "Profissional"],
        "focus_areas": ["Biomecânica (Técnica)", "Tática e Decisão", "Jogos de Perna (Footwork)", "Mental"]
    }
}

# --- CONSTANTS ---
PRIMARY_COLOR = (0, 51, 102)    
ACCENT_COLOR = (102, 204, 0)    
TEXT_COLOR = (50, 50, 50)       

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

# --- MAIN PAGE LAYOUT ---
st.set_page_config(page_title="Tennis AI Lab", page_icon="🎾", layout="wide")

# --- LANGUAGE SETUP ---
# Simple query param check or default to English
if "lang" not in st.session_state:
    st.session_state.lang = "English"

def set_language():
    # Callback to update language
    pass

with st.sidebar:
    st.title("⚙️ Config")
    # This widget controls the whole app language
    selected_lang = st.selectbox(
        "Language / Idioma", 
        ["English", "Portuguese"], 
        key="lang_select"
    )
    
    # 🕵️ CREATOR MODE (Hidden Toggle)
    st.divider()
    creator_mode = st.checkbox("Creator Mode (Social Media)", value=False)
    if creator_mode:
        st.caption("✅ Enabled: Reports will include Instagram/Reels suggestions.")

# Load the dictionary for the selected language
t = TRANSLATIONS[selected_lang]

# --- UI CONTENT ---
st.title(t["ui_title"])
st.markdown(t["ui_subtitle"])

# --- FILE UPLOADER ---
video_content = None
uploaded_file = st.file_uploader(t["ui_upload_label"], type=["mp4", "mov"])

if uploaded_file:
    st.video(uploaded_file)
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    video_content = tfile.name
    tfile.close()

# --- SIDEBAR: REST OF CONFIG ---
with st.sidebar:
    st.header(t["ui_sec_player"])
    st.info("💡 " + ("Critical if multiple people are visible." if selected_lang == "English" else "Crítico se houver várias pessoas."))
    player_description = st.text_input(t["ui_desc_label"], placeholder=t["ui_desc_placeholder"])
    
    st.divider()
    
    st.header(t["ui_sec_context"])
    player_level = st.selectbox(t["ui_level_label"], t["levels"])
    player_notes = st.text_area(t["ui_notes_label"], placeholder="...")
    analysis_focus = st.multiselect(t["ui_focus_label"], t["focus_areas"], default=[t["focus_areas"][0]])

# --- ACTION AREA ---
col1, col2 = st.columns([2, 1])

with col1:
    if st.button(t["ui_btn_analyze"], type="primary", use_container_width=True):
        
        if not video_content:
            st.warning(t["ui_warning_video"])
            st.stop()
            
        if not player_description:
            st.warning(t["ui_warning_desc"])
            st.stop()

        try:
            client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
            
            with st.spinner("Uploading video to AI Engine..."):
                video_file = client.files.upload(file=video_content)
            
            # Polling Loop
            status_text = st.empty()
            bar = st.progress(0)
            while video_file.state.name == "PROCESSING":
                status_text.caption("⏳ AI processing..." if selected_lang == "English" else "⏳ IA processando...")
                time.sleep(2)
                video_file = client.files.get(name=video_file.name)
                bar.progress(50)
            
            if video_file.state.name == "FAILED":
                st.error("Processing failed.")
                st.stop()
            
            bar.progress(100)
            status_text.empty()
            gemini_video_part = video_file

            # --- DYNAMIC PROMPT BUILDING ---
            
            # 1. Base Instructions
            base_prompt = f"""
            You are an elite tennis performance coach (ATP/WTA level).
            TARGET PLAYER: {player_description}
            LEVEL: {player_level}
            NOTES: {player_notes}
            FOCUS: {', '.join(analysis_focus)}
            LANGUAGE: {t['prompt_instruction']}
            
            STRUCTURE:
            1. Quick Assessment (Summary)
            2. Detailed Observation (Technique & Tactics)
            3. 3 Key Drills/Cues
            """
            
            # 2. Creator Mode Add-on (The "Secret Sauce")
            social_add_on = ""
            if creator_mode:
                social_add_on = """
                
                --- SOCIAL MEDIA CONTENT PACK ---
                (This section is for the editor, separate from the coach report)
                
                Identify 2-3 "Viral Worthy" moments in the video.
                Format exactly like this:
                
                **CLIP 1:** [MM:SS - MM:SS]
                **HOOK:** (A catchy text overlay for the video, e.g., "Stop Hitting Net!")
                **CAPTION:** (A short, engaging Instagram caption with hashtags)
                **WHY:** (Why this moment is shareable - e.g., "Great reaction time" or "Perfect mistake to learn from")
                """

            full_prompt = base_prompt + social_add_on
            
            # Generate
            with st.spinner("🤖 Analyzing..." if selected_lang == "English" else "🤖 Analisando..."):
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[gemini_video_part, full_prompt]
                )

            # Display Results
            st.success(t["ui_success"])
            st.markdown("### 📋 " + t["label_coach"])
            st.markdown(response.text)
            
            # PDF Generation
            # Note: We do NOT include the Social Media part in the PDF (Client doesn't need to see it)
            # We filter it out if needed, or just print everything.
            # For now, let's print everything, but in the future, we can split it.
            
            try:
                pdf_bytes = create_pdf(response.text, player_description, player_notes, player_level, selected_lang)
                st.download_button(
                    label=t["ui_download_btn"],
                    data=bytes(pdf_bytes),
                    file_name=f"tennis_analysis_{selected_lang}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"⚠️ PDF Error: {e}")
            
        finally:
            if video_content and os.path.exists(video_content):
                os.unlink(video_content)
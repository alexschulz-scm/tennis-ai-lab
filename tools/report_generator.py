import time
import os
import re
import qrcode
from PIL import Image
from fpdf import FPDF

TRANSLATIONS = {
    "English": {
        "ui_title": "🎾 Court Lens AI",
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
        "ui_level_options": ["Beginner (NTRP 1.0-2.5)", "Intermediate (NTRP 3.0-4.0)", "Advanced (NTRP 4.5+)", "Pro"],
        "ui_notes_label": "Context / Notes:",
        "ui_focus_label": "Focus Areas:",
        "focus_areas": ["Biomechanics (Technique)", "Tactical Choices", "Footwork & Movement", "Mental Game"],
        "pdf_watch_video": ">> WATCH DRILL VIDEO (Click Here)",
        "pdf_scan_qr": "Scan to watch on phone"
    },
    "Portuguese": {
        "ui_title": "🎾 Court Lens AI",
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
        "ui_level_options": ["Iniciante", "Intermediário", "Avançado", "Profissional"],
        "ui_notes_label": "Contexto / Notas:",
        "ui_focus_label": "Áreas de Foco:",
        "focus_areas": ["Biomecânica (Técnica)", "Tática e Decisão", "Jogos de Perna (Footwork)", "Mental"],
        "pdf_watch_video": ">> ASSISTIR VIDEO DO DRILL (Clique Aqui)",
        "pdf_scan_qr": "Escaneie para ver no celular"
    }
}

class ProReport(FPDF):
    def __init__(self, player_name, level, lang_key, report_type):
        super().__init__()
        self.player_name = player_name
        self.level = level
        self.lang_key = lang_key
        self.labels = TRANSLATIONS[lang_key]
        self.report_type = report_type
        self.header_text = "COURT LENS AI | " + ("Quick Fix" if "Quick" in report_type or "Rápida" in report_type else "Full Audit")
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=20, top=20, right=20)

    def header(self):
        if self.page_no() == 1: return
        self.set_fill_color(0, 101, 189) 
        self.rect(0, 0, 210, 15, 'F') 
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(255, 255, 255) 
        self.set_xy(20, 4)
        self.cell(0, 8, clean_for_pdf(self.header_text), align='L')
        self.ln(20)

    # --- NEW: CALCULATE PROPORTIONAL DIMENSIONS ---
    def get_fitted_dimensions(self, img_path, max_w, max_h):
        try:
            with Image.open(img_path) as img:
                orig_w, orig_h = img.size
            ratio = min(max_w / orig_w, max_h / orig_h)
            new_w = orig_w * ratio
            new_h = orig_h * ratio
            return new_w, new_h
        except:
            return max_w, max_h * 0.56 # Fallback

    def create_cover_page(self, cover_img_path=None):
        self.add_page()
        self.set_fill_color(14, 17, 23)
        self.rect(0, 0, 210, 297, 'F')
        
        self.set_y(40)
        self.set_font('Helvetica', 'B', 36)
        self.set_text_color(255, 255, 255) 
        title_text = "QUICK FIX" if "Quick" in self.report_type or "Rápida" in self.report_type else "FULL AUDIT"
        self.cell(0, 20, title_text, align='C', new_x="LMARGIN", new_y="NEXT")
        
        self.set_font('Helvetica', '', 18)
        self.set_text_color(0, 101, 189) 
        self.cell(0, 10, "COURT LENS AI ANALYSIS", align='C', new_x="LMARGIN", new_y="NEXT")
        
        if cover_img_path and os.path.exists(cover_img_path):
            # --- UPDATED: Use Smart Resize ---
            max_w, max_h = 140, 90
            img_w, img_h = self.get_fitted_dimensions(cover_img_path, max_w, max_h)
            x_pos = (210 - img_w) / 2
            
            self.image(cover_img_path, x=x_pos, y=80, w=img_w, h=img_h)
            self.set_draw_color(0, 101, 189)
            self.set_line_width(1)
            self.rect(x_pos, 80, img_w, img_h)
        
        self.set_fill_color(255, 255, 255)
        self.rect(40, 180, 130, 60, 'F')
        self.set_xy(45, 185)
        self.set_text_color(14, 17, 23)
        self.set_font('Helvetica', 'B', 14)
        self.multi_cell(120, 8, clean_for_pdf(f"Player: {self.player_name}"), align='C')
        self.set_x(45)
        self.set_font('Helvetica', '', 12)
        self.cell(120, 8, clean_for_pdf(f"Level: {self.level}"), align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_x(45)
        self.cell(120, 8, f"Date: {time.strftime('%d/%m/%Y')}", align='C', new_x="LMARGIN", new_y="NEXT")

    def chapter_body(self, text, fix_img_path=None):
        image_inserted = False 
        
        self.add_page()
        self.set_text_color(50, 50, 50)
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, "Detailed Analysis", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        self.set_font('Helvetica', '', 11)

        lines = text.split('\n')

        for line in lines:
            safe_line = clean_for_pdf(line).strip()
            
            # 🛑 FILTER
            if "Shot Log" in safe_line or "JSON_DATA" in safe_line or "SEARCH_QUERY" in safe_line:
                break
                
            if not safe_line:
                self.ln(4)
                continue
            
            # 1. HEADERS
            if safe_line.startswith('##') or (safe_line.startswith('**') and safe_line.endswith('**')):
                self.ln(5)
                self.set_fill_color(240, 240, 240)
                self.set_font('Helvetica', 'B', 12)
                self.set_text_color(0, 101, 189) 
                content = safe_line.replace('**', '').replace('##', '').strip()
                self.cell(0, 8, content, fill=True, new_x="LMARGIN", new_y="NEXT")
                self.set_font('Helvetica', '', 11)
                self.set_text_color(50, 50, 50)
            
            # 2. LISTS
            elif safe_line.startswith('- ') or safe_line.startswith('* '):
                clean_item = safe_line[1:].replace('**', '').strip()
                self.set_x(28)
                self.multi_cell(0, 5, chr(149) + " " + clean_item)
                
            # 3. TEXT
            else:
                self.set_x(20)
                clean_text_line = safe_line.replace('**', '')
                if "The Bad" in safe_line or "Main Issue" in safe_line:
                     self.set_font('Helvetica', 'B', 11)
                     self.multi_cell(0, 6, clean_text_line)
                     self.set_font('Helvetica', '', 11)
                else:
                    self.multi_cell(0, 6, clean_text_line)

            # 4. IMAGE INJECTION
            if fix_img_path and os.path.exists(fix_img_path) and not image_inserted:
                triggers = ["The Bad", "Main Issue", "Correção", "Major Flaws"]
                if any(trigger in safe_line for trigger in triggers):
                    self.ln(5)
                    
                    # --- UPDATED: Use Smart Resize ---
                    max_w, max_h = 120, 80 
                    img_w, img_h = self.get_fitted_dimensions(fix_img_path, max_w, max_h)
                    
                    x_pos = (210 - img_w) / 2
                    if self.get_y() + img_h > 270: self.add_page()
                    
                    self.image(fix_img_path, x=x_pos, w=img_w, h=img_h)
                    self.ln(img_h + 2)
                    
                    self.set_font('Helvetica', 'I', 9)
                    self.set_text_color(200, 0, 0)
                    self.cell(0, 5, "Visual Evidence: Area for Improvement", align='C', new_x="LMARGIN", new_y="NEXT")
                    self.ln(5)
                    self.set_text_color(50, 50, 50)
                    self.set_font('Helvetica', '', 11)
                    image_inserted = True

    # --- NEW: CONFIDENCE SECTION ---
    def add_confidence_section(self, confidence_data):
        if not confidence_data: return
        
        # Ensure we don't start at bottom of page
        if self.get_y() > 200: self.add_page()
        else: self.ln(10)
        
        self.set_fill_color(245, 245, 245)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(14, 17, 23)
        self.cell(0, 10, "AI Confidence Audit (Beta)", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        self.set_font('Helvetica', '', 9)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 5, "The AI self-evaluates the visibility of its observations to ensure accuracy.")
        self.ln(5)

        for log in confidence_data:
            score = float(log.get("confidence_score", 0))
            claim = clean_for_pdf(log.get("claim", "Observation"))
            evidence = clean_for_pdf(log.get("evidence", ""))
            
            # Color Coding for Score
            if score >= 8.5: 
                self.set_text_color(0, 100, 0) # Green
            elif score < 8.0: 
                self.set_text_color(180, 0, 0) # Red
            else: 
                self.set_text_color(200, 120, 0) # Orange
            
            self.set_font('Helvetica', 'B', 11)
            self.cell(0, 6, f"{score}/10  - {claim}", new_x="LMARGIN", new_y="NEXT")
            
            self.set_text_color(100, 100, 100) # Grey
            self.set_font('Helvetica', 'I', 9)
            self.multi_cell(0, 5, f"Evidence: {evidence}")
            self.ln(3)

    def add_qr_page(self, video_link):
        if not video_link: return
        self.add_page()
        self.set_fill_color(14, 17, 23)
        self.rect(0, 0, 210, 297, 'F')
        
        self.set_y(80)
        self.set_font('Helvetica', 'B', 24)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "TRAINING RESOURCES", align='C', new_x="LMARGIN", new_y="NEXT")
        
        self.ln(20)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(0, 101, 189)
        self.cell(0, 10, clean_for_pdf(self.labels["pdf_watch_video"]), align='C', link=video_link, new_x="LMARGIN", new_y="NEXT")
        
        self.ln(10)
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(video_link)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        img_path = "temp_qr.png"
        img.save(img_path)
        x_pos = (210 - 80) / 2
        self.image(img_path, x=x_pos, w=80)
        if os.path.exists(img_path): os.remove(img_path)

def clean_for_pdf(text):
    """Sanitizes text: Removes emojis, markdown stars, and fixes encoding."""
    text = re.sub(r'[^\x00-\x7F]+', '', text) 
    replacements = {
        "–": "-", "—": "--", "“": '"', "”": '"', 
        "‘": "'", "’": "'", "…": "...", "•": "-" 
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- UPDATED CREATE FUNCTION ---
def create_pdf(text, name, level, lang, r_type, video_link, images={}, confidence_data=[]):
    pdf = ProReport(name, level, lang, r_type)
    pdf.create_cover_page(images.get("cover"))
    pdf.chapter_body(text, fix_img_path=images.get("fix"))
    
    # Add the new section
    pdf.add_confidence_section(confidence_data)
    
    pdf.add_qr_page(video_link)
    return pdf.output(dest='S')
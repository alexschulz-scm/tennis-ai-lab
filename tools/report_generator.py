import time
import os
import re
import qrcode
from fpdf import FPDF

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

        # --- ADD VIDEO LINK & QR CODE ---
        if video_link:
            self.add_page()
            self.set_fill_color(0, 51, 102)
            self.rect(0, 0, 210, 297, 'F')
            
            self.set_y(60)
            self.set_font('Helvetica', 'B', 24)
            self.set_text_color(255, 255, 255)
            self.cell(0, 10, "TRAINING RESOURCES", align='C', new_x="LMARGIN", new_y="NEXT")
            
            self.ln(20)
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(100, 200, 255) 
            self.cell(0, 10, clean_for_pdf(self.labels["pdf_watch_video"]), align='C', link=video_link, new_x="LMARGIN", new_y="NEXT")
            
            self.ln(10)
            # QR Generation
            qr = qrcode.QRCode(box_size=10, border=4)
            qr.add_data(video_link)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')
            img_path = "temp_qr.png"
            img.save(img_path)
            
            x_pos = (210 - 80) / 2
            self.image(img_path, x=x_pos, w=80)
            
            self.ln(5)
            self.set_font('Helvetica', '', 12)
            self.set_text_color(200, 200, 200)
            self.cell(0, 10, clean_for_pdf(self.labels["pdf_scan_qr"]), align='C')
            
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


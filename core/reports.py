"""core/reports.py
Generate professional Executive Summary PDF reports.
"""
from datetime import datetime, timezone
import io
from fpdf import FPDF
from core.risk_engine import compute_summary_stats

class ReportPDF(FPDF):
    def header(self):
        # Arial bold 15
        self.set_font('helvetica', 'B', 15)
        self.set_text_color(255, 75, 75)
        # Title
        self.cell(0, 10, 'SupplyRadar - Executive Risk Summary', 0, 1, 'C')
        # Line break
        self.ln(5)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        # Page number
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def sanitize_text(text: str) -> str:
    """Removes unsupported unicode characters like emojis and smart quotes for FPDF latin-1."""
    if not isinstance(text, str):
        return ""
    text = text.replace("—", "-").replace("–", "-").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_executive_pdf(articles: list[dict], profile: dict) -> bytes:
    """Generates a PDF report from the given list of scored articles."""
    pdf = ReportPDF()
    pdf.add_page()
    
    now = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    stats = compute_summary_stats(articles)
    
    # ── Meta Info ───────────────────────────────────────────────────────────
    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(50, 50, 50)
    user_name = sanitize_text(profile.get('name', 'User'))
    ind_name = sanitize_text(profile.get('industry_name', 'General Industry'))
    pdf.cell(0, 6, f"Generated for: {user_name} ({ind_name})", 0, 1)
    pdf.cell(0, 6, f"Date: {now}", 0, 1)
    pdf.ln(10)
    
    # ── Executive Summary Metrics ──────────────────────────────────────────
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "24-Hour Snapshot", border='B', ln=1)
    pdf.ln(2)
    
    pdf.set_font('helvetica', '', 11)
    pdf.cell(0, 6, f"* Total Events Monitored: {stats['total']}", 0, 1)
    pdf.cell(0, 6, f"* HIGH Risk Events: {stats['high']}", 0, 1)
    pdf.cell(0, 6, f"* Watchlist Impacts: {stats['watchlist_hits']}", 0, 1)
    pdf.ln(10)
    
    # ── Watchlist Hits (Highest Priority) ──────────────────────────────────
    wl_hits = [a for a in articles if a.get("watchlist_match", {}).get("is_watchlist_hit")]
    if wl_hits:
        pdf.set_font('helvetica', 'B', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, "Targeted Watchlist Disruptions", border='B', ln=1)
        pdf.ln(2)
        
        pdf.set_font('helvetica', '', 10)
        for a in wl_hits[:5]:
            matched = [m['item'] for m in a.get('watchlist_match', {}).get('matched', [])]
            match_str = ", ".join(matched)
            risk = a.get("risk_level", "Low").upper()
            impact = a.get("impact", {}).get("description", "No impact estimate")
            
            pdf.set_font('helvetica', 'B', 10)
            if risk == "HIGH":
                pdf.set_text_color(200, 0, 0)
            elif risk == "MEDIUM":
                pdf.set_text_color(200, 150, 0)
            else:
                pdf.set_text_color(0, 150, 0)
            pdf.write(6, f"[{risk}] ")
            
            pdf.set_text_color(0, 0, 0)
            pdf.write(6, f"{sanitize_text(a.get('raw_text', ''))}\n")
            
            pdf.set_font('helvetica', 'I', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 5, f"Matches: {sanitize_text(match_str)} | Impact: {sanitize_text(impact)}\n")
        pdf.ln(5)
    
    # ── Top High Risk Global Events ────────────────────────────────────────
    high_risks = [a for a in articles if a.get("risk_level") == "High" and a not in wl_hits]
    if high_risks:
        pdf.set_font('helvetica', 'B', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, "Other Global HIGH Risk Events", border='B', ln=1)
        pdf.ln(2)
        
        for a in high_risks[:5]:
            cat = a.get("category", {}).get("label", "General")
            impact = a.get("impact", {}).get("description", "No impact estimate")
            
            pdf.set_font('helvetica', 'B', 10)
            pdf.set_text_color(200, 0, 0)
            pdf.write(6, f"[{cat}] ")
            
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, sanitize_text(a.get('raw_text', '')))
            
            pdf.set_font('helvetica', 'I', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 5, f"Impact: {sanitize_text(impact)}\n")
    
    # Output to byte string
    pdf_bytes = pdf.output(dest='S')
    return bytes(pdf_bytes)

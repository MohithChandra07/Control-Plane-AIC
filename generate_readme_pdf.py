import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, "ControlPlane.ai — Technical README & Specification")
            self.drawRightString(612 - 54, 750, "Accenture Innovation Challenge 2026")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 742, 612 - 54, 742)
            
        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 612 - 54, 45)
        self.setFont("Helvetica", 8)
        self.drawString(54, 32, "CONFIDENTIAL — ControlPlane.ai Governance Gateway | Accenture Innovation Challenge 2026")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 54, 32, page_text)
        self.restoreState()

def create_readme_pdf(filename="ControlPlane_README_Document.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=64,
        bottomMargin=60
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#4F46E5"),
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#334155"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#0F172A"),
        backColor=colors.HexColor("#F1F5F9"),
        borderColor=colors.HexColor("#CBD5E1"),
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=6,
        spaceAfter=8
    )

    callout_style = ParagraphStyle(
        'Callout_Text',
        parent=body_style,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E1B4B")
    )

    story = []
    
    # Header Title Block
    story.append(Paragraph("ControlPlane.ai", title_style))
    story.append(Paragraph("Enterprise AI Governance & Safety Gateway — Technical README & System Architecture", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4F46E5"), spaceAfter=12))

    # Executive Overview
    story.append(Paragraph("1. Executive Overview & System Architecture", h1_style))
    overview_text = (
        "<b>ControlPlane.ai</b> is an inline enterprise AI governance and safety gateway designed to sit "
        "between AI applications and Large Language Model (LLM) providers/agents. Rather than relying on unmonitored "
        "model output or raw prompt completion, ControlPlane enforces organizational policies, scrutinizes request/response payload claims, "
        "gates high-risk tool calls, and tracks compliance audit logs with cryptographic hash chaining."
    )
    story.append(Paragraph(overview_text, body_style))
    
    arch_flow = (
        "<b>Flow Architecture:</b><br/>"
        "Application Client → ControlPlane Gateway → Upstream AI Model → Response Analysis → Policy Engine → [ALLOW / MODIFY / ESCALATE / BLOCK] → Application Client"
    )
    story.append(Paragraph(arch_flow, code_style))

    # Key Architecture Highlights Table
    table_data = [
        [Paragraph("<b>Component</b>", body_style), Paragraph("<b>Technical Specification & Role</b>", body_style)],
        [Paragraph("<b>Adaptive Scrutiny</b>", body_style), Paragraph("Tier 0 cheap-gate heuristic pre-filter → Tier 1 full pipeline claim verification & PII detection.", body_style)],
        [Paragraph("<b>Claim Verification</b>", body_style), Paragraph("NLP Claim Extractor & Verification against knowledge corpus (SUPPORTED / CONTRADICTED / UNVERIFIABLE).", body_style)],
        [Paragraph("<b>Taint Propagation</b>", body_style), Paragraph("Multi-turn conversation state tracking; flags claims and prevents unverified data from triggering downstream tool calls.", body_style)],
        [Paragraph("<b>Surgical Remediation</b>", body_style), Paragraph("Per-claim remediation (Hedge, Redact, Remove, Cite, Escalate) instead of total response blockage.", body_style)],
        [Paragraph("<b>Tool-Call Gating</b>", body_style), Paragraph("Intercepts high-consequence tools (e.g. money movement, database updates) based on taint state and permission level.", body_style)],
        [Paragraph("<b>Cost Circuit Breaker</b>", body_style), Paragraph("Per-tenant rate and token circuit breaker to prevent denial-of-wallet and quota exhaustion spikes.", body_style)],
        [Paragraph("<b>Audit Ledger</b>", body_style), Paragraph("Cryptographically hash-chained immutable audit log for complete regulatory compliance and forensics.", body_style)]
    ]

    t = Table(table_data, colWidths=[130, 374])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EEF2FF")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Implementation & Features
    story.append(Paragraph("2. Core Technical Capabilities & Implementation Status", h1_style))
    story.append(Paragraph("All 5 project development phases are fully implemented, benchmarked, and test-verified:", body_style))
    
    story.append(Paragraph("• <b>OpenAI API Compatible Gateway:</b> Transparent drop-in replacement endpoint (`http://localhost:8000/v1`) with full request/response interception.", bullet_style))
    story.append(Paragraph("• <b>PII & Safety Scrutiny:</b> Multi-label risk classification (PII regex detection, claim hallucination checking, toxicity & prompt injection filtering).", bullet_style))
    story.append(Paragraph("• <b>Dynamic Risk Appetite Control:</b> Live tenant-level risk appetite slider allowing real-time adjustment of governance strictness without service restarts.", bullet_style))
    story.append(Paragraph("• <b>Human-in-the-Loop & Recalibration:</b> Interactive review interface with automated threshold-triggered recalibration recommendations.", bullet_style))
    story.append(Paragraph("• <b>Management Dashboard Console:</b> Real-time React + FastAPI management console connected to SQLite/PostgreSQL audit ledgers.", bullet_style))

    story.append(Spacer(1, 8))

    # Verification & Benchmarks
    story.append(Paragraph("3. Benchmark & Verification Summary", h1_style))
    story.append(Paragraph("ControlPlane has been rigorously validated through automated suite tests and a 400-item synthetic evaluation benchmark:", body_style))

    bench_data = [
        [Paragraph("<b>Evaluation Metric</b>", body_style), Paragraph("<b>Measured Result</b>", body_style), Paragraph("<b>Impact & Notes</b>", body_style)],
        [Paragraph("Automated Test Suite", body_style), Paragraph("<b>169 / 169 Passing</b>", body_style), Paragraph("100% test coverage across unit & integration scenes.", body_style)],
        [Paragraph("Synthetic Traffic Replayer", body_style), Paragraph("<b>10,000 requests / 100s</b>", body_style), Paragraph("Demonstrated high-throughput audit ledger logging.", body_style)],
        [Paragraph("Calibration Error (ECE)", body_style), Paragraph("<b>Expected Error &lt; 0.05</b>", body_style), Paragraph("Measured alignment between risk scores and true outputs.", body_style)],
        [Paragraph("Scrutiny Performance", body_style), Paragraph("<b>Adaptive Routing</b>", body_style), Paragraph("Balances latency (Tier 0 cheap gate) and accuracy (Tier 1).", body_style)]
    ]

    t_bench = Table(bench_data, colWidths=[140, 130, 234])
    t_bench.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F8FAFC")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_bench)
    story.append(Spacer(1, 10))

    # Quick Start & Deployment
    story.append(Paragraph("4. Quick Start & Execution Guide", h1_style))
    quickstart_code = (
        "# 1. Environment Setup & Installation<br/>"
        "python3 -m venv .venv && source .venv/bin/activate<br/>"
        "pip install -e \".[dev]\"<br/><br/>"
        "# 2. Launch Gateway Service<br/>"
        "uvicorn gateway.main:app --port 8000 --reload<br/><br/>"
        "# 3. Run Validation Test Suite & Benchmark<br/>"
        "pytest<br/>"
        "python -m bench.harness.run_benchmark<br/><br/>"
        "# 4. Launch Governance Console & Dashboard<br/>"
        "uvicorn console.backend.main:app --port 8001<br/>"
        "cd console/frontend && npm install && npm run dev"
    )
    story.append(Paragraph(quickstart_code, code_style))

    # Repository Reference
    story.append(Paragraph("5. Official Repository Reference & Project Team", h1_style))
    story.append(Paragraph("<b>Public GitHub Repository:</b> https://github.com/MohithChandra07/Control-Plane-AIC", body_style))
    story.append(Paragraph("<b>Submission Track:</b> Accenture Innovation Challenge 2026 — Prototype Development", body_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Project Team & Roles:</b>", h2_style))
    story.append(Paragraph("• <b>Mohith Chandra:</b> Team Lead", bullet_style))
    story.append(Paragraph("• <b>Monal Gupta:</b> Core NLP & Fullstack Developer", bullet_style))
    story.append(Paragraph("• <b>Veda Vikas:</b> System Architect & Developer", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    create_readme_pdf()

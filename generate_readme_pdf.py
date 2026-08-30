import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image
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
        self.setFillColor(colors.HexColor("#475569"))
        
        # Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, "ControlPlane.ai — Technical Specification & Architecture Manual")
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
        fontSize=26,
        leading=30,
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
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14.5,
        textColor=colors.HexColor("#334155"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=5
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

    # Image loading helper to prevent execution crashes
    def load_image(path, width=440, height=220):
        if os.path.exists(path):
            img = Image(path, width=width, height=height)
            img.hAlign = 'CENTER'
            return img
        return Paragraph(f"<i>[Screenshot Asset Missing: {path}]</i>", body_style)

    story = []
    
    # COVER PAGE BLOCK (Page 1)
    # ----------------------------------------------------
    story.append(Spacer(1, 20))
    story.append(Paragraph("ControlPlane.ai", title_style))
    story.append(Paragraph("Inline AI Governance & Safety Gateway", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2.5, color=colors.HexColor("#4F46E5"), spaceAfter=15))
    
    # Intro Summary Box
    intro_p = Paragraph(
        "<b>ControlPlane</b> is a high-performance inline gateway that sits between your AI application "
        "and Large Language Models (LLMs) or agents. By intercepting every request and response, "
        "ControlPlane validates claims, sanitizes PII, intercepts untrusted prompt injections, gates "
        "high-consequence tool calls, and writes an immutable, cryptographically hash-chained audit ledger.",
        body_style
    )
    
    intro_table = Table([[intro_p]], colWidths=[504])
    intro_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(intro_table)
    story.append(Spacer(1, 20))

    # Meta Info block
    meta_data = [
        [Paragraph("<b>Submission Track</b>", body_style), Paragraph("Accenture Innovation Challenge 2026 — Prototype Development Track", body_style)],
        [Paragraph("<b>Developing Institution</b>", body_style), Paragraph("Indian Institute of Technology (IIT) Patna", body_style)],
        [Paragraph("<b>Status</b>", body_style), Paragraph("Phase 5 (Calibration & Verification) — Complete & Verified", body_style)],
        [Paragraph("<b>Open Source Repo</b>", body_style), Paragraph("https://github.com/MohithChandra07/Control-Plane-AIC", body_style)],
        [Paragraph("<b>Project Team</b>", body_style), Paragraph("<b>Mohith Chandra</b> (Team Lead & Core Engineer)<br/><b>Monal Gupta</b> (Core NLP & Fullstack Developer)<br/><b>Veda Vikas</b> (System Architect & Developer)", body_style)]
    ]
    t_meta = Table(meta_data, colWidths=[140, 364])
    t_meta.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    
    story.append(PageBreak())

    # PAGE 2: ARCHITECTURE & CORE PIPELINE
    # ----------------------------------------------------
    story.append(Paragraph("1. System Architecture & Gateway Flow", h1_style))
    story.append(Paragraph(
        "ControlPlane integrates transparently into existing software architectures by presenting an OpenAI-compatible "
        "endpoint. Your application updates only its API base URL, forwarding all traffic through the gateway.",
        body_style
    ))
    
    arch_flow = (
        "<b>Transaction Flow:</b><br/>"
        "Application Client → ControlPlane Gateway → Upstream AI Model → Response Analysis → Policy Engine → [ALLOW / MODIFY / ESCALATE / BLOCK] → Application Client"
    )
    story.append(Paragraph(arch_flow, code_style))
    
    story.append(Spacer(1, 5))
    story.append(Paragraph("<b>ControlPlane 3D WebGL Interface & Showcase</b>", h2_style))
    story.append(load_image("docs/assets/hero_3d_showcase.png", width=460, height=230))
    
    story.append(Spacer(1, 5))
    story.append(Paragraph("2. Technical Implementation Matrix", h1_style))
    
    table_data = [
        [Paragraph("<b>Capability</b>", body_style), Paragraph("<b>Technical Mechanism & Role</b>", body_style)],
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
    
    story.append(PageBreak())

    # PAGE 3: BENCHMARKS & DYNAMIC CALIBRATION
    # ----------------------------------------------------
    story.append(Paragraph("3. Empirical Evaluation & Calibration Metrics", h1_style))
    story.append(Paragraph(
        "ControlPlane is continuously evaluated using a 400-item synthetic benchmark dataset, measuring precision, "
        "recall, latency overhead, and Expected Calibration Error (ECE) under three distinct configurations:",
        body_style
    ))
    
    story.append(Paragraph("• <b>ALWAYS_SHALLOW (Tier 0 Gate):</b> Fast execution (~1.71ms latency) but runs no advanced verification or PII checks.", bullet_style))
    story.append(Paragraph("• <b>ALWAYS_DEEP (Full Pipeline):</b> High precision and recall (~2.94ms latency) but runs full claim verification on all inputs.", bullet_style))
    story.append(Paragraph("• <b>ADAPTIVE (Dynamic Routing):</b> Routes dynamically based on confidence thresholds, maintaining 99.4% recall while saving 30.5% in execution overhead.", bullet_style))
    
    story.append(Spacer(1, 5))
    story.append(Paragraph("<b>Adaptive Scrutiny Evaluation Metrics</b>", h2_style))
    story.append(load_image("docs/assets/adaptive_scrutiny.png", width=460, height=230))
    story.append(Spacer(1, 5))
    
    story.append(Paragraph("Key Verification Statistics", h2_style))

    bench_data = [
        [Paragraph("<b>Evaluation Metric</b>", body_style), Paragraph("<b>Measured Result</b>", body_style), Paragraph("<b>Impact & Notes</b>", body_style)],
        [Paragraph("Automated Test Suite", body_style), Paragraph("<b>169 / 169 Passing</b>", body_style), Paragraph("100% test coverage across unit & integration scenes.", body_style)],
        [Paragraph("Synthetic Traffic Replayer", body_style), Paragraph("<b>10,000 requests / 100s</b>", body_style), Paragraph("Demonstrated high-throughput audit ledger logging.", body_style)],
        [Paragraph("Calibration Error (ECE)", body_style), Paragraph("<b>Expected Error &lt; 0.05</b>", body_style), Paragraph("Measured alignment between risk scores and true outputs.", body_style)],
        [Paragraph("Multi-Tenant Policy", body_style), Paragraph("<b>3 Configurations</b>", body_style), Paragraph("Dedicated enforcement rules for Support, Copilot, and Regulated agent.", body_style)]
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
    
    story.append(PageBreak())

    # PAGE 4: GOVERNANCE CONSOLE
    # ----------------------------------------------------
    story.append(Paragraph("4. Human-in-the-Loop & Recalibration", h1_style))
    story.append(Paragraph(
        "ControlPlane features a live React dashboard where compliance reviewers mark governance decisions as "
        "<b>Agree / Disagree</b>. Disagreement scores feed directly into `policy/recalibration.py`. When disagreements "
        "cross the confidence threshold, the engine automatically suggests optimized updates to the tenant's risk appetite.",
        body_style
    ))
    
    story.append(Spacer(1, 5))
    story.append(Paragraph("<b>ControlPlane Real-Time Operational Overview Console</b>", h2_style))
    story.append(load_image("docs/assets/governance_console.png", width=460, height=230))
    story.append(Spacer(1, 10))
    
    story.append(PageBreak())

    # PAGE 5: QUICKSTART & INTEGRATION
    # ----------------------------------------------------
    story.append(Paragraph("5. Technical Quickstart & API Integration Guide", h1_style))
    story.append(Paragraph(
        "Deploy the gateway locally or in a containerized environment, and route model payloads to it directly:",
        body_style
    ))
    
    quickstart_code = (
        "# 1. Environment Setup & Dependency Installation<br/>"
        "python3 -m venv .venv && source .venv/bin/activate<br/>"
        "pip install -e \".[dev]\"<br/><br/>"
        "# 2. Launch Gateway Proxy Server<br/>"
        "uvicorn gateway.main:app --port 8000 --reload<br/><br/>"
        "# 3. Run Validation Test Suite & Benchmark Harness<br/>"
        "pytest<br/>"
        "python -m bench.harness.run_benchmark<br/><br/>"
        "# 4. Launch Governance Console Dashboard Backend<br/>"
        "DATABASE_URL=\"sqlite+aiosqlite:///$(pwd)/demo/replayer/traffic.db\" \\<br/>"
        "  uvicorn console.backend.main:app --port 8002 --reload"
    )
    story.append(Paragraph(quickstart_code, code_style))

    story.append(Spacer(1, 5))
    story.append(Paragraph("<b>Terminal Execution Output (Passing Test Suite)</b>", h2_style))
    story.append(load_image("docs/assets/test_benchmark_terminal.png", width=460, height=230))
    story.append(Spacer(1, 5))
    
    story.append(Paragraph("6. Project Team & Reference", h1_style))
    story.append(Paragraph("• <b>Mohith Chandra</b> (Team Lead & Core Engineer) — mohithg404@gmail.com", bullet_style))
    story.append(Paragraph("• <b>Monal Gupta</b> (Core NLP & Fullstack Developer) — monalgupta.work@gmail.com", bullet_style))
    story.append(Paragraph("• <b>Veda Vikas</b> (System Architect & Developer) — vedavikas02@gmail.com", bullet_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph("<b>GitHub Repository:</b> https://github.com/MohithChandra07/Control-Plane-AIC", body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    create_readme_pdf()

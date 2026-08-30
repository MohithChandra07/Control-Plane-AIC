import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class ProposalNumberedCanvas(canvas.Canvas):
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
            self.drawString(54, 750, "ControlPlane.ai — Executive Business Proposal")
            self.drawRightString(612 - 54, 750, "Accenture Innovation Challenge 2026")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 742, 612 - 54, 742)
            
        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 612 - 54, 45)
        self.setFont("Helvetica", 8)
        self.drawString(54, 32, "CONFIDENTIAL — ControlPlane.ai | Accenture Innovation Challenge 2026 Submission")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 54, 32, page_text)
        self.restoreState()

def create_proposal_pdf(filename="ControlPlane_Business_Proposal.pdf"):
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
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#4F46E5"),
        spaceAfter=14
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

    callout_style = ParagraphStyle(
        'Callout_Text',
        parent=body_style,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E1B4B")
    )

    story = []
    
    # Title Banner
    story.append(Paragraph("ControlPlane.ai — Business Proposal", title_style))
    story.append(Paragraph("Enterprise AI Governance, Responsible Agent Security & Safety Gateway", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4F46E5"), spaceAfter=10))

    # Executive Summary
    story.append(Paragraph("1. Executive Summary", h1_style))
    story.append(Paragraph(
        "As enterprises rapidly adopt Large Language Models (LLMs) and Autonomous AI Agents, governance, "
        "compliance, financial risk control, and safety have emerged as mandatory operational imperatives. "
        "<b>ControlPlane.ai</b> is an enterprise-grade AI governance and safety gateway that sits directly between applications "
        "and upstream AI models or tool-calling agents. Rather than relying on unmonitored model outputs, ControlPlane programmatically "
        "inspects inputs/outputs, enforces custom tenant policies, redacts sensitive PII, verifies factual claims against knowledge repositories, "
        "tracks multi-turn data taint, and gates high-consequence tool calls before real-world execution.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # Problem Statement & Market Pain
    story.append(Paragraph("2. The Market Pain & Core Problem", h1_style))
    story.append(Paragraph("Enterprise deployments of Generative AI face three critical vulnerability vectors:", body_style))
    story.append(Paragraph("• <b>Hallucination & Financial Liability:</b> Unverified claims made by customer service bots (e.g. promising non-existent refunds or incorrect pricing) can lead to direct legal liability.", bullet_style))
    story.append(Paragraph("• <b>Data Contamination & Tool Exploitation:</b> Tainted or unverified claims generated early in a conversation can carry over into downstream tool calls (e.g., automated execution of `issue_refund`), executing real monetary transactions.", bullet_style))
    story.append(Paragraph("• <b>Compliance & Regulatory Risk:</b> Tightening regulations like the EU AI Act and NIST AI RMF mandate cryptographically verifiable audit trails, PII redaction, and human-in-the-loop oversight.", bullet_style))
    story.append(Spacer(1, 4))

    # Value Proposition Matrix Table
    story.append(Paragraph("3. ControlPlane.ai Solution Architecture", h1_style))
    
    sol_table_data = [
        [Paragraph("<b>Governance Pillar</b>", body_style), Paragraph("<b>ControlPlane Technical Capability</b>", body_style), Paragraph("<b>Business Value Impact</b>", body_style)],
        [Paragraph("<b>Adaptive Scrutiny</b>", body_style), Paragraph("Tier 0 cheap heuristic gate + Tier 1 claim verification pipeline.", body_style), Paragraph("Reduces API cost by routing non-critical requests through low-latency gates.", body_style)],
        [Paragraph("<b>Surgical Remediation</b>", body_style), Paragraph("Per-claim remediation (Hedge, Redact, Remove, Cite, Escalate).", body_style), Paragraph("Preserves positive user experience without dropping full responses unnecessarily.", body_style)],
        [Paragraph("<b>Multi-Turn Taint Tracking</b>", body_style), Paragraph("Conversation state tracking linking unverified claims to downstream tool parameters.", body_style), Paragraph("Prevents unauthorized financial transactions and rogue agent actions.", body_style)],
        [Paragraph("<b>Immutable Audit Ledger</b>", body_style), Paragraph("Cryptographically hash-chained transaction logging.", body_style), Paragraph("Ensures 100% audit readiness for regulatory compliance.", body_style)],
        [Paragraph("<b>Dynamic Risk Appetite</b>", body_style), Paragraph("Live slider control + human reviewer recalibration feedback loop.", body_style), Paragraph("Empowers compliance officers to adjust risk appetite live without code deployments.", body_style)]
    ]

    t_sol = Table(sol_table_data, colWidths=[120, 200, 184])
    t_sol.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EEF2FF")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_sol)
    story.append(Spacer(1, 8))

    # Business Model & Market Opportunity
    story.append(Paragraph("4. Market Opportunity & Business Model", h1_style))
    story.append(Paragraph("The total addressable market (TAM) for Enterprise AI Trust, Risk, and Security Management (AI TRiSM) is projected to exceed <b>$35 Billion by 2028</b>.", body_style))
    
    story.append(Paragraph("<b>Monetization Architecture:</b>", body_style))
    story.append(Paragraph("1. <b>SaaS Gateway Tier:</b> Consumption-based model per 1M governed tokens + active managed tenant policies.", bullet_style))
    story.append(Paragraph("2. <b>Enterprise VPC / On-Prem License:</b> Flat annual enterprise license per gateway instance with dedicated compliance connectors.", bullet_style))
    story.append(Paragraph("3. <b>Accenture Managed Services Integration:</b> Partner integration embedding ControlPlane into Accenture's AI Transformation offerings.", bullet_style))
    story.append(Spacer(1, 4))

    # Financial & Projections Table
    story.append(Paragraph("5. Financial Projections (USD)", h1_style))
    
    fin_data = [
        [Paragraph("<b>Metric</b>", body_style), Paragraph("<b>Year 1</b>", body_style), Paragraph("<b>Year 2</b>", body_style), Paragraph("<b>Year 3</b>", body_style)],
        [Paragraph("Enterprise Clients", body_style), Paragraph("15", body_style), Paragraph("60", body_style), Paragraph("220", body_style)],
        [Paragraph("Annual Recurring Revenue (ARR)", body_style), Paragraph("$1.2M", body_style), Paragraph("$5.8M", body_style), Paragraph("$24.5M", body_style)],
        [Paragraph("Gross Margin (%)", body_style), Paragraph("78%", body_style), Paragraph("82%", body_style), Paragraph("86%", body_style)]
    ]
    
    t_fin = Table(fin_data, colWidths=[150, 110, 120, 124])
    t_fin.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F8FAFC")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_fin)
    story.append(Spacer(1, 8))

    # Accenture Synergy & Competitive Advantage
    story.append(Paragraph("6. Strategic Alignment with Accenture", h1_style))
    story.append(Paragraph(
        "ControlPlane provides Accenture with a high-value proprietary governance asset to differentiate its AI Consulting "
        "and System Integration practices. By offering pre-built compliance policies for regulated industries (Healthcare, Banking, Public Sector), "
        "Accenture can accelerate enterprise AI deployments while mitigating risk.",
        body_style
    ))

    # Roadmap
    story.append(Paragraph("7. Product Roadmap & Milestones", h1_style))
    story.append(Paragraph("• <b>Q3 2026:</b> Production gateway rollout, Kubernetes Operator release, and automated NIST AI RMF compliance reporting.", bullet_style))
    story.append(Paragraph("• <b>Q4 2026:</b> Integration with Enterprise SSO (Okta/Azure AD), Hardware Security Module (HSM) hash signing, and fine-tuned NLI verification models.", bullet_style))

    doc.build(story, canvasmaker=ProposalNumberedCanvas)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    create_proposal_pdf()

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import CondPageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


FONT_NAME = "HYSMyeongJo-Medium"  # 서버 운영체제와 관계없이 쓸 수 있는 한글 CID 글꼴
NAVY = colors.HexColor("#172A46")
BLUE = colors.HexColor("#2563EB")
SLATE = colors.HexColor("#475569")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#DCE3EC")
PANEL = colors.HexColor("#F4F7FB")
BLUE_PANEL = colors.HexColor("#EFF6FF")
GREEN_PANEL = colors.HexColor("#ECFDF5")
RED_PANEL = colors.HexColor("#FEF2F2")

pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))


def text(value, fallback="문서에서 확인되지 않음"):
    return escape(str(value or fallback)).replace("\n", "<br/>")


def status_label(item):
    status = item.get("status", "확인 필요")
    if status != "확인 필요":
        return status
    return (
        "회사정보 보완 필요"
        if "미입력" in item.get("explanation", "")
        else "공고문 확인 필요"
    )


def build_styles():
    styles = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle("Brand", parent=styles["Normal"], fontName=FONT_NAME, fontSize=11, leading=15, textColor=colors.white),
        "brand_right": ParagraphStyle("BrandRight", parent=styles["Normal"], fontName=FONT_NAME, fontSize=8, leading=12, textColor=colors.HexColor("#BFDBFE"), alignment=TA_RIGHT),
        "title": ParagraphStyle("TitleKo", parent=styles["Title"], fontName=FONT_NAME, fontSize=20, leading=29, textColor=NAVY, spaceAfter=5),
        "subtitle": ParagraphStyle("SubtitleKo", parent=styles["Normal"], fontName=FONT_NAME, fontSize=9, leading=14, textColor=MUTED),
        "section_number": ParagraphStyle("SectionNumber", parent=styles["Normal"], fontName=FONT_NAME, fontSize=9, leading=13, textColor=BLUE),
        "section_title": ParagraphStyle("SectionTitle", parent=styles["Heading2"], fontName=FONT_NAME, fontSize=13, leading=18, textColor=NAVY),
        "body": ParagraphStyle("BodyKo", parent=styles["BodyText"], fontName=FONT_NAME, fontSize=9.2, leading=15, textColor=SLATE),
        "small": ParagraphStyle("SmallKo", parent=styles["BodyText"], fontName=FONT_NAME, fontSize=7.8, leading=12, textColor=MUTED),
        "label": ParagraphStyle("LabelKo", parent=styles["BodyText"], fontName=FONT_NAME, fontSize=8, leading=12, textColor=MUTED),
        "value": ParagraphStyle("ValueKo", parent=styles["BodyText"], fontName=FONT_NAME, fontSize=9.5, leading=14, textColor=NAVY),
        "score": ParagraphStyle("ScoreKo", parent=styles["Heading1"], fontName=FONT_NAME, fontSize=25, leading=29, textColor=BLUE, alignment=TA_CENTER),
        "score_label": ParagraphStyle("ScoreLabelKo", parent=styles["BodyText"], fontName=FONT_NAME, fontSize=8, leading=12, textColor=MUTED, alignment=TA_CENTER),
        "table_header": ParagraphStyle("TableHeaderKo", parent=styles["BodyText"], fontName=FONT_NAME, fontSize=8, leading=12, textColor=colors.white),
        "callout": ParagraphStyle("CalloutKo", parent=styles["BodyText"], fontName=FONT_NAME, fontSize=8, leading=13, textColor=colors.HexColor("#1E40AF")),
    }


def draw_page(canvas, document):
    canvas.saveState()
    width, height = A4
    if document.page > 1:
        canvas.setFont(FONT_NAME, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, height - 12 * mm, "BID LINK  |  AI 입찰 분석 리포트")
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, height - 15 * mm, width - 18 * mm, height - 15 * mm)
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 17 * mm, width - 18 * mm, 17 * mm)
    canvas.setFont(FONT_NAME, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 11 * mm, "AI 분석 결과는 입찰 참여 전 담당자의 최종 검토가 필요합니다.")
    canvas.drawRightString(width - 18 * mm, 11 * mm, f"{document.page}")
    canvas.restoreState()


def section_heading(story, number, title, styles):
    story.append(CondPageBreak(22 * mm))  # 제목과 첫 내용이 서로 다른 페이지로 갈라지지 않게 공간 확보
    heading = Table(
        [[Paragraph(number, styles["section_number"]), Paragraph(title, styles["section_title"])]],
        colWidths=[10 * mm, 164 * mm],
    )
    heading.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.7, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([Spacer(1, 5 * mm), heading, Spacer(1, 3 * mm)])


def list_content(items, styles):
    values = items or ["문서에서 확인되지 않음"]
    return [Paragraph(f"- {text(item)}", styles["body"]) for item in values]


def add_list_section(story, number, title, items, styles):
    section_heading(story, number, title, styles)
    story.extend(list_content(items, styles))


def add_strength_risk_section(story, number, report, styles):
    section_heading(story, number, "강점과 위험 요소", styles)
    strengths = "<br/>".join(f"- {text(item)}" for item in (report.get("strengths") or ["확인된 강점 없음"]))
    risks = "<br/>".join(f"- {text(item)}" for item in (report.get("risks") or ["확인된 위험 없음"]))
    comparison = Table(
        [[Paragraph("우리 회사의 강점", styles["value"]), Paragraph("위험 요소", styles["value"])], [Paragraph(strengths, styles["body"]), Paragraph(risks, styles["body"])]],
        colWidths=[87 * mm, 87 * mm],
    )
    comparison.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), GREEN_PANEL),
        ("BACKGROUND", (1, 0), (1, -1), RED_PANEL),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(comparison)


def build_analysis_pdf(analysis):
    """DB에 저장된 분석 JSON을 OpenAI 재호출 없이 정식 보고서 PDF로 만듭니다."""

    report = analysis.report
    notice = analysis.saved_bid.bid_notice
    overview = report.get("overview") or {}
    styles = build_styles()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=23 * mm,
        title=f"{notice.title} AI 입찰 분석 리포트",
        author="Bid Link",
    )
    story = []

    brand_bar = Table(
        [[Paragraph("BID LINK", styles["brand"]), Paragraph("AI BID ANALYSIS REPORT", styles["brand_right"])]],
        colWidths=[87 * mm, 87 * mm],
    )
    brand_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([
        brand_bar,
        Spacer(1, 10 * mm),
        Paragraph("AI 입찰 적합도 분석 리포트", styles["title"]),
        Paragraph(text(notice.title), styles["subtitle"]),
        Paragraph(f"공고번호 {text(notice.bid_ntce_no)}  |  발주기관 {text(notice.notice_organization)}", styles["subtitle"]),
        Spacer(1, 7 * mm),
    ])

    score_table = Table(
        [[
            [Paragraph("입찰 적합도", styles["score_label"]), Paragraph(f"{report.get('fit_score', 0)}점", styles["score"])],
            [Paragraph("종합 의견", styles["score_label"]), Paragraph(text(report.get("recommendation")), styles["value"])],
            [Paragraph("분석 생성일", styles["score_label"]), Paragraph(f"{analysis.created_at:%Y. %m. %d.}", styles["value"])],
        ]],
        colWidths=[50 * mm, 65 * mm, 59 * mm],
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), BLUE_PANEL),
        ("BACKGROUND", (1, 0), (-1, 0), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([score_table, Spacer(1, 4 * mm)])

    notice_callout = Table(
        [[Paragraph("적합도는 낙찰 확률이 아니라 공고 요건과 입력된 회사정보의 일치 정도입니다. '회사정보 보완 필요'는 해당 입력값을 추가하면 다시 판단할 수 있다는 뜻입니다.", styles["callout"])]],
        colWidths=[174 * mm],
    )
    notice_callout.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_PANEL),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#BFDBFE")),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(notice_callout)

    section_heading(story, "01", "분석 요약", styles)
    story.append(Paragraph(text(report.get("summary")), styles["body"]))

    add_strength_risk_section(story, "02", report, styles)

    section_heading(story, "03", "사업 개요", styles)
    overview_rows = [
        ("발주기관", overview.get("ordering_organization")),
        ("예산 / 추정가격", overview.get("budget")),
        ("입찰 마감", overview.get("bid_deadline")),
        ("계약 기간", overview.get("contract_period")),
        ("사업 내용", overview.get("project_summary")),
    ]
    overview_table = Table(
        [[Paragraph(text(label), styles["label"]), Paragraph(text(value), styles["body"])] for label, value in overview_rows],
        colWidths=[36 * mm, 138 * mm],
    )
    overview_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PANEL),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(overview_table)

    story.append(CondPageBreak(65 * mm))  # 평가 제목과 표가 서로 다른 페이지로 갈라지지 않게 확보
    section_heading(story, "04", "평가 항목", styles)
    evaluation_rows = [[Paragraph(label, styles["table_header"]) for label in ["평가 항목", "점수", "판정", "판단 근거"]]]
    for item in report.get("evaluation_items") or []:
        references = ", ".join(f"출처 {number}" for number in item.get("source_numbers", []))
        explanation = item.get("explanation", "")
        if references:
            explanation = f"{explanation} ({references})"
        evaluation_rows.append([
            Paragraph(text(item.get("name")), styles["small"]),
            Paragraph(f"{item.get('score', 0)} / {item.get('max_score', 0)}", styles["small"]),
            Paragraph(text(status_label(item)), styles["small"]),
            Paragraph(text(explanation), styles["small"]),
        ])
    evaluation_table = Table(evaluation_rows, colWidths=[34 * mm, 20 * mm, 36 * mm, 84 * mm], repeatRows=1)
    evaluation_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(evaluation_table)

    detail_sections = [
        ("05", "참가 자격", "eligibility"),
        ("06", "필수 제출 서류", "required_documents"),
        ("07", "기술평가 기준", "technical_evaluation"),
        ("08", "가격평가 기준", "price_evaluation"),
        ("09", "주요 과업", "main_tasks"),
        ("10", "요구 인력 및 자격", "required_staff"),
        ("11", "필수 인증 및 실적", "certifications_and_experience"),
        ("12", "계약상 주의사항", "contract_cautions"),
    ]
    for number, title, key in detail_sections:
        add_list_section(story, number, title, report.get(key) or [], styles)

    add_list_section(story, "13", "회사가 반드시 확인할 사항", report.get("company_checks") or [], styles)
    add_list_section(story, "14", "참여 준비 전략", report.get("action_strategy") or [], styles)

    section_heading(story, "15", "문서 출처", styles)
    source_rows = [[Paragraph("번호", styles["table_header"]), Paragraph("파일명", styles["table_header"]), Paragraph("문서 위치", styles["table_header"])]]
    for source in report.get("sources") or []:
        source_rows.append([
            Paragraph(str(source.get("number", "-")), styles["small"]),
            Paragraph(text(source.get("file_name")), styles["small"]),
            Paragraph(text(source.get("location")), styles["small"]),
        ])
    source_table = Table(source_rows, colWidths=[16 * mm, 95 * mm, 63 * mm], repeatRows=1)
    source_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(source_table)

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    buffer.seek(0)
    return buffer

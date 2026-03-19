import io
import os
import logging
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

logger = logging.getLogger(__name__)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, Image as RLImage
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from schemas import ReportInput

# ─── Кольори ──────────────────────────────────────────
PRIMARY     = colors.HexColor("#0f4c81")
SECONDARY   = colors.HexColor("#00b894")
ACCENT      = colors.HexColor("#6c5ce7")
LIGHT_BLUE  = colors.HexColor("#dbeafe")
LIGHT_GREEN = colors.HexColor("#d1fae5")
LIGHT_GRAY  = colors.HexColor("#f3f4f6")
DANGER      = colors.HexColor("#e17055")
WHITE       = colors.white
DARK        = colors.HexColor("#1e293b")

CHART_COLORS = ['#0f4c81', '#00b894', '#6c5ce7', '#e17055', '#fdcb6e']
PAGE_W = A4[0] - 4 * cm


# ─── Реєстрація шрифтів ───────────────────────────────
def register_fonts():
    """Завантажуємо шрифт з папки fonts/ поруч з цим файлом"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    regular = os.path.join(base_dir, 'fonts', 'DejaVuSans.ttf')
    bold    = os.path.join(base_dir, 'fonts', 'DejaVuSans-Bold.ttf')

    if os.path.exists(regular) and os.path.exists(bold):
        try:
            pdfmetrics.registerFont(TTFont('DejaVu', regular))
            pdfmetrics.registerFont(TTFont('DejaVu-Bold', bold))
            logger.info("Fonts loaded: %s", regular)
            return True
        except Exception as e:
            logger.error("Font error: %s", e)
            return False

    # Fallback: системні шляхи
    system_paths = [
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        ('/usr/share/fonts/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'),
    ]
    for r, b in system_paths:
        if os.path.exists(r) and os.path.exists(b):
            try:
                pdfmetrics.registerFont(TTFont('DejaVu', r))
                pdfmetrics.registerFont(TTFont('DejaVu-Bold', b))
                logger.info("Fonts loaded from system: %s", r)
                return True
            except Exception as e:
                logger.warning("System font failed: %s", e)

    logger.warning("Fonts not found — using transliteration fallback")
    return False


USE_CYRILLIC = register_fonts()


def safe(text) -> str:
    """Якщо є кириличний шрифт — повертаємо оригінал, інакше транслітерація"""
    if not isinstance(text, str):
        text = str(text)
    if USE_CYRILLIC:
        return text
    translit = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','є':'ye',
        'ж':'zh','з':'z','и':'y','і':'i','ї':'yi','й':'y','к':'k',
        'л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s',
        'т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh',
        'щ':'shch','ь':"'",'ю':'yu','я':'ya',
        'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Є':'Ye',
        'Ж':'Zh','З':'Z','И':'Y','І':'I','Ї':'Yi','Й':'Y','К':'K',
        'Л':'L','М':'M','Н':'N','О':'O','П':'P','Р':'R','С':'S',
        'Т':'T','У':'U','Ф':'F','Х':'Kh','Ц':'Ts','Ч':'Ch','Ш':'Sh',
        'Щ':'Shch','Ь':"'",'Ю':'Yu','Я':'Ya','№':'#'
    }
    return ''.join(translit.get(c, c) for c in text)


def F():
    return 'DejaVu'      if USE_CYRILLIC else 'Helvetica'

def FB():
    return 'DejaVu-Bold' if USE_CYRILLIC else 'Helvetica-Bold'


def fig_to_image(fig, width_cm=17, height_cm=8):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return RLImage(buf, width=width_cm * cm, height=height_cm * cm)


# ─── Графік 1: NPV Bar Chart ──────────────────────────
def chart_npv(data: ReportInput):
    names = [safe(f.name) for f in data.financial_results]
    npvs  = [f.npv for f in data.financial_results]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    bars = ax.bar(names, npvs,
                  color=[CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(names))],
                  width=0.5, zorder=3, edgecolor='white', linewidth=1.5)
    ax.axhline(0, color='#374151', linewidth=1, linestyle='--', alpha=0.5)
    for bar, val in zip(bars, npvs):
        ax.text(bar.get_x() + bar.get_width()/2,
                val + (max(abs(v) for v in npvs) * 0.02),
                f'{val:,.0f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold', color='#1e293b')
    ax.set_title('Net Present Value (NPV) by Measure', fontsize=13,
                 fontweight='bold', color='#0f4c81', pad=12)
    ax.set_ylabel('NPV (UAH)', fontsize=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return fig_to_image(fig, 17, 6)


# ─── Графік 2: IRR та BCR ─────────────────────────────
def chart_irr_bcr(data: ReportInput):
    names = [safe(f.name) for f in data.financial_results]
    irrs  = [f.irr for f in data.financial_results]
    bcrs  = [f.bcr for f in data.financial_results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    bars1 = ax1.bar(names, irrs, color='#0f4c81', width=0.5, zorder=3, edgecolor='white')
    ax1.axhline(10, color='#e17055', linewidth=1.5, linestyle='--', label='Discount rate 10%')
    for bar, val in zip(bars1, irrs):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                 f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax1.set_title('IRR (%)', fontsize=12, fontweight='bold', color='#0f4c81')
    ax1.set_ylabel('IRR (%)')
    ax1.legend(fontsize=8)
    ax1.grid(axis='y', linestyle='--', alpha=0.4)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    bar_colors = ['#00b894' if b >= 1 else '#e17055' for b in bcrs]
    bars2 = ax2.bar(names, bcrs, color=bar_colors, width=0.5, zorder=3, edgecolor='white')
    ax2.axhline(1, color='#374151', linewidth=1.5, linestyle='--', label='BCR = 1 (breakeven)')
    for bar, val in zip(bars2, bcrs):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                 f'{val:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax2.set_title('Benefit-Cost Ratio (BCR)', fontsize=12, fontweight='bold', color='#0f4c81')
    ax2.set_ylabel('BCR')
    ax2.legend(fontsize=8)
    ax2.grid(axis='y', linestyle='--', alpha=0.4)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    fig.tight_layout(pad=2)
    return fig_to_image(fig, 17, 5.5)


# ─── Графік 3: NPV по роках ───────────────────────────
def chart_npv_yearly(data: ReportInput):
    has_details = any(f.yearly_details for f in data.financial_results)
    if not has_details:
        return None

    fig, ax = plt.subplots(figsize=(10, 4.5))
    for i, f in enumerate(data.financial_results):
        if not f.yearly_details:
            continue
        years = [d['year'] for d in f.yearly_details]
        cumulative = [d['cumulative_discounted'] for d in f.yearly_details]
        color = CHART_COLORS[i % len(CHART_COLORS)]
        ax.plot(years, cumulative, color=color, linewidth=2.5,
                label=safe(f.name), marker='o', markersize=3)
        ax.fill_between(years, cumulative, alpha=0.08, color=color)

    ax.axhline(0, color='#374151', linewidth=1, linestyle='--', alpha=0.6, label='NPV = 0')
    ax.set_title('Cumulative Discounted Cash Flow by Year',
                 fontsize=13, fontweight='bold', color='#0f4c81', pad=12)
    ax.set_xlabel('Year', fontsize=10)
    ax.set_ylabel('Cumulative NPV (UAH)', fontsize=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.legend(fontsize=9, loc='lower right')
    ax.grid(linestyle='--', alpha=0.4)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return fig_to_image(fig, 17, 6)


# ─── Графік 4: CO₂ ────────────────────────────────────
def chart_co2(data: ReportInput):
    names = [safe(e.name) for e in data.eco_results]
    co2   = [e.co2_reduction_tons_per_year for e in data.eco_results]
    dmg   = [e.averted_damage_uah / 1000 for e in data.eco_results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    bars1 = ax1.bar(names, co2, color='#00b894', width=0.5, zorder=3, edgecolor='white')
    for bar, val in zip(bars1, co2):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                 f'{val:.1f} t', ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax1.set_title('CO2 Reduction (t/year)', fontsize=12, fontweight='bold', color='#00b894')
    ax1.set_ylabel('CO2 (tons/year)')
    ax1.grid(axis='y', linestyle='--', alpha=0.4)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    bars2 = ax2.bar(names, dmg, color='#6c5ce7', width=0.5, zorder=3, edgecolor='white')
    for bar, val in zip(bars2, dmg):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                 f'{val:.1f}K', ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax2.set_title('Averted Environmental Damage (K UAH)',
                  fontsize=12, fontweight='bold', color='#6c5ce7')
    ax2.set_ylabel('Damage (K UAH/year)')
    ax2.grid(axis='y', linestyle='--', alpha=0.4)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    fig.tight_layout(pad=2)
    return fig_to_image(fig, 17, 5.5)


# ─── Графік 5: Radar ──────────────────────────────────
def chart_radar(data: ReportInput):
    fin = data.financial_results
    eco = data.eco_results
    if len(fin) < 2:
        return None

    metrics   = ['NPV', 'IRR', 'BCR x10', 'CO2', 'Payback inv']
    n_metrics = len(metrics)
    angles    = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
    angles   += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

    max_npv = max(abs(f.npv) for f in fin) or 1
    # Фільтруємо sentinel -1.0 (IRR не існує) перед нормалізацією
    valid_irrs = [f.irr for f in fin if f.irr >= 0]
    max_irr = max(valid_irrs) if valid_irrs else 1
    max_co2 = max(e.co2_reduction_tons_per_year for e in eco) or 1
    max_pb  = max((f.simple_payback for f in fin if f.simple_payback > 0), default=1)

    for i, f in enumerate(fin):
        # Пошук CO2 без урахування регістру та зайвих пробілів
        f_name_norm = f.name.strip().lower()
        eco_match = next((e for e in eco if e.name.strip().lower() == f_name_norm), None)
        if eco_match is None:
            logger.warning("Radar chart: no eco match for financial measure '%s'", f.name)
        co2_val   = eco_match.co2_reduction_tons_per_year if eco_match else 0
        pb_inv    = max(0, 10 - (f.simple_payback / max_pb * 10)) if f.simple_payback > 0 else 0

        # IRR sentinel -1.0 (не існує) відображається як 0 на radar chart
        irr_val = max(0, f.irr / max_irr * 10) if f.irr >= 0 else 0

        values = [
            max(0, f.npv / max_npv * 10),
            irr_val,
            min(10, f.bcr * 10) if f.bcr > 0 else 0,
            co2_val / max_co2 * 10,
            pb_inv,
        ]
        values += values[:1]

        color = CHART_COLORS[i % len(CHART_COLORS)]
        ax.plot(angles, values, color=color, linewidth=2, label=safe(f.name))
        ax.fill(angles, values, color=color, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics, fontsize=10)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2','4','6','8','10'], fontsize=7)
    ax.grid(color='#94a3b8', linestyle='--', linewidth=0.5, alpha=0.7)
    ax.set_title('Multi-Criteria Comparison\n(normalized 0-10)',
                 fontsize=12, fontweight='bold', color='#0f4c81', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.1), fontsize=9)
    fig.tight_layout()
    return fig_to_image(fig, 12, 9)


# ─── Графік 6: Consensus Ranking ─────────────────────
def chart_ranking(data: ReportInput):
    ranking = sorted(data.ranking, key=lambda r: r.consensus_rank)
    names   = [safe(r.name) for r in ranking]
    scores  = [len(ranking) - r.consensus_rank + 1 for r in ranking]

    fig, ax = plt.subplots(figsize=(8, 3.5))
    bars = ax.barh(names, scores,
                   color=[CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(names))],
                   height=0.5, zorder=3, edgecolor='white')
    for bar, r in zip(bars, ranking):
        ax.text(bar.get_width() + 0.05,
                bar.get_y() + bar.get_height()/2,
                f'Rank #{r.consensus_rank}',
                va='center', fontsize=9, fontweight='bold', color='#374151')
    ax.set_title('Consensus Ranking', fontsize=12, fontweight='bold', color='#0f4c81')
    ax.set_xlabel('Score (higher = better)', fontsize=9)
    ax.set_xlim(0, max(scores) * 1.3)
    ax.grid(axis='x', linestyle='--', alpha=0.4)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    return fig_to_image(fig, 14, 4.5)


# ─── Стилі ────────────────────────────────────────────
def build_styles():
    styles = getSampleStyleSheet()
    f  = F()
    fb = FB()
    return {
        'title': ParagraphStyle('T', parent=styles['Normal'],
            fontSize=20, textColor=PRIMARY, spaceAfter=4,
            alignment=TA_CENTER, fontName=fb),
        'subtitle': ParagraphStyle('ST', parent=styles['Normal'],
            fontSize=11, textColor=colors.HexColor('#64748b'),
            spaceAfter=2, alignment=TA_CENTER, fontName=f),
        'h1': ParagraphStyle('H1', parent=styles['Normal'],
            fontSize=14, textColor=PRIMARY, spaceBefore=16,
            spaceAfter=8, fontName=fb),
        'h2': ParagraphStyle('H2', parent=styles['Normal'],
            fontSize=11, textColor=colors.HexColor('#374151'),
            spaceBefore=10, spaceAfter=6, fontName=fb),
        'normal': ParagraphStyle('N', parent=styles['Normal'],
            fontSize=9, spaceAfter=4, fontName=f, textColor=DARK),
        'small': ParagraphStyle('S', parent=styles['Normal'],
            fontSize=8, fontName=f,
            textColor=colors.HexColor('#64748b')),
        'center': ParagraphStyle('C', parent=styles['Normal'],
            fontSize=9, alignment=TA_CENTER, fontName=f),
        'right': ParagraphStyle('R', parent=styles['Normal'],
            fontSize=8, alignment=TA_RIGHT, fontName=f,
            textColor=colors.HexColor('#64748b')),
    }


def make_table(data, col_widths, header_bg=None):
    if header_bg is None:
        header_bg = PRIMARY

    f  = F()
    fb = FB()

    def cell(text, bold=False):
        if isinstance(text, str):
            return Paragraph(text, ParagraphStyle(
                'cell', fontName=fb if bold else f,
                fontSize=8, leading=11, wordWrap='CJK',
            ))
        return text

    converted = []
    for row_idx, row in enumerate(data):
        new_row = [cell(str(val), bold=(row_idx == 0)) for val in row]
        converted.append(new_row)

    table = Table(converted, colWidths=col_widths, repeatRows=1)
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    table.setStyle(TableStyle(style))
    return table


def section_bar(color=PRIMARY):
    return Table(
        [['']],
        colWidths=[PAGE_W], rowHeights=[0.25*cm],
        style=TableStyle([('BACKGROUND', (0,0), (-1,-1), color)])
    )


# ─── Головна функція ──────────────────────────────────
def generate_pdf(data: ReportInput) -> bytes:
    buffer = io.BytesIO()
    s  = build_styles()
    f  = F()
    fb = FB()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"Eco Analysis Report — {safe(data.project_name)}",
    )

    story = []

    # ════ ТИТУЛЬНА СТОРІНКА ════════════════════════════
    story.append(Spacer(1, 1*cm))
    story.append(section_bar(PRIMARY))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph("TECHNICO-ECONOMIC ANALYSIS", s['title']))
    story.append(Paragraph("REPORT", s['title']))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("Environmental Measures Evaluation System", s['subtitle']))
    story.append(Spacer(1, 0.3*cm))
    story.append(section_bar(SECONDARY))
    story.append(Spacer(1, 0.8*cm))

    # Інфо блок
    info_rows = [
        ('Project:',           safe(data.project_name)),
        ('Description:',       safe(data.project_description or '—')),
        ('Analyst:',           safe(data.analyst_name)),
        ('Generated:',         datetime.now().strftime('%d.%m.%Y %H:%M')),
        ('Measures analyzed:', str(len(data.financial_results))),
        ('Recommended:',       safe(data.best_measure)),
    ]
    info_table = Table(
        [[
            Paragraph(k, ParagraphStyle('ik', fontName=fb, fontSize=9, textColor=PRIMARY)),
            Paragraph(v, ParagraphStyle('iv', fontName=f,  fontSize=9)),
        ] for k, v in info_rows],
        colWidths=[3.5*cm, PAGE_W - 3.5*cm],
        style=TableStyle([
            ('TOPPADDING',    (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LINEBELOW', (0,-1), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0,4), (-1,4), colors.HexColor('#f0fdf4')),
            ('BACKGROUND', (0,5), (-1,5), LIGHT_GREEN),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ])
    )
    story.append(info_table)
    story.append(Spacer(1, 1.5*cm))

    # Зміст
    story.append(Paragraph("TABLE OF CONTENTS", s['h2']))
    toc = [
        ('1.', 'Financial Analysis',          '2'),
        ('2.', 'Financial Charts',            '3'),
        ('3.', 'Environmental Impact',        '4'),
        ('4.', 'Consolidated Ranking',        '5'),
        ('4b.','AHP / TOPSIS Analysis',       '5'),
        ('4d.','Sensitivity Analysis',        '6'),
        ('5.', 'Multi-Criteria Comparison',   '6'),
        ('6.', 'Recommendation',              '7'),
    ]
    for num, title, page in toc:
        story.append(Table(
            [[num, title, page]],
            colWidths=[1*cm, PAGE_W - 2*cm, 1*cm],
            style=TableStyle([
                ('FONTNAME',  (0,0), (-1,-1), f),
                ('FONTSIZE',  (0,0), (-1,-1), 9),
                ('TEXTCOLOR', (1,0), (1,0), PRIMARY),
                ('ALIGN',     (2,0), (2,0), 'RIGHT'),
                ('LINEBELOW', (0,0), (-1,0), 0.3, colors.HexColor('#e2e8f0')),
                ('TOPPADDING',    (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ])
        ))

    # ════ 1. ФІНАНСОВИЙ АНАЛІЗ ════════════════════════
    story.append(Spacer(1, 0.5*cm))
    story.append(section_bar(PRIMARY))
    story.append(Paragraph("1. Financial Analysis", s['h1']))
    story.append(Paragraph(
        "Key financial performance indicators for each measure:", s['normal']
    ))

    fin_header = ['Measure', 'NPV (UAH)', 'IRR (%)', 'BCR',
                  'Payback (yrs)', 'Disc.Payback', 'LCCA (UAH)']
    fin_data = [fin_header]
    for f_item in data.financial_results:
        fin_data.append([
            safe(f_item.name),
            f'{f_item.npv:,.0f}',
            f'{f_item.irr:.1f}%',
            f'{f_item.bcr:.3f}',
            f'{f_item.simple_payback:.1f}' if f_item.simple_payback > 0 else 'N/A',
            f'{f_item.discounted_payback:.0f}' if f_item.discounted_payback > 0 else 'N/A',
            f'{f_item.lcca:,.0f}',
        ])

    col_w = [4.5*cm, 2.5*cm, 1.8*cm, 1.8*cm, 2.2*cm, 2.0*cm, 2.2*cm]
    fin_table = make_table(fin_data, col_w)

    best_idx = next(
        (i+1 for i, fi in enumerate(data.financial_results)
         if safe(fi.name) == safe(data.best_measure)), None
    )
    if best_idx:
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, best_idx), (-1, best_idx), colors.HexColor('#d1fae5')),
            ('FONTNAME',   (0, best_idx), (-1, best_idx), fb),
        ]))

    story.append(fin_table)
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "Note: NPV > 0 = profitable. IRR > discount rate = efficient. "
        "BCR > 1 = benefits exceed costs. Highlighted = recommended measure.",
        s['small']
    ))

    # ════ 2. ГРАФІКИ ══════════════════════════════════
    story.append(Spacer(1, 0.5*cm))
    story.append(section_bar(PRIMARY))
    story.append(Paragraph("2. Financial Charts", s['h1']))

    story.append(Paragraph("2.1 NPV Comparison", s['h2']))
    story.append(chart_npv(data))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("2.2 IRR and BCR Analysis", s['h2']))
    story.append(chart_irr_bcr(data))
    story.append(Spacer(1, 0.3*cm))

    yearly_chart = chart_npv_yearly(data)
    if yearly_chart:
        story.append(Paragraph("2.3 Cumulative Discounted Cash Flow by Year", s['h2']))
        story.append(yearly_chart)
        story.append(Spacer(1, 0.3*cm))

    # ════ 3. ЕКОЛОГІЧНИЙ ЕФЕКТ ════════════════════════
    story.append(section_bar(SECONDARY))
    story.append(Paragraph("3. Environmental Impact Assessment", s['h1']))

    eco_header = ['Measure', 'CO2 Reduction (t/yr)', 'Averted Damage (UAH)', 'CO2 Value (USD)']
    eco_rows = [eco_header]
    for e in data.eco_results:
        eco_rows.append([
            safe(e.name),
            f'{e.co2_reduction_tons_per_year:.1f}',
            f'{e.averted_damage_uah:,.0f}',
            f'${e.total_co2_value_usd:,.0f}',
        ])
    total_co2 = sum(e.co2_reduction_tons_per_year for e in data.eco_results)
    total_dmg = sum(e.averted_damage_uah for e in data.eco_results)
    eco_rows.append(['TOTAL', f'{total_co2:.1f}', f'{total_dmg:,.0f}', '—'])

    col_w2 = [5*cm, 4*cm, 4.5*cm, 4.5*cm]
    eco_table = make_table(eco_rows, col_w2, header_bg=SECONDARY)
    eco_table.setStyle(TableStyle([
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#d1fae5')),
        ('FONTNAME',   (0,-1), (-1,-1), fb),
    ]))
    story.append(eco_table)
    story.append(Spacer(1, 0.3*cm))
    story.append(chart_co2(data))

    # ════ 4. ЗВЕДЕНИЙ РЕЙТИНГ ════════════════════════
    story.append(Spacer(1, 0.3*cm))
    story.append(section_bar(ACCENT))
    story.append(Paragraph("4. Consolidated Ranking", s['h1']))

    rank_header = ['Measure', 'NPV Rank', 'CO2 Rank', 'AHP Rank', 'TOPSIS Rank', 'CONSENSUS']
    rank_rows = [rank_header]
    for r in sorted(data.ranking, key=lambda x: x.consensus_rank):
        rank_rows.append([
            safe(r.name),
            f'#{r.rank_npv}',
            f'#{r.rank_co2}',
            f'#{r.rank_ahp}' if r.rank_ahp else '—',
            f'#{r.rank_topsis}' if r.rank_topsis else '—',
            f'#{r.consensus_rank}',
        ])

    col_w3 = [5*cm, 2.3*cm, 2.3*cm, 2.3*cm, 2.3*cm, 2.8*cm]
    rank_table = make_table(rank_rows, col_w3, header_bg=ACCENT)
    rank_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#d1fae5')),
        ('FONTNAME',   (0, 1), (-1, 1), fb),
    ]))
    story.append(rank_table)

    # ════ 4b. AHP/TOPSIS ══════════════════════════════
    if data.ahp_data:
        story.append(Spacer(1, 0.3*cm))
        story.append(section_bar(ACCENT))
        story.append(Paragraph("4b. AHP Analysis — Criteria Weights", s['h1']))

        cr = data.ahp_data.consistency_ratio
        cr_color = colors.HexColor('#d1fae5') if cr < 0.1 else colors.HexColor('#fee2e2')
        story.append(Table(
            [[Paragraph(
                f'Consistency Ratio (CR) = {cr:.4f} — '
                f'{"Consistent ✓" if cr < 0.1 else "NOT Consistent ✗"}',
                ParagraphStyle('cr', fontName=fb, fontSize=9)
            )]],
            colWidths=[PAGE_W],
            style=TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), cr_color),
                ('TOPPADDING', (0,0), (-1,-1), 7),
                ('BOTTOMPADDING', (0,0), (-1,-1), 7),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
            ])
        ))
        story.append(Spacer(1, 0.2*cm))

        ahp_header = ['Criterion', 'Weight (%)', 'Priority']
        ahp_rows = [ahp_header]
        max_w = max(data.ahp_data.weights)
        for c, w in zip(data.ahp_data.criteria, data.ahp_data.weights):
            ahp_rows.append([
                safe(c),
                f'{w*100:.1f}%',
                '★ Most important' if w == max_w else '',
            ])
        story.append(make_table(ahp_rows, [8*cm, 4*cm, PAGE_W-12*cm], header_bg=ACCENT))

        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("AHP Ranking of Alternatives", s['h2']))
        ahp_rank_header = ['Rank', 'Alternative', 'Weighted Score']
        ahp_rank_rows = [ahp_rank_header]
        for r in data.ahp_data.ranking:
            ahp_rank_rows.append([
                f'#{r["rank"]}',
                safe(r['name']),
                f'{r["score"]:.4f}',
            ])
        story.append(make_table(ahp_rank_rows, [2*cm, 9*cm, PAGE_W-11*cm], header_bg=ACCENT))

    if data.topsis_data:
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("4c. TOPSIS Ranking", s['h1']))
        topsis_header = ['Rank', 'Alternative', 'Closeness Coeff.', 'To Ideal', 'To Anti-Ideal']
        topsis_rows = [topsis_header]
        for r in data.topsis_data.ranking:
            topsis_rows.append([
                f'#{r["rank"]}',
                safe(r['name']),
                f'{r["closeness_coefficient"]:.4f}',
                f'{r["distance_to_ideal"]:.4f}',
                f'{r["distance_to_anti_ideal"]:.4f}',
            ])
        story.append(make_table(
            topsis_rows,
            [2*cm, 5*cm, 4*cm, 3*cm, PAGE_W-14*cm],
            header_bg=ACCENT
        ))

    # ════ 4d. SENSITIVITY ANALYSIS ════════════════════
    if data.sensitivity_data:
        story.append(Spacer(1, 0.3*cm))
        story.append(section_bar(PRIMARY))
        story.append(Paragraph("4d. Sensitivity Analysis (Tornado)", s['h1']))
        story.append(Paragraph(
            "Parameters sorted by impact on NPV (highest influence first):", s['normal']
        ))

        PARAM_LABELS = {
            'expected_savings':   'Expected Savings',
            'initial_investment': 'Initial Investment',
            'discount_rate':      'Discount Rate',
            'operational_cost':   'Operational Cost',
            'lifetime_years':     'Lifetime (years)',
        }

        max_impact = max(r.impact_percent for r in data.sensitivity_data) or 1
        sens_header = ['#', 'Parameter', 'Impact on NPV (UAH)', 'Influence']
        sens_rows = [sens_header]
        for i, r in enumerate(data.sensitivity_data):
            filled = int(r.impact_percent / max_impact * 20)
            bar = '█' * filled + '░' * (20 - filled)
            sens_rows.append([
                str(i + 1),
                PARAM_LABELS.get(r.parameter, r.parameter),
                f'{r.impact_percent:,.0f}',
                bar,
            ])
        story.append(make_table(
            sens_rows,
            [1.2*cm, 5*cm, 4*cm, PAGE_W-10.2*cm],
            header_bg=PRIMARY
        ))

    # ════ 5. RADAR CHART ══════════════════════════════
    story.append(Spacer(1, 0.3*cm))
    story.append(section_bar(PRIMARY))
    story.append(Paragraph("5. Multi-Criteria Comparison (Radar)", s['h1']))

    radar = chart_radar(data)
    if radar:
        story.append(chart_ranking(data))
        story.append(Spacer(1, 0.3*cm))
        story.append(radar)

    # ════ 6. РЕКОМЕНДАЦІЯ ═════════════════════════════
    story.append(Spacer(1, 0.5*cm))
    story.append(section_bar(SECONDARY))
    story.append(Paragraph("6. Recommendation", s['h1']))

    rec_table = Table(
        [[
            Paragraph('RECOMMENDED\nMEASURE', ParagraphStyle(
                'RB', fontName=fb, fontSize=10,
                textColor=WHITE, alignment=TA_CENTER
            )),
            Paragraph(safe(data.best_measure), ParagraphStyle(
                'RV', fontName=fb, fontSize=16, textColor=PRIMARY
            )),
        ]],
        colWidths=[3.5*cm, PAGE_W - 3.5*cm],
        style=TableStyle([
            ('BACKGROUND', (0,0), (0,0), SECONDARY),
            ('BACKGROUND', (1,0), (1,0), LIGHT_GREEN),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 12),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
            ('LEFTPADDING',   (0,0), (-1,-1), 12),
        ])
    )
    story.append(rec_table)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(safe(data.recommendation), s['normal']))

    # ════ ФУТЕР ════════════════════════════════════════
    story.append(Spacer(1, 1*cm))
    story.append(section_bar(PRIMARY))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Generated by Eco Analysis System | "
        f"{datetime.now().strftime('%d.%m.%Y %H:%M')} | Confidential",
        s['right']
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
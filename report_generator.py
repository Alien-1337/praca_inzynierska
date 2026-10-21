"""Raport PDF z analizą awarii: wskaźniki, wykresy i zestawienie zgłoszeń."""
import calendar
import functools
import io
import os
import re
import textwrap
from collections import defaultdict
from datetime import datetime
from xml.sax.saxutils import escape

import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, HRFlowable, Image,
                                KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle)

import db_utils as db

MONTH_NAMES = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec",
               "sierpień", "wrzesień", "październik", "listopad", "grudzień"]

ALL_MACHINES = "Wszystkie maszyny"

PRIMARY = "#1F3A5F"
SECONDARY = "#4A7BA6"
ACCENT = "#D98E04"
DANGER = "#B5412F"
OK_COLOR = "#2E7D4F"
MUTED = "#6B7380"
GRID = "#D9DDE3"
LIGHT = "#F3F5F8"
TEXT = "#222B36"

STATUS_COLORS = {
    db.STATUS_REPORTED: DANGER,
    db.STATUS_IN_REPAIR: "#B26A00",
    db.STATUS_RESOLVED: OK_COLOR,
}

PAGE_W, PAGE_H = A4
MARGIN_X = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X

_fonts_ready = False


def month_label(year, month):
    name = MONTH_NAMES[month - 1]
    return f"{name[0].upper()}{name[1:]} {year}"


def month_range(year, month):
    """Pierwszy dzień miesiąca i pierwszy dzień następnego (koniec przedziału)."""
    start = datetime(year, month, 1).date()
    end = datetime(year + (month == 12), month % 12 + 1, 1).date()
    return start, end


def default_filename(year, month, machine=None):
    scope = machine or ALL_MACHINES
    scope = re.sub(r"[^\w-]+", "_", scope, flags=re.UNICODE).strip("_")
    return f"Raport_awarii_{year}-{month:02d}_{scope}.pdf"


def _register_fonts():
    # DejaVu jest dołączony do matplotlib, więc działa na każdym systemie i ma polskie znaki
    global _fonts_ready
    if _fonts_ready:
        return
    folder = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
    for name, file in (("DejaVu", "DejaVuSans.ttf"), ("DejaVu-Bold", "DejaVuSans-Bold.ttf"),
                       ("DejaVu-Italic", "DejaVuSans-Oblique.ttf"),
                       ("DejaVu-BoldItalic", "DejaVuSans-BoldOblique.ttf")):
        pdfmetrics.registerFont(TTFont(name, os.path.join(folder, file)))
    pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold",
                                  italic="DejaVu-Italic", boldItalic="DejaVu-BoldItalic")
    _fonts_ready = True


def _styles():
    def style(name, **kw):
        base = dict(fontName="DejaVu", fontSize=9, leading=12.5, textColor=colors.HexColor(TEXT))
        base.update(kw)
        return ParagraphStyle(name, **base)

    return {
        "title": style("title", fontName="DejaVu-Bold", fontSize=24, leading=28,
                       textColor=colors.HexColor(PRIMARY)),
        "subtitle": style("subtitle", fontSize=12, leading=16, textColor=colors.HexColor(MUTED)),
        "h2": style("h2", fontName="DejaVu-Bold", fontSize=12, leading=15,
                    textColor=colors.HexColor(PRIMARY), spaceBefore=10, spaceAfter=2),
        "body": style("body"),
        "bullet": style("bullet", leftIndent=10, bulletIndent=0, spaceAfter=2),
        "meta_label": style("meta_label", fontSize=7.5, textColor=colors.HexColor(MUTED)),
        "meta_value": style("meta_value", fontSize=9),
        "kpi_value": style("kpi_value", fontName="DejaVu-Bold", fontSize=15, leading=19,
                           textColor=colors.HexColor(PRIMARY)),
        "kpi_label": style("kpi_label", fontSize=7.5, leading=9, textColor=colors.HexColor(MUTED)),
        "caption": style("caption", fontSize=8, leading=10, textColor=colors.HexColor(MUTED)),
        "note": style("note", fontSize=7.5, leading=10, textColor=colors.HexColor(MUTED)),
        "cell": style("cell", fontSize=7, leading=8.6),
        "cell_right": style("cell_right", fontSize=7, leading=8.6, alignment=TA_RIGHT),
        "head": style("head", fontName="DejaVu-Bold", fontSize=7, leading=8.6, textColor=colors.white),
        "head_right": style("head_right", fontName="DejaVu-Bold", fontSize=7, leading=8.6,
                            textColor=colors.white, alignment=TA_RIGHT),
    }


# ---------- formatowanie ----------

def fmt_number(value, decimals=0):
    text = f"{value:,.{decimals}f}"
    return text.translate({ord(","): "\u00a0", ord("."): ","})


def fmt_money(value):
    return f"{fmt_number(value, 2)} PLN"


def fmt_duration(minutes):
    minutes = int(round(minutes))
    hours, rest = divmod(minutes, 60)
    if hours:
        return f"{fmt_number(minutes)} min ({hours} h {rest:02d} min)"
    return f"{minutes} min"


def fmt_hours(minutes):
    minutes = int(round(minutes))
    hours, rest = divmod(minutes, 60)
    return f"{hours} h {rest:02d} min" if hours else f"{minutes} min"


def _p(text):
    return escape("" if text is None else str(text))


# ---------- dane ----------

def _number(value):
    return float(value) if value is not None else 0.0


def summarize(rows):
    resolved = [r for r in rows if r[db.F_DOWNTIME] is not None]
    downtime = sum(int(r[db.F_DOWNTIME]) for r in resolved)
    return {
        "count": len(rows),
        "open": sum(1 for r in rows if r[db.F_STATUS] != db.STATUS_RESOLVED),
        "resolved": len(resolved),
        "downtime": downtime,
        "mttr": downtime / len(resolved) if resolved else 0.0,
        "labor": sum(_number(r[db.F_LABOR]) for r in rows),
        "parts": sum(_number(r[db.F_PARTS]) for r in rows),
        "total": sum(_number(r[db.F_TOTAL]) for r in rows),
    }


def _grouped(rows, key_index, value_of, limit=8):
    """Sumy po grupach, malejąco; nadmiar grup trafia do pozycji 'Pozostałe'."""
    sums = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        key = r[key_index] or "brak danych"
        a, b = value_of(r)
        sums[key][0] += a
        sums[key][1] += b
    items = sorted(sums.items(), key=lambda kv: kv[1][0] + kv[1][1], reverse=True)
    if len(items) > limit:
        head, tail = items[:limit - 1], items[limit - 1:]
        head.append(("Pozostałe", [sum(v[0] for _, v in tail), sum(v[1] for _, v in tail)]))
        items = head
    return items


# ---------- wykresy ----------

def _light(func):
    """Statystyki w aplikacji ustawiają ciemny styl matplotlib; raport ma być zawsze jasny."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with matplotlib.rc_context(matplotlib.rcParamsDefault):
            return func(*args, **kwargs)
    return wrapper


def _png(fig):
    FigureCanvasAgg(fig)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=250)
    return buf.getvalue()


def _axes(width_in, height_in):
    fig = Figure(figsize=(width_in, height_in), facecolor="white")
    ax = fig.add_subplot(111)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#B8BEC8")
    ax.tick_params(colors=TEXT, labelsize=7.5, length=3, color="#B8BEC8")
    ax.set_facecolor("white")
    return fig, ax


def _empty_chart(width_in, height_in, message):
    fig = Figure(figsize=(width_in, height_in), facecolor="white")
    fig.text(0.5, 0.5, message, ha="center", va="center", color=MUTED, fontsize=9)
    return _png(fig)


def _wrap(label, width=14):
    return textwrap.fill(str(label), width)


@_light
def chart_failure_types(rows, w, h):
    counts = defaultdict(int)
    for r in rows:
        counts[r[db.F_TYPE] or "brak danych"] += 1
    items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:8]
    if not items:
        return _empty_chart(w, h, "Brak danych")
    fig, ax = _axes(w, h)
    labels = [_wrap(k, 26) for k, _ in items][::-1]
    values = [v for _, v in items][::-1]
    bars = ax.barh(labels, values, color=SECONDARY, height=0.62)
    top = max(values)
    for bar, value in zip(bars, values):
        ax.text(value + top * 0.015, bar.get_y() + bar.get_height() / 2, str(value),
                va="center", fontsize=8, color=TEXT)
    ax.set_xlim(0, top * 1.12)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel("Liczba awarii", fontsize=8, color=MUTED)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout(pad=0.6)
    return _png(fig)


@_light
def chart_pareto(rows, key_index, w, h):
    items = _grouped(rows, key_index, lambda r: (_number(r[db.F_DOWNTIME]), 0.0))
    items = [(k, v[0]) for k, v in items if v[0] > 0]
    if not items:
        return _empty_chart(w, h, "Brak zakończonych napraw, więc brak danych o przestojach")
    fig, ax = _axes(w, h)
    labels = [_wrap(k) for k, _ in items]
    values = [v for _, v in items]
    xs = range(len(values))
    bars = ax.bar(xs, values, color=PRIMARY, width=0.6)
    top = max(values)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + top * 0.02, fmt_number(value),
                ha="center", va="bottom", fontsize=7.5, color=TEXT)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylim(0, top * 1.18)
    ax.set_ylabel("Przestój [min]", fontsize=8, color=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)

    total = sum(values)
    cumulative, running = [], 0.0
    for value in values:
        running += value
        cumulative.append(running / total * 100)
    ax2 = ax.twinx()
    ax2.plot(list(xs), cumulative, color=ACCENT, marker="o", markersize=3.5, linewidth=1.5)
    ax2.set_ylim(0, 110)
    ax2.set_ylabel("Udział skumulowany [%]", fontsize=8, color=MUTED)
    ax2.tick_params(labelsize=7.5, colors=TEXT, length=3, color="#B8BEC8")
    for side in ("top", "left"):
        ax2.spines[side].set_visible(False)
    ax2.spines["right"].set_color("#B8BEC8")
    fig.tight_layout(pad=0.6)
    return _png(fig)


@_light
def chart_daily_downtime(rows, year, month, w, h):
    days = calendar.monthrange(year, month)[1]
    per_day = [0.0] * days
    for r in rows:
        if r[db.F_DOWNTIME] is not None and r[db.F_DATE]:
            per_day[r[db.F_DATE].day - 1] += int(r[db.F_DOWNTIME])
    if not any(per_day):
        return _empty_chart(w, h, "Brak zakończonych napraw, więc brak danych o przestojach")
    fig, ax = _axes(w, h)
    xs = list(range(1, days + 1))
    peak = max(per_day)
    colors_ = [DANGER if v == peak else SECONDARY for v in per_day]
    ax.bar(xs, per_day, color=colors_, width=0.7)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(d) for d in xs], fontsize=7)
    ax.set_xlim(0.4, days + 0.6)
    ax.set_ylim(0, peak * 1.15)
    ax.set_xlabel("Dzień miesiąca", fontsize=8, color=MUTED)
    ax.set_ylabel("Przestój [min]", fontsize=8, color=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout(pad=0.6)
    return _png(fig)


@_light
def chart_costs(rows, key_index, w, h):
    items = _grouped(rows, key_index, lambda r: (_number(r[db.F_LABOR]), _number(r[db.F_PARTS])))
    items = [(k, v) for k, v in items if v[0] + v[1] > 0]
    if not items:
        return _empty_chart(w, h, "Brak kosztów do pokazania")
    fig, ax = _axes(w, h)
    labels = [_wrap(k) for k, _ in items]
    labor = [v[0] for _, v in items]
    parts = [v[1] for _, v in items]
    xs = list(range(len(items)))
    ax.bar(xs, labor, color=PRIMARY, width=0.6, label="Robocizna")
    ax.bar(xs, parts, bottom=labor, color=ACCENT, width=0.6, label="Części")
    top = max(a + b for a, b in zip(labor, parts))
    for x, a, b in zip(xs, labor, parts):
        ax.text(x, a + b + top * 0.02, fmt_number(a + b), ha="center", va="bottom", fontsize=7.5, color=TEXT)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylim(0, top * 1.18)
    ax.set_ylabel("Koszt [PLN]", fontsize=8, color=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(fontsize=7.5, frameon=False, loc="upper right")
    fig.tight_layout(pad=0.6)
    return _png(fig)


# ---------- elementy dokumentu ----------

def _image(png, width, height):
    return Image(io.BytesIO(png), width=width, height=height)


def _section(title, styles):
    return [Paragraph(_p(title), styles["h2"]),
            HRFlowable(width="100%", thickness=0.6, color=colors.HexColor(GRID), spaceAfter=5)]


def _kpi_table(stats, styles):
    def card(value, label):
        return [Paragraph(value, styles["kpi_value"]), Paragraph(_p(label), styles["kpi_label"])]

    def money(value):
        return f"{fmt_number(value, 2)} <font size=9>PLN</font>"

    gap = 6 * mm
    cell_w = (CONTENT_W - 2 * gap) / 3
    mttr = fmt_hours(stats["mttr"]) if stats["resolved"] else "-"
    data = [
        [card(str(stats["count"]), "Liczba awarii"), "",
         card(str(stats["open"]), "Awarie otwarte (bez zakończonej naprawy)"), "",
         card(fmt_hours(stats["downtime"]), f"Łączny przestój ({fmt_number(stats['downtime'])} min)")],
        ["", "", "", "", ""],
        [card(mttr, "Średni czas naprawy (MTTR)"), "",
         card(money(stats["total"]), f"Koszt całkowity (robocizna: {fmt_number(stats['labor'], 2)} PLN)"), "",
         card(money(stats["parts"]), "Koszt części z magazynu")],
    ]
    table = Table(data, colWidths=[cell_w, gap, cell_w, gap, cell_w],
                  rowHeights=[17 * mm, 3 * mm, 17 * mm])
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for row in (0, 2):
        for col in (0, 2, 4):
            style += [("BACKGROUND", (col, row), (col, row), colors.HexColor(LIGHT)),
                      ("LINEBEFORE", (col, row), (col, row), 2.2, colors.HexColor(PRIMARY)),
                      ("LEFTPADDING", (col, row), (col, row), 9),
                      ("RIGHTPADDING", (col, row), (col, row), 6)]
    table.setStyle(TableStyle(style))
    return table


def _meta_table(year, month, machine, generated_by, styles):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    last_day = calendar.monthrange(year, month)[1]

    def cell(label, value):
        return [Paragraph(_p(label), styles["meta_label"]), Paragraph(_p(value), styles["meta_value"])]

    data = [[cell("ZAKRES", machine or ALL_MACHINES),
             cell("OKRES", f"{year}-{month:02d}-01 - {year}-{month:02d}-{last_day:02d}"),
             cell("WYGENEROWANO", now),
             cell("PRZYGOTOWAŁ", generated_by)]]
    table = Table(data, colWidths=[40 * mm, 52 * mm, 40 * mm, CONTENT_W - 132 * mm])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return table


def _observations(rows, stats, machine, key_index):
    notes = []
    group_name = "maszyna" if machine is None else "podsystem"
    downtime_by = _grouped(rows, key_index, lambda r: (_number(r[db.F_DOWNTIME]), 0.0))
    downtime_by = [(k, v[0]) for k, v in downtime_by if v[0] > 0]
    if downtime_by and stats["downtime"]:
        name, minutes = downtime_by[0]
        notes.append(f"Największy łączny przestój ma {group_name} <b>{_p(name)}</b>: "
                     f"{fmt_duration(minutes)}, czyli {minutes / stats['downtime'] * 100:.0f}% wszystkich przestojów.")
    types = defaultdict(int)
    for r in rows:
        types[r[db.F_TYPE] or "brak danych"] += 1
    kind, n = max(types.items(), key=lambda kv: kv[1])
    notes.append(f"Najczęstszy typ awarii: <b>{_p(kind)}</b> ({n} z {stats['count']} zgłoszeń, "
                 f"{n / stats['count'] * 100:.0f}%).")
    if stats["open"]:
        notes.append(f"Do zakończenia pozostaje {stats['open']} awarii (nie wliczono ich do przestojów i MTTR).")
    else:
        notes.append("Wszystkie zgłoszone awarie z tego okresu zostały naprawione.")
    return notes


def _failures_table(rows, styles):
    heads = ["ID", "Data", "Godz.", "Maszyna", "Podsystem", "Typ awarii i opis", "Status",
             "Przestój [min]", "Koszt [PLN]"]
    widths = [8, 17, 10, 22, 22, 42, 19, 15, 19]
    scale = CONTENT_W / (sum(widths) * mm)
    widths = [w * mm * scale for w in widths]

    data = [[Paragraph(h, styles["head_right"] if i >= 7 else styles["head"]) for i, h in enumerate(heads)]]
    for r in rows:
        description = (r[db.F_DESCRIPTION] or "").replace("\n", " ").strip()
        if len(description) > 60:
            description = description[:57] + "..."
        kind = f"<b>{_p(r[db.F_TYPE])}</b>"
        if description:
            kind += f'<br/><font color="{MUTED}">{_p(description)}</font>'
        status_color = STATUS_COLORS.get(r[db.F_STATUS], TEXT)
        downtime = fmt_number(r[db.F_DOWNTIME]) if r[db.F_DOWNTIME] is not None else "-"
        cost = fmt_number(_number(r[db.F_TOTAL]), 2) if r[db.F_TOTAL] is not None else "-"
        data.append([
            Paragraph(str(r[db.F_ID]), styles["cell"]),
            Paragraph(f"{r[db.F_DATE]:%Y-%m-%d}" if r[db.F_DATE] else "-", styles["cell"]),
            Paragraph(_p(r[db.F_TIME_REPORTED] or "-"), styles["cell"]),
            Paragraph(_p(r[db.F_AREA] or "-"), styles["cell"]),
            Paragraph(_p(r[db.F_SUBSYSTEM] or "-"), styles["cell"]),
            Paragraph(kind, styles["cell"]),
            Paragraph(f'<font color="{status_color}"><b>{_p(r[db.F_STATUS])}</b></font>', styles["cell"]),
            Paragraph(downtime, styles["cell_right"]),
            Paragraph(cost, styles["cell_right"]),
        ])

    stats = summarize(rows)
    data.append([Paragraph("<b>Razem</b>", styles["cell"]), "", "", "", "", "", "",
                 Paragraph(f"<b>{fmt_number(stats['downtime'])}</b>", styles["cell_right"]),
                 Paragraph(f"<b>{fmt_number(stats['total'], 2)}</b>", styles["cell_right"])])

    table = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(PRIMARY)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, colors.HexColor(GRID)),
        ("LINEABOVE", (0, -1), (-1, -1), 0.9, colors.HexColor(PRIMARY)),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor(LIGHT)),
        ("SPAN", (0, -1), (6, -1)),   # etykieta "Razem" nie mieści się w wąskiej kolumnie ID
    ]
    for i in range(2, len(data) - 1, 2):
        style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(LIGHT)))
    table.setStyle(TableStyle(style))
    return table


# ---------- strona ----------

def _numbered_canvas(footer_left):
    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._pages)
            for state in self._pages:
                self.__dict__.update(state)
                self._footer(total)
                super().showPage()
            super().save()

        def _footer(self, total):
            self.setStrokeColor(colors.HexColor(GRID))
            self.setLineWidth(0.6)
            self.line(MARGIN_X, 14 * mm, PAGE_W - MARGIN_X, 14 * mm)
            self.setFont("DejaVu", 7.5)
            self.setFillColor(colors.HexColor(MUTED))
            self.drawString(MARGIN_X, 9.5 * mm, footer_left)
            self.drawRightString(PAGE_W - MARGIN_X, 9.5 * mm, f"Strona {self._pageNumber} z {total}")

    return NumberedCanvas


def _draw_header(c, doc, right_text):
    c.saveState()
    c.setFillColor(colors.HexColor(PRIMARY))
    c.rect(0, PAGE_H - 11 * mm, PAGE_W, 11 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("DejaVu-Bold", 9)
    c.drawString(MARGIN_X, PAGE_H - 7.2 * mm, "CMMS")
    c.setFont("DejaVu", 8.5)
    c.drawString(MARGIN_X + 14 * mm, PAGE_H - 7.2 * mm, "Raport awaryjności")
    c.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 7.2 * mm, right_text)
    c.restoreState()


# ---------- główna funkcja ----------

def build_report(rows, year, month, machine, generated_by, output_path):
    """Zapisuje raport PDF do output_path. machine=None oznacza wszystkie maszyny."""
    if not rows:
        raise ValueError("Brak awarii w wybranym zakresie.")

    _register_fonts()
    styles = _styles()
    stats = summarize(rows)
    scope = machine or ALL_MACHINES
    period = month_label(year, month)

    # dla jednej maszyny porównujemy podsystemy, dla wszystkich - maszyny
    key_index = db.F_SUBSYSTEM if machine else db.F_AREA
    group_word = "podsystemu" if machine else "maszyny"

    chart_h = 52 * mm
    chart_w_in = CONTENT_W / 25.4 / mm
    chart_h_in = chart_h / 25.4 / mm

    story = [
        Spacer(1, 1 * mm),
        Paragraph("Raport awaryjności", styles["title"]),
        Paragraph(f"{_p(period)} | {_p(scope)}", styles["subtitle"]),
        Spacer(1, 4 * mm),
        _meta_table(year, month, machine, generated_by, styles),
    ]

    story += _section("1. Podsumowanie", styles)
    story += [_kpi_table(stats, styles), Spacer(1, 4 * mm)]
    story += [Paragraph("Najważniejsze obserwacje", ParagraphStyle(
        "obs", parent=styles["body"], fontName="DejaVu-Bold", spaceAfter=3))]
    for note in _observations(rows, stats, machine, key_index):
        story.append(Paragraph(note, styles["bullet"], bulletText="\u2022"))

    # nagłówek sekcji zawsze razem z pierwszym wykresem
    story.append(KeepTogether(_section("2. Analiza przyczyn i miejsc awarii", styles) + [
        _image(chart_failure_types(rows, chart_w_in, chart_h_in), CONTENT_W, chart_h),
        Paragraph("Rys. 1. Liczba awarii według typu.", styles["caption"]),
        Spacer(1, 3 * mm)]))
    story.append(KeepTogether([
        _image(chart_pareto(rows, key_index, chart_w_in, chart_h_in), CONTENT_W, chart_h),
        Paragraph(f"Rys. 2. Przestoje według {group_word} (wykres Pareto z udziałem skumulowanym).",
                  styles["caption"]),
        Spacer(1, 2 * mm)]))

    story.append(KeepTogether(_section("3. Przebieg w czasie i koszty", styles) + [
        _image(chart_daily_downtime(rows, year, month, chart_w_in, chart_h_in), CONTENT_W, chart_h),
        Paragraph(f"Rys. 3. Łączny przestój w poszczególnych dniach miesiąca (dzień z największym "
                  f"przestojem zaznaczono kolorem czerwonym).", styles["caption"]),
        Spacer(1, 3 * mm)]))
    story.append(KeepTogether([
        _image(chart_costs(rows, key_index, chart_w_in, chart_h_in), CONTENT_W, chart_h),
        Paragraph(f"Rys. 4. Koszty napraw według {group_word}: robocizna i części z magazynu.",
                  styles["caption"]),
        Spacer(1, 2 * mm)]))

    story.append(CondPageBreak(60 * mm))   # nagłówek tabeli nie zostaje sam na dole strony
    story += _section("4. Zestawienie awarii", styles)
    story.append(_failures_table(rows, styles))
    story += [Spacer(1, 4 * mm), Paragraph(
        "MTTR to suma przestojów podzielona przez liczbę napraw zakończonych. Koszt robocizny wynika "
        "z czasu przestoju i stawki godzinowej osoby naprawiającej, a koszt części z ceny części "
        "w magazynie. Awarie otwarte nie mają jeszcze przestoju ani kosztów.", styles["note"])]

    right = f"{period} | {scope}"
    doc = BaseDocTemplate(
        output_path, pagesize=A4, leftMargin=MARGIN_X, rightMargin=MARGIN_X,
        topMargin=18 * mm, bottomMargin=19 * mm,
        title=f"Raport awaryjności - {period} - {scope}", author=generated_by,
        subject="Analiza awarii", creator="CMMS")
    frame = Frame(MARGIN_X, 19 * mm, CONTENT_W, PAGE_H - 37 * mm, id="main",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame],
                                       onPage=lambda c, d: _draw_header(c, d, right))])
    footer = f"Wygenerowano {datetime.now():%Y-%m-%d %H:%M} | {generated_by}"
    doc.build(story, canvasmaker=_numbered_canvas(footer))
    return output_path

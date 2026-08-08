"""Regenerate CA2 presentation PPTX, speaker notes DOCX, and live demo DOCX.

Applies review fixes: true vs realistic foresight, three-bin wording, reward,
benchmark labels, RL concepts, teamwork, ethics breadth, synced notes.
Also aligned with current dashboard nav + User Guide (Twin / Price Monitor /
Agent Play / Results / Overview).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from pptx import Presentation
from pptx.dml.color import RGBColor as PptRGB
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import nsmap
from pptx.util import Emu, Inches as PptInches, Pt as PptPt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "presentation"
OUT.mkdir(parents=True, exist_ok=True)
ASSETS = OUT / "_assets"
ASSETS.mkdir(exist_ok=True)

# Brand colours
NAVY = PptRGB(0x07, 0x0D, 0x1A)
SLATE = PptRGB(0x0C, 0x14, 0x24)
GOLD = PptRGB(0xF5, 0x9E, 0x1A)
WHITE = PptRGB(0xF8, 0xFA, 0xFC)
MUTED = PptRGB(0x94, 0xA3, 0xB8)
GREEN = PptRGB(0x22, 0xC5, 0x5E)
CARD = PptRGB(0x12, 0x1A, 0x2B)

SLIDE_W = PptInches(13.333)
SLIDE_H = PptInches(7.5)

TEAM = [
    ("Nathan Rocha", "20082900", "Data & MDP / Twin demo driver"),
    ("Nadeesha Jayasuriya", "20093736", "RL experiment / Results narrator"),
    ("Emmanuel Addoh", "10592825", "Opening & closing (non-technical)"),
    ("Bahadir Demir", "20098301", "Dashboard & demo support"),
]

# Exact headline numbers (oracle-direction privileged Q)
COSTS = {
    "No-battery reference": 160.75,
    "Perfect-info bound": 74.92,
    "Greedy (5-action)": 90.39,
    "Current Q": 124.23,
    "Privileged Q\n(true 4h direction)": 139.68,
}

SPEAKER_NOTES = {
    1: (
        "CA1 asked whether RL could beat simple solar self-consumption. "
        "CA2 asks whether forward-looking price information helps a tabular agent time grid arbitrage — "
        "and we tested that with a deployed digital twin. "
        "Emmanuel opens with the team and closes takeaways (non-technical). "
        "Nathan covers the problem/MDP and drives the Twin demo; Nadeesha owns the experiment narrative; "
        "Bahadir supports the recorded dashboard demo (backup clicks if needed)."
    ),
    2: (
        "Frame the problem: solar self-use is easy with rules; profitable timing needs the future. "
        "Our experiment isolates information — not just another algorithm tweak. "
        "Emphasise: more actions without matching information can raise the household bill."
    ),
    3: (
        "The agent is the battery controller; the environment is the simulated household and grid. "
        "Five actions make price actionable. Privileged agents get a three-bin price-direction feature "
        "over the next four hours. State grows from 540 to 1620. "
        "Reward is negative adjusted electricity cost, including cycling cost and terminal SOC valuation — "
        "so Q-Learning maximises reward by minimising cost. "
        "Learning uses a Q(s,a) table, ε-greedy exploration in training, and an argmax evaluation policy, "
        "with updates controlled by α and γ. "
        "Tabular Q-Learning keeps state–action values directly inspectable; deep RL becomes useful if the state space grows substantially."
    ),
    4: (
        "Fairness is the point: retrain and evaluate everything under wholesale export. "
        "Headline numbers use Privileged Q with the true four-hour direction signal — an oracle-style probe of that feature. "
        "Realistic climatology + persistence forecasting is available in the deployment and experiment runner, "
        "but it is not the source of the 139.68 AUD headline. "
        "Do not mix these AUD totals with older fixed-FiT CA2 runs."
    ),
    5: (
        "Aggregate results across 53 held-out days. "
        "Greedy 90.39 is the best evaluated deployable controller. "
        "Current Q about 124; Privileged true-direction about 140. "
        "Greedy wins 96% of days. "
        "True four-hour direction alone did not help — privileged used arbitrage more and still cost more. "
        "The hypothesis was not supported under this experimental setup."
    ),
    6: (
        "This is the required CA2 theory-versus-deployed story: "
        "perfect information sets a lower-cost bound; deployable policies sit above it; "
        "a coarse three-bin direction feature did not close the gap. "
        "Import pays wholesale plus 0.22 while export pays wholesale, so round-trip sell is hard; "
        "profitable foresight is mostly charge cheap then discharge to load."
    ),
    7: (
        "The dashboard is the working-deployment mark. Top nav: Digital Twin, Price Monitor, Agent Play, Results, Overview. "
        "Twin auto-runs once, then use Run comparison after settings change; winner strip, charts, and timestep inspector. "
        "Price Monitor is live AEMO NSW1 with typical PV/load — separate from historical Twin. "
        "Ethics is broader than bill harm: transparency of experimental tariff and partial live inputs; "
        "privacy and consent for future smart-meter data; fairness of access to batteries and tariffs; "
        "generalisability limited to one Ausgrid household and NSW1; "
        "safety via SOC and power limits, manual override, and greedy as fallback; "
        "and honesty that this is a software twin, not a physical battery. "
        "Agent Play is an interactive oversight demonstration — not a scientifically fair competition — "
        "because the human always sees a realistic forecast while Privileged Q may use true four-hour direction. "
        "Operator steps are in deliverables/GreineQ_User_Guide.docx."
    ),
    8: (
        "Be precise, not generic. Limitations: three-bin direction without magnitude; experimental wholesale export; "
        "larger privileged table may under-train at 10k episodes; live feed is price-real and meter-partial. "
        "Next step targets magnitude or spread foresight — the bottleneck we identified — "
        "and keep greedy as a safety baseline until RL beats it on held-out days. "
        "After this slide: switch to the dashboard for the recorded demo (~5 min), then return for Emmanuel’s slide 9 close."
    ),
    9: (
        "Emmanuel closes the recording in one plain line: we made arbitrage actionable, tested whether a four-hour "
        "three-bin direction feature helps tabular RL, found it does not beat greedy under this setup, and shipped a "
        "dashboard that makes that gap visible. Stop cleanly — this is a 15-minute recording with no Q&A."
    ),
    10: (
        "Sources slide — do not include in the recording unless the brief requires provenance on screen."
    ),
}


def _set_run(run, *, size=18, bold=False, color=WHITE, font="Calibri"):
    run.font.size = PptPt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font


def _add_textbox(slide, left, top, width, height, text, *, size=18, bold=False, color=WHITE, align=PP_ALIGN.LEFT, font="Calibri"):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    _set_run(run, size=size, bold=bold, color=color, font=font)
    return box


def _add_bullets(slide, left, top, width, height, lines, *, size=15, color=WHITE):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.level = 0
        p.space_after = PptPt(6)
        run = p.add_run()
        run.text = "•  " + line
        _set_run(run, size=size, color=color)
    return box


def _fill_shape(shape, rgb):
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb
    shape.line.fill.background()


def _bg(slide):
    fill = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    _fill_shape(fill, NAVY)
    # keep background behind other shapes
    spTree = slide.shapes._spTree
    sp = fill._element
    spTree.remove(sp)
    spTree.insert(2, sp)


def _footer(slide, page, total=10):
    # Safe footer well inside canvas
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, PptInches(0.4), PptInches(7.05), PptInches(12.5), PptInches(0.28))
    _fill_shape(bar, SLATE)
    _add_textbox(
        slide,
        PptInches(0.5),
        PptInches(7.05),
        PptInches(10),
        PptInches(0.28),
        f"GréineQ  ·  B9AI105 CA2  ·  {page}/{total}",
        size=10,
        color=MUTED,
    )


def _title(slide, text):
    _add_textbox(slide, PptInches(0.5), PptInches(0.28), PptInches(12.2), PptInches(0.55), text, size=28, bold=True, color=GOLD)


def _card(slide, left, top, width, height):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    _fill_shape(shp, CARD)
    shp.adjustments[0] = 0.08
    return shp


def _notes(slide, text):
    notes = slide.notes_slide
    tf = notes.notes_text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text


def make_dashboard_mock(path: Path) -> None:
    """Stylised Digital Twin panel for Slide 7 (matches current Twin UX)."""
    fig, ax = plt.subplots(figsize=(7.2, 4.4), facecolor="#0c1424")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    fig.patch.set_facecolor("#0c1424")

    # Outer panel
    ax.add_patch(plt.Rectangle((0.2, 0.3), 9.6, 5.4, fill=True, facecolor="#121a2b", linewidth=0, zorder=0))
    # Mini top nav
    for i, label in enumerate(["Twin", "Price", "Play", "Results"]):
        x = 0.45 + i * 1.55
        ax.add_patch(plt.Rectangle((x, 5.15), 1.4, 0.38, fill=True, facecolor="#1e293b", linewidth=0))
        ax.text(x + 0.7, 5.34, label, color="#f8fafc" if i == 0 else "#94a3b8", fontsize=7, ha="center", va="center")

    ax.text(0.45, 4.75, "Digital Twin  ·  2012-07-14  ·  Historical replay", color="#f59e1a", fontsize=10, fontweight="bold", va="center")
    ax.text(0.45, 4.4, "Same day · same tariff · Greedy · Current Q · Privileged Q", color="#94a3b8", fontsize=7.5, va="center")

    # Winner strip
    ax.add_patch(plt.Rectangle((0.45, 3.85), 9.1, 0.42, fill=True, facecolor="#14532d", linewidth=0))
    ax.text(5.0, 4.06, "Winning agent  ·  Greedy   Saved vs no-battery", color="#86efac", fontsize=8, ha="center", va="center", fontweight="bold")

    # Mini cost bars (day-level illustration)
    names = ["Greedy", "Current Q", "Privileged"]
    vals = [90.4, 124.2, 139.7]
    colors = ["#22c55e", "#38bdf8", "#f59e1a"]
    for i, (n, v, c) in enumerate(zip(names, vals, colors)):
        y = 3.15 - i * 0.7
        ax.add_patch(plt.Rectangle((0.5, y), 0.15 + v / 40, 0.48, fill=True, facecolor=c, alpha=0.85, linewidth=0))
        ax.text(0.55, y + 0.24, f"{n}   {v:.1f} AUD", color="#f8fafc", fontsize=8.5, va="center")

    ax.text(0.45, 0.55, "Run comparison after settings change  ·  timestep inspector  ·  zoom 100%", color="#64748b", fontsize=7.5)
    fig.tight_layout(pad=0.2)
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def make_bar_chart(path: Path) -> None:
    labels = list(COSTS.keys())
    values = list(COSTS.values())
    colors = ["#64748b", "#6366f1", "#22c55e", "#38bdf8", "#f59e1a"]
    fig, ax = plt.subplots(figsize=(10.5, 4.2), facecolor="#070d1a")
    ax.set_facecolor("#0c1424")
    bars = ax.bar(labels, values, color=colors, width=0.62)
    ax.set_ylabel("Net cost (AUD)", color="#e2e8f0")
    ax.tick_params(colors="#94a3b8")
    for spine in ax.spines.values():
        spine.set_color("#1e293b")
    ax.set_title("Aggregate net cost — 53 held-out test days", color="#f8fafc", fontsize=13, pad=10)
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + 2.5, f"{v:.1f}", ha="center", va="bottom", color="#f8fafc", fontsize=9)
    ax.set_ylim(0, 185)
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def build_pptx() -> Path:
    chart_path = ASSETS / "ca2_net_cost_bars.png"
    make_bar_chart(chart_path)
    dash_path = ASSETS / "ca2_dashboard_mock.png"
    make_dashboard_mock(dash_path)

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]

    # --- 1 Title ---
    s = prs.slides.add_slide(blank)
    _bg(s)
    _add_textbox(s, PptInches(0.7), PptInches(1.5), PptInches(11.8), PptInches(0.9), "GréineQ CA2", size=40, bold=True, color=GOLD, align=PP_ALIGN.CENTER)
    _add_textbox(
        s,
        PptInches(1.2),
        PptInches(2.4),
        PptInches(10.8),
        PptInches(0.8),
        "Tabular RL for solar battery dispatch — when foresight meets the grid",
        size=20,
        color=WHITE,
        align=PP_ALIGN.CENTER,
    )
    _add_textbox(
        s,
        PptInches(1.2),
        PptInches(3.15),
        PptInches(10.8),
        PptInches(2.0),
        "Nathan Rocha  ·  20082900  ·  Data & MDP\n"
        "Nadeesha Jayasuriya  ·  20093736  ·  RL experiment & deployment\n"
        "Emmanuel Addoh  ·  10592825  ·  Opening & closing\n"
        "Bahadir Demir  ·  20098301  ·  Dashboard & demo support\n\n"
        "B9AI105 Reinforcement Learning  ·  Forecast-information experiment",
        size=14,
        color=MUTED,
        align=PP_ALIGN.CENTER,
    )
    _add_textbox(
        s,
        PptInches(1.2),
        PptInches(5.45),
        PptInches(10.8),
        PptInches(0.7),
        "Slides: Emmanuel 1 & 9  ·  Nathan 2–3, 7  ·  Nadeesha 4–6, 8  ·  Bahadir demo backup\n"
        "15-min recording · no Q&A  ·  Demo: Nathan drives · Nadeesha narrates · Bahadir backup",
        size=12,
        color=GOLD,
        align=PP_ALIGN.CENTER,
    )
    _footer(s, 1)
    _notes(s, SPEAKER_NOTES[1])

    # --- 2 Problem ---
    s = prs.slides.add_slide(blank)
    _bg(s)
    _title(s, "Problem & CA2 question")
    _card(s, PptInches(0.5), PptInches(1.05), PptInches(5.9), PptInches(3.4))
    _add_textbox(s, PptInches(0.75), PptInches(1.2), PptInches(5.4), PptInches(0.4), "Household decision every 30 minutes", size=16, bold=True, color=GOLD)
    _add_bullets(
        s,
        PptInches(0.75),
        PptInches(1.7),
        PptInches(5.4),
        PptInches(2.5),
        [
            "Use solar / charge / discharge — easy with rules",
            "Buy low / use or sell later — needs future price timing",
            "Richer action space without matching information can raise the bill",
        ],
        size=14,
    )
    _card(s, PptInches(6.7), PptInches(1.05), PptInches(6.1), PptInches(3.4))
    _add_textbox(s, PptInches(6.95), PptInches(1.2), PptInches(5.6), PptInches(0.4), "CA2 research question", size=16, bold=True, color=GOLD)
    _add_textbox(
        s,
        PptInches(6.95),
        PptInches(1.8),
        PptInches(5.6),
        PptInches(2.3),
        "Does a short three-bin price-direction foresight feature help tabular RL beat a strong greedy baseline under a fair, arbitrage-capable MDP?",
        size=16,
        color=WHITE,
    )
    _add_textbox(
        s,
        PptInches(0.5),
        PptInches(4.7),
        PptInches(12.2),
        PptInches(1.6),
        "Why it matters for deployment: capability without information quality is an ethics and safety risk — "
        "we treat that as part of the CA2 story, not a side note.",
        size=14,
        color=MUTED,
    )
    _footer(s, 2)
    _notes(s, SPEAKER_NOTES[2])

    # --- 3 MDP ---
    s = prs.slides.add_slide(blank)
    _bg(s)
    _title(s, "MDP — agent, environment, learning")
    # Agent-env loop
    a = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PptInches(1.2), PptInches(1.1), PptInches(3.2), PptInches(1.1))
    _fill_shape(a, CARD)
    _add_textbox(s, PptInches(1.3), PptInches(1.25), PptInches(3.0), PptInches(0.8), "AGENT\nBattery controller (Q-Learning)", size=13, bold=True, color=GOLD, align=PP_ALIGN.CENTER)
    e = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PptInches(8.7), PptInches(1.1), PptInches(3.4), PptInches(1.1))
    _fill_shape(e, CARD)
    _add_textbox(s, PptInches(8.8), PptInches(1.25), PptInches(3.2), PptInches(0.8), "ENVIRONMENT\nSimulated household + grid", size=13, bold=True, color=GOLD, align=PP_ALIGN.CENTER)
    _add_textbox(s, PptInches(4.6), PptInches(1.15), PptInches(3.8), PptInches(0.45), "action →", size=14, color=MUTED, align=PP_ALIGN.CENTER)
    _add_textbox(s, PptInches(4.6), PptInches(1.65), PptInches(3.8), PptInches(0.45), "← state, reward", size=14, color=MUTED, align=PP_ALIGN.CENTER)

    _add_bullets(
        s,
        PptInches(0.55),
        PptInches(2.5),
        PptInches(12.2),
        PptInches(3.8),
        [
            "State: SOC × PV × load × price × time-of-day (+ foresight bin for privileged) — Current 540 · Privileged 1620",
            "Actions (5): Hold · Solar charge · Discharge · Grid-charge · Export",
            "Reward = negative adjusted electricity cost, including battery cycling cost and terminal SOC valuation",
            "Learning: Q(s,a) value table · ε-greedy training exploration · argmax evaluation policy · updates controlled by α and γ",
            "Tariff honesty (experimental): retail import = wholesale + margin; export priced at wholesale — not a household FiT",
            "Data: Ausgrid Customer 1 + AEMO NSW1 · one day = 48 half-hour steps · chronological train/val/test",
        ],
        size=13,
    )
    _footer(s, 3)
    _notes(s, SPEAKER_NOTES[3])

    # --- 4 Experiment ---
    s = prs.slides.add_slide(blank)
    _bg(s)
    _title(s, "Experiment design — fair comparison")
    _add_textbox(
        s,
        PptInches(0.5),
        PptInches(0.95),
        PptInches(12.2),
        PptInches(0.4),
        "Same physics, same tariff, same held-out test days  ·  Q-Learning 10k episodes × 5 seeds (42–46)",
        size=13,
        color=MUTED,
    )
    rows = [
        ("Controller", "Information used"),
        ("Greedy (5-action)", "Current state + price heuristics"),
        ("Current Q", "Current state only"),
        ("Privileged Q — true 4h direction", "Current + true next-4h direction (3 bins)"),
        ("Perfect-info bound", "Full future prices (benchmark only)"),
    ]
    y0 = PptInches(1.45)
    for i, (a, b) in enumerate(rows):
        y = y0 + PptInches(0.42) * i
        bgc = GOLD if i == 0 else CARD
        tc = NAVY if i == 0 else WHITE
        r1 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, PptInches(0.5), y, PptInches(5.5), PptInches(0.38))
        _fill_shape(r1, bgc)
        r2 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, PptInches(6.05), y, PptInches(6.7), PptInches(0.38))
        _fill_shape(r2, bgc)
        _add_textbox(s, PptInches(0.6), y + PptInches(0.05), PptInches(5.3), PptInches(0.3), a, size=12, bold=(i == 0), color=tc)
        _add_textbox(s, PptInches(6.15), y + PptInches(0.05), PptInches(6.5), PptInches(0.3), b, size=12, bold=(i == 0), color=tc)

    _add_bullets(
        s,
        PptInches(0.5),
        PptInches(3.8),
        PptInches(12.2),
        PptInches(2.6),
        [
            "Privileged signal: max(price next 8 half-hours) − current → FALL_OR_FLAT / MODERATE_RISE / STRONG_RISE (train-only tertiles)",
            "Headline results use the true four-hour direction signal (information probe on that feature)",
            "Realistic forecast mode (climatology + persistence) is available in deployment/runner — not the source of these headline AUD totals",
            "Fairness rule: do not mix with older fixed-FiT CA2 numbers",
        ],
        size=13,
    )
    _footer(s, 4)
    _notes(s, SPEAKER_NOTES[4])

    # --- 5 Results chart ---
    s = prs.slides.add_slide(blank)
    _bg(s)
    _title(s, "Aggregate results — 53 held-out days")
    _add_textbox(
        s,
        PptInches(0.5),
        PptInches(0.95),
        PptInches(12.2),
        PptInches(0.35),
        "Wholesale-export setting  ·  Privileged Q = true four-hour direction (mean ± std over 5 seeds where shown)",
        size=12,
        color=MUTED,
    )
    s.shapes.add_picture(str(chart_path), PptInches(0.55), PptInches(1.4), width=PptInches(12.2))
    _add_textbox(
        s,
        PptInches(0.5),
        PptInches(5.7),
        PptInches(12.2),
        PptInches(0.9),
        "Win rate: Greedy 96.2% · Current Q 3.8% · Privileged (true direction) 0%\n"
        "Finding: a three-bin future-direction feature alone was not enough — Privileged used arbitrage more and still cost more.\n"
        "Labels: no-battery reference · perfect-information lower-cost bound · greedy = best evaluated deployable controller.",
        size=12,
        color=WHITE,
    )
    _footer(s, 5)
    _notes(s, SPEAKER_NOTES[5])

    # --- 6 Theory vs deployed ---
    s = prs.slides.add_slide(blank)
    _bg(s)
    _title(s, "Theory vs deployed")
    _card(s, PptInches(0.5), PptInches(1.1), PptInches(6.0), PptInches(4.6))
    _add_textbox(s, PptInches(0.7), PptInches(1.25), PptInches(5.6), PptInches(0.35), "Theory", size=16, bold=True, color=GOLD)
    _add_bullets(
        s,
        PptInches(0.7),
        PptInches(1.75),
        PptInches(5.6),
        PptInches(3.6),
        [
            "Perfect information sets a lower-cost bound (~74.9 AUD)",
            "Foresight should help timing of grid-charge / discharge-to-load",
            "Larger action space increases capability",
        ],
        size=14,
    )
    _card(s, PptInches(6.8), PptInches(1.1), PptInches(6.0), PptInches(4.6))
    _add_textbox(s, PptInches(7.0), PptInches(1.25), PptInches(5.6), PptInches(0.35), "Deployed reality", size=16, bold=True, color=GOLD)
    _add_bullets(
        s,
        PptInches(7.0),
        PptInches(1.75),
        PptInches(5.6),
        PptInches(3.6),
        [
            "Best evaluated deployable policy is still greedy (~90.4 AUD)",
            "Three-bin direction ≠ magnitude or load-aware value of charging",
            "More arbitrage actions without matching info → higher bill (~140 AUD)",
        ],
        size=14,
    )
    _footer(s, 6)
    _notes(s, SPEAKER_NOTES[6])

    # --- 7 Deployment + ethics ---
    s = prs.slides.add_slide(blank)
    _bg(s)
    _title(s, "Working deployment & ethics")
    s.shapes.add_picture(str(dash_path), PptInches(0.45), PptInches(1.05), width=PptInches(6.2))
    _add_textbox(
        s,
        PptInches(0.5),
        PptInches(5.35),
        PptInches(6.1),
        PptInches(1.2),
        "Nav: Twin · Price Monitor · Agent Play · Results · Overview\n"
        "Price Monitor ≠ Twin  ·  Landing animation = heuristic, not trained Q\n"
        "User Guide: deliverables/GreineQ_User_Guide.docx",
        size=10,
        color=MUTED,
    )
    _add_textbox(s, PptInches(6.85), PptInches(1.05), PptInches(6.0), PptInches(0.35), "Ethics (broader than bill harm)", size=15, bold=True, color=GOLD)
    _add_bullets(
        s,
        PptInches(6.85),
        PptInches(1.5),
        PptInches(5.9),
        PptInches(4.8),
        [
            "Transparency: experimental tariff & partial live inputs disclosed",
            "Privacy: future smart-meter feeds need consent & security",
            "Fairness: batteries / wholesale exposure not equally accessible",
            "Generalisability: one Ausgrid household, one NSW region",
            "Safety: SOC/power limits, manual override, greedy fallback",
            "Hardware: software twin — not a physical battery deployment",
            "Agent Play = oversight demo (realistic forecast vs true-direction privileged)",
        ],
        size=12,
    )
    _footer(s, 7)
    _notes(s, SPEAKER_NOTES[7])

    # --- 8 Limitations ---
    s = prs.slides.add_slide(blank)
    _bg(s)
    _title(s, "Limitations & next steps")
    _card(s, PptInches(0.5), PptInches(1.1), PptInches(6.0), PptInches(4.7))
    _add_textbox(s, PptInches(0.7), PptInches(1.25), PptInches(5.6), PptInches(0.35), "Limitations (precise)", size=16, bold=True, color=GOLD)
    _add_bullets(
        s,
        PptInches(0.7),
        PptInches(1.8),
        PptInches(5.6),
        PptInches(3.7),
        [
            "Three-bin direction, not magnitude or load-aware value",
            "Wholesale-export tariff is experimental (not retail FiT)",
            "Privileged table 3× larger — may under-train at 10k episodes",
            "Live feed is price-real, meter-partial (disclosed)",
        ],
        size=14,
    )
    _card(s, PptInches(6.8), PptInches(1.1), PptInches(6.0), PptInches(4.7))
    _add_textbox(s, PptInches(7.0), PptInches(1.25), PptInches(5.6), PptInches(0.35), "Next (targeted)", size=16, bold=True, color=GOLD)
    _add_bullets(
        s,
        PptInches(7.0),
        PptInches(1.8),
        PptInches(5.6),
        PptInches(3.7),
        [
            "Richer foresight: magnitude / spread features",
            "Function approximation if state grows further",
            "Keep greedy as safety baseline until RL beats it on held-out days",
        ],
        size=14,
    )
    _footer(s, 8)
    _notes(s, SPEAKER_NOTES[8])

    # --- 9 Takeaways ---
    s = prs.slides.add_slide(blank)
    _bg(s)
    _title(s, "Takeaways")
    _add_bullets(
        s,
        PptInches(0.7),
        PptInches(1.4),
        PptInches(11.8),
        PptInches(3.5),
        [
            "CA2 made price actionable (5 actions) and then tested information, not only algorithms",
            "Under this wholesale-export setup, greedy remains the best evaluated deployable controller",
            "True four-hour three-bin direction did not beat greedy — hypothesis not supported here",
            "Digital Twin + Agent Play make the theory–deployed gap visible and challengeable",
        ],
        size=16,
    )
    _add_textbox(
        s,
        PptInches(0.7),
        PptInches(5.2),
        PptInches(11.8),
        PptInches(0.8),
        "15-minute recording · no Q&A  ·  End after this close",
        size=14,
        color=GOLD,
    )
    _footer(s, 9)
    _notes(s, SPEAKER_NOTES[9])

    # --- 10 Sources (unpresented) ---
    s = prs.slides.add_slide(blank)
    _bg(s)
    _title(s, "Sources & artefacts (backup — do not present)")
    _add_bullets(
        s,
        PptInches(0.6),
        PptInches(1.2),
        PptInches(12.0),
        PptInches(5.0),
        [
            "Ausgrid Solar Home Electricity Data (half-hourly PV / load)",
            "AEMO NSW1 regional reference price (RRP)",
            "Experiment outputs: results/logs/forecast_exp_*.csv · results/models/Q_q_learning_*_forecast_exp_*.npy",
            "Findings: deliverables/notebooklm/CA2_Forecast_Info_Experiment_Findings.md",
            "User Guide: deliverables/GreineQ_User_Guide.docx (also .md) — Twin / Play / Results / Price Monitor",
            "Local dashboard: http://localhost:8501  (prefer over production mirror greineq-agent.sudocod.com)",
            "Repo branch: ca2_agent",
        ],
        size=13,
    )
    _footer(s, 10)
    _notes(s, SPEAKER_NOTES[10])

    path = OUT / "GreineQ_CA2_Presentation.pptx"
    prs.save(path)
    return path


def _docx_styles(doc: Document):
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)


def build_speaker_notes_docx() -> Path:
    doc = Document()
    _docx_styles(doc)
    h = doc.add_heading("GréineQ CA2 — Speaker Notes", level=0)
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p = doc.add_paragraph()
    p.add_run("Synced with PowerPoint Presenter View notes (same wording). ").bold = True
    p.add_run(
        "Brand spelling: GréineQ. Format: 15-minute recorded presentation — no technical Q&A. "
        "Team roster and student numbers are on the title slide."
    )

    doc.add_heading("Team & slide allocation", level=1)
    for name, sid, role in TEAM:
        doc.add_paragraph(f"{name} — {sid} — {role}", style="List Bullet")
    doc.add_paragraph(
        "Spoken ownership: Emmanuel Addoh — slides 1 (title/team) and 9 (closing takeaways), non-technical. "
        "Nathan Rocha — slides 2–3 and 7. Nadeesha Jayasuriya — slides 4–6 and 8. "
        "Bahadir Demir — recorded demo backup (clicks if Nathan needs a hand)."
    )
    doc.add_paragraph(
        "Recorded run order: slides 1–8 (~8 min) → dashboard demo (~5–5.5 min) → slide 9 close (~1–1.5 min). "
        "Total 15 minutes. Do not leave time for Q&A. Skip sources slide in the recording."
    )
    doc.add_paragraph(
        "Demo on recording: Nathan Rocha = driver; Nadeesha Jayasuriya = narrator / clock; "
        "Bahadir Demir = backup. Emmanuel Addoh speaks only open and close — no demo mouse."
    )

    titles = {
        1: "Title",
        2: "Problem & CA2 question",
        3: "MDP — agent, environment, learning",
        4: "Experiment design",
        5: "Aggregate results",
        6: "Theory vs deployed",
        7: "Working deployment & ethics",
        8: "Limitations & next steps",
        9: "Takeaways",
        10: "Sources (unpresented)",
    }
    for i in range(1, 11):
        doc.add_heading(f"Slide {i} — {titles[i]}", level=1)
        doc.add_paragraph(SPEAKER_NOTES[i])

    doc.add_heading("Key phrases (do say / don’t say)", level=1)
    doc.add_paragraph("Say: three-bin price-direction feature — not “bit”.", style="List Bullet")
    doc.add_paragraph("Say: Privileged Q — true four-hour direction for headline AUD.", style="List Bullet")
    doc.add_paragraph("Say: realistic forecast mode exists in deployment but is not the headline source.", style="List Bullet")
    doc.add_paragraph("Say: hypothesis was not supported under this experimental setup.", style="List Bullet")
    doc.add_paragraph("Say: tabular keeps values inspectable — not “exact forever”.", style="List Bullet")
    doc.add_paragraph("Say: Agent Play is an oversight demo — realistic forecast for the human.", style="List Bullet")
    doc.add_paragraph("Say: Price Monitor is live wholesale + typical PV/load — not historical Twin.", style="List Bullet")
    doc.add_paragraph("Avoid mixing wholesale-export AUD with older fixed-FiT CA2 runs.", style="List Bullet")

    path = OUT / "GreineQ_CA2_Speaker_Notes.docx"
    doc.save(path)
    return path


def build_demo_plan_docx() -> Path:
    doc = Document()
    _docx_styles(doc)
    doc.add_heading("GréineQ CA2 — 15-minute recorded run", level=0)
    doc.add_paragraph(
        "Format: one continuous 15-minute recording. No live panel. No technical Q&A. "
        "Operator detail: deliverables/GreineQ_User_Guide.docx."
    )
    doc.add_paragraph(
        "Order: slides 1–8 (~8 min) → dashboard demo (~5–5.5 min) → slide 9 close (~1–1.5 min). "
        "Skip slide 10 (sources). Cut Agent Play / Price Monitor first if over time."
    )

    doc.add_heading("Roles (named)", level=1)
    doc.add_paragraph(
        "Opening & closing (slides 1 and 9): Emmanuel Addoh (10592825) — non-technical; no demo mouse.",
        style="List Bullet",
    )
    doc.add_paragraph("Driver: Nathan Rocha (20082900) — clicks only; no improvisation.", style="List Bullet")
    doc.add_paragraph("Narrator / clock: Nadeesha Jayasuriya (20093736) — speaks over demo.", style="List Bullet")
    doc.add_paragraph("Backup clicks: Bahadir Demir (20098301) — if Nathan needs a hand mid-recording.", style="List Bullet")

    doc.add_heading("Frozen demo configuration", level=1)
    doc.add_paragraph("URL: http://localhost:8501 (local). Do not rely on production for the recording.", style="List Bullet")
    doc.add_paragraph(
        "Top nav: Digital Twin · Price Monitor · Agent Play · Results · Overview",
        style="List Bullet",
    )
    doc.add_paragraph("Day split: Test days (held out).", style="List Bullet")
    doc.add_paragraph("Exact test day: 2012-07-14.", style="List Bullet")
    doc.add_paragraph(
        "Controllers: Greedy (5-action), Current Q, Privileged Q — true 4h signal.",
        style="List Bullet",
    )
    doc.add_paragraph(
        "Exact demo models (forecast_exp, seed 42): "
        "Q_q_learning_20260807_180535_forecast_exp_current_seed42.npy · "
        "Q_q_learning_20260807_180659_forecast_exp_privileged_seed42.npy "
        "(results/models/). Do not retrain mid-recording.",
        style="List Bullet",
    )
    doc.add_paragraph(
        "Browser: full screen, zoom 100%; after Twin loads, collapse sidebar for a clean capture.",
        style="List Bullet",
    )

    doc.add_heading("Pre-flight (before record)", level=1)
    for item in [
        "python scripts/system_test.py",
        "Start dashboard: .\\run_dashboard.ps1 or streamlit run dashboard/app.py",
        "Verify forecast_exp current + privileged models — screenshots ready as fallback",
        "Mute notifications; close chat apps; test mic levels for all speakers",
        "Open PPTX on slides; keep localhost:8501 ready on a second window/desktop",
        "Do a 60-second dry run of Twin Run comparison so the first open is warm",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_heading("Full 15-minute timing", level=1)
    rows = [
        ("0:00–0:45", "Title & team intro", "Emmanuel · Slide 1"),
        ("0:45–2:00", "Problem & CA2 question", "Nathan · Slide 2"),
        ("2:00–3:15", "MDP — agent, env, learning", "Nathan · Slide 3"),
        ("3:15–4:30", "Experiment design", "Nadeesha · Slide 4"),
        ("4:30–5:45", "Aggregate results", "Nadeesha · Slide 5"),
        ("5:45–6:45", "Theory vs deployed", "Nadeesha · Slide 6"),
        ("6:45–7:45", "Working deployment & ethics", "Nathan · Slide 7"),
        ("7:45–8:30", "Limitations & next steps → switch to app", "Nadeesha · Slide 8"),
        ("8:30–11:30", "Digital Twin fair comparison", "Nathan / Nadeesha · Twin"),
        ("11:30–12:45", "Experiment Results headline", "Nadeesha · Results"),
        ("12:45–13:45", "Agent Play (1–2 clicks) — cut if late", "Nathan / Nadeesha · Play"),
        ("13:45–15:00", "Closing takeaways — stop recording", "Emmanuel · Slide 9"),
    ]
    table = doc.add_table(rows=1 + len(rows), cols=3)
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Time", "Segment", "Owner / view"
    for i, (a, b, c) in enumerate(rows, 1):
        table.rows[i].cells[0].text = a
        table.rows[i].cells[1].text = b
        table.rows[i].cells[2].text = c

    doc.add_heading("Demo script (8:30–13:45)", level=1)

    doc.add_heading("Digital Twin (8:30–11:30)", level=2)
    doc.add_paragraph(
        "Open Digital Twin. Day split = Test; day = 2012-07-14. "
        "Ensure Greedy + Current Q + Privileged Q — true 4h signal. "
        "Run comparison if needed. Point to winner strip, KPIs, table, one chart, one inspector step. "
        "Narrator: same day, same tariff; greedy usually wins; true four-hour direction alone does not close the gap. "
        "Skip Price Monitor unless you are ahead of time."
    )

    doc.add_heading("Experiment Results (11:30–12:45)", level=2)
    doc.add_paragraph(
        "Headline: No-battery 160.75 · Perfect foresight 74.92 · Greedy 90.39 · Current Q ~124 · Privileged ~140. "
        "Say the hypothesis was not supported under this experimental setup."
    )

    doc.add_heading("Agent Play (12:45–13:45) — first cut if over time", level=2)
    doc.add_paragraph(
        "Setup → Current Q opponent → Start. Oversight framing: human sees realistic forecast. "
        "One or two actions only. Do not play all 48 steps."
    )

    doc.add_heading("Closing (13:45–15:00)", level=2)
    doc.add_paragraph(
        "Return to slide 9. Emmanuel delivers the one-line takeaway and stops. No Q&A invitation."
    )

    doc.add_heading("If running long — cut order", level=1)
    for item in [
        "Drop Price Monitor entirely",
        "Drop Agent Play",
        "Shorten Twin to winner strip + one table glance only",
        "Keep Results numbers + Emmanuel close",
    ]:
        doc.add_paragraph(item, style="List Number")

    doc.add_heading("Failure modes (during recording)", level=1)
    for a, b in [
        ("App crash / duplicate key", "Hard refresh or screenshots; keep talking"),
        ("Missing models", "Screenshots only — never retrain mid-recording"),
        ("Twin blank / stale", "Click Run comparison once; or screenshots"),
        ("Wrong tariff narrative", "These AUD are wholesale-export experiment totals"),
    ]:
        doc.add_paragraph(f"{a}: {b}", style="List Bullet")

    doc.add_heading("Happy-path checklist", level=1)
    for item in [
        "Slides 1–8 on time (~8:30)",
        "Twin 2012-07-14 · three controllers · winner visible",
        "Results · 90.39 vs ~124 vs ~140 · hypothesis not supported",
        "Play only if ahead · one action · oversight line",
        "Slide 9 · Emmanuel close · stop recording at 15:00",
    ]:
        doc.add_paragraph(item, style="List Number")

    path = OUT / "GreineQ_CA2_Live_Demo_Plan.docx"
    doc.save(path)
    return path


def update_markdown_mirrors():
    slides_md = ROOT / "deliverables" / "notebooklm" / "CA2_Presentation_Slides.md"
    demo_md = ROOT / "deliverables" / "notebooklm" / "CA2_Live_Demo_Plan.md"
    slides_md.write_text(
        "# GréineQ CA2 — Presentation (source of truth in PowerPoint)\n\n"
        "Canonical files:\n\n"
        "- `deliverables/presentation/GreineQ_CA2_Presentation.pptx`\n"
        "- `deliverables/presentation/GreineQ_CA2_Speaker_Notes.docx`\n"
        "- `deliverables/presentation/GreineQ_CA2_Live_Demo_Plan.docx`\n"
        "- Operator guide: `deliverables/GreineQ_User_Guide.docx`\n\n"
        "**Format:** 15-minute recorded presentation — **no technical Q&A**.\n\n"
        "Order: slides 1–8 → dashboard demo → Emmanuel slide 9 close. Skip sources in the recording.\n"
        "Team: Emmanuel open/close · Nathan technical + demo drive · Nadeesha experiment + narrate · "
        "Bahadir demo backup.\n",
        encoding="utf-8",
    )
    demo_md.write_text(
        "# GréineQ CA2 — 15-minute recorded run\n\n"
        "See Word document: `deliverables/presentation/GreineQ_CA2_Live_Demo_Plan.docx`.\n\n"
        "**Format:** 15-min recording · no Q&A · **Day:** 2012-07-14 · "
        "**Driver:** Nathan · **Narrator:** Nadeesha · **Backup:** Bahadir · "
        "**Open/close:** Emmanuel · **URL:** http://localhost:8501\n",
        encoding="utf-8",
    )


def main():
    pptx = build_pptx()
    notes = build_speaker_notes_docx()
    demo = build_demo_plan_docx()
    update_markdown_mirrors()
    print("Wrote", pptx)
    print("Wrote", notes)
    print("Wrote", demo)


if __name__ == "__main__":
    main()

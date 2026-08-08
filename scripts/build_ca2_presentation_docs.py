"""Build CA2 PowerPoint + demo plan + speaker notes Word docs."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt as DocPt
from docx.shared import RGBColor as DocRGB
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "deliverables" / "presentation"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = RGBColor(0x07, 0x0D, 0x1A)
AMBER = RGBColor(0xF5, 0x9E, 0x1A)
AMBER2 = RGBColor(0xFB, 0xBF, 0x24)
WHITE = RGBColor(0xF8, 0xFA, 0xFC)
MUTED = RGBColor(0x94, 0xA3, 0xB8)
LIGHT = RGBColor(0xCB, 0xD5, 0xE1)


def set_run_font(run, size=18, bold=False, color=WHITE, name="Calibri"):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = name


def add_bg(slide, prs, color=NAVY):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    sp_tree = slide.shapes._spTree
    sp = shape._element
    sp_tree.remove(sp)
    sp_tree.insert(2, sp)


def add_accent_bar(slide, prs):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.08))
    bar.fill.solid()
    bar.fill.fore_color.rgb = AMBER
    bar.line.fill.background()


def add_title(slide, text, top=0.35, size=32):
    box = slide.shapes.add_textbox(Inches(0.55), Inches(top), Inches(12.2), Inches(0.7))
    tf = box.text_frame
    tf.word_wrap = True
    run = tf.paragraphs[0].add_run()
    run.text = text
    set_run_font(run, size=size, bold=True, color=WHITE)


def add_subtitle(slide, text, top=1.0, size=16, color=MUTED):
    box = slide.shapes.add_textbox(Inches(0.55), Inches(top), Inches(12.2), Inches(0.45))
    tf = box.text_frame
    tf.word_wrap = True
    run = tf.paragraphs[0].add_run()
    run.text = text
    set_run_font(run, size=size, color=color)


def add_bullets(slide, items, left=0.55, top=1.6, width=12.2, height=5.0, size=18):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level = item.get("level", 0)
        p.space_after = Pt(8)
        run = p.add_run()
        run.text = item["text"]
        set_run_font(
            run,
            size=size - 2 * item.get("level", 0),
            bold=item.get("bold", False),
            color=item.get("color", LIGHT),
        )


def add_notes(slide, text):
    notes = slide.notes_slide
    tf = notes.notes_text_frame
    tf.clear()
    run = tf.paragraphs[0].add_run()
    run.text = text


def add_footer(slide, page, total=9):
    box = slide.shapes.add_textbox(Inches(0.55), Inches(7.05), Inches(10), Inches(0.3))
    run = box.text_frame.paragraphs[0].add_run()
    run.text = f"GreineQ  ·  B9AI105 CA2  ·  {page}/{total}"
    set_run_font(run, size=11, color=MUTED)


def add_table(slide, rows, left=0.55, top=2.0, width=12.2, col_widths=None):
    n_rows = len(rows)
    n_cols = len(rows[0])
    table_shape = slide.shapes.add_table(
        n_rows, n_cols, Inches(left), Inches(top), Inches(width), Inches(0.42 * n_rows)
    )
    table = table_shape.table
    if col_widths:
        for i, w in enumerate(col_widths):
            table.columns[i].width = Inches(w)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = table.cell(r, c)
            cell.text = str(val)
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    set_run_font(run, size=13, bold=(r == 0), color=WHITE if r == 0 else LIGHT)
            fill = cell.fill
            fill.solid()
            if r == 0:
                fill.fore_color.rgb = RGBColor(0x1E, 0x29, 0x3B)
            elif r % 2:
                fill.fore_color.rgb = RGBColor(0x12, 0x1A, 0x2B)
            else:
                fill.fore_color.rgb = RGBColor(0x0F, 0x17, 0x29)


def build_pptx() -> Path:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    # 1 Title
    s = prs.slides.add_slide(blank)
    add_bg(s, prs)
    add_accent_bar(s, prs)
    box = s.shapes.add_textbox(Inches(0.7), Inches(2.0), Inches(11.8), Inches(1.4))
    tf = box.text_frame
    run = tf.paragraphs[0].add_run()
    run.text = "GreineQ CA2"
    set_run_font(run, size=48, bold=True, color=AMBER2)
    p2 = tf.add_paragraph()
    run = p2.add_run()
    run.text = "Tabular RL for solar battery dispatch — when foresight meets the grid"
    set_run_font(run, size=22, color=LIGHT)
    box = s.shapes.add_textbox(Inches(0.7), Inches(4.0), Inches(11.8), Inches(1.5))
    tf = box.text_frame
    lines = [
        "B9AI105 Reinforcement Learning",
        "Forecast-information experiment  ·  Digital Twin  ·  Play vs Agent",
        "CA1 solar-only → CA2 5-action arbitrage → foresight test",
    ]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        run = p.add_run()
        run.text = line
        set_run_font(run, size=16, color=MUTED)
    add_notes(
        s,
        "CA1 asked whether RL could beat simple solar self-consumption. "
        "CA2 asks whether forward-looking price information helps a tabular agent "
        "time grid arbitrage — and we tested that with a deployed dashboard.",
    )
    add_footer(s, 1)

    # 2 Problem
    s = prs.slides.add_slide(blank)
    add_bg(s, prs)
    add_accent_bar(s, prs)
    add_title(s, "Problem & CA2 question")
    add_subtitle(s, "Household decision every 30 minutes")
    add_table(
        s,
        [
            ["Need", "Reality"],
            ["Use solar, charge / discharge battery", "Easy with rules"],
            ["Buy low / sell or use later (arbitrage)", "Needs future price timing"],
        ],
        top=1.6,
        col_widths=[6.0, 6.2],
    )
    add_bullets(
        s,
        [
            {"text": "CA2 research question", "bold": True, "color": AMBER2},
            {
                "text": "Does a short price-direction foresight signal help tabular RL beat a "
                "strong greedy baseline under a fair, arbitrage-capable MDP?"
            },
            {
                "text": "Why it matters: more actions without matching information can raise the household bill.",
                "color": MUTED,
            },
        ],
        top=3.6,
        size=17,
    )
    add_notes(
        s,
        "Frame the problem: solar self-use is easy; profitable timing needs the future. "
        "Our experiment isolates whether a coarse foresight bit is enough.",
    )
    add_footer(s, 2)

    # 3 MDP
    s = prs.slides.add_slide(blank)
    add_bg(s, prs)
    add_accent_bar(s, prs)
    add_title(s, "MDP — theory")
    add_subtitle(s, "One day = 48 half-hour steps  ·  Ausgrid Customer 1 + AEMO NSW1")
    add_table(
        s,
        [
            ["Element", "Design"],
            ["State", "SOC × PV × load × price × time (+ foresight bin if privileged)"],
            ["Actions (5)", "Hold · Solar charge · Discharge · Grid-charge · Export"],
            ["Reward", "Net electricity cost (+ battery wear / terminal SOC)"],
            ["State sizes", "Current Q: 540   ·   Privileged Q: 1620 (×3 foresight bins)"],
        ],
        top=1.55,
        col_widths=[2.8, 9.4],
    )
    add_bullets(
        s,
        [
            {"text": "Tariff honesty (experimental)", "bold": True, "color": AMBER2},
            {
                "text": "Retail import = wholesale + margin; export priced at wholesale "
                "(not a household FiT) — disclosed in UI & README."
            },
        ],
        top=4.5,
        size=16,
    )
    add_notes(
        s,
        "Five actions make price actionable. Privileged agents get a 4-hour price-direction bit. "
        "State grows from 540 to 1620. Export uses wholesale — experimental, not FiT.",
    )
    add_footer(s, 3)

    # 4 Experiment
    s = prs.slides.add_slide(blank)
    add_bg(s, prs)
    add_accent_bar(s, prs)
    add_title(s, "Experiment design — fair comparison")
    add_subtitle(s, "Same physics, same tariff, same held-out test days  ·  Q-Learning 10k episodes × 5 seeds")
    add_table(
        s,
        [
            ["Controller", "Information"],
            ["Greedy (5-action)", "Current price + heuristics"],
            ["Current Q", "Current state only"],
            ["Privileged Q (4h)", "Current + direction of max price over next ~4h"],
            ["Oracle", "Perfect foresight (bound only)"],
        ],
        top=1.55,
        col_widths=[3.5, 8.7],
    )
    add_bullets(
        s,
        [
            {
                "text": "Privileged signal: max(price next 8 steps) − current → "
                "FALL_OR_FLAT / MODERATE_RISE / STRONG_RISE"
            },
            {
                "text": "Train-only tertiles · forecast mode = climatology + persistence (deployable-style)",
                "color": MUTED,
            },
        ],
        top=4.6,
        size=16,
    )
    add_notes(
        s,
        "Fairness is the point: retrain and evaluate everything under wholesale export. "
        "Do not mix with older fixed-FiT numbers. Forecast mode is deployable-style foresight.",
    )
    add_footer(s, 4)

    # 5 Results
    s = prs.slides.add_slide(blank)
    add_bg(s, prs)
    add_accent_bar(s, prs)
    add_title(s, "Headline results — 53-day test")
    add_subtitle(s, "Wholesale-export setting  ·  memorise these numbers")
    add_table(
        s,
        [
            ["Controller", "Net cost (AUD)", "Notes"],
            ["No battery", "160.75", "Upper bound"],
            ["Perfect foresight (bound)", "74.92", "Information ceiling"],
            ["Greedy (5-action)", "90.39", "Best deployable"],
            ["Current Q (mean ± std)", "124.23 ± 11.65", "Uses arbitrage"],
            ["Privileged Q (4h)", "139.68 ± 5.55", "Uses more — costs more"],
        ],
        top=1.5,
        col_widths=[4.2, 3.5, 4.5],
    )
    add_bullets(
        s,
        [
            {
                "text": "Win rate: Greedy 96.2% of days · Current Q 3.8% · Privileged 0%",
                "bold": True,
                "color": AMBER2,
            },
            {"text": "Finding: future-price direction alone was insufficient."},
        ],
        top=5.3,
        size=16,
    )
    add_notes(
        s,
        "Greedy 90.39 still best. Privileged direction alone did not help — used arbitrage more "
        "and still cost more. Win rate 96% greedy. Do not mix with fixed-FiT CA2 numbers.",
    )
    add_footer(s, 5)

    # 6 Theory vs deployed
    s = prs.slides.add_slide(blank)
    add_bg(s, prs)
    add_accent_bar(s, prs)
    add_title(s, "Theory vs deployed")
    add_table(
        s,
        [
            ["Theory", "Deployed reality"],
            ["Oracle shows large headroom vs no battery", "Policies that can arbitrage still lose to greedy"],
            ["Foresight should help timing", "Coarse rise/flat/fall ≠ how much or when vs load"],
            ["Bigger action space = more capability", "Without matching info → worse household bill"],
        ],
        top=1.5,
        col_widths=[5.8, 6.4],
    )
    add_bullets(
        s,
        [
            {"text": "Why direction fails here", "bold": True, "color": AMBER2},
            {"text": "Import pays wholesale + 0.22; export pays wholesale → round-trip sell is hard."},
            {"text": "Profitable foresight is mostly charge cheap → discharge to load later — not export high."},
            {"text": "Privileged table is 3× larger → harder to learn with the same episode budget."},
        ],
        top=4.2,
        size=15,
    )
    add_notes(
        s,
        "This is the required CA2 story: theory promises headroom; deployable policies don't capture it; "
        "coarse foresight didn't close the gap. A negative explained result is the contribution.",
    )
    add_footer(s, 6)

    # 7 Deployment
    s = prs.slides.add_slide(blank)
    add_bg(s, prs)
    add_accent_bar(s, prs)
    add_title(s, "Working deployment")
    add_table(
        s,
        [
            ["Surface", "Shows"],
            ["Digital Twin", "Same day · Greedy vs Current Q vs Privileged Q · KPIs · energy flow"],
            ["Play vs Agent", "Human vs RL on identical twins · 4h forecast for the human"],
            ["Experiment Results", "Curated headline table"],
            ["Live AEMO panel", "Real NSW1 wholesale (PV/load = disclosed medians)"],
        ],
        top=1.5,
        col_widths=[3.5, 8.7],
    )
    add_bullets(
        s,
        [
            {
                "text": "Ethics: richer autonomy without foresight quality → financial harm risk.",
                "bold": True,
                "color": AMBER2,
            },
            {"text": "Response: staged rollout / human-in-the-loop — Play mode demonstrates oversight."},
        ],
        top=4.8,
        size=16,
    )
    add_notes(
        s,
        "Dashboard is the working deployment mark. Live AEMO is real price but partial metering — disclosed. "
        "Play vs Agent is the oversight story.",
    )
    add_footer(s, 7)

    # 8 Limitations
    s = prs.slides.add_slide(blank)
    add_bg(s, prs)
    add_accent_bar(s, prs)
    add_title(s, "Limitations & next steps")
    add_bullets(
        s,
        [
            {"text": "Limitations (precise)", "bold": True, "color": AMBER2},
            {"text": "Direction bins, not magnitude or load-aware value of charging"},
            {"text": "Wholesale-export tariff is experimental (not retail FiT)"},
            {"text": "Tabular Q + 1620 states may be under-trained at 10k episodes"},
            {"text": "Live feed is price-real, meter-partial (disclosed)"},
            {"text": "Next (targeted)", "bold": True, "color": AMBER2},
            {"text": "Richer foresight: magnitude / spread features — not only tertiles"},
            {"text": "Or function approximation if the state grows further"},
            {"text": "Keep greedy as a safety baseline until RL beats it on held-out days"},
        ],
        top=1.5,
        size=17,
    )
    add_notes(
        s,
        "Be precise, not generic. Next step targets the actual bottleneck we found — magnitude foresight — "
        "not another algorithm tweak.",
    )
    add_footer(s, 8)

    # 9 Close
    s = prs.slides.add_slide(blank)
    add_bg(s, prs)
    add_accent_bar(s, prs)
    add_title(s, "Takeaways", top=1.8, size=36)
    add_bullets(
        s,
        [
            {"text": "CA2 made price actionable (5 actions) and then tested information, not just algorithms."},
            {"text": "Under a fair wholesale-export MDP, greedy still wins; direction foresight did not close the gap."},
            {"text": "Digital Twin + Play vs Agent make the theory–deployed gap visible and interactive."},
            {
                "text": "Demo next → Digital Twin comparison · optional Play vs Agent · live price panel",
                "bold": True,
                "color": AMBER2,
            },
        ],
        top=2.8,
        size=18,
    )
    add_notes(
        s,
        "Close in one line: we made arbitrage actionable, tested whether 4h price direction helps tabular RL, "
        "found it does not beat greedy, and shipped a dashboard that shows that result. Invite questions.",
    )
    add_footer(s, 9)

    path = OUT / "GreineQ_CA2_Presentation.pptx"
    prs.save(path)
    return path


def set_doc_style(doc: Document) -> None:
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = DocPt(11)
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")


def add_heading_colored(doc: Document, text: str, level: int = 1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = DocRGB(0x0C, 0x14, 0x24)
    return h


def add_bullet(doc: Document, text: str, bold_prefix: str | None = None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_prefix:
        r = p.add_run(bold_prefix)
        r.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    return p


def build_demo_docx() -> Path:
    demo = Document()
    set_doc_style(demo)
    title = demo.add_heading("GreineQ CA2 — Live Demo Plan", 0)
    for run in title.runs:
        run.font.color.rgb = DocRGB(0xB4, 0x53, 0x09)

    p = demo.add_paragraph()
    p.add_run("Module: ").bold = True
    p.add_run("B9AI105 Reinforcement Learning\n")
    p.add_run("Companion slides: ").bold = True
    p.add_run("GreineQ_CA2_Presentation.pptx\n")
    p.add_run("Primary URL: ").bold = True
    p.add_run("http://localhost:8501  (local ca2_agent)\n")
    p.add_run("Backup URL: ").bold = True
    p.add_run("https://greineq-agent.sudocod.com/ (may lag branch features)")

    add_heading_colored(demo, "1. Pre-flight (T-15 min)", 1)
    add_heading_colored(demo, "Machine checklist", 2)
    for line in [
        'cd "d:\\DBS - Sem 2\\RL\\rl-battery-dispatch"',
        "python scripts/system_test.py",
        ".\\run_dashboard.ps1",
        "# or: python -m streamlit run dashboard/app.py --server.port 8501",
    ]:
        para = demo.add_paragraph(line)
        for run in para.runs:
            run.font.name = "Consolas"

    for item in [
        "Dashboard opens; landing shows logo + Digital Twin / Play vs Agent under the tagline",
        "Models present under results/models/ (at least current + privileged Q)",
        "Browser zoom 110-125%; sidebar expanded; readable on projector",
        "Close Slack/email; mute notifications",
        "Write down one known-good test day from the Twin dropdown",
    ]:
        add_bullet(demo, item)

    add_heading_colored(demo, "Freeze UI settings (Digital Twin)", 2)
    table = demo.add_table(rows=4, cols=2)
    table.style = "Table Grid"
    data = [
        ("Control", "Value"),
        ("Day split", "Test days (held out)"),
        ("Controllers", "Greedy (5-action) · Current Q · Privileged Q (4h)"),
        ("Advanced", "Leave collapsed unless asked"),
    ]
    for i, (a, b) in enumerate(data):
        table.rows[i].cells[0].text = a
        table.rows[i].cells[1].text = b
        if i == 0:
            for cell in table.rows[i].cells:
                for para in cell.paragraphs:
                    for r in para.runs:
                        r.bold = True

    add_heading_colored(demo, "Roles (if team demo)", 2)
    for a, b in [
        ("Driver", " — Clicks only; does not improvise"),
        ("Narrator", " — Speaks over demo; watches clock"),
        ("Backup", " — Screenshots of Twin KPIs + findings table on USB/phone"),
    ]:
        add_bullet(demo, b, bold_prefix=a)

    add_heading_colored(demo, "2. Timing overview (about 8-10 min)", 1)
    t = demo.add_table(rows=6, cols=3)
    t.style = "Table Grid"
    rows = [
        ("Min", "Segment", "View"),
        ("0:00-0:45", "Landing & story hook", "Home"),
        ("0:45-4:00", "Digital Twin — fair comparison", "Twin"),
        ("4:00-6:30", "Theory vs deployed + Results", "Results / Twin"),
        ("6:30-8:30", "Play vs Agent (oversight) or live AEMO", "Play / Twin"),
        ("8:30-9:00", "Close + invite Q&A", "—"),
    ]
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            t.rows[i].cells[j].text = val
            if i == 0:
                for para in t.rows[i].cells[j].paragraphs:
                    for r in para.runs:
                        r.bold = True
    demo.add_paragraph("If the slot is shorter: cut Play and keep Twin + Results headline.")

    add_heading_colored(demo, "3. Script — Landing (0:00-0:45)", 1)
    add_bullet(demo, "Open landing (Overview if already inside).", bold_prefix="Click: ")
    add_bullet(demo, "Logo → tagline → compact CTAs → day replay animation.", bold_prefix="Show: ")
    p = demo.add_paragraph()
    r = p.add_run("Say: ")
    r.bold = True
    p.add_run(
        '"This is GreineQ. CA2 is not only another training run — it is a deployed digital twin. '
        'Two entries: compare controllers, or play against the agent."'
    )
    add_bullet(demo, "Do not scroll into long explain text unless asked.")

    add_heading_colored(demo, "4. Script — Digital Twin (0:45-4:00)", 1)
    add_bullet(demo, "Digital Twin (landing or top nav).", bold_prefix="Click: ")
    add_bullet(demo, "Loader → KPIs + winner line + table.", bold_prefix="Wait for: ")
    demo.add_paragraph("Point to, in order:")
    for item in [
        "Winner line — who won today and by how much vs no battery",
        "Three KPIs — winner net cost / savings / final SOC",
        "Controller comparison table — Greedy vs Current Q vs Privileged Q",
        "Energy flow chart — SOC and actions over the day",
        "Sidebar Replay — optional two-second glance",
    ]:
        add_bullet(demo, item)
    p = demo.add_paragraph()
    r = p.add_run("Say: ")
    r.bold = True
    p.add_run(
        '"Same customer day, same tariff, same physics. Greedy, Current Q, and Privileged Q with a '
        "4-hour price-direction signal. Winner is lowest net electricity cost. On most held-out days "
        'greedy wins — privileged foresight direction alone does not close the gap."'
    )
    p = demo.add_paragraph()
    r = p.add_run("If asked about cherry-picking: ")
    r.bold = True
    p.add_run(
        '"The 53-day aggregate is on Experiment Results: greedy wins about 96% of days. '
        'This screen is one transparent day you can change in the sidebar."'
    )

    add_heading_colored(demo, "5. Script — Experiment Results (4:00-6:00)", 1)
    add_bullet(demo, "Experiment Results", bold_prefix="Click: ")
    demo.add_paragraph("Memorise and point at:")
    for a, b in [
        ("No battery", " — 160.75 AUD"),
        ("Oracle bound", " — 74.92 AUD"),
        ("Greedy", " — 90.39 AUD"),
        ("Current Q", " — ~124 AUD"),
        ("Privileged Q", " — ~140 AUD"),
    ]:
        add_bullet(demo, b, bold_prefix=a)
    p = demo.add_paragraph()
    r = p.add_run("Theory vs deployed sentence (for marks): ")
    r.bold = True
    p.add_run(
        '"Perfect foresight sets a lower bound of about 75 AUD. Deployable policies sit well above that. '
        "Giving the agent a coarse 'will price rise?' bit did not turn theory into a better deployed bill.\""
    )

    add_heading_colored(demo, "6. Script — Play vs Agent (6:00-8:00)", 1)
    add_bullet(
        demo,
        "Play vs Agent — title then Choose your action buttons; day/opponent in sidebar.",
        bold_prefix="Click: ",
    )
    for item in [
        "Point at action row: Hold / Solar charge / Discharge / Grid-charge / Export",
        "Click Hold or Discharge once or twice — show step/SOC/price update",
        "Expand Your 4-hour price forecast — human sees forecast; agent uses trained policy",
        "Do not play all 48 steps live",
    ]:
        add_bullet(demo, item)
    p = demo.add_paragraph()
    r = p.add_run("Say: ")
    r.bold = True
    p.add_run(
        '"Play vs Agent is human-in-the-loop on identical twins. Do not give a richer action space '
        'full autonomy until the agent beats a safe baseline on held-out days."'
    )

    add_heading_colored(demo, "7. Live AEMO panel (optional 60-90 s)", 1)
    add_bullet(demo, "Digital Twin → expander Live AEMO price (demo)", bold_prefix="Where: ")
    p = demo.add_paragraph()
    r = p.add_run("Say: ")
    r.bold = True
    p.add_run(
        '"Wholesale price here is live NSW1. Solar and load are historical medians for this hour — '
        'disclosed, not hidden."'
    )

    add_heading_colored(demo, "8. Close (8:30-9:00)", 1)
    p = demo.add_paragraph()
    r = p.add_run("Say: ")
    r.bold = True
    p.add_run(
        '"CA2 contribution in one line: we made arbitrage actionable, tested whether 4h price direction '
        "helps tabular RL, found it does not beat greedy under this tariff, and shipped a dashboard that "
        'lets you see — and challenge — that result."'
    )

    add_heading_colored(demo, "9. Failure modes & recovery", 1)
    ft = demo.add_table(rows=7, cols=2)
    ft.style = "Table Grid"
    fails = [
        ("Failure", "Recovery"),
        ("Import / duplicate-key error", "Hard refresh; restart streamlit run dashboard/app.py"),
        (
            "No models",
            "python -m src.forecast_info_experiment --quick --foresight forecast --agents q_learning --tag demo",
        ),
        ("Twin stuck loading", "Click Run comparison; or change day and run again"),
        ("Play broken", "Skip to Results table + Twin screenshots"),
        ("Production site outdated", "Prefer localhost; production may lag ca2_agent"),
        ("Wrong tariff narrative", "These AUD are wholesale-export experiment — not fixed-FiT CA2 runs"),
    ]
    for i, (a, b) in enumerate(fails):
        ft.rows[i].cells[0].text = a
        ft.rows[i].cells[1].text = b
        if i == 0:
            for cell in ft.rows[i].cells:
                for para in cell.paragraphs:
                    for r in para.runs:
                        r.bold = True

    add_heading_colored(demo, "10. Demo day happy-path checklist", 1)
    for item in [
        "Landing → Digital Twin",
        "Greedy + Current Q + Privileged Q selected",
        "Results load; winner visible",
        "Experiment Results → point at 90.39 vs ~124 vs ~140",
        "Play vs Agent → show buttons under title + one action",
        "Close with theory-vs-deployed sentence",
    ]:
        add_bullet(demo, item)
    demo.add_paragraph("Stop talking when the clock hits the end of the demo block — leave air for Q&A.")

    path = OUT / "GreineQ_CA2_Live_Demo_Plan.docx"
    demo.save(path)
    return path


def build_speaker_notes_docx() -> Path:
    notes = Document()
    set_doc_style(notes)
    title = notes.add_heading("GreineQ CA2 — Speaker Notes", 0)
    for run in title.runs:
        run.font.color.rgb = DocRGB(0xB4, 0x53, 0x09)

    p = notes.add_paragraph()
    p.add_run("Use with: ").bold = True
    p.add_run("GreineQ_CA2_Presentation.pptx\n")
    p.add_run("Suggested talk length: ").bold = True
    p.add_run("5-7 minutes (then hand to live demo)\n")
    p.add_run("Tip: ").bold = True
    p.add_run("Read the bold Say blocks aloud; use tips only if asked.")

    slides = [
        (
            "Slide 1 — Title",
            "Timing: 20-30 s",
            "CA1 asked whether RL could beat simple solar self-consumption. CA2 asks whether "
            "forward-looking price information helps a tabular agent time grid arbitrage — and we "
            "tested that with a deployed dashboard.",
            [
                "Mention Digital Twin + Play vs Agent as the live system.",
                "Do not dive into numbers yet.",
            ],
        ),
        (
            "Slide 2 — Problem & CA2 question",
            "Timing: 40-50 s",
            "Households already know how to self-consume solar. Arbitrage — buy low, use or sell later — "
            "needs future price timing. Our CA2 question: does a short price-direction foresight signal "
            "help tabular RL beat a strong greedy baseline under a fair, arbitrage-capable MDP? This "
            "matters because more actions without matching information can raise the bill.",
            ["Emphasise the research question once, clearly.", "Link to deployment risk early."],
        ),
        (
            "Slide 3 — MDP",
            "Timing: 45-60 s",
            "One day is forty-eight half-hour steps. State is SOC, PV, load, price, and time-of-day; "
            "privileged agents also get a foresight bin. Five actions: hold, solar charge, discharge, "
            "grid-charge, and export. Reward is net electricity cost with battery wear and terminal SOC. "
            "Current Q has five hundred forty states; privileged has sixteen twenty. Export uses wholesale "
            "pricing — experimental, disclosed, not a household feed-in tariff.",
            [
                "If asked why wholesale: it makes export economically meaningful for the experiment.",
                "State sizes show the privileged agent has a harder learning problem.",
            ],
        ),
        (
            "Slide 4 — Experiment design",
            "Timing: 45-60 s",
            "Fair comparison: same physics, same tariff, same test days. Controllers are greedy five-action, "
            "current-info Q, privileged Q with four-hour price direction, and a perfect-foresight oracle as "
            "a bound only. The privileged signal is max price over the next eight steps minus current, binned "
            "into fall-or-flat, moderate rise, or strong rise using train-only tertiles. We train Q-Learning "
            "for ten thousand episodes across five seeds. Forecast mode uses climatology plus persistence — "
            "deployable-style foresight.",
            [
                "Stress fairness: do not mix with older fixed-FiT AUD totals.",
                "Oracle is a bound, not a deployable controller.",
            ],
        ),
        (
            "Slide 5 — Headline results",
            "Timing: 60-75 s",
            "On fifty-three held-out days: no battery one hundred sixty point seven five; oracle bound "
            "seventy-four point nine two; greedy ninety point three nine — best deployable; current Q about "
            "one twenty-four; privileged about one forty. Greedy wins ninety-six percent of days; privileged "
            "wins zero. One-line finding: future-price direction alone was insufficient — privileged Q used "
            "arbitrage more and still cost more.",
            [
                "Memorise: 160.75 / 74.92 / 90.39 / ~124 / ~140 / 96% win rate.",
                "Pause after the one-line finding.",
            ],
        ),
        (
            "Slide 6 — Theory vs deployed",
            "Timing: 50-60 s",
            "This is the required CA2 story. Theory: oracle shows headroom. Deployed: policies that can "
            "arbitrage still lose to greedy. Foresight should help, but a coarse rise-flat-fall bit does not "
            "encode how large the spread is, or when discharge to load matters. Import pays wholesale plus "
            "twenty-two cents; export pays wholesale — round-trip sell is hard. Profitable foresight is mostly "
            "charge cheap then discharge to load later. The privileged table is three times larger, so it is "
            "harder to learn with the same budget. A negative, explained result is stronger than an unexplained win.",
            [
                "Say 'theory versus deployed' explicitly for marks.",
                "Ethics hook: more capability without information raised the bill.",
            ],
        ),
        (
            "Slide 7 — Working deployment",
            "Timing: 40-50 s",
            "We ship a Digital Twin for same-day controller comparison, Play versus Agent for human-in-the-loop "
            "on identical twins, curated Experiment Results, and a live AEMO panel where wholesale price is real "
            "and PV/load medians are disclosed. Ethics: richer autonomy without foresight quality risks financial "
            "harm — staged rollout and human oversight, which Play mode demonstrates.",
            [
                "Hand off to the live demo after this slide if timing is tight.",
                "Disclosed partial metering is honesty, not a bug.",
            ],
        ),
        (
            "Slide 8 — Limitations & next",
            "Timing: 35-45 s",
            "Limitations are precise: direction bins not magnitude; experimental wholesale export; tabular Q at "
            "sixteen twenty states may be under-trained at ten thousand episodes; live feed is price-real and "
            "meter-partial. Next steps target the bottleneck: richer magnitude or spread foresight, or function "
            "approximation if the state grows — and keep greedy as a safety baseline until RL beats it on held-out days.",
            [
                "Avoid vague 'more data / more compute' answers.",
                "Next step must target the bottleneck we identified.",
            ],
        ),
        (
            "Slide 9 — Close",
            "Timing: 20-30 s",
            "Three takeaways: we made price actionable and tested information not just algorithms; under wholesale "
            "export greedy still wins and direction foresight did not close the gap; the dashboard makes that gap "
            "visible. Demo next.",
            [
                "Invite questions on MDP, foresight signal, or ethics.",
                "Do not introduce new numbers on the close slide.",
            ],
        ),
    ]

    for title_s, timing, say, tips in slides:
        add_heading_colored(notes, title_s, 1)
        p = notes.add_paragraph()
        r = p.add_run(timing)
        r.italic = True
        r.font.color.rgb = DocRGB(0x64, 0x74, 0x8B)
        p = notes.add_paragraph()
        r = p.add_run("Say:\n")
        r.bold = True
        p.add_run(say)
        p = notes.add_paragraph()
        r = p.add_run("Delivery tips:")
        r.bold = True
        for tip in tips:
            add_bullet(notes, tip)

    add_heading_colored(notes, "Numbers to memorise", 1)
    for line in [
        "No battery: 160.75 AUD",
        "Oracle bound: 74.92 AUD",
        "Greedy (5-action): 90.39 AUD (best deployable)",
        "Current Q: 124.23 ± 11.65 AUD",
        "Privileged Q (4h): 139.68 ± 5.55 AUD",
        "Win rate: Greedy 96.2% · Current Q 3.8% · Privileged 0%",
        "States: Current 540 · Privileged 1620",
        "Training: Q-Learning, 10,000 episodes, seeds 42-46",
    ]:
        add_bullet(notes, line)

    add_heading_colored(notes, "30-second cheat lines", 1)
    for a, b in [
        ("MDP", " — Five actions; privileged adds a 4h price-direction bit; 540 vs 1620 states."),
        ("Result", " — Greedy 90.4 AUD; Current Q ~124; Privileged ~140; greedy wins 96% of days."),
        ("Why", " — Direction does not encode how large the spread is, or discharge-to-load timing."),
        ("Ethics", " — More actions without better information raised the bill — do not deploy blindly."),
        ("Demo", " — Same day, three controllers, winner = lowest net cost."),
    ]:
        add_bullet(notes, b, bold_prefix=a)

    add_heading_colored(notes, "Planted Q&A (short answers)", 1)
    for q, a in [
        ("Did CA2 fail?", "No — ceiling/actions worked; foresight direction was the falsified hypothesis."),
        ("Why not Deep RL?", "Tabular is exact and interpretable at 540-1620; deep when state grows further."),
        ("Why wholesale export?", "Makes export meaningful for the experiment; disclosed as experimental."),
        ("Why greedy wins?", "Strong heuristic + coarse foresight + larger privileged table."),
        ("Ethics?", "More capability without information raised cost → staged deployment."),
    ]:
        p = notes.add_paragraph()
        r = p.add_run(f"Q: {q}\n")
        r.bold = True
        p.add_run(f"A: {a}")

    path = OUT / "GreineQ_CA2_Speaker_Notes.docx"
    notes.save(path)
    return path


def main() -> None:
    pptx = build_pptx()
    demo = build_demo_docx()
    notes = build_speaker_notes_docx()
    print("Wrote:")
    print(" ", pptx)
    print(" ", demo)
    print(" ", notes)


if __name__ == "__main__":
    main()

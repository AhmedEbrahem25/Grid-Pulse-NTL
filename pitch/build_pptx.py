"""Generate Grid-Pulse-NTL.pptx — a 16:9 investor/judge deck that mirrors the
pitch page's identity (petrol-ink ground, signal-cyan accent, semantic status
colours, mono readouts). Run in a container that has python-pptx:

    pip install python-pptx && python build_pptx.py
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ---- palette (matches pitch/index.html) ----
INK   = RGBColor(0x0A, 0x0E, 0x0F)
INK2  = RGBColor(0x0E, 0x14, 0x18)
PANEL = RGBColor(0x10, 0x16, 0x1A)
LINE  = RGBColor(0x1E, 0x2A, 0x2F)
LINE2 = RGBColor(0x2A, 0x3A, 0x41)
FG    = RGBColor(0xE8, 0xEE, 0xF0)
MUTED = RGBColor(0x8A, 0x9B, 0xA1)
DIM   = RGBColor(0x5F, 0x71, 0x78)
SIGNAL= RGBColor(0x34, 0xC8, 0xE0)
SIGDIM= RGBColor(0x1C, 0x6A, 0x74)
THEFT = RGBColor(0xFF, 0x4D, 0x5E)
TECH  = RGBColor(0xF4, 0xA6, 0x3B)
OK    = RGBColor(0x3D, 0xDC, 0x84)

SANS = "Segoe UI"
SANS_B = "Segoe UI Semibold"
MONO = "Consolas"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = 13.333, 7.5


def slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid(); bg.fill.fore_color.rgb = INK
    bg.line.fill.background()
    bg.shadow.inherit = False
    return s


def _no_autosize(tf):
    # keep text boxes from resizing; we place them deliberately
    tf.word_wrap = True


def box(s, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    return tf


def para(tf, runs, size=14, color=FG, bold=False, font=SANS, align=PP_ALIGN.LEFT,
         space_after=4, space_before=0, line=1.12, first=False):
    p = tf.paragraphs[0] if first and not tf.paragraphs[0].runs else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after); p.space_before = Pt(space_before)
    try:
        p.line_spacing = line
    except Exception:
        pass
    if isinstance(runs, str):
        runs = [(runs, {})]
    for text, ov in runs:
        r = p.add_run(); r.text = text
        f = r.font
        f.size = Pt(ov.get("size", size))
        f.bold = ov.get("bold", bold)
        f.name = ov.get("font", font)
        f.color.rgb = ov.get("color", color)
        if ov.get("spacing"):
            _letter_spacing(r, ov["spacing"])
    return p


def _letter_spacing(run, pts):
    rPr = run._r.get_or_add_rPr()
    rPr.set("spc", str(int(pts * 100)))


def rrect(s, x, y, w, h, fill=PANEL, line=LINE, line_w=1.0, radius=0.08):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line; shp.line.width = Pt(line_w)
    shp.shadow.inherit = False
    try:
        shp.adjustments[0] = radius
    except Exception:
        pass
    return shp


def bar(s, x, y, w, h, frac, fill=SIGNAL, track=RGBColor(0x0D, 0x15, 0x19)):
    t = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    t.fill.solid(); t.fill.fore_color.rgb = track; t.line.color.rgb = LINE; t.line.width = Pt(0.75)
    t.shadow.inherit = False
    try: t.adjustments[0] = 0.5
    except Exception: pass
    fw = max(0.04, w * frac)
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(fw), Inches(h))
    b.fill.solid(); b.fill.fore_color.rgb = fill; b.line.fill.background()
    b.shadow.inherit = False
    try: b.adjustments[0] = 0.5
    except Exception: pass


def strip(s, x, y, h, color):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(0.045), Inches(h))
    r.fill.solid(); r.fill.fore_color.rgb = color; r.line.fill.background(); r.shadow.inherit = False


def eyebrow(s, x, y, num, label):
    tf = box(s, x, y, 8, 0.4)
    para(tf, [(f"{num}   ", {"color": SIGDIM, "font": MONO, "size": 13, "spacing": 1.0}),
              (label, {"color": SIGNAL, "font": MONO, "size": 12.5, "spacing": 2.6})], first=True)


# ============================================================ Slide 1 — hero
s = slide()
tf = box(s, 0.7, 0.55, 11, 0.4)
para(tf, [("GRID-PULSE NTL", {"color": SIGNAL, "font": MONO, "size": 13, "spacing": 3.0, "bold": True}),
          ("    //  Kafr El-Sheikh · autonomous NTL detection", {"color": DIM, "font": MONO, "size": 12})], first=True)

tf = box(s, 0.7, 1.35, 7.1, 2.2)
para(tf, [("The grid loses power\nit can't ", {"color": FG, "size": 40, "bold": True, "font": SANS_B})], line=1.0, first=True)
# second line with colored 'see'
p = tf.paragraphs[0]
p.runs[0].text = "The grid loses power it can't "
r = p.add_run(); r.text = "see"; r.font.size = Pt(40); r.font.bold = True; r.font.name = SANS_B; r.font.color.rgb = SIGNAL
r2 = p.add_run(); r2.text = ". We find it."; r2.font.size = Pt(40); r2.font.bold = True; r2.font.name = SANS_B; r2.font.color.rgb = FG

tf = box(s, 0.7, 3.55, 6.7, 1.6)
para(tf, [("Every distribution transformer leaks energy — some to heat, some to theft. "
           "Grid-Pulse learns how much loss is ", {"color": MUTED, "size": 14.5}),
          ("normal right now", {"color": FG, "size": 14.5, "bold": True}),
          (" — load, temperature, hour — and flags only the unexplained rest as theft, "
           "with the reason it decided.", {"color": MUTED, "size": 14.5})], line=1.3, first=True)

# hero stats
tf = box(s, 0.7, 5.35, 3.2, 1.0)
para(tf, [("≈ 30B EGP", {"color": FG, "font": MONO, "size": 30, "bold": True})], first=True)
para(tf, [("lost to non-technical loss in Egypt, every year", {"color": MUTED, "size": 12})], space_before=2)
tf = box(s, 4.3, 5.35, 3.0, 1.0)
para(tf, [("< 1 month", {"color": FG, "font": MONO, "size": 30, "bold": True})], first=True)
para(tf, [("payback per instrumented transformer kiosk", {"color": MUTED, "size": 12})], space_before=2)

# verdict card (right)
cx, cy, cw, ch = 8.2, 1.35, 4.4, 5.15
rrect(s, cx, cy, cw, ch, fill=INK2, line=LINE2, radius=0.05)
tf = box(s, cx + 0.32, cy + 0.28, cw - 0.64, 0.4)
para(tf, [("◆ THEFT SUSPECTED", {"color": THEFT, "font": MONO, "size": 11.5, "spacing": 1.6, "bold": True}),
          ("        TX-KFS-0456 · single", {"color": MUTED, "font": MONO, "size": 11})], first=True)
tf = box(s, cx + 0.30, cy + 0.72, cw - 0.6, 1.0)
para(tf, [("94%", {"color": THEFT, "font": MONO, "size": 54, "bold": True}),
          ("  theft probability", {"color": MUTED, "size": 13})], first=True)
tf = box(s, cx + 0.32, cy + 1.78, cw - 0.64, 0.5)
para(tf, [("~3.08 kW unaccounted beyond natural loss — dispatch field inspection.",
           {"color": RGBColor(0xC3, 0xD0, 0xD4), "size": 12})], line=1.25, first=True)
reasons = [
    ("Energy imbalance", "+3076 W"),
    ("Expected loss exceeded", "+951% vs baseline"),
    ("Power factor dropped", "0.66 (≥ 0.92)"),
    ("THD increased", "22% (> 10%)"),
    ("Load outside normal pattern", "anomaly 0.83"),
]
tf = box(s, cx + 0.32, cy + 2.40, cw - 0.6, 2.0)
for i, (rl, rd) in enumerate(reasons):
    para(tf, [("✓  ", {"color": THEFT, "font": MONO, "size": 11.5, "bold": True}),
              (rl + "   ", {"color": FG, "size": 11.5, "bold": True}),
              (rd, {"color": DIM, "font": MONO, "size": 10})], first=(i == 0), space_after=5)
# tiles
ty = cy + 4.22
for i, (val, lab, col) in enumerate([("3.40", "MEASURED LOSS", FG), ("0.32", "AI BASELINE", FG), ("3.08", "UNACCOUNTED", THEFT)]):
    tx = cx + 0.32 + i * 1.28
    rrect(s, tx, ty, 1.18, 0.78, fill=RGBColor(0x0B, 0x10, 0x13), line=LINE, radius=0.12)
    tf = box(s, tx + 0.12, ty + 0.10, 0.96, 0.6)
    para(tf, [(val, {"color": col, "font": MONO, "size": 17, "bold": True}), (" kW", {"color": col, "size": 9})], first=True)
    para(tf, [(lab, {"color": DIM, "font": MONO, "size": 7.5, "spacing": 1.0})], space_before=1)


# ============================================================ Slide 2 — problem
s = slide()
eyebrow(s, 0.7, 0.6, "01", "THE PROBLEM")
tf = box(s, 0.7, 1.05, 11, 1.0)
para(tf, [("Why the grid is blind", {"color": FG, "size": 34, "bold": True, "font": SANS_B})], first=True)
tf = box(s, 0.7, 1.95, 11.9, 0.7)
para(tf, [("Cable and transformer losses are real, and they rise with heat and load. A fixed threshold "
           "cries wolf all summer — so operators mute it, and real theft hides in the noise.",
           {"color": MUTED, "size": 15})], line=1.3, first=True)

tf = box(s, 0.7, 3.2, 7.0, 3.2, anchor=MSO_ANCHOR.MIDDLE)
para(tf, [("A brick-kiln, a workshop, a battery of hair-dryers hooked past the meter — the transformer feels it as ",
           {"color": FG, "size": 23, "bold": True}),
          ("“more loss.”", {"color": TECH, "size": 23, "bold": True}),
          (" Without context, every hot afternoon looks like theft, and every theft looks like a hot afternoon.",
           {"color": FG, "size": 23, "bold": True})], line=1.28, first=True)

figs = [("~30%", "of generated power lost to NTL in the worst-hit zones", THEFT),
        ("7", "independent inputs the model weighs — not temperature alone", SIGNAL),
        ("3 beats", "is all it takes to show a judge the difference, live", FG)]
fy = 3.15
for val, d, col in figs:
    tf = box(s, 8.4, fy, 4.2, 1.0)
    para(tf, [(val, {"color": col, "font": MONO, "size": 34, "bold": True})], first=True)
    para(tf, [(d, {"color": MUTED, "size": 12.5})], space_before=1, line=1.2)
    fy += 1.15


# ============================================================ Slide 3 — moat / 3 beats
s = slide()
eyebrow(s, 0.7, 0.6, "02", "THE MOAT")
tf = box(s, 0.7, 1.05, 11.9, 1.0)
para(tf, [("Separating heat from theft", {"color": FG, "size": 34, "bold": True, "font": SANS_B})], first=True)
tf = box(s, 0.7, 1.95, 11.9, 0.7)
para(tf, [("Same transformer, three readings. The AI baseline rises with the heat — so the middle case raises ",
           {"color": MUTED, "size": 15}),
          ("no", {"color": TECH, "size": 15, "bold": True, "font": SANS}),
          (" alarm. Only the third leaves an unexplained residual. This is the whole demo.",
           {"color": MUTED, "size": 15})], line=1.3, first=True)

beats = [
    ("● NORMAL", OK, "Baseline load", "Registered demand, clean waveform. Energy balance holds.",
     [("load", "6.85 kW", False), ("power factor", "0.98", False), ("residual", "−0.17 kW", False), ("probability", "0%", False)]),
    ("● TECHNICAL LOSS", TECH, "Hot day, 45 °C", "Loss climbs — but the model expects it. R rises with heat. No false alarm.",
     [("load", "7.00 kW", False), ("AI baseline", "↑ tracks temp", False), ("residual", "−0.15 kW", False), ("probability", "0%", False)]),
    ("● THEFT SUSPECTED", THEFT, "Unregistered hook", "+3.4 kW draw, PF collapses, THD spikes. Baseline stays flat — residual explodes.",
     [("load", "10.2 kW", False), ("power factor", "0.66", False), ("residual", "+3.08 kW", True), ("probability", "94%", True)]),
]
bx, by, bw, bh = 0.7, 2.95, 3.87, 3.9
for i, (tag, col, title, desc, rows) in enumerate(beats):
    x = bx + i * (bw + 0.32)
    rrect(s, x, by, bw, bh, fill=PANEL, line=LINE, radius=0.05)
    strip(s, x, by, bh, col)
    tf = box(s, x + 0.3, by + 0.26, bw - 0.5, 0.35)
    para(tf, [(tag, {"color": col, "font": MONO, "size": 11.5, "spacing": 1.4, "bold": True})], first=True)
    tf = box(s, x + 0.3, by + 0.66, bw - 0.5, 0.4)
    para(tf, [(title, {"color": FG, "size": 18, "bold": True})], first=True)
    tf = box(s, x + 0.3, by + 1.12, bw - 0.55, 1.0)
    para(tf, [(desc, {"color": MUTED, "size": 12})], line=1.25, first=True)
    tf = box(s, x + 0.3, by + 2.25, bw - 0.6, 1.5)
    for j, (k, v, hl) in enumerate(rows):
        para(tf, [(k, {"color": DIM, "font": MONO, "size": 12}),
                  ("        " if len(k) < 8 else "    ", {}),
                  (v, {"color": THEFT if hl else RGBColor(0xCD, 0xD8, 0xDB), "font": MONO, "size": 12, "bold": hl})],
             first=(j == 0), space_after=4)


# ============================================================ Slide 4 — model
s = slide()
eyebrow(s, 0.7, 0.6, "03", "THE MODEL")
tf = box(s, 0.7, 1.05, 11.9, 1.0)
para(tf, [("Multi-factor, and it shows its work", {"color": FG, "size": 34, "bold": True, "font": SANS_B})], first=True)
tf = box(s, 0.7, 1.95, 11.9, 0.7)
para(tf, [("A temperature-only model reads as a toy. Ours weighs seven signals; a Random-Forest learns what "
           "natural loss should be, and the verdict names every reason it fired.", {"color": MUTED, "size": 15})],
     line=1.3, first=True)

tf = box(s, 0.7, 3.0, 6, 0.35)
para(tf, [("LEARNED FEATURE IMPORTANCE · TECHNICAL-LOSS MODEL", {"color": SIGNAL, "font": MONO, "size": 10.5, "spacing": 1.6})], first=True)
feats = [("load_w", 1.00, "0.58"), ("temp_c", 0.47, "0.27"), ("current_a", 0.26, "0.15"),
         ("hour", 0.04, "0.002"), ("day_of_week", 0.03, "0.001"), ("voltage_v", 0.03, "0.001"), ("rated_kva", 0.03, "0.001")]
fy = 3.5
for name, frac, val in feats:
    tf = box(s, 0.7, fy, 1.5, 0.3, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, [(name, {"color": RGBColor(0xCD, 0xD8, 0xDB), "font": MONO, "size": 12})], first=True)
    bar(s, 2.3, fy + 0.045, 3.0, 0.16, frac)
    tf = box(s, 5.45, fy, 0.7, 0.3, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, [(val, {"color": MUTED, "font": MONO, "size": 11})], align=PP_ALIGN.RIGHT, first=True)
    fy += 0.42

# pipeline (right)
tf = box(s, 6.9, 3.0, 6, 0.35)
para(tf, [("DETECTION PIPELINE", {"color": SIGNAL, "font": MONO, "size": 10.5, "spacing": 1.6})], first=True)
steps = [("①", "Energy balance", "feeder power − registered meters = measured loss"),
         ("②", "AI technical-loss baseline", "predicts normal loss now → residual = measured − expected"),
         ("③", "Harmonics & power factor", "illegal loads distort the waveform"),
         ("④", "Temporal anomaly", "Isolation Forest flags draws that don't fit the curve"),
         ("⑤", "Fusion + explainable verdict", "probability, reasons checklist, estimated stolen kW")]
py = 3.5
for gi, t, d in steps:
    tf = box(s, 6.9, py, 6, 0.6)
    para(tf, [(gi + "  ", {"color": SIGNAL, "font": MONO, "size": 13, "bold": True}),
              (t, {"color": FG, "size": 13.5, "bold": True})], first=True)
    para(tf, [("      " + d, {"color": MUTED, "size": 11.5})], space_before=1)
    py += 0.66


# ============================================================ Slide 5 — hardware
s = slide()
eyebrow(s, 0.7, 0.6, "04", "THE HARDWARE")
tf = box(s, 0.7, 1.05, 11.9, 1.0)
para(tf, [("From breadboard to busbar", {"color": FG, "size": 34, "bold": True, "font": SANS_B})], first=True)
tf = box(s, 0.7, 1.95, 11.9, 0.7)
para(tf, [("A real edge node, not a slide. Current transformer → signal conditioning → ESP32 → a strict, "
           "signed telemetry contract the backend enforces on every packet.", {"color": MUTED, "size": 15})],
     line=1.3, first=True)

cards = [
    ("EDGE NODE — TODAY", "ESP32 + split-core CT",
     ["SCT-013-000 clamp, 100 A : 50 mA, non-invasive", "33 Ω burden + 1.65 V bias into the ADC — measured",
      "EmonLib RMS, calibration ≈ 60.6, NTP-timestamped", "Posts contract-valid JSON with a bearer token"]),
    ("PRODUCTION — ROADMAP", "Kiosk-grade sensing",
     ["Rogowski coils on the LV busbar, IP65", "LoRaWAN backhaul — no field Wi-Fi",
      "TinyML on-device: send only on theft (−99% bw)", "Theft-location triangulation across feeders"]),
    ("BACKEND", "FastAPI · Redis · Celery",
     ["Strict JSON-Schema contract: bad body → 422", "Bad token → 401, every packet authenticated",
      "Inline or worker detection — same verdict", "Live map + verdicts over WebSocket"]),
    ("THE INTERFACE", "An operator's console",
     ["Every transformer on a map: green / amber / red", "Big probability + reasons checklist",
      "One tap: dispatch inspection, or dismiss", "2 s polling fallback if the socket drops"]),
]
cw, chh = 5.9, 2.15
for i, (lbl, title, items) in enumerate(cards):
    x = 0.7 + (i % 2) * (cw + 0.33)
    y = 3.05 + (i // 2) * (chh + 0.28)
    rrect(s, x, y, cw, chh, fill=PANEL, line=LINE, radius=0.05)
    tf = box(s, x + 0.3, y + 0.22, cw - 0.6, 0.3)
    para(tf, [(lbl, {"color": SIGNAL, "font": MONO, "size": 10, "spacing": 1.5})], first=True)
    tf = box(s, x + 0.3, y + 0.52, cw - 0.6, 0.4)
    para(tf, [(title, {"color": FG, "size": 16, "bold": True})], first=True)
    tf = box(s, x + 0.3, y + 1.0, cw - 0.55, 1.1)
    for j, it in enumerate(items):
        para(tf, [("›  ", {"color": SIGDIM, "font": MONO, "size": 12}),
                  (it, {"color": RGBColor(0xC3, 0xD0, 0xD4), "size": 11.5})], first=(j == 0), space_after=3, line=1.15)


# ============================================================ Slide 6 — business
s = slide()
eyebrow(s, 0.7, 0.6, "05", "THE BUSINESS")
tf = box(s, 0.7, 1.05, 11.9, 1.0)
para(tf, [("A business the ministry funds itself", {"color": FG, "size": 34, "bold": True, "font": SANS_B})], first=True)
tf = box(s, 0.7, 1.95, 11.9, 0.7)
para(tf, [("We don't sell software they have to justify — we take a share of the energy we recover. "
           "The first month of caught theft pays for the kiosk.", {"color": MUTED, "size": 15})], line=1.3, first=True)

cells = [("≈ 30B EGP", "annual NTL loss in Egypt — the pool we recover against", THEFT),
         ("< 1 mo", "ROI per instrumented kiosk at typical recovery rates", OK),
         ("SaaS + HaaS", "hardware-as-a-service + platform, or % of recovered energy", SIGNAL)]
cw = 3.87
for i, (val, d, col) in enumerate(cells):
    x = 0.7 + i * (cw + 0.32)
    rrect(s, x, 3.05, cw, 1.85, fill=PANEL, line=LINE, radius=0.06)
    tf = box(s, x + 0.32, 3.35, cw - 0.6, 0.7)
    para(tf, [(val, {"color": col, "font": MONO, "size": 30, "bold": True})], first=True)
    tf = box(s, x + 0.32, 4.15, cw - 0.6, 0.7)
    para(tf, [(d, {"color": MUTED, "size": 12.5})], line=1.25, first=True)

tf = box(s, 0.7, 5.3, 11.9, 1.4)
para(tf, [("Customer: ", {"color": FG, "size": 15, "bold": True}),
          ("distribution companies and the Ministry of Electricity.   ", {"color": RGBColor(0xC3, 0xD0, 0xD4), "size": 15}),
          ("Wedge: ", {"color": FG, "size": 15, "bold": True}),
          ("one region, a few hundred kiosks, measured recovery.   ", {"color": RGBColor(0xC3, 0xD0, 0xD4), "size": 15}),
          ("Moat: ", {"color": FG, "size": 15, "bold": True}),
          ("the labelled theft data we accumulate makes every next region's model sharper — a data advantage a "
           "fixed-threshold competitor can never catch.", {"color": RGBColor(0xC3, 0xD0, 0xD4), "size": 15})],
     line=1.35, first=True)


# ============================================================ Slide 7 — close
s = slide()
tf = box(s, 1.0, 2.4, 11.3, 0.5)
para(tf, [("THE PITCH, IN ONE LINE", {"color": SIGNAL, "font": MONO, "size": 12.5, "spacing": 3.0})], align=PP_ALIGN.CENTER, first=True)
tf = box(s, 1.0, 3.0, 11.3, 1.8)
para(tf, [("We turn a blind meter reading into\na decision an inspector can act on.",
           {"color": FG, "size": 38, "bold": True, "font": SANS_B})], align=PP_ALIGN.CENTER, line=1.1, first=True)
tf = box(s, 2.6, 4.9, 8.1, 1.0)
para(tf, [("Working edge node, real trained model, explainable verdict, and a demo that lands in three clicks. "
           "Built in Kafr El-Sheikh — to be deployed across the grid.", {"color": MUTED, "size": 14})],
     align=PP_ALIGN.CENTER, line=1.35, first=True)
tf = box(s, 1.0, 6.7, 11.3, 0.4)
para(tf, [("NORMAL   ·   TECHNICAL_LOSS   ·   NTL_THEFT_SUSPECTED", {"color": DIM, "font": MONO, "size": 11.5, "spacing": 1.5})],
     align=PP_ALIGN.CENTER, first=True)

out = "Grid-Pulse-NTL.pptx"
prs.save(out)
print("saved", out, "-", len(prs.slides._sldIdLst), "slides")

from http.server import BaseHTTPRequestHandler
import json, io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime

# ── YORDAMCHI FUNKSIYALAR ─────────────────────────────────────
def parse_d(s):
    try: return datetime.strptime(s, "%d.%m.%Y")
    except: return datetime.min

def in_davr(sana, dan, gacha):
    if not dan and not gacha: return True
    d = parse_d(sana)
    if dan and d < datetime.strptime(dan, "%Y-%m-%d"): return False
    if gacha and d > datetime.strptime(gacha, "%Y-%m-%d"): return False
    return True

def davr_label(dan, gacha):
    if dan and gacha:
        d1 = ".".join(reversed(dan.split("-")))
        d2 = ".".join(reversed(gacha.split("-")))
        return d1 + " — " + d2
    return "Hammasi"

def open_pdf(blob):
    from urllib.request import urlopen
    return blob

# ── RANGLAR ──────────────────────────────────────────────────
C_DARK    = colors.HexColor('#111111')
C_HDR     = colors.HexColor('#1a1a1a')
C_GOLD    = colors.HexColor('#b8860b')
C_GREEN   = colors.HexColor('#2e7d32')
C_RED     = colors.HexColor('#c62828')
C_WHITE   = colors.white
C_GRAY    = colors.HexColor('#F7F7F7')
C_BLUE    = colors.HexColor('#1565c0')
C_ORANGE  = colors.HexColor('#C05621')
C_MUTED   = colors.HexColor('#718096')
C_AMBER   = colors.HexColor('#b8860b')

# ── PARAGRAF YORDAMCHISI ──────────────────────────────────────
def P(text, font='Helvetica', size=10, color=colors.black, align='LEFT'):
    a = {'LEFT': TA_LEFT, 'CENTER': TA_CENTER, 'RIGHT': TA_RIGHT}
    s = ParagraphStyle('p', fontName=font, fontSize=size,
        textColor=color, alignment=a.get(align, TA_LEFT), leading=size + 3)
    return Paragraph(str(text) if text is not None else '', s)

def title_p(text):
    s = ParagraphStyle('t', fontName='Helvetica-Bold', fontSize=13,
        textColor=C_DARK, alignment=TA_CENTER, spaceAfter=3)
    return Paragraph(text, s)

def sub_p(text):
    s = ParagraphStyle('s', fontName='Helvetica', fontSize=8,
        textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=5)
    return Paragraph(text, s)

# ── JADVAL USLUBI (umumiy) ────────────────────────────────────
def base_style():
    return [
        ('BACKGROUND',   (0, 0), (-1,  0), C_HDR),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',         (0, 0), (-1, -1), 0.4, colors.HexColor('#dddddd')),
        ('ROWHEIGHT',    (0, 0), ( 0,  0), 22),
        ('TOPPADDING',   (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
        ('LEFTPADDING',  (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]

# ═══════════════════════════════════════════════════════════════
# 1. ZAVOD HISOBOTI — A4 landscape
# ═══════════════════════════════════════════════════════════════
def build_pdf(zavodlar, filter_zavod, dan, gacha, label):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
        leftMargin=8*mm, rightMargin=8*mm, topMargin=8*mm, bottomMargin=8*mm)
    story = []

    # ── Jadval 1: Kirdi-chiqdi ──
    HDR = ["Sana","Zavod","Tur","+/-","Kimga","Kirim(g)","Naqt($)","Kurs","Naqt→g","Lom(g)","Lom($)","Chiqim(g)","Ostatka(g)"]
    CW  = [x*mm for x in [24, 26, 16, 9, 26, 22, 24, 16, 20, 20, 24, 22, 24]]
    hdr_row = [P(h, 'Helvetica-Bold', 9, C_WHITE, 'CENTER') for h in HDR]

    all_rows = []
    for z in zavodlar:
        if filter_zavod and z["nom"] != filter_zavod: continue
        for t in z.get("turlar", []):
            bal = 0.0
            for op in t.get("tarix", []):
                if op["tip"] == "mol":      bal += op.get("gramm", 0)
                elif op["tip"] == "vozvrat": bal  = max(0, bal - op.get("gramm", 0))
                else:                        bal  = max(0, bal - (op.get("jami") or 0))
                if not in_davr(op["sana"], dan, gacha): continue
                all_rows.append({
                    "sana": op["sana"], "zavod": z["nom"], "tur": t["nom"],
                    "tip": op["tip"], "op": op, "ostatka": round(bal, 2)
                })
    all_rows.sort(key=lambda r: parse_d(r["sana"]))

    tdata = [hdr_row]; rstyles = []
    for ri, row in enumerate(all_rows, 1):
        op = row["op"]
        is_k = row["tip"] == "mol"
        is_v = row["tip"] == "vozvrat"
        def cell(v, bold=False, color=colors.HexColor('#212121'), align='LEFT'):
            f = 'Helvetica-Bold' if bold else 'Helvetica'
            return P(v, f, 9, color, align)

        trow = [
            cell(row["sana"]),
            cell(row["zavod"]),
            cell(row["tur"]),
            P("↓" if is_k else ("↩" if is_v else "↑"), 'Helvetica-Bold', 11,
              C_GREEN if is_k else (C_BLUE if is_v else C_RED), 'CENTER'),
            cell("" if is_k else (op.get("kimga") or "")),
            cell(f"+{op.get('gramm',0):,.2f}" if is_k else
                 (f"-{op.get('gramm',0):,.2f}" if is_v else ""),
                 bold=True, color=C_GREEN if is_k else C_BLUE, align='RIGHT'),
            cell(f"{op.get('naqtSumma',0):,.0f}" if not is_k else "", align='RIGHT'),
            cell(str(op.get("naqtKurs",""))   if not is_k else "", align='RIGHT'),
            cell(f"{op.get('naqtGramm',0):,.2f}" if not is_k else "", align='RIGHT'),
            cell(f"{op.get('lomGramm',0):,.2f}" if not is_k else "", align='RIGHT'),
            cell(f"{op.get('lomPul',0):,.0f}"   if not is_k else "", align='RIGHT'),
            cell(f"{op.get('jami',0):,.2f}"     if not is_k else "",
                 bold=True, color=C_RED, align='RIGHT'),
            P(f"{row['ostatka']:,.2f}", 'Helvetica-Bold', 9, C_AMBER, 'RIGHT'),
        ]
        tdata.append(trow)
        rstyles.append(('BACKGROUND', (0, ri), (-1, ri), C_WHITE if ri % 2 else C_GRAY))

    # Jami qator
    tK = round(sum(r["op"].get("gramm", 0) for r in all_rows if r["tip"] == "mol"), 2)
    tC = round(sum(r["op"].get("jami", 0) for r in all_rows if r["tip"] == "tolov"), 2)
    tN = round(sum(r["op"].get("naqtSumma", 0) for r in all_rows if r["tip"] == "tolov"), 2)
    tL = round(sum(r["op"].get("lomPul", 0) for r in all_rows if r["tip"] == "tolov"), 2)
    fin = {}
    for r in all_rows: fin[r["zavod"] + "|" + r["tur"]] = r["ostatka"]
    tO = round(sum(fin.values()), 2)
    jr = len(tdata)
    tdata.append([
        P('JAMI', 'Helvetica-Bold', 9, C_WHITE, 'CENTER'), '', '', '', '',
        P(f'+{tK:,.2f}g', 'Helvetica-Bold', 9, colors.HexColor('#68D391'), 'RIGHT'),
        P(f'Naqt: {tN:,.0f}$', 'Helvetica-Bold', 9, colors.HexColor('#F6E05E'), 'RIGHT'),
        '', '', '',
        P(f'Lom: {tL:,.0f}$', 'Helvetica-Bold', 9, colors.HexColor('#F6E05E'), 'RIGHT'),
        P(f'-{tC:,.2f}g', 'Helvetica-Bold', 9, colors.HexColor('#FC8181'), 'RIGHT'),
        P(f'{tO:,.2f}g', 'Helvetica-Bold', 10, colors.HexColor('#F6E05E'), 'RIGHT'),
    ])
    rstyles += [('BACKGROUND', (0, jr), (-1, jr), C_DARK), ('SPAN', (0, jr), (4, jr))]

    t1 = Table(tdata, colWidths=CW, repeatRows=1)
    t1.setStyle(TableStyle(base_style() + rstyles))

    story.append(title_p("TILLA HISOB — Kirdi-Chiqdi" +
                          (" — " + filter_zavod if filter_zavod else " (Barcha)")))
    story.append(sub_p("Davr: " + label))
    story.append(t1)
    story.append(Spacer(1, 8*mm))

    # ── Jadval 2: Tur bo'yicha xulosa ──
    H2 = ["Zavod", "Tur", "Kirim(g)", "Chiqim(g)", "Ostatka(g)", "Naqt($)", "Lom($)", "Jami($)"]
    H2CW = [x*mm for x in [35, 25, 30, 30, 30, 36, 36, 36]]
    h2hdr = [P(h, 'Helvetica-Bold', 9, C_WHITE, 'CENTER') for h in H2]
    h2data = [h2hdr]; h2styles = []
    gK = gC = gO = gN = gL = 0; ri2 = 1

    for z in zavodlar:
        if filter_zavod and z["nom"] != filter_zavod: continue
        for t in z.get("turlar", []):
            tk = tc = tn = tl = bal = 0
            for op in t.get("tarix", []):
                if op["tip"] == "mol":      bal += op.get("gramm", 0)
                elif op["tip"] == "vozvrat": bal = max(0, bal - op.get("gramm", 0))
                else:                        bal = max(0, bal - (op.get("jami") or 0))
                if not in_davr(op["sana"], dan, gacha): continue
                if op["tip"] == "mol": tk += op.get("gramm", 0)
                else:
                    tc += op.get("jami", 0)
                    tn += op.get("naqtSumma", 0)
                    tl += op.get("lomPul", 0)
            o = round(bal, 2)
            bg = C_GRAY if ri2 % 2 == 0 else C_WHITE
            h2data.append([
                P(z["nom"], size=9),
                P(t["nom"], size=9),
                P(f'{tk:,.2f}', 'Helvetica-Bold', 9, C_GREEN, 'RIGHT'),
                P(f'{tc:,.2f}', 'Helvetica-Bold', 9, C_RED, 'RIGHT'),
                P(f'{o:,.2f}',  'Helvetica-Bold', 10, C_GOLD, 'RIGHT'),
                P(f'{tn:,.2f}', size=9, color=C_ORANGE, align='RIGHT'),
                P(f'{tl:,.2f}', size=9, color=C_ORANGE, align='RIGHT'),
                P(f'{(tn+tl):,.2f}', size=9, color=C_ORANGE, align='RIGHT'),
            ])
            h2styles.append(('BACKGROUND', (0, ri2), (-1, ri2), bg))
            gK += tk; gC += tc; gO += o; gN += tn; gL += tl; ri2 += 1

    jr2 = len(h2data)
    h2data.append([
        P('JAMI', 'Helvetica-Bold', 9, C_WHITE, 'CENTER'), '',
        P(f'{gK:,.2f}', 'Helvetica-Bold', 9, colors.HexColor('#68D391'), 'RIGHT'),
        P(f'{gC:,.2f}', 'Helvetica-Bold', 9, colors.HexColor('#FC8181'), 'RIGHT'),
        P(f'{gO:,.2f}', 'Helvetica-Bold', 9, colors.HexColor('#F6E05E'), 'RIGHT'),
        P(f'{gN:,.2f}', 'Helvetica-Bold', 9, colors.HexColor('#FBD38D'), 'RIGHT'),
        P(f'{gL:,.2f}', 'Helvetica-Bold', 9, colors.HexColor('#FBD38D'), 'RIGHT'),
        P(f'{(gN+gL):,.2f}', 'Helvetica-Bold', 9, colors.HexColor('#FBD38D'), 'RIGHT'),
    ])
    h2styles += [('BACKGROUND', (0, jr2), (-1, jr2), C_DARK), ('SPAN', (0, jr2), (1, jr2))]

    ht = Table(h2data, colWidths=H2CW, repeatRows=1)
    ht.setStyle(TableStyle(base_style() + h2styles))

    story.append(title_p("HISOBOT — Tur bo'yicha kirdi-chiqdi"))
    story.append(sub_p("Davr: " + label))
    story.append(ht)

    doc.build(story)
    return buf.getvalue()

# ═══════════════════════════════════════════════════════════════
# 2. TO'LOV CHEKI — 72mm termal
# ═══════════════════════════════════════════════════════════════
class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
            tip    = body.get("tip", "")





            # Default: zavod hisoboti
            zavodlar     = body.get("zavodlar", [])
            dan          = body.get("dan")
            gacha        = body.get("gacha")
            filter_zavod = body.get("zavod")
            label        = davr_label(dan, gacha)
            pdf = build_pdf(zavodlar, filter_zavod, dan, gacha, label)
            self._send_pdf(pdf, "tilla-hisobot.pdf")

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _send_pdf(self, pdf_bytes, filename):
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", f"inline; filename={filename}")
        self.send_header("Content-Length", str(len(pdf_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(pdf_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # loglarni o'chirish

from http.server import BaseHTTPRequestHandler
import json, io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, FrameBreak
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

# ── v1.05: TUR BO'YICHA HARAKAT (davr boshidagi ostatka + har harakat) ──
# Davr boshidagi ostatka — dan sanasidan OLDINGI hamma amal (tarixdan).
# Manfiy ostatka qanday bo'lsa shunday ko'rsatiladi (Ibrohim: «farqi yo'q
# ko'rsatsin»). Eski jadvallardagi max(0, …) qoidasiga TEGILMADI.
def _g(x):
    return round(float(x or 0), 2)

def _fg(x):
    return f"{x:,.2f}g"

def _fn(x):
    v = float(x or 0)
    return f"{v:,.2f}".rstrip('0').rstrip('.') if v != int(v) else f"{int(v):,}"

def _op_qatorlar(op):
    """[(yozuv, formula, gramm_ishorali)] — gramm yig'indisi balansga teng."""
    tip = op.get("tip")
    if tip == "mol":
        return [("mol olindi", "", _g(op.get("gramm")))]
    if tip == "vozvrat":
        return [("vozvrat qilindi", "", -_g(op.get("gramm")))]
    jami = _g(op.get("jami"))
    out = []
    if op.get("zapros"):
        zP, zL, zT = _g(op.get("zPul")), _g(op.get("zLom")), _g(op.get("zToza"))
        gT = _g(zT * 1.7)
        gP = _g(jami - zL - gT)
        if zP > 0:
            kurs = f" / {zP / gP:,.2f} kurs" if gP > 0.001 else ""
            out.append(("zapros: pul berildi", f"{_fn(zP)}$" + kurs, -gP))
        if zL > 0:
            out.append(("zapros: lom berildi", f"{zL:,.2f}g lom", -zL))
        if zT > 0:
            out.append(("zapros: 999 berildi", f"{zT:,.2f}g x 1.7", -gT))
    else:
        nS, nK, nG = _g(op.get("naqtSumma")), op.get("naqtKurs") or 0, _g(op.get("naqtGramm"))
        lG, lK, lP, lE = _g(op.get("lomGramm")), op.get("lomKurs") or 0, _g(op.get("lomPul")), _g(op.get("lomGEq"))
        if nS > 0:
            out.append(("naqt berildi", f"{_fn(nS)}$ / {_fn(nK)} kurs", -nG))
        if lG > 0:
            out.append(("lom berildi", f"{lG:,.2f}g x {_fn(lK)} = {_fn(lP)}$ / {_fn(nK)} kurs", -lE))
    qoldi = _g(-jami - sum(q[2] for q in out))
    if not out or abs(qoldi) > 0.009:
        out.append(("to'lov", "", qoldi if out else -jami))
    return out

def _dan_oldin(sana, dan):
    return bool(dan) and parse_d(sana) < datetime.strptime(dan, "%Y-%m-%d")

def _gacha_keyin(sana, gacha):
    return bool(gacha) and parse_d(sana) > datetime.strptime(gacha, "%Y-%m-%d")

def _kun_oldin(dan):
    from datetime import timedelta
    return (datetime.strptime(dan, "%Y-%m-%d") - timedelta(days=1)).strftime("%d.%m.%Y")

def _gacha_lbl(gacha):
    return ".".join(reversed(gacha.split("-"))) if gacha else datetime.now().strftime("%d.%m.%Y")

C_CREAM = colors.HexColor('#fbf1d6')
C_CARDH = colors.HexColor('#f3ecd9')

def _summary_box(matn, turlar, kenglik):
    qism = " &nbsp;·&nbsp; ".join(f"{n} {_fg(v)}" for n, v in turlar)
    t = Table([[P(f"<b>{matn}</b> &nbsp;&nbsp; {qism}", size=9.5, color=colors.HexColor('#5a3e00'))]],
              colWidths=[kenglik])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), C_CREAM),
                           ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#e0c97a')),
                           ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                           ('LEFTPADDING', (0, 0), (-1, -1), 8)]))
    return t

def _tur_karta(zavod_nom, t, dan, gacha, kenglik):
    bosh = 0.0; ops = []
    for op in t.get("tarix", []):
        if _gacha_keyin(op.get("sana", ""), gacha): continue
        qs = _op_qatorlar(op)
        if _dan_oldin(op.get("sana", ""), dan):
            bosh += sum(q[2] for q in qs)
        else:
            ops.append((op.get("sana", ""), qs))
    bosh = _g(bosh)
    ops.sort(key=lambda r: parse_d(r[0]))   # sort barqaror — bir kundagi tartib saqlanadi
    if not ops and abs(bosh) < 0.005:
        return None, bosh, bosh
    cw = [22*mm, kenglik - 22*mm - 24*mm, 24*mm]
    grey = colors.HexColor('#8a8a8a')
    rows = [[P(f"<b>{zavod_nom} · {t['nom']}</b>", size=9.5, align='CENTER'), '', '']]
    st = [('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 0), C_CARDH),
          ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#cfcfcf')),
          ('VALIGN', (0, 0), (-1, -1), 'TOP'),
          ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
          ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]
    bal = bosh
    if dan:
        rows.append([P(_kun_oldin(dan), size=8, color=grey), P("kun oxiridagi ostatka", size=8.5, color=colors.HexColor('#555555')),
                     P(f"<b>{_fg(bosh)}</b>", size=9, color=C_GOLD, align='RIGHT')])
        st.append(('BACKGROUND', (0, len(rows) - 1), (-1, len(rows) - 1), colors.HexColor('#fff8e6')))
    oldingi = None
    for i, (sana, qs) in enumerate(ops):
        for qi, (yoz, f, g) in enumerate(qs):
            matn = yoz + (f"<br/><font size=7.5 color='#8a8a8a'>{f}</font>" if f else "")
            rang = C_GREEN if g > 0 else (C_BLUE if yoz == "vozvrat qilindi" else C_RED)
            rows.append([P(sana if sana != oldingi else "", size=8, color=grey),
                         P(matn, size=8.5, color=colors.HexColor('#444444')),
                         P(f"<b>{'+' if g > 0 else ''}{_fg(g)}</b>", size=9, color=rang, align='RIGHT')])
            oldingi = sana
            bal = _g(bal + g)
        kun_tugadi = (i == len(ops) - 1) or ops[i + 1][0] != sana
        if kun_tugadi:
            rows.append(['', '', P(f"<b>{_fg(bal)}</b>", size=9, align='RIGHT')])
            r = len(rows) - 1
            st += [('LINEABOVE', (0, r), (-1, r), 0.4, colors.HexColor('#e3e3e3')),
                   ('LINEBELOW', (0, r), (-1, r), 0.6, colors.HexColor('#bdbdbd')),
                   ('BACKGROUND', (0, r), (-1, r), colors.HexColor('#fafafa'))]
    rows.append([P("<b>QOLDI</b>", size=9.5), '', P(f"<b>{_fg(bal)}</b>", size=10, color=C_GOLD, align='RIGHT')])
    r = len(rows) - 1
    st += [('SPAN', (0, r), (1, r)), ('BACKGROUND', (0, r), (-1, r), C_CREAM),
           ('LINEABOVE', (0, r), (-1, r), 0.6, colors.HexColor('#cfcfcf'))]
    tb = Table(rows, colWidths=cw, repeatRows=1)
    tb.setStyle(TableStyle(st))
    return tb, bosh, bal

def harakat_bolim(zavodlar, filter_zavod, dan, gacha, label, to_liq, ustun):
    """Sahifa shablonlari: 'head' (sarlavha + 2 ustun), 'cols' (2 ustun), 'full'."""
    story = []
    birinchi = True
    for z in zavodlar:
        if filter_zavod and z["nom"] != filter_zavod: continue
        kartalar = []; boshlar = []; oxirlar = []
        for t in z.get("turlar", []):
            tb, b, o = _tur_karta(z["nom"], t, dan, gacha, ustun)
            if tb is None: continue
            kartalar.append(tb); boshlar.append((t["nom"], b)); oxirlar.append((t["nom"], o))
        if not kartalar: continue
        if not birinchi:
            story += [NextPageTemplate('head'), PageBreak()]
        birinchi = False
        story.append(NextPageTemplate('cols'))
        story.append(title_p("TILLA HISOB — " + z["nom"] + " · tur bo'yicha harakat"))
        story.append(sub_p("Davr: " + label))
        if dan:
            story.append(_summary_box(f"{_kun_oldin(dan)} kun oxiridagi ostatka: {_fg(_g(sum(v for _, v in boshlar)))}", boshlar, to_liq))
        story.append(FrameBreak())
        for k in kartalar:
            story += [k, Spacer(1, 4*mm)]
        story.append(_summary_box(f"{_gacha_lbl(gacha)} holatiga ostatka: {_fg(_g(sum(v for _, v in oxirlar)))}", oxirlar, ustun))
    if story:
        story += [NextPageTemplate('full'), PageBreak()]
    return story

# ═══════════════════════════════════════════════════════════════
# 1. ZAVOD HISOBOTI — A4 landscape
# ═══════════════════════════════════════════════════════════════
def build_pdf(zavodlar, filter_zavod, dan, gacha, label):
    buf = io.BytesIO()
    # v1.05: BaseDocTemplate — harakat bo'limi 2 ustunli sahifalarda, qolgani to'liq kenglikda
    doc = BaseDocTemplate(buf, pagesize=landscape(A4),
        leftMargin=8*mm, rightMargin=8*mm, topMargin=8*mm, bottomMargin=8*mm)
    W, H, x0, y0 = doc.width, doc.height, doc.leftMargin, doc.bottomMargin
    gap, hh = 6*mm, 30*mm
    cw = (W - gap) / 2
    t_full = PageTemplate('full', [Frame(x0, y0, W, H, id='f')])
    t_head = PageTemplate('head', [Frame(x0, y0 + H - hh, W, hh, id='h'),
                                   Frame(x0, y0, cw, H - hh, id='l1'),
                                   Frame(x0 + cw + gap, y0, cw, H - hh, id='r1')])
    t_cols = PageTemplate('cols', [Frame(x0, y0, cw, H, id='l'),
                                   Frame(x0 + cw + gap, y0, cw, H, id='r')])
    story = harakat_bolim(zavodlar, filter_zavod, dan, gacha, label, W - 12, cw - 12)   # v1.05
    doc.addPageTemplates([t_head, t_cols, t_full] if story else [t_full, t_head, t_cols])

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

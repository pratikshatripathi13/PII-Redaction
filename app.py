"""PII Redaction Tool — Streamlit UI (redaction / document-security styling).

Thin UI over the existing pipeline (pii_redactor.webservice). No detection or
redaction logic lives here. The document preview is a fixed sample excerpt used to
show how detected PII is masked; the actual redaction runs on the uploaded file.

Run locally:  streamlit run app.py
"""
import html as ihtml
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st

from pii_redactor.models import CATEGORIES
from pii_redactor.webservice import redact_bytes

st.set_page_config(page_title="PII Redaction Tool", page_icon="▮", layout="centered")

CAT_LABEL = {
    "EMAIL": "Email", "PHONE": "Phone", "NAME": "Name", "COMPANY": "Company",
    "ADDRESS": "Address", "SSN": "SSN", "CREDIT_CARD": "Credit card",
    "DOB": "DOB", "IP": "IP",
}

# Fixed sample excerpt (prospectus-style) used only for the live preview.
SAMPLE = [
    ("Our Company Secretary and Compliance Officer is ", None),
    ("Sarthak Malvadkar", "NAME"),
    (". Investor queries may be sent to ", None),
    ("cs.connect@kshinternational.com", "EMAIL"),
    (" or by telephone at ", None),
    ("+91 20 4505 3237", "PHONE"),
    (". The registered office of ", None),
    ("KSH International Limited", "COMPANY"),
    (" is situated at ", None),
    ("11/3, 11/4 and 11/5, Village Birdewadi, Chakan Taluka – Khed, Pune – 410 501", "ADDRESS"),
    (".", None),
]

if "selected" not in st.session_state:
    st.session_state.selected = set(CATEGORIES)


def toggle(cat):
    s = st.session_state.selected
    s.discard(cat) if cat in s else s.add(cat)


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root { --ink:#1A1A1A; --paper:#F4F1E9; --card:#FBFAF4; --rule:#D9D2C2;
        --muted:#6B6459; --stamp:#8B2E2E; --bar:#141414; }
html, body, [class*="css"] { font-family:'Spectral', Georgia, serif; color:var(--ink); }
#MainMenu, header, footer { visibility:hidden; }
.block-container { padding-top:1.4rem; max-width:820px; }

.mono { font-family:'IBM Plex Mono', monospace; }

.banner { display:flex; justify-content:space-between; align-items:center;
  border:1px solid var(--ink); background:var(--card); padding:7px 12px;
  font-family:'IBM Plex Mono',monospace; font-size:.72rem; letter-spacing:.14em;
  text-transform:uppercase; margin-bottom:16px; }
.banner .stamp { color:var(--stamp); border:1.5px solid var(--stamp); padding:1px 7px;
  font-weight:600; letter-spacing:.18em; }

.title { font-size:2.05rem; font-weight:700; letter-spacing:-.01em; margin:0; }
.lead { color:var(--muted); font-size:1.02rem; margin:4px 0 6px; max-width:640px; }

.step { font-family:'IBM Plex Mono',monospace; font-size:.72rem; letter-spacing:.16em;
  text-transform:uppercase; color:var(--muted); border-bottom:1px solid var(--rule);
  padding-bottom:4px; margin:22px 0 10px; }

/* document preview — the signature element */
.preview { position:relative; background:
  repeating-linear-gradient(var(--card), var(--card) 31px, #efeadd 31px, #efeadd 32px);
  border:1px solid var(--rule); border-left:3px solid var(--ink);
  padding:20px 24px; box-shadow:0 8px 24px rgba(26,26,26,.06); }
.preview .cap { position:absolute; top:-10px; left:16px; background:var(--card);
  padding:0 8px; font-family:'IBM Plex Mono',monospace; font-size:.66rem;
  letter-spacing:.16em; text-transform:uppercase; color:var(--muted); }
.preview .doc { font-size:1.06rem; line-height:2.0; margin:6px 0 0; }
.preview .conf { position:absolute; top:16px; right:14px; color:var(--stamp);
  border:2px solid var(--stamp); padding:2px 9px; font-family:'IBM Plex Mono',monospace;
  font-weight:600; letter-spacing:.22em; font-size:.8rem; transform:rotate(-9deg); opacity:.32; }
.bar { background:var(--bar); color:transparent; border-radius:1px; padding:1px 3px;
  user-select:none; -webkit-box-decoration-break:clone; box-decoration-break:clone; }
.pii { font-family:'IBM Plex Mono',monospace; font-size:.9em; background:#efe7d3;
  border-bottom:1.5px dotted var(--stamp); padding:0 2px; }
.legend { font-family:'IBM Plex Mono',monospace; font-size:.72rem; color:var(--muted);
  margin-top:10px; display:flex; gap:18px; }
.legend .sw { display:inline-block; width:26px; height:11px; vertical-align:middle; margin-right:6px; border-radius:1px; }

/* toggles + buttons */
div.stButton > button {
  font-family:'IBM Plex Mono',monospace !important; text-transform:uppercase !important;
  letter-spacing:.08em !important; font-size:.78rem !important; border-radius:2px !important;
  padding:.5rem .4rem !important; }
div.stButton > button[kind="primary"] {
  background:var(--bar) !important; color:#F4F1E9 !important; border:1px solid var(--bar) !important; }
div.stButton > button[kind="secondary"] {
  background:var(--card) !important; color:var(--muted) !important; border:1px solid var(--rule) !important; }
div.stDownloadButton > button {
  font-family:'IBM Plex Mono',monospace !important; text-transform:uppercase !important;
  letter-spacing:.1em !important; font-weight:600 !important; border-radius:2px !important;
  background:var(--bar) !important; color:#F4F1E9 !important; border:1px solid var(--bar) !important;
  padding:.62rem 1rem !important; }
[data-testid="stFileUploaderDropzone"] { border:1.5px dashed var(--ink); border-radius:2px;
  background:var(--card); }

/* redaction report */
.report { border:1px solid var(--ink); background:var(--card); padding:18px 22px; }
.report .rh { font-family:'IBM Plex Mono',monospace; font-size:.72rem; letter-spacing:.18em;
  text-transform:uppercase; color:var(--muted); border-bottom:1px solid var(--rule);
  padding-bottom:6px; margin-bottom:12px; }
.report .total { display:flex; align-items:baseline; gap:10px; margin-bottom:10px; }
.report .total .n { font-size:2.6rem; font-weight:700; }
.report .total .l { font-family:'IBM Plex Mono',monospace; font-size:.74rem; letter-spacing:.14em;
  text-transform:uppercase; color:var(--muted); }
.ledger { font-family:'IBM Plex Mono',monospace; font-size:.9rem; }
.lrow { display:flex; align-items:baseline; gap:8px; padding:3px 0; }
.lrow .lk { color:var(--ink); } .lrow .lv { font-weight:600; }
.lrow .ld { flex:1; border-bottom:1px dotted #b9b2a1; transform:translateY(-4px); }
.note { color:var(--muted); font-size:.9rem; font-style:italic; margin-top:12px; }
</style>
""", unsafe_allow_html=True)

# ---- banner + title ----
st.markdown("""
<div class="banner"><span>PII Redaction · Document Security</span>
<span class="stamp">Confidential</span></div>
""", unsafe_allow_html=True)
st.markdown('<p class="title">PII Redaction</p>', unsafe_allow_html=True)
st.markdown('<p class="lead">Upload a legal or financial document. Detected personal '
            'information — names, emails, phone numbers, companies and addresses — is replaced '
            'with realistic synthetic values before the file goes further.</p>',
            unsafe_allow_html=True)

# ---- step 1: upload ----
st.markdown('<div class="step">01 · Upload document</div>', unsafe_allow_html=True)
uploaded = st.file_uploader("Upload a .docx file", type=["docx"], label_visibility="collapsed")
if uploaded is not None:
    st.markdown(f'<div class="mono" style="font-size:.8rem;color:#6B6459;">▮ {ihtml.escape(uploaded.name)}'
                f' · {uploaded.size/1024:.0f} KB</div>', unsafe_allow_html=True)

# ---- step 2: choose categories (drives the live preview) ----
st.markdown('<div class="step">02 · Select what to redact</div>', unsafe_allow_html=True)
sel = st.session_state.selected
for start in range(0, len(CATEGORIES), 3):
    cols = st.columns(3)
    for col, cat in zip(cols, CATEGORIES[start:start + 3]):
        on = cat in sel
        with col:
            st.button(CAT_LABEL[cat], key=f"t_{cat}",
                      type="primary" if on else "secondary",
                      on_click=toggle, args=(cat,), use_container_width=True)

# ---- live preview ----
parts = ['<div class="preview"><div class="cap">Live preview · sample excerpt</div>',
         '<div class="conf">REDACTED</div><p class="doc">']
for text, cat in SAMPLE:
    esc = ihtml.escape(text)
    if cat is None:
        parts.append(esc)
    elif cat in sel:
        parts.append(f'<span class="bar">{esc}</span>')
    else:
        parts.append(f'<span class="pii">{esc}</span>')
parts.append('</p><div class="legend">'
             '<span><span class="sw" style="background:#141414"></span>redacted</span>'
             '<span><span class="sw" style="background:#efe7d3;border-bottom:1.5px dotted #8B2E2E"></span>detected, kept</span>'
             '</div></div>')
st.markdown("".join(parts), unsafe_allow_html=True)

# ---- step 3: redact ----
st.markdown('<div class="step">03 · Run redaction</div>', unsafe_allow_html=True)
with st.expander("Options"):
    use_spacy = st.checkbox(
        "Use spaCy NER (experimental)", value=False,
        help="Optional secondary model for names/companies/addresses. Requires spaCy and "
             "en_core_web_sm; ignored otherwise. Rule-based detectors are the default.")
    st.caption("The original file is never modified — redaction runs on a copy.")

if st.button("▮  Redact Document", type="primary", use_container_width=True):
    if uploaded is None:
        st.warning("Please upload a .docx file first.")
    elif not sel:
        st.warning("Please select at least one PII category.")
    else:
        with st.spinner("Redacting…"):
            st.session_state["result"] = redact_bytes(
                uploaded.getvalue(), sorted(sel), use_spacy=use_spacy)

# ---- redaction report ----
result = st.session_state.get("result")
if result:
    summary = result["summary"]
    by_cat = summary["by_category"]
    order = ["EMAIL", "PHONE", "NAME", "COMPANY", "ADDRESS"]
    order += [c for c in CATEGORIES if c not in order and by_cat.get(c, 0)]
    rows = "".join(
        f'<div class="lrow"><span class="lk">{CAT_LABEL[c]}</span>'
        f'<span class="ld"></span><span class="lv">{by_cat.get(c, 0)}</span></div>'
        for c in order)
    st.markdown(
        f'<div class="report"><div class="rh">Redaction report</div>'
        f'<div class="total"><span class="n">{summary["total_redactions"]}</span>'
        f'<span class="l">items redacted</span></div>'
        f'<div class="ledger">{rows}</div></div>', unsafe_allow_html=True)

    st.write("")
    st.download_button(
        "Download Redacted DOCX", data=result["redacted_bytes"], file_name="redacted.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True)
    st.download_button(
        "Download Audit Log", data=result["audit_bytes"], file_name="audit_log.jsonl",
        mime="application/json", use_container_width=True)
    st.markdown('<div class="note">The original document is not modified — redaction runs on a '
                'copy. The audit log records hashed identifiers and the synthetic values, not the '
                'original PII.</div>', unsafe_allow_html=True)

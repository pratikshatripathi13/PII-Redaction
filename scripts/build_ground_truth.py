"""Build gold_spans.jsonl from a MANUAL, detector-independent annotation.

Methodology (see README / evaluation report):
  * Evaluation scope = a stratified sample of 70 text units: PII-dense units
    (contact/identity blocks, promoter/director tables, registered-office lines)
    plus a seeded random sample of prose units for false-positive estimation.
  * Within each scored unit EVERY true PII span is annotated below by reading the
    actual text — NOT by copying detector output. This deliberately includes
    entities the detector is expected to miss (e.g. the CEO named only in prose,
    firms without a legal suffix, Corporation-suffixed customers, address
    fragments), so recall is measured honestly.
  * Offsets are computed mechanically from the annotated substrings, so the gold
    file stores category + offsets only — no raw PII values are committed.

Categories present in this document: EMAIL, PHONE, NAME, COMPANY, ADDRESS.
(SSN, CREDIT_CARD, IP, DOB do not occur — reported as 0-support, never fabricated.)
"""
from __future__ import annotations

import json
import sys

from pii_redactor.document.loader import DocxDocument

# (category, exact substring) annotations per unit id.
GOLD: dict[str, list[tuple[str, str]]] = {
    # ---- registered office / issuer contact ----
    "body-135": [("ADDRESS", "11/3, 11/4 and 11/5, Village Birdewadi, Chakan Taluka - Khed, Pune – 410 501")],
    "body-138": [("EMAIL", "cs.connect@kshinternational.com")],
    "cell-25":  [("EMAIL", "cs.connect@kshinternational.com"), ("PHONE", "+ 91 20 45053237")],
    "cell-324": [("ADDRESS", "11/3, 11/4 and 11/5, Village Birdewadi, Chakan Taluka-Khed, Pune – 410 501")],
    "cell-356": [("ADDRESS", "Plot No. 5, Chakan Industrial Area, Phase II, Village Khalumbre, Taluka Khed, Pune – 410 501")],
    # ---- prose FP-check units (no PII) ----
    "body-221": [], "body-1194": [], "body-1672": [], "body-1956": [], "body-2199": [],
    "body-2208": [], "body-3108": [], "body-3423": [], "body-3448": [], "body-3625": [],
    "body-3877": [], "cell-284": [], "cell-311": [], "cell-366": [], "cell-377": [],
    "cell-384": [], "cell-460": [], "cell-515": [], "cell-670": [], "cell-751": [],
    "body-4179": [], "body-4210": [], "body-4216": [], "body-4225": [],
    "cell-4037": [], "cell-4058": [],
    # ---- customers (company names; several lack a legal suffix -> expected misses) ----
    "body-2377": [
        ("COMPANY", "Al-Ahleia Switchgear Co."),
        ("COMPANY", "Bharat Bijlee Limited"),
        ("COMPANY", "CG Power and Industrial Solutions Limited"),
        ("COMPANY", "Emirates Transformer & Switchgear Limited"),
        ("COMPANY", "Georgia Transformer Corporation"),
        ("COMPANY", "Nidec Industrial Automation India Private Limited"),
        ("COMPANY", "Transformers & Rectifiers (India) Limited"),
        ("COMPANY", "Virginia Transformer Corporation"),
    ],
    # ---- corporate office / BRLM / registrar / bankers ----
    "body-4012": [("ADDRESS", "Pune 411 045")],
    "body-4085": [("COMPANY", "ICICI Securities Limited"),
                  ("ADDRESS", "ICICI Venture House Appasaheb Marathe Marg Prabhadevi, Mumbai – 400 025")],
    "body-4086": [("PHONE", "+91 22 6807 7100"), ("EMAIL", "ksh@icicisecurities.com"),
                  ("EMAIL", "customercare@icicisecurities.com")],
    "body-4181": [("COMPANY", "ICICI Securities Limited"),
                  ("ADDRESS", "ICICI Venture House Appasaheb Marathe Marg Prabhadevi, Mumbai – 400 025")],
    "body-4193": [("PHONE", "+91 22 4079 1000")],
    "body-4197": [("ADDRESS", "1st Floor, L B S Marg, Vikhroli (West) Mumbai 400083"),
                  ("PHONE", "+91 81081 14949")],
    "body-4198": [("EMAIL", "kshinternational.ipo@in.mpms.mufg.com")],
    "body-4200": [("NAME", "Shanti Gopalkrishnan")],
    "body-4205": [("ADDRESS", "Next to Kanjurmarg Railway Station, Kanjurmarg (East) Mumbai – 400042")],
    "body-4206": [("PHONE", "+91 22 30752929"), ("PHONE", "+91 22 30752928"), ("PHONE", "+91 22 30752914")],
    "body-4207": [("EMAIL", "siddharth.jadhav@hdfcbank.com"), ("EMAIL", "sachin.gawade@hdfcbank.com"),
                  ("EMAIL", "eric.bacha@hdfcbank.com"), ("EMAIL", "tushar.gavankar@hdfcbank.com"),
                  ("EMAIL", "pravin.teli2@hdfcbank.com")],
    "body-4222": [("PHONE", "+91 22 30752929"), ("PHONE", "+91 22 30752928"), ("PHONE", "+91 22 30752914")],
    "body-4231": [("ADDRESS", "163, 5th Floor, H.T.Parekh Marg Backbay Reclamation Churchgate, Mumbai – 400020"),
                  ("PHONE", "022-68052182"), ("EMAIL", "Ipocmg@icicibank.com"), ("NAME", "Varun Badai")],
    "body-4267": [("ADDRESS", "Pune – 411 038")],
    "body-4329": [("ADDRESS", "Pune – 411 001")],
    "body-4332": [("EMAIL", "manisha.shukla@hdfcbank.com")],
    "body-4336": [("ADDRESS", "Pune – 411 003")],
    "body-4338": [("PHONE", "+91 20 2561 8211"), ("NAME", "Tushar Wakhele")],
    "body-4339": [("EMAIL", "rm6.ifbpune@sbi.co.in")],
    "body-4352": [("PHONE", "+91 20 7157 6403"), ("NAME", "Anand Soni"),
                  ("EMAIL", "anand.soni@bajajfinserv.in")],
    "cell-112": [("PHONE", "+91 81081 14949")],
    "cell-113": [("EMAIL", "kshinternational.ipo@in.mpms.mufg.com")],
    "cell-170": [("EMAIL", "ksh.ipo@nuvama.com")],
    "cell-172": [("EMAIL", "customerservice.mb@nuvama.com")],
    "cell-186": [("PHONE", "+91 81081 14949")],
    "cell-187": [("EMAIL", "kshinternational.ipo@in.mpms.mufg.com")],
    "cell-4284": [("PHONE", "+ 91 20 6729 5100")],
    # ---- KMP / promoters / group entities ----
    "cell-253": [("NAME", "Sandesh Bhagwat")],
    "cell-316": [("NAME", "Kushal Subbayya Hegde"), ("NAME", "Pushpa Kushal Hegde"),
                 ("NAME", "Rajesh Kushal Hegde"), ("NAME", "Rohit Kushal Hegde")],
    "cell-281": [("COMPANY", "Waterloo Motors Private Limited"),
                 ("COMPANY", "KSH Project Management Services Private Limited"),
                 ("COMPANY", "KSH Infra Park 5 Private Limited"),
                 ("COMPANY", "KSH Infra Park VI Private Limited"),
                 ("COMPANY", "KSH Distriparks Private Limited"),
                 ("COMPANY", "KSH Integrated Logistics Private Limited"),
                 ("COMPANY", "Kushal Motors and Electricals Private Limited"),
                 ("COMPANY", "Waterloo Industrial Park I Private Limited"),
                 ("COMPANY", "Waterloo Industrial Park II Private Limited"),
                 ("COMPANY", "Waterloo Industrial Park III Private Limited"),
                 ("COMPANY", "Waterloo Industrial Park IV Private Limited"),
                 ("COMPANY", "Waterloo Industrial Park V Private Limited"),
                 ("COMPANY", "Waterloo Industrial Park VI Private Limited"),
                 ("COMPANY", "Waterloo Industrial Park VIII Private Limited"),
                 ("COMPANY", "Waterloo Industrial Park IX Private Limited"),
                 ("COMPANY", "Waterloo Industrial Park IX B Private Limited")],
    "cell-650": [("COMPANY", "Nuvama Wealth Management Limited"),
                 ("COMPANY", "ICICI Securities Limited")],
    "cell-3027": [("NAME", "Kushal Hegde"),
                  ("COMPANY", "Shubhkamal Leasing and Investment Private Limited")],
    # ---- director residential addresses ----
    "cell-4043": [("ADDRESS", "3 Prabhat Road, opposite PYC basketball court, Erandawane, Deccan Gymkhana, Pune – 411 004")],
    "cell-4047": [("ADDRESS", "Pratik Bunglow, Senapati Bapat Road, behind Sahara Hotel, Shivajinagar, Model Colony, Pune – 411 016")],
    "cell-4051": [("ADDRESS", "602, Gopalkrupa Apartment, Bhonde colony, Prabhat Road, Erandawane, Pune – 411 004")],
    "cell-4055": [("ADDRESS", "A-259, JK Road, Minal Residency, Huzur, Govindpura, Bhopal – 462 023")],
    "cell-4059": [("ADDRESS", "A29, Abhimanshree Society, Pashan Road, Pune – 411 008")],
    "cell-4289": [("COMPANY", "Hingne Tare & Associates"),
                  ("ADDRESS", "Flat No. 102, Sai Complex Shaniwar Peth, Pune – 411 030")],
}


def main():
    doc = DocxDocument("Red Herring Prospectus (1).docx")
    texts = {u.unit_id: u.text for u in doc.units()}
    out, problems = [], []
    for uid, anns in GOLD.items():
        text = texts.get(uid)
        if text is None:
            problems.append(f"UNIT NOT FOUND: {uid}")
            continue
        used = []  # (start,end) already claimed, to place repeated substrings correctly
        for cat, sub in anns:
            start = -1
            search_from = 0
            while True:
                idx = text.find(sub, search_from)
                if idx == -1:
                    break
                if all(not (idx < e and s < idx + len(sub)) for s, e in used):
                    start = idx
                    break
                search_from = idx + 1
            if start == -1:
                problems.append(f"SUBSTRING NOT FOUND in {uid} [{cat}]: {sub!r}")
                continue
            end = start + len(sub)
            used.append((start, end))
            out.append({"unit_id": uid, "start": start, "end": end, "category": cat})

    if problems:
        print("ANNOTATION PROBLEMS:", file=sys.stderr)
        for p in problems:
            print("  ", p, file=sys.stderr)

    with open("ground_truth/gold_spans.jsonl", "w", encoding="utf-8") as f:
        f.write("# gold spans: category + offsets only (no raw PII). See build_ground_truth.py\n")
        for row in out:
            f.write(json.dumps(row) + "\n")
    # Scope = every annotated unit (including zero-PII prose units), so that
    # false positives in prose are counted during scoring.
    with open("ground_truth/scope.json", "w", encoding="utf-8") as f:
        json.dump(sorted(GOLD.keys()), f, indent=1)
    print(f"units annotated: {len(GOLD)} | gold spans: {len(out)} | problems: {len(problems)}")


if __name__ == "__main__":
    main()

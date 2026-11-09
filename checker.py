import re
from database import get_db

CLAIM_PATTERNS = {
    "CLAIM-01": [r"\bno\.?\s*1\b", r"\bnumber\s+(?:one|1)\b", r"#\s*1\b",
                 r"\bbest\b", r"\bleading\b", r"\btop[- ]rated\b"],
    "CLAIM-02": [r"\bguarantee[ds]?\b", r"\b100\s*%", r"\balways\b",
                 r"\bnever fails?\b", r"\brisk[- ]free\b"],
    "CLAIM-03": [r"\bcures?\b", r"\bheals?\b", r"\bboosts?\s+immunity\b",
                 r"\bhealthy for everyone\b", r"\bmedically\b"],
}

CLAIM_EXPLAIN = {
    "CLAIM-01": "This ranking claim is not supported by any entry in the approved evidence ledger.",
    "CLAIM-02": "Absolute guarantees and promises like this cannot be supported and are not allowed.",
    "CLAIM-03": "Health or medical claims are not allowed in brand content.",
}

CLAIM_FIX = {
    "CLAIM-01": "Remove the ranking claim or use a verified strength, e.g. 'Over 40 cafes across 6 cities'.",
    "CLAIM-02": "Replace it with a promise you can support, e.g. 'We work hard to make every visit enjoyable'.",
    "CLAIM-03": "Remove the health claim and describe taste or ingredients instead.",
}

FACT_PATTERNS = {
    "founding year": r"(?:founded|established|started|since)(?:\s+in)?\s+(\d{4})",
    "cafes": r"(\d+)\+?\s*(?:cafes|cafés|outlets|stores)",
    "cities": r"(\d+)\s*cities",
    "price": r"Cold Brew Classic[^.\n]*?(?:Rs\.?|₹|INR)\s*(\d+)",
}


def run_rule_checks(text):
    conn = get_db()
    rules = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM rules")}
    terms = [dict(r) for r in conn.execute("SELECT * FROM terminology")]
    facts = [dict(r) for r in conn.execute("SELECT * FROM approved_facts")]
    ledger = [dict(r) for r in conn.execute("SELECT * FROM evidence_ledger")]
    conn.close()

    findings = []

    def add(rule_id, start, end, explanation, fix):
        rule = rules.get(rule_id, {})
        findings.append({
            "rule_id": rule_id,
            "origin": "rule",
            "flagged_text": text[start:end],
            "start": start,
            "end": end,
            "explanation": explanation,
            "severity": rule.get("severity", "major"),
            "confidence": 1.0,
            "suggested_fix": fix,
        })

    # 1. Terminology (banned terms)
    taken = []
    for t in sorted(terms, key=lambda x: -len(x["banned"])):
        same = t["banned"].lower() == t["preferred"].lower()
        flags = 0 if same else re.IGNORECASE
        for m in re.finditer(r"\b" + re.escape(t["banned"]) + r"\b", text, flags):
            if any(m.start() < te and m.end() > ts for ts, te in taken):
                continue
            taken.append((m.start(), m.end()))
            pref = t["preferred"]
            if m.group()[0].isupper() and pref[0].islower():
                pref = pref[0].upper() + pref[1:]
            add(t["rule_id"], m.start(), m.end(),
                f'"{m.group()}" is not an approved term. Use "{pref}" instead.', pref)

    # 2. Unsupported claims
    for rule_id, patterns in CLAIM_PATTERNS.items():
        for p in patterns:
            for m in re.finditer(p, text, re.IGNORECASE):
                add(rule_id, m.start(), m.end(),
                    CLAIM_EXPLAIN[rule_id], CLAIM_FIX[rule_id])

    # 3. Tone: shouting
    for m in re.finditer(r"\b[A-Z]{4,}\b", text):
        add("TONE-02", m.start(), m.end(),
            "ALL CAPS reads as shouting and does not match our friendly voice.",
            m.group().capitalize())
    for m in re.finditer(r"!{2,}", text):
        add("TONE-02", m.start(), m.end(),
            "Repeated exclamation marks feel pushy. Use one at most.", "!")

    # 4. Facts: figures must match approved facts
    ledger_spans = []
    for l in ledger:
        for m in re.finditer(re.escape(l["claim"]), text, re.IGNORECASE):
            ledger_spans.append((m.start(), m.end()))
    for f in facts:
        pattern = FACT_PATTERNS.get(f["topic"])
        num = re.search(r"\d+", f["fact"])
        if not pattern or not num:
            continue
        expected = int(num.group())
        for m in re.finditer(pattern, text, re.IGNORECASE):
            if int(m.group(1)) == expected:
                continue
            if any(ls <= m.start() and m.end() <= le for ls, le in ledger_spans):
                continue
            add("FACT-01", m.start(), m.end(),
                f'The text says "{m.group()}", but the approved fact is: '
                f'"{f["fact"]}" (Source: {f["source"]}).',
                f'Use the approved figure: {f["fact"]}')

    # 5. Readability: long sentences
    for m in re.finditer(r"[^.!?\n]+[.!?]?", text):
        sentence = m.group()
        if len(sentence.split()) > 30:
            add("READ-01", m.start(), m.end(),
                f"This sentence has {len(sentence.split())} words. Keep sentences under 30 words.",
                "Split it into two shorter sentences.")

    findings.sort(key=lambda x: x["start"])
    return findings


if __name__ == "__main__":
    sample = ("Nova Brew is India's No. 1 coffee shop! We GUARANTEE 100% happy customers. "
              "We have 60 cafes in 8 cities, founded in 2015. "
              "Our Cold Brew Classic is only Rs 149 and cures tiredness.")
    for f in run_rule_checks(sample):
        print(f"[{f['severity']}] {f['rule_id']}: {f['flagged_text']!r} -> {f['suggested_fix']}")
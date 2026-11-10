import hashlib
import json
from database import get_db
from checker import run_rule_checks
from ai import ask_ai, mask_sensitive, MODEL

CACHE_VERSION = "v2"  # changing this ignores old cached AI answers

SYSTEM = """You are a brand-governance reviewer. Use ONLY the rules provided.
Reply ONLY with JSON in this shape:
{"findings":[{"rule_id":"...","flagged_text":"...","explanation":"...","suggested_fix":"..."}],"rewrite":"..."}
Rules for your answer:
- Report a finding ONLY for a clear violation of one of the provided rules (mainly tone). Do not give style advice.
- If the content already follows the rules, return an empty findings list.
- rule_id must be one of the provided rule IDs. flagged_text must be copied EXACTLY from the content.
- Do not repeat anything in "already_found".
- explanation: one or two simple sentences saying why, naming the rule.
- suggested_fix: replacement wording that keeps the creator's intent.
- rewrite: the full content rewritten to fix ALL issues (including already_found) while keeping the creator's purpose.
  The rewrite must NOT contain: ranking or superlative claims (No. 1, best, leading, ultimate), guarantees or absolutes
  (guaranteed, 100%, always, never), health claims, ALL CAPS words, more than one exclamation mark, pushy or
  fear-based pressure (buy now or regret), or any banned term. Use the preferred terms from banned_terms.
  Never invent facts or numbers; use only approved_facts. Keep sentences under 30 words."""

REPAIR = """You fix a brand rewrite. Reply ONLY with JSON: {"rewrite":"..."}
Rewrite the text so that it no longer has any of the listed problems, keeps the same purpose, uses only the
approved_facts for any numbers, and follows the provided rules. Use preferred terms from banned_terms."""


def content_hash(body):
    return hashlib.sha256((CACHE_VERSION + "|" + mask_sensitive(body)).encode("utf-8")).hexdigest()


def get_cached(body):
    conn = get_db()
    row = conn.execute("SELECT response FROM ai_cache_log WHERE content_hash = ?",
                       (content_hash(body),)).fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row["response"])
        except ValueError:
            return None
    return None


def _call(system, payload):
    last_error = None
    for _ in range(2):  # one retry
        try:
            data = json.loads(ask_ai(system, json.dumps(payload, ensure_ascii=False)))
            if isinstance(data, dict):
                return data
            raise ValueError("AI reply was not a JSON object")
        except Exception as e:
            last_error = e
    print("AI review failed:", last_error)
    return None


def verify_rewrite(rewrite, context):
    """Only show a rewrite that passes our own rule engine (repair it up to 2 times)."""
    if not rewrite.strip():
        return ""
    for _ in range(2):
        problems = run_rule_checks(rewrite)
        if not problems:
            return rewrite
        payload = dict(context)
        payload["rewrite"] = rewrite
        payload["problems"] = [{"rule_id": p["rule_id"], "flagged_text": p["flagged_text"],
                                "explanation": p["explanation"]} for p in problems]
        fixed = _call(REPAIR, payload)
        if not fixed or not str(fixed.get("rewrite") or "").strip():
            return ""
        rewrite = str(fixed["rewrite"])
    return rewrite if not run_rule_checks(rewrite) else ""


def run_ai_review(body, rule_findings):
    """Returns {"findings": [...], "rewrite": "..."} or None if the AI is unavailable."""
    cached = get_cached(body)
    if cached is not None:
        return cached
    conn = get_db()
    rules = [dict(r) for r in conn.execute("SELECT id, title, text FROM rules")]
    facts = [r["fact"] for r in conn.execute("SELECT fact FROM approved_facts")]
    terms = [dict(r) for r in conn.execute("SELECT banned, preferred FROM terminology")]
    conn.close()
    already = [{"rule_id": f["rule_id"], "flagged_text": f["flagged_text"]} for f in rule_findings]
    context = {"rules": rules, "approved_facts": facts, "banned_terms": terms}
    payload = dict(context)
    payload["content"] = mask_sensitive(body)
    payload["already_found"] = already
    data = _call(SYSTEM, payload)
    if data is None:
        return None
    data.setdefault("findings", [])
    data["rewrite"] = verify_rewrite(str(data.get("rewrite") or ""), context)
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO ai_cache_log (content_hash, response, provider) VALUES (?,?,?)",
        (content_hash(body), json.dumps(data), "groq:" + MODEL))
    conn.commit()
    conn.close()
    return data


def clean_findings(data, body, rules, existing_texts):
    """Keep only AI findings that cite a real rule and quote the text exactly."""
    out = []
    seen = set(existing_texts)
    for f in (data.get("findings") or [])[:6]:
        if not isinstance(f, dict):
            continue
        rule_id = f.get("rule_id")
        text = f.get("flagged_text") or ""
        if rule_id not in rules or not text or text not in body:
            continue
        if any(text in s or s in text for s in seen):
            continue
        seen.add(text)
        out.append({
            "rule_id": rule_id,
            "origin": "ai",
            "flagged_text": text,
            "explanation": str(f.get("explanation") or "Flagged by AI review.")[:400],
            "severity": rules[rule_id],
            "confidence": 0.7,
            "suggested_fix": str(f.get("suggested_fix") or "")[:400],
        })
    return out
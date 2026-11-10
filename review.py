from database import get_db
from checker import run_rule_checks
from ai_review import run_ai_review, clean_findings


def carry_over(conn, prev_version_id, new_findings):
    """Keep Ignore / Ask-a-reviewer decisions when the same issue is still in the new version."""
    old = conn.execute(
        "SELECT f.rule_id, f.flagged_text, d.user_id, d.action, d.reason "
        "FROM findings f JOIN decisions d ON d.finding_id = f.id "
        "WHERE f.version_id = ? AND d.action IN ('ignore','verify')",
        (prev_version_id,)).fetchall()
    for new_id, f in new_findings:
        for o in old:
            if o["rule_id"] == f["rule_id"] and o["flagged_text"] == f["flagged_text"]:
                conn.execute(
                    "INSERT INTO decisions (finding_id, user_id, action, reason) VALUES (?,?,?,?)",
                    (new_id, o["user_id"], o["action"], o["reason"]))
                break


def save_findings(item_id, version_id, body, prev_version_id=None):
    findings = run_rule_checks(body)
    ai_data = run_ai_review(body, findings)  # None if the AI is unavailable
    conn = get_db()
    if ai_data:
        rules = {r["id"]: r["severity"] for r in conn.execute("SELECT id, severity FROM rules")}
        findings = findings + clean_findings(ai_data, body, rules,
                                             [f["flagged_text"] for f in findings])
    new_findings = []
    for f in findings:
        cur = conn.execute(
            "INSERT INTO findings (item_id, version_id, rule_id, origin, flagged_text, "
            "explanation, severity, confidence, suggested_fix) VALUES (?,?,?,?,?,?,?,?,?)",
            (item_id, version_id, f["rule_id"], f["origin"], f["flagged_text"],
             f["explanation"], f["severity"], f["confidence"], f["suggested_fix"]))
        new_findings.append((cur.lastrowid, f))
    if prev_version_id:
        carry_over(conn, prev_version_id, new_findings)
    conn.commit()
    conn.close()
    return len(findings)


def create_submission(creator_id, title, content_type, body):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO content_items (title, content_type, creator_id, status) VALUES (?,?,?,?)",
        (title, content_type, creator_id, "In Review"))
    item_id = cur.lastrowid
    cur = conn.execute(
        "INSERT INTO content_versions (item_id, version_no, body, changed_by) VALUES (?,?,?,?)",
        (item_id, 1, body, creator_id))
    version_id = cur.lastrowid
    conn.commit()
    conn.close()
    save_findings(item_id, version_id, body)
    return item_id


def add_version(item_id, user_id, body):
    conn = get_db()
    prev = conn.execute(
        "SELECT id, version_no FROM content_versions WHERE item_id = ? "
        "ORDER BY version_no DESC LIMIT 1", (item_id,)).fetchone()
    cur = conn.execute(
        "INSERT INTO content_versions (item_id, version_no, body, changed_by) VALUES (?,?,?,?)",
        (item_id, prev["version_no"] + 1, body, user_id))
    version_id = cur.lastrowid
    conn.execute("UPDATE content_items SET status = 'In Review' WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    save_findings(item_id, version_id, body, prev_version_id=prev["id"])
    return prev["version_no"] + 1
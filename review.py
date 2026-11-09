from database import get_db
from checker import run_rule_checks


def save_findings(item_id, version_id, body):
    findings = run_rule_checks(body)
    conn = get_db()
    for f in findings:
        conn.execute(
            "INSERT INTO findings (item_id, version_id, rule_id, origin, flagged_text, "
            "explanation, severity, confidence, suggested_fix) VALUES (?,?,?,?,?,?,?,?,?)",
            (item_id, version_id, f["rule_id"], f["origin"], f["flagged_text"],
             f["explanation"], f["severity"], f["confidence"], f["suggested_fix"]))
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
    last = conn.execute(
        "SELECT MAX(version_no) AS n FROM content_versions WHERE item_id = ?",
        (item_id,)).fetchone()["n"] or 0
    cur = conn.execute(
        "INSERT INTO content_versions (item_id, version_no, body, changed_by) VALUES (?,?,?,?)",
        (item_id, last + 1, body, user_id))
    version_id = cur.lastrowid
    conn.execute("UPDATE content_items SET status = 'In Review' WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    save_findings(item_id, version_id, body)
    return last + 1
from werkzeug.security import generate_password_hash
from database import get_db, init_db

# Sample data for a FICTIONAL company, used only for demo and testing.

USERS = [
    ("Demo Creator", "creator@demo.com", "demo123", "creator"),
    ("Demo Reviewer", "reviewer@demo.com", "demo123", "reviewer"),
    ("Demo Manager", "manager@demo.com", "demo123", "manager"),
    ("Demo Admin", "admin@demo.com", "demo123", "admin"),
]

# (id, category, title, text, severity)
RULES = [
    ("TONE-01", "Tone", "Friendly and professional voice",
     "Write in a warm, respectful voice. Avoid pushy, aggressive or fear-based language.", "major"),
    ("TONE-02", "Tone", "No shouting or excessive punctuation",
     "Do not use ALL CAPS words or more than one exclamation mark in a row.", "minor"),
    ("CLAIM-01", "Claims", "No unsupported ranking claims",
     "Do not claim to be No. 1, the best, the leading or the top brand unless the claim is listed in the approved evidence ledger.", "critical"),
    ("CLAIM-02", "Claims", "No absolute guarantees",
     "Do not promise guarantees or absolutes such as 'guaranteed', '100%', 'always' or 'never fails'.", "critical"),
    ("CLAIM-03", "Claims", "No health claims",
     "Do not make health or medical claims such as 'cures', 'boosts immunity' or 'healthy for everyone'.", "critical"),
    ("TERM-01", "Terminology", "Use approved brand and product names",
     "Always write NovaBrew as one word and use approved product names.", "major"),
    ("TERM-02", "Terminology", "Use approved brand vocabulary",
     "Use brand vocabulary such as 'guests' instead of 'customers' and 'cafe' instead of 'coffee shop'.", "minor"),
    ("FACT-01", "Facts", "Figures must match approved facts",
     "Numbers such as founding year, number of cafes, cities and prices must match the approved facts.", "major"),
    ("READ-01", "Accessibility", "Keep sentences easy to read",
     "Keep sentences under 30 words so content is easy to read for everyone.", "minor"),
]

# (topic, fact, source)
FACTS = [
    ("founding year", "NovaBrew was founded in 2018.", "Company Fact Sheet 2026"),
    ("cafes", "NovaBrew has 45 cafes.", "Company Fact Sheet 2026"),
    ("cities", "NovaBrew operates in 6 cities.", "Company Fact Sheet 2026"),
    ("price", "Cold Brew Classic costs Rs 199.", "Price List Oct 2026"),
    ("sourcing", "Beans are sourced from Coorg and Chikmagalur.", "Sourcing Policy 2026"),
]

# (banned, preferred, rule_id)
TERMS = [
    ("Nova Brew", "NovaBrew", "TERM-01"),
    ("novabrew", "NovaBrew", "TERM-01"),
    ("NovaBrew Express", "NovaBrew Go", "TERM-01"),
    ("customers", "guests", "TERM-02"),
    ("customer", "guest", "TERM-02"),
    ("coffee shop", "cafe", "TERM-02"),
    ("cheap", "affordable", "TERM-02"),
]

# (claim, source)
EVIDENCE = [
    ("Over 40 cafes across 6 cities", "Company Fact Sheet 2026"),
    ("Rated 4.4 out of 5 by guests", "Guest Survey 2026"),
]


def seed():
    init_db()
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0] > 0:
        conn.close()
        print("Already seeded. Nothing changed.")
        return
    for name, email, pw, role in USERS:
        conn.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
            (name, email, generate_password_hash(pw), role))
    conn.executemany(
        "INSERT INTO rules (id, category, title, text, severity) VALUES (?,?,?,?,?)", RULES)
    conn.executemany(
        "INSERT INTO approved_facts (topic, fact, source) VALUES (?,?,?)", FACTS)
    conn.executemany(
        "INSERT INTO terminology (banned, preferred, rule_id) VALUES (?,?,?)", TERMS)
    conn.executemany(
        "INSERT INTO evidence_ledger (claim, source) VALUES (?,?)", EVIDENCE)
    conn.commit()
    print("Seeded:",
          conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], "users,",
          conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0], "rules,",
          conn.execute("SELECT COUNT(*) FROM approved_facts").fetchone()[0], "facts,",
          conn.execute("SELECT COUNT(*) FROM terminology").fetchone()[0], "terms,",
          conn.execute("SELECT COUNT(*) FROM evidence_ledger").fetchone()[0], "evidence")
    conn.close()

def seed_samples():
    """3 sample items so the demo is never empty. Hand-written, no AI calls."""
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM content_items").fetchone()[0] > 0:
        conn.close()
        return
    uid = {r["role"]: r["id"] for r in conn.execute("SELECT id, role FROM users")}
    creator, reviewer, manager = uid["creator"], uid["reviewer"], uid["manager"]

    def make_item(title, status, bodies):
        cur = conn.execute(
            "INSERT INTO content_items (title, content_type, creator_id, status) VALUES (?,?,?,?)",
            (title, "Social media post", creator, status))
        item_id = cur.lastrowid
        vids = []
        for n, body in enumerate(bodies, 1):
            c = conn.execute(
                "INSERT INTO content_versions (item_id, version_no, body, changed_by) VALUES (?,?,?,?)",
                (item_id, n, body, creator))
            vids.append(c.lastrowid)
        return item_id, vids

    def add_finding(item_id, vid, rule_id, text, why, sev, fix, action=None, reason=""):
        c = conn.execute(
            "INSERT INTO findings (item_id, version_id, rule_id, origin, flagged_text, "
            "explanation, severity, suggested_fix) VALUES (?,?,?,?,?,?,?,?)",
            (item_id, vid, rule_id, "rule", text, why, sev, fix))
        if action:
            conn.execute(
                "INSERT INTO decisions (finding_id, user_id, action, reason) VALUES (?,?,?,?)",
                (c.lastrowid, creator, action, reason))

    def add_approval(item_id, user, decision, note):
        conn.execute(
            "INSERT INTO approvals (item_id, user_id, decision, note) VALUES (?,?,?,?)",
            (item_id, user, decision, note))

    # 1) APPROVED: fixed in version 2
    i1, v1 = make_item("[Sample] Cold Brew launch post", "Approved", [
        "Try the best coffee in India. Our customers love Cold Brew Classic.",
        "Try our Cold Brew Classic at Rs 199. Our guests love it."])
    add_finding(i1, v1[0], "CLAIM-01", "the best coffee in India",
                "Ranking claim is not in the approved evidence ledger.", "critical",
                "Remove the ranking claim.", "accept")
    add_finding(i1, v1[0], "TERM-02", "customers",
                "Brand vocabulary says to use 'guests'.", "minor",
                "Use 'guests'.", "accept")
    add_approval(i1, creator, "submitted", "Version 2 submitted.")
    add_approval(i1, manager, "approve", "Clean and factual. Approved.")

    # 2) PENDING REVIEW: waiting for the reviewer
    i2, v2 = make_item("[Sample] Wellness cold brew promo", "Pending Review", [
        "Boost your day with NovaBrew! Our cold brew boosts immunity and is healthy for everyone!!"])
    add_finding(i2, v2[0], "CLAIM-03", "boosts immunity",
                "Health claims are not allowed.", "critical",
                "Remove the health claim.", "verify",
                "Our nutrition partner says this is true. Please check.")
    add_finding(i2, v2[0], "TONE-02", "!!",
                "Avoid more than one exclamation mark in a row.", "minor",
                "Use a single '!'.", "ignore", "Small style issue for a festival post.")
    add_approval(i2, creator, "submitted", "Version 1 submitted.")

    # 3) CHANGES REQUESTED: reviewer said must fix
    i3, v3 = make_item("[Sample] Expansion announcement", "Changes Requested", [
        "NovaBrew has 60 cafes in 8 cities. We are guaranteed to be your favourite."])
    add_finding(i3, v3[0], "FACT-01", "60 cafes",
                "Approved facts say NovaBrew has 45 cafes.", "major",
                "Use 45 cafes.", "accept")
    add_finding(i3, v3[0], "CLAIM-02", "guaranteed",
                "Absolute guarantees are not allowed.", "critical",
                "Remove 'guaranteed'.", "verify",
                "We want a strong promise in this post.")
    conn.execute(
        "INSERT INTO reviewer_decisions (item_id, rule_id, flagged_text, reviewer_id, outcome, note) "
        "VALUES (?,?,?,?,?,?)",
        (i3, "CLAIM-02", "guaranteed", reviewer, "must_fix",
         "We cannot promise this. Please reword."))
    add_approval(i3, creator, "submitted", "Version 1 submitted.")
    add_approval(i3, reviewer, "sent_back",
                 "Some findings must be fixed. See the notes on each finding.")

    conn.commit()
    conn.close()
    print("Sample items added.")


_seed_base = seed


def seed():
    _seed_base()
    seed_samples()

if __name__ == "__main__":
    seed()
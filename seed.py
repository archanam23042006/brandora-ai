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


if __name__ == "__main__":
    seed()
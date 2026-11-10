# brandora-ai

**No content gets published without a Brand Passport.**

Brandora AI is a pre-publication brand-governance platform. Content is checked against approved guidelines, facts and terminology stored in a database. Every issue shows the reason, rule ID, severity and a suggested fix. Humans make the decisions (creator, reviewer, manager). AI only gives advice.

Team NEXAURA | CodeTitans India 2026 | Problem by Inkloom AI

**Live demo:** https://brandora-ai-ccmc.onrender.com
(Free tier: the first load after idle can take 30 to 60 seconds.)

## Demo login (no sign-in needed)
On the login page, click one of the 4 demo buttons: Creator, Reviewer, Manager, Admin.

## Workflow
1. Creator submits content (title, type, text). Version 1 is saved and checked.
2. Findings come from our rule engine and from one AI review. Each has a rule ID, severity, reason and suggested fix.
3. Creator decides on each finding: Accept, Ignore (with reason, not allowed for critical), or Ask a reviewer for an exception.
4. Optional: AI-assisted rewrite (creator only). The rewrite is checked by our own rule engine before it is shown.
5. Creator revises (new version, re-checked) and submits for approval. Submit is blocked while findings are still open.
6. Reviewer decides on exception requests: Must fix or Approve exception.
7. Manager approves, requests changes, or rejects (notes required for the last two).
8. **Brand Passport** page for each item: versions, findings, decisions, reviewer notes, approvals, AI-use disclosure and final status. It can be printed.
9. **Brand Memory (Insights)** page for reviewer, manager and admin: most flagged rules, most ignored or escalated rules (possible unclear guidelines), reviewer outcomes.

## Completed features (Round 2)
1. Login with hashed passwords, 4 roles (Creator, Reviewer, Manager, Admin) and one-click demo accounts
2. Brand Vault seed data for fictional NovaBrew: 9 numbered rules, approved facts, terminology, evidence entries
3. Text submission with Version 1 saved and a new version on every revision
4. Rule engine: banned terms, risky claims, ALL CAPS, repeated "!", fact and number mismatches, long sentences
5. AI review (Groq) for tone, explanation and suggested fix. AI findings are kept only if they cite a real rule and quote the text exactly.
6. AI-assisted rewrite (creator only), checked by our rule engine before it is shown
7. Email and phone masking, AI cache by content hash, rule-based fallback if AI fails
8. Findings screen with flagged text, reason, rule ID, severity, confidence and suggested fix
9. Creator decisions: Accept, Ignore with reason, Ask reviewer for exception (critical findings cannot be ignored alone)
10. Reviewer queue and manager decision (Approve, Request changes, Reject)
11. Status tracking, approval history and version history
12. Printable Brand Passport per item, with AI-use disclosure
13. Brand Memory (Insights) tables: most-flagged rules, most-ignored or escalated rules, reviewer outcomes
14. Live deployment on Render with 3 hand-written sample items

## Changes from the original plan
- Brand Vault is loaded from seed data for fictional NovaBrew. The admin upload and edit screen is deferred to Round 3.
- TF-IDF retrieval and evidence-ledger checks are deferred to Round 3. In Round 2 the rule engine does the reliable checks and the AI is given the Brand Vault rules.
- Added one-click demo login so judges can use the product without sign-in help.
- Added a reviewer queue: critical findings cannot be ignored by the creator alone.
- Added AI-assisted rewrite, checked by our rule engine before it is shown.
- Brand Passport and Brand Memory were built in Round 2, earlier than planned (Brand Memory is table-based).

## Architecture
- `app.py`: Flask routes, roles and login checks, workflow helpers
- `database.py`: SQLite schema
- `seed.py`: fictional demo data and 3 sample items
- `checker.py`: regex rule engine (banned terms, risky claims, ALL CAPS, repeated "!", fact and number mismatches, long sentences)
- `review.py`: saves findings, creates submissions and new versions
- `ai.py`: calls the Groq API, masks emails and phone numbers
- `ai_review.py`: AI review, rewrite check, cache, cleaning of AI findings
- `templates/` and `static/`: pages and styling

## Technology
Python 3.10+, Flask, Flask-Login, SQLite, Requests, python-dotenv, Gunicorn, HTML and CSS, deployed on Render. AI provider: Groq.

## AI use (disclosure)
- Model: `openai/gpt-oss-20b` through the Groq API.
- One AI review call per new content version (cached by content hash).
- Up to 2 extra repair calls, only when the AI rewrite fails our own rule checks.
- Emails and phone numbers are masked before text is sent to the AI.
- AI findings are only kept if they cite a real rule and quote the text exactly. They are labelled "AI" with confidence 0.7.
- AI gives advice only. Humans make every decision.
- AI coding assistants were used to help write and debug this project. The team tested the result.

## Data note
NovaBrew is a **fictional** company. All rules, facts, terms and users are demo data. The 3 items starting with "[Sample]" are hand-written sample data, so the site is never empty. They were not produced by the AI.

## Run locally
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Create a `.env` file with:
```
SECRET_KEY=any-long-random-text
GROQ_API_KEY=your-groq-key
```
Then run:
```
python app.py
```
Open http://127.0.0.1:5000

## Known limits
- Free-tier hosting: the SQLite database resets when Render restarts. Demo data is re-created automatically.
- Text content only. Image checks are not built yet.
- Reviewer, manager and admin accounts are demo-only.
- Rule checks are regex-based, so they can miss or wrongly flag some text. AI findings can also be wrong.

## Planned for Round 3
1. Image and accessibility review (OCR, contrast, alt text, colours)
2. Brand learning: suggest rewrites for unclear rules, add trend charts, retrieval of relevant rules, and learn from reviewer decisions.
3. Accuracy testing: a test set that measures detection accuracy, plus a "false flag" feedback button

## Contribution
Solo participant: Archana M built all parts (product, backend, database, AI integration, frontend, testing, deployment and documentation).
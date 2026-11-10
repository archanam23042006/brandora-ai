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
2. Brand learning: a deeper dashboard that finds repeated mistakes and unclear guidelines (an early version is the Insights page)
3. Accuracy testing: a test set that measures detection accuracy, plus a "false flag" feedback button
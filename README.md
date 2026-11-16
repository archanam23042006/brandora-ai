# brandora-ai

**No content gets published without a Brand Passport.**

Brandora AI is a pre-publication brand-governance platform. Content is checked against approved guidelines, facts and terminology stored in a database. Every issue shows the reason, rule ID, severity and a suggested fix. Humans make the decisions (creator, reviewer, manager). AI only gives advice.

Team NEXAURA | CodeTitans India 2026 | Problem by Inkloom AI

**Live demo:** https://brandora-ai-ccmc.onrender.com
(Free tier: the first load after idle can take 30 to 60 seconds.)

**Repo:** https://github.com/archanam23042006/brandora-ai

## Demo login (no sign-in needed)
On the login page, click one of the 4 demo buttons: Creator, Reviewer, Manager, Admin.

## Workflow (Round 3 working flow)
1. Creator submits content (title, type, text and an optional image with alt text). Version 1 is saved and checked.
2. Findings come from our rule engine, one AI review and the image checks. Each has a rule ID, severity, reason and suggested fix.
3. TF-IDF retrieval picks the most relevant rules for the AI. The rule engine still checks every rule.
4. Image checks: alt-text, colour contrast, brand colours, and OCR for text inside the image. Text found by OCR goes through the rule engine.
5. Creator decides on each finding: Accept, Ignore (with reason, not allowed for critical), Ask a reviewer for an exception, or report a False flag.
6. Optional: AI-assisted rewrite (creator only). The rewrite is checked by our own rule engine before it is shown.
7. Creator revises (new version, re-checked) and submits for approval. Ignore and Ask decisions carry over to the new version. Submit is blocked while findings are still open.
8. Reviewer decides on exception requests: Must fix or Approve exception.
9. Manager approves, requests changes, or rejects (notes required for the last two).
10. **Brand Passport** page for each item: versions, findings, decisions, reviewer notes, approvals, AI-use disclosure and final status. It can be printed.
11. **Brand Memory (Insights)** page for reviewer, manager and admin: most flagged rules, most ignored or escalated rules, reviewer outcomes, false-flag reports and learning suggestions.
12. **Admin screen**: add and edit rules, banned terms, facts and the evidence ledger. Upload a .txt guideline file, and each line becomes a candidate rule that Admin adds with one click. Learning suggestions only suggest, and Admin decides.
13. Errors are handled with styled pages and clear messages (empty text, text over 5000 characters, wrong file, wrong role, double click).

## Completed features (Round 3)
All Round 2 features are kept (login with 4 roles, rule engine, AI review, AI rewrite, approval workflow, versions, Brand Passport, Brand Memory). Built in Round 3:
1. Image upload (PNG, JPG, WEBP, max 2 MB), validated with Pillow, with alt text shown on the item page
2. Alt-text edit box that saves a new version and re-checks
3. Alt-text check: missing is major, too short or generic is minor, over 125 characters is minor
4. Colour contrast check: whole-image WCAG estimate, ratio under 3 is major
5. Brand colour check: fixed NovaBrew palette (coffee brown #4B2E1E, cream #F5ECD7, green #0F766E), a finding if under 5% of pixels are close
6. OCR with OCR.space: text inside images goes through the rule engine
7. TF-IDF retrieval in plain Python: the top 5 relevant rules plus the tone rule are sent to the AI
8. Admin screen: rules, banned terms, facts and evidence ledger
9. Admin .txt guideline upload: each line is a candidate rule, and Admin clicks "Add as rule"
10. Evidence ledger: an exact approved claim stops the CLAIM-01 flag
11. False-flag button on findings, with a table in Insights
12. Learning suggestions: a rule ignored 3+ times or with 2+ false flags is suggested. It only suggests, and Admin decides.
13. Decision carry-over when a new version is created
14. Styled error pages (403, 404, 413, 500), 5000-character limit, double-click protection, input validation
15. Testing with 10 test cases on the live site


## Testing
All tests were run on the live site in incognito and all passed.
1. Clean text: no or minor findings
2. Text with claims: CLAIM-01, CLAIM-02 and TONE-02 found
3. Wrong facts: FACT-01 found
4. Empty content: clear message, no crash
5. A .txt file renamed .png: "That file is not a valid image"
6. Refresh (F5) on the item page: no duplicate item
7. Ignore and Ask decisions: still there in Version 2
8. Full journey: Creator, Reviewer, Manager, ends as Approved with history
9. Wrong role (Reviewer opens /submit): clear "only creators" message
10. Text over 5000 characters: clear message, no crash

Double-clicking "Review content" creates one item only.

Bugs found and fixed: submit button did nothing (stray form tag), decisions blank after re-check (carry-over added), suggested fixes mentioned NovaBrew facts on unrelated content (made generic), a stray div in the item page, scikit-learn hung on import (replaced with plain-Python TF-IDF), and the 404 page was the plain Flask default (styled error pages added).

## Architecture
- `app.py`: Flask routes, roles and login checks, workflow helpers, error handlers
- `database.py`: SQLite schema (including the item_images table)
- `seed.py`: fictional demo data and 3 sample items
- `checker.py`: regex rule engine (banned terms, risky claims, ALL CAPS, repeated "!", fact and number mismatches, long sentences)
- `review.py`: saves findings, creates submissions and new versions, carries over decisions
- `ai.py`: calls the Groq API, masks emails and phone numbers
- `ai_review.py`: AI review, rewrite check, cache, cleaning of AI findings
- `retrieval.py`: plain-Python TF-IDF rule retrieval
- `image_checks.py`: alt-text, contrast, brand colour and OCR checks
- `templates/` and `static/`: pages and styling

## Technology
Python 3.10+, Flask, Flask-Login, SQLite, Jinja2, Pillow, Requests, python-dotenv, Gunicorn, HTML and CSS, deployed on Render. AI provider: Groq. OCR provider: OCR.space.

## AI use (disclosure)
- Model: `openai/gpt-oss-20b` through the Groq API.
- One AI review call per new content version (cached by content hash).
- Up to 2 extra repair calls, only when the AI rewrite fails our own rule checks.
- Emails and phone numbers are masked before text is sent to the AI.
- AI findings are only kept if they cite a real rule and quote the text exactly. They are labelled "AI" with confidence 0.7.
- AI gives advice only. Humans make every decision.
- The AI model is text-only and cannot see images.
- OCR.space receives a shrunk copy of uploaded images to read text. This is also shown on the item page.
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
OCR_API_KEY=your-ocrspace-key
```
Then run:
```
python app.py
```
Open http://127.0.0.1:5000

## Known limits
- Free-tier hosting: the SQLite database resets when Render restarts. Demo data is re-created automatically.
- Fixed NovaBrew colour palette. Contrast is a whole-image estimate, not per text line.
- OCR depends on the OCR.space free tier. If it is down, OCR is skipped silently.
- Built-in detectors are fixed in code. Admin edits text and severity, not logic.
- Reviewer, manager and admin accounts are demo-only.
- Rule checks are regex-based, so they can miss or wrongly flag some text. AI findings can also be wrong.

## Roadmap
- Short term: PostgreSQL for permanent storage, comments screen, Admin creates reviewer and manager accounts, editable colour palette
- Medium term: rule rewrite suggestions from repeated ignores (Admin approves), charts in Brand Memory, per-line contrast, DOCX and PDF input
- Long term: AI vision to write and check alt text, a brand-specific trained model, multiple companies

## Round 3: what we built

### Improvement 1: Image and accessibility checks (DONE)
- Image upload (PNG, JPG, WEBP, max 2 MB), validated with Pillow
- Alt text field, shown on the item page. Editing it saves a new version and re-checks.
- Alt-text check: missing is major, too short or generic is minor, over 125 characters is minor
- Colour contrast check: whole-image WCAG estimate, ratio under 3 is major
- Brand colour check: fixed NovaBrew palette, a finding if under 5% of pixels are close to it
- OCR with OCR.space: text found inside the image goes through the rule engine
- Not built: checking that alt text matches the picture (a human decides)

### Improvement 2: Smarter detection and brand learning (DONE, with limits)
- TF-IDF retrieval (retrieval.py, plain Python): picks the top 5 relevant rules plus the tone rule for the AI. The rule engine still checks every rule.
- Admin screen: add and edit rules, banned terms, facts and evidence ledger
- Admin .txt guideline upload: each line is a candidate rule, and Admin clicks "Add as rule"
- Evidence ledger: an exact approved claim stops the CLAIM-01 flag
- False-flag button on findings, with a table in Insights
- Learning suggestions: a rule ignored 3+ times or with 2+ false flags is suggested. It only suggests, and Admin decides.
- Not built: automatic rule changes

### Improvement 3: Reliability (DONE)
- Styled error pages (403, 404, 413, 500)
- 5000-character limit, double-click protection, empty-input message
- Image validation (a fake .png shows a clear message)
- Decisions carry over to the new version after a revision
- 10 test cases passed on the live site (see Testing)
- Bugs found and fixed (see Bugs found and fixed)

### Not built in Round 3
Continuous brand learning, alt text matching the picture,editable colour palette.

## Contribution
Solo participant: Archana M (04archu26@gmail.com) built all parts (product, backend, database, AI integration, frontend, testing, deployment and documentation).
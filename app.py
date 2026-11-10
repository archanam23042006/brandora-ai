import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, abort)
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
import re
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db
from seed import seed
from review import create_submission, add_version

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

login_manager = LoginManager(app)
login_manager.login_view = "login"

DEMO_ACCOUNTS = {
    "creator": "creator@demo.com",
    "reviewer": "reviewer@demo.com",
    "manager": "manager@demo.com",
    "admin": "admin@demo.com",
}

BLOCKING = ("open", "accepted", "must_fix")

HISTORY_LABELS = {
    "submitted": "submitted for approval",
    "reviewed": "finished the review",
    "sent_back": "sent it back to the creator",
    "approve": "approved it",
    "changes": "requested changes",
    "reject": "rejected it",
}


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.name = row["name"]
        self.email = row["email"]
        self.role = row["role"]

@app.template_filter("ist")
def to_ist(value):
    if not value:
        return ""
    try:
        dt = datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S") + timedelta(hours=5, minutes=30)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except ValueError:
        return str(value)
@app.template_filter("status_class")
def status_class(status):
    return {"Approved": "st-approved", "Rejected": "st-rejected",
            "Changes Requested": "st-changes", "Pending Review": "st-pending",
            "Ready for Approval": "st-ready", "In Review": "st-review"}.get(status, "st-review")
   
@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return User(row) if row else None


def can_edit_item(it):
    owner_or_admin = (current_user.role == "admin" or
                      (current_user.role == "creator" and it["creator_id"] == current_user.id))
    return owner_or_admin and it["status"] in ("In Review", "Changes Requested")


def finding_state(f):
    if f["review_outcome"] == "allow":
        return "allowed"
    if f["review_outcome"] == "must_fix":
        return "must_fix"
    if f["decision_action"] == "verify":
        return "waiting"
    if f["decision_action"] == "ignore":
        return "ignored"
    if f["decision_action"] == "accept":
        return "accepted"
    return "open"


def load_findings(conn, item_id, version_id):
    rows = conn.execute(
        "SELECT f.*, r.title AS rule_title, d.action AS decision_action, "
        "d.reason AS decision_reason, rd.outcome AS review_outcome, "
        "rd.note AS review_note, ru.name AS reviewer_name "
        "FROM findings f "
        "LEFT JOIN rules r ON r.id = f.rule_id "
        "LEFT JOIN decisions d ON d.finding_id = f.id "
        "LEFT JOIN reviewer_decisions rd ON rd.item_id = f.item_id "
        "  AND rd.rule_id = f.rule_id AND rd.flagged_text = f.flagged_text "
        "LEFT JOIN users ru ON ru.id = rd.reviewer_id "
        "WHERE f.item_id = ? AND f.version_id = ? "
        "ORDER BY CASE f.severity WHEN 'critical' THEN 0 WHEN 'major' THEN 1 ELSE 2 END, f.id",
        (item_id, version_id)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["state"] = finding_state(d)
        out.append(d)
    return out


def latest_version(conn, item_id):
    return conn.execute(
        "SELECT * FROM content_versions WHERE item_id = ? "
        "ORDER BY version_no DESC LIMIT 1", (item_id,)).fetchone()


def get_item_or_404(conn, item_id):
    it = conn.execute("SELECT * FROM content_items WHERE id = ?", (item_id,)).fetchone()
    if not it:
        conn.close()
        abort(404)
    return it


def log_approval(conn, item_id, decision, note):
    conn.execute(
        "INSERT INTO approvals (item_id, user_id, decision, note) VALUES (?,?,?,?)",
        (item_id, current_user.id, decision, note))
STAGES = ["1. Fix issues", "2. Reviewer check", "3. Manager approval", "4. Approved"]


def stage_of(status):
    return {"In Review": 0, "Changes Requested": 0, "Pending Review": 1,
            "Ready for Approval": 2, "Approved": 3, "Rejected": 2}.get(status, 0)


def next_message(status, role):
    creator_like = role in ("creator", "admin")
    if status == "In Review":
        if creator_like:
            return ("Your turn. Go through each finding below: choose Accept (you will fix the text), "
                    "Ignore (small issues only, with a reason) or Ask a reviewer. Then edit your text "
                    "in the box at the bottom and press Submit for approval.")
        return "The creator is still fixing this content. Nothing to do yet."
    if status == "Changes Requested":
        if creator_like:
            return ("Changes were requested. Read the notes on the findings and in the approval "
                    "history, edit your text at the bottom, and submit again.")
        return "Sent back to the creator. Waiting for the revised content."
    if status == "Pending Review":
        if role in ("reviewer", "admin"):
            return ("Your turn. For each finding marked 'Waiting for a reviewer', choose Must fix "
                    "(the creator must change it) or Approve exception (the reason is valid, so it is "
                    "allowed). Then press Finish review.")
        return "Waiting for a reviewer to check the exception requests. Nothing to do now."
    if status == "Ready for Approval":
        if role in ("manager", "admin"):
            return "Your turn. Check the findings and notes below, then Approve, Request changes or Reject."
        return "Waiting for manager approval. Nothing to do now."
    if status == "Approved":
        return "Approved. This content is cleared for publication."
    if status == "Rejected":
        return "Rejected. See the manager's note in the approval history."
    return ""

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if row and check_password_hash(row["password_hash"], password):
            login_user(User(row))
            return redirect(url_for("home"))
        flash("Wrong email or password.")
    return render_template("login.html")

def password_problems(pw):
    p = []
    if len(pw) < 8:
        p.append("at least 8 characters")
    if not re.search(r"[A-Z]", pw):
        p.append("one capital letter")
    if not re.search(r"[a-z]", pw):
        p.append("one small letter")
    if not re.search(r"\d", pw):
        p.append("one number")
    if not re.search(r"[!@#$%&*?]", pw):
        p.append("one symbol like @ # $ % &")
    return p


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        errors = []
        if not name:
            errors.append("Please enter your name.")
        if not re.fullmatch(r"[a-z0-9._]+@gmail\.com", email):
            errors.append("Use a Gmail address, like yourname@gmail.com.")
        probs = password_problems(pw)
        if probs:
            errors.append("Password needs: " + ", ".join(probs) + ".")
        if not errors:
            conn = get_db()
            exists = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if exists:
                errors.append("This email is already registered. Please log in.")
                conn.close()
            else:
                conn.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
                    (name, email, generate_password_hash(pw), "creator"))
                conn.commit()
                row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                conn.close()
                login_user(User(row))
                return redirect(url_for("home"))
        for e in errors:
            flash(e)
    return render_template("signup.html")

@app.route("/demo/<role>")
def demo(role):
    email = DEMO_ACCOUNTS.get(role)
    if not email:
        return redirect(url_for("login"))
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    login_user(User(row))
    return redirect(url_for("home"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/home")
@login_required
def home():
    conn = get_db()
    base = ("SELECT ci.*, u.name AS creator_name FROM content_items ci "
            "JOIN users u ON u.id = ci.creator_id ")
    if current_user.role == "creator":
        items = conn.execute(base + "WHERE ci.creator_id = ? ORDER BY ci.id DESC",
                             (current_user.id,)).fetchall()
    else:
        items = conn.execute(base + "ORDER BY ci.id DESC").fetchall()
    conn.close()
    todo_status = {"reviewer": ["Pending Review"],
                   "manager": ["Ready for Approval"],
                   "admin": ["Pending Review", "Ready for Approval"],
                   "creator": ["Changes Requested"]}.get(current_user.role, [])
    todo = [i for i in items if i["status"] in todo_status]
    return render_template("home.html", items=items, todo=todo)


@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit():
    if current_user.role not in ("creator", "admin"):
        flash("Only creators can submit content. Log in as Creator to try it.")
        return redirect(url_for("home"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content_type = request.form.get("content_type", "Social media post")
        body = request.form.get("body", "").strip()
        if len(re.findall(r"[A-Za-z0-9]", title)) < 3:
            flash("Please write a proper title (at least 3 letters or numbers).")
            return render_template("submit.html", title=title, body=body)
        if not body:
            flash("Please paste some content to review.")
            return render_template("submit.html", title=title, body=body)
        item_id = create_submission(current_user.id, title, content_type, body)
        return redirect(url_for("item", item_id=item_id))
    return render_template("submit.html")


@app.route("/item/<int:item_id>")
@login_required
def item(item_id):
    conn = get_db()
    it = conn.execute(
        "SELECT ci.*, u.name AS creator_name FROM content_items ci "
        "JOIN users u ON u.id = ci.creator_id WHERE ci.id = ?", (item_id,)).fetchone()
    if not it:
        conn.close()
        abort(404)
    if current_user.role == "creator" and it["creator_id"] != current_user.id:
        conn.close()
        abort(403)
    version = latest_version(conn, item_id)
    findings = load_findings(conn, item_id, version["id"])
    versions = conn.execute(
        "SELECT v.version_no, v.created_at, u.name AS author, "
        "(SELECT COUNT(*) FROM findings WHERE version_id = v.id) AS finding_count "
        "FROM content_versions v LEFT JOIN users u ON u.id = v.changed_by "
        "WHERE v.item_id = ? ORDER BY v.version_no DESC", (item_id,)).fetchall()
    hist_rows = conn.execute(
        "SELECT a.*, u.name AS user_name, u.role AS user_role FROM approvals a "
        "JOIN users u ON u.id = a.user_id WHERE a.item_id = ? ORDER BY a.id DESC",
        (item_id,)).fetchall()
    conn.close()
    history = []
    for h in hist_rows:
        d = dict(h)
        d["label"] = HISTORY_LABELS.get(h["decision"], h["decision"])
        history.append(d)
    counts = {"critical": 0, "major": 0, "minor": 0}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    waiting_count = sum(1 for f in findings if f["state"] == "waiting")
    role = current_user.role
    can_review = role in ("reviewer", "admin") and it["status"] == "Pending Review"
    can_approve = role in ("manager", "admin") and it["status"] == "Ready for Approval"
    return render_template("item.html", item=it, version=version, findings=findings,
                           counts=counts, versions=versions, history=history,
                           can_edit=can_edit_item(it), can_review=can_review,
                           can_approve=can_approve, waiting_count=waiting_count,
                           stages=STAGES, stage=stage_of(it["status"]),
                           next_msg=next_message(it["status"], role))


@app.route("/finding/<int:finding_id>/decide", methods=["POST"])
@login_required
def decide(finding_id):
    action = request.form.get("action", "")
    reason = request.form.get("reason", "").strip()
    if action not in ("accept", "ignore", "verify"):
        abort(400)
    conn = get_db()
    f = conn.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
    if not f:
        conn.close()
        abort(404)
    it = get_item_or_404(conn, f["item_id"])
    if not can_edit_item(it):
        conn.close()
        abort(403)
    if action in ("ignore", "verify") and not reason:
        conn.close()
        return redirect(url_for("item", item_id=it["id"], err=finding_id)
                        + f"#finding-{finding_id}")
    # Critical findings cannot be ignored by the creator alone: a reviewer must decide.
    if action == "ignore" and f["severity"] == "critical":
        action = "verify"
        flash("This is a critical finding, so it was sent to a reviewer instead of being ignored.")
    conn.execute("DELETE FROM decisions WHERE finding_id = ?", (finding_id,))
    conn.execute(
        "INSERT INTO decisions (finding_id, user_id, action, reason) VALUES (?,?,?,?)",
        (finding_id, current_user.id, action, reason))
    conn.commit()
    ordered = conn.execute(
        "SELECT id FROM findings WHERE item_id = ? AND version_id = ? "
        "ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'major' THEN 1 ELSE 2 END, id",
        (f["item_id"], f["version_id"])).fetchall()
    conn.close()
    ids = [r["id"] for r in ordered]
    idx = ids.index(finding_id)
    anchor = f"#finding-{ids[idx + 1]}" if idx + 1 < len(ids) else "#revise"
    return redirect(url_for("item", item_id=it["id"]) + anchor)


@app.route("/item/<int:item_id>/revise", methods=["POST"])
@login_required
def revise(item_id):
    conn = get_db()
    it = get_item_or_404(conn, item_id)
    conn.close()
    if not can_edit_item(it):
        abort(403)
    body = request.form.get("body", "").strip()
    if not body:
        flash("Content cannot be empty.")
        return redirect(url_for("item", item_id=item_id))
    n = add_version(item_id, current_user.id, body)
    flash(f"Version {n} saved and re-checked.")
    return redirect(url_for("item", item_id=item_id))


@app.route("/item/<int:item_id>/submit-for-approval", methods=["POST"])
@login_required
def submit_for_approval(item_id):
    conn = get_db()
    it = get_item_or_404(conn, item_id)
    if not can_edit_item(it):
        conn.close()
        abort(403)
    v = latest_version(conn, item_id)
    findings = load_findings(conn, item_id, v["id"])
    blocking = [f for f in findings if f["state"] in BLOCKING]
    if blocking:
        conn.close()
        flash(f"{len(blocking)} finding(s) still need action. Fix the text and re-check, "
              "or choose Ignore (with a reason) or Ask a human to verify.")
        return redirect(url_for("item", item_id=item_id))
    waiting = any(f["state"] == "waiting" for f in findings)
    new_status = "Pending Review" if waiting else "Ready for Approval"
    conn.execute("UPDATE content_items SET status = ? WHERE id = ?", (new_status, item_id))
    log_approval(conn, item_id, "submitted", f"Version {v['version_no']} submitted.")
    conn.commit()
    conn.close()
    flash("Submitted. A reviewer will check it." if waiting
          else "Submitted. It is ready for manager approval.")
    return redirect(url_for("item", item_id=item_id))


@app.route("/finding/<int:finding_id>/review", methods=["POST"])
@login_required
def review_finding(finding_id):
    if current_user.role not in ("reviewer", "admin"):
        abort(403)
    outcome = request.form.get("outcome", "")
    note = request.form.get("note", "").strip()
    if outcome not in ("must_fix", "allow"):
        abort(400)
    conn = get_db()
    f = conn.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
    if not f:
        conn.close()
        abort(404)
    it = get_item_or_404(conn, f["item_id"])
    if it["status"] != "Pending Review":
        conn.close()
        abort(403)
    if outcome == "must_fix" and not note:
        conn.close()
        return redirect(url_for("item", item_id=it["id"], rerr=finding_id)
                        + f"#finding-{finding_id}")
    conn.execute(
        "DELETE FROM reviewer_decisions WHERE item_id = ? AND rule_id IS ? AND flagged_text = ?",
        (f["item_id"], f["rule_id"], f["flagged_text"]))
    conn.execute(
        "INSERT INTO reviewer_decisions (item_id, rule_id, flagged_text, reviewer_id, outcome, note) "
        "VALUES (?,?,?,?,?,?)",
        (f["item_id"], f["rule_id"], f["flagged_text"], current_user.id, outcome, note))
    conn.commit()
    conn.close()
    return redirect(url_for("item", item_id=it["id"]) + f"#finding-{finding_id}")


@app.route("/item/<int:item_id>/finish-review", methods=["POST"])
@login_required
def finish_review(item_id):
    if current_user.role not in ("reviewer", "admin"):
        abort(403)
    conn = get_db()
    it = get_item_or_404(conn, item_id)
    if it["status"] != "Pending Review":
        conn.close()
        abort(403)
    v = latest_version(conn, item_id)
    findings = load_findings(conn, item_id, v["id"])
    waiting = [f for f in findings if f["state"] == "waiting"]
    if waiting:
        conn.close()
        flash(f"{len(waiting)} finding(s) still need your decision.")
        return redirect(url_for("item", item_id=item_id))
    if any(f["state"] == "must_fix" for f in findings):
        conn.execute("UPDATE content_items SET status = 'Changes Requested' WHERE id = ?", (item_id,))
        log_approval(conn, item_id, "sent_back", "Some findings must be fixed. See the notes on each finding.")
        flash("Sent back to the creator.")
    else:
        conn.execute("UPDATE content_items SET status = 'Ready for Approval' WHERE id = ?", (item_id,))
        log_approval(conn, item_id, "reviewed", "All findings resolved. Ready for manager approval.")
        flash("Review finished. It is ready for manager approval.")
    conn.commit()
    conn.close()
    return redirect(url_for("item", item_id=item_id))


@app.route("/item/<int:item_id>/approval", methods=["POST"])
@login_required
def approval(item_id):
    if current_user.role not in ("manager", "admin"):
        abort(403)
    decision = request.form.get("decision", "")
    note = request.form.get("note", "").strip()
    if decision not in ("approve", "changes", "reject"):
        abort(400)
    conn = get_db()
    it = get_item_or_404(conn, item_id)
    if it["status"] != "Ready for Approval":
        conn.close()
        abort(403)
    if decision in ("changes", "reject") and not note:
        conn.close()
        flash("Please write a note for the creator.")
        return redirect(url_for("item", item_id=item_id))
    status = {"approve": "Approved", "changes": "Changes Requested", "reject": "Rejected"}[decision]
    conn.execute("UPDATE content_items SET status = ? WHERE id = ?", (status, item_id))
    log_approval(conn, item_id, decision, note)
    conn.commit()
    conn.close()
    flash(f"Status: {status}")
    return redirect(url_for("item", item_id=item_id))


seed()  # creates tables and sample data if the database is empty

if __name__ == "__main__":
    app.run(debug=True)
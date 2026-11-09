import os
from dotenv import load_dotenv
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, abort)
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import check_password_hash
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


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.name = row["name"]
        self.email = row["email"]
        self.role = row["role"]


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
    return render_template("home.html", items=items)


@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit():
    if current_user.role not in ("creator", "admin"):
        flash("Only creators can submit content. Log in as Creator to try it.")
        return redirect(url_for("home"))
    if request.method == "POST":
        title = request.form.get("title", "").strip() or "Untitled content"
        content_type = request.form.get("content_type", "Social media post")
        body = request.form.get("body", "").strip()
        if not body:
            flash("Please paste some content to review.")
            return redirect(url_for("submit"))
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
    version = conn.execute(
        "SELECT * FROM content_versions WHERE item_id = ? "
        "ORDER BY version_no DESC LIMIT 1", (item_id,)).fetchone()
    findings = conn.execute(
        "SELECT f.*, r.title AS rule_title, d.action AS decision_action, "
        "d.reason AS decision_reason "
        "FROM findings f "
        "LEFT JOIN rules r ON r.id = f.rule_id "
        "LEFT JOIN decisions d ON d.finding_id = f.id "
        "WHERE f.item_id = ? AND f.version_id = ? "
        "ORDER BY CASE f.severity WHEN 'critical' THEN 0 WHEN 'major' THEN 1 ELSE 2 END, f.id",
        (item_id, version["id"])).fetchall()
    versions = conn.execute(
        "SELECT v.version_no, v.created_at, u.name AS author, "
        "(SELECT COUNT(*) FROM findings WHERE version_id = v.id) AS finding_count "
        "FROM content_versions v LEFT JOIN users u ON u.id = v.changed_by "
        "WHERE v.item_id = ? ORDER BY v.version_no DESC", (item_id,)).fetchall()
    conn.close()
    counts = {"critical": 0, "major": 0, "minor": 0}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    return render_template("item.html", item=it, version=version, findings=findings,
                           counts=counts, versions=versions, can_edit=can_edit_item(it))


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
    it = conn.execute("SELECT * FROM content_items WHERE id = ?", (f["item_id"],)).fetchone()
    if not can_edit_item(it):
        conn.close()
        abort(403)
    if action == "ignore" and not reason:
        conn.close()
        return redirect(url_for("item", item_id=it["id"], err=finding_id)
                        + f"#finding-{finding_id}")
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
    it = conn.execute("SELECT * FROM content_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    if not it:
        abort(404)
    if not can_edit_item(it):
        abort(403)
    body = request.form.get("body", "").strip()
    if not body:
        flash("Content cannot be empty.")
        return redirect(url_for("item", item_id=item_id))
    n = add_version(item_id, current_user.id, body)
    flash(f"Version {n} saved and re-checked.")
    return redirect(url_for("item", item_id=item_id))


seed()  # creates tables and sample data if the database is empty

if __name__ == "__main__":
    app.run(debug=True)
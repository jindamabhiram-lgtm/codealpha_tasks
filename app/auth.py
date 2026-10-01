import re
import secrets
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def csrf_valid():
    return secrets.compare_digest(session.get("csrf_token", ""), request.form.get("csrf_token", ""))

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        if not csrf_valid():
            flash("Your form expired. Please try again.", "error")
        else:
            name, email, password = request.form.get("name", "").strip(), request.form.get("email", "").strip().lower(), request.form.get("password", "")
            if len(name) < 2 or len(name) > 80:
                flash("Please enter a name between 2 and 80 characters.", "error")
            elif not EMAIL_RE.match(email):
                flash("Please enter a valid email address.", "error")
            elif len(password) < 8:
                flash("Password must be at least 8 characters.", "error")
            elif User.query.filter_by(email=email).first():
                flash("An account with that email already exists.", "error")
            else:
                user = User(name=name, email=email)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                session["user_id"] = user.id
                flash("Welcome to PulseTrack.", "success")
                return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        if not csrf_valid():
            flash("Your form expired. Please try again.", "error")
        else:
            user = User.query.filter_by(email=request.form.get("email", "").strip().lower()).first()
            if not user or not user.check_password(request.form.get("password", "")):
                flash("Email or password is incorrect.", "error")
            else:
                session.clear()
                session["user_id"] = user.id
                return redirect(url_for("main.dashboard"))
    return render_template("auth/login.html")

@auth_bp.post("/logout")
def logout():
    if csrf_valid():
        session.clear()
    return redirect(url_for("auth.login"))
from datetime import date, timedelta
import secrets
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_
from app import db
from app.models import User, Workout

main_bp = Blueprint("main", __name__)

@main_bp.before_app_request
def prepare_request():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)

def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None

@main_bp.app_context_processor
def inject_user():
    return {"current_user": current_user(), "csrf_token": session.get("csrf_token", "")}

@main_bp.before_request
def require_login():
    if request.endpoint and request.endpoint.startswith("main.") and request.endpoint != "main.index" and not current_user():
        return redirect(url_for("auth.login"))

@main_bp.get("/")
def index():
    return redirect(url_for("main.dashboard")) if current_user() else redirect(url_for("auth.login"))

@main_bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    user = current_user()
    if request.method == "POST":
        if not secrets.compare_digest(session.get("csrf_token", ""), request.form.get("csrf_token", "")):
            flash("Your form expired. Please try again.", "error")
        else:
            title, workout_type = request.form.get("title", "").strip(), request.form.get("workout_type", "").strip()
            try:
                duration, calories = int(request.form.get("duration", "0")), int(request.form.get("calories", "0"))
                completed_on = date.fromisoformat(request.form.get("completed_on", ""))
            except (TypeError, ValueError):
                duration = calories = 0
                completed_on = None
            if not title or len(title) > 120 or workout_type not in {"Strength", "Cardio", "Mobility", "Sport"}:
                flash("Add a title and choose a valid workout type.", "error")
            elif not 1 <= duration <= 1440 or not 0 <= calories <= 10000 or not completed_on:
                flash("Check the duration, calories, and date values.", "error")
            else:
                db.session.add(Workout(user_id=user.id, title=title, workout_type=workout_type, duration=duration, calories=calories, completed_on=completed_on))
                db.session.commit()
                flash("Workout added to your history.", "success")
                return redirect(url_for("main.dashboard"))
    query = request.args.get("q", "").strip()
    workouts_query = Workout.query.filter_by(user_id=user.id)
    if query:
        workouts_query = workouts_query.filter(or_(Workout.title.ilike(f"%{query}%"), Workout.workout_type.ilike(f"%{query}%")))
    workouts = workouts_query.order_by(Workout.completed_on.desc(), Workout.id.desc()).all()
    all_workouts = Workout.query.filter_by(user_id=user.id).all()
    recent = [workout for workout in all_workouts if workout.completed_on >= date.today() - timedelta(days=6)]
    return render_template("dashboard.html", workouts=workouts, total_workouts=len(all_workouts), week_minutes=sum(w.duration for w in recent), week_calories=sum(w.calories for w in recent), query=query, today=date.today().isoformat())

@main_bp.post("/workouts/<int:workout_id>/delete")
def delete_workout(workout_id):
    workout = Workout.query.filter_by(id=workout_id, user_id=current_user().id).first()
    if not workout or not secrets.compare_digest(session.get("csrf_token", ""), request.form.get("csrf_token", "")):
        flash("Unable to remove that workout.", "error")
    else:
        db.session.delete(workout)
        db.session.commit()
        flash("Workout removed.", "success")
    return redirect(url_for("main.dashboard"))
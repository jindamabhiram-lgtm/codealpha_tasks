from flask import Blueprint, jsonify, request
from app import db
from app.main import current_user
from app.models import Workout

api_bp = Blueprint("api", __name__)

@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})

@api_bp.get("/workouts")
def workouts():
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401
    return jsonify({"data": [workout.to_dict() for workout in Workout.query.filter_by(user_id=user.id).order_by(Workout.completed_on.desc()).all()]})

@api_bp.post("/workouts")
def create_workout():
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401
    payload = request.get_json(silent=True) or {}
    required = {"title", "workout_type", "duration", "calories", "completed_on"}
    if not required.issubset(payload):
        return jsonify({"error": "Missing workout fields"}), 400
    try:
        from datetime import date
        duration, calories = int(payload["duration"]), int(payload["calories"])
        completed_on = date.fromisoformat(payload["completed_on"])
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid workout values"}), 400
    if not str(payload["title"]).strip() or payload["workout_type"] not in {"Strength", "Cardio", "Mobility", "Sport"} or not 1 <= duration <= 1440 or not 0 <= calories <= 10000:
        return jsonify({"error": "Workout values are out of range"}), 400
    workout = Workout(user_id=user.id, title=str(payload["title"]).strip(), workout_type=payload["workout_type"], duration=duration, calories=calories, completed_on=completed_on)
    db.session.add(workout)
    db.session.commit()
    return jsonify(workout.to_dict()), 201
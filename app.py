import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, get_week_dates, get_month_dates, calculate_streaks
from functools import wraps

# Configure application
app = Flask(__name__)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Database connection helper
def get_db():
    """Get database connection."""
    db = sqlite3.connect('habit_tracker.db')
    db.row_factory = sqlite3.Row
    return db

# Create tables on startup
with app.app_context():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()

@app.after_request
def after_request(response):
    """Ensure responses aren't cached."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    """Show habit dashboard."""
    db = get_db()
    
    # Get user's habits
    habits = db.execute(
        "SELECT * FROM habits WHERE user_id = ? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()
    
    # Get today's date
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get completion status for today
    completed_today = db.execute(
        """SELECT habit_id FROM habit_logs 
           WHERE user_id = ? AND completed_at = ?""",
        (session["user_id"], today)
    ).fetchall()
    completed_ids = [log['habit_id'] for log in completed_today]
    
    # Calculate statistics for each habit
    habit_stats = []
    for habit in habits:
        current_streak, longest_streak = calculate_streaks(db, habit['id'], session["user_id"])
        
        # Get total completions
        total_completions = db.execute(
            "SELECT COUNT(*) as count FROM habit_logs WHERE habit_id = ?",
            (habit['id'],)
        ).fetchone()['count']
        
        habit_stats.append({
            'habit': habit,
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'total_completions': total_completions,
            'completed_today': habit['id'] in completed_ids
        })
    
    db.close()
    
    return render_template("index.html", habit_stats=habit_stats, today=today)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""
    session.clear()
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username:
            flash("Must provide username", "error")
            return render_template("login.html")
        elif not password:
            flash("Must provide password", "error")
            return render_template("login.html")
        
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        db.close()
        
        if user is None or not check_password_hash(user['hash'], password):
            flash("Invalid username and/or password", "error")
            return render_template("login.html")
        
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        flash("Welcome back!", "success")
        return redirect("/")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""
    session.clear()
    flash("You have been logged out", "info")
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        
        if not username:
            flash("Must provide username", "error")
            return render_template("register.html")
        elif not password:
            flash("Must provide password", "error")
            return render_template("register.html")
        elif password != confirmation:
            flash("Passwords don't match", "error")
            return render_template("register.html")
        elif len(password) < 8:
            flash("Password must be at least 8 characters", "error")
            return render_template("register.html")
        
        db = get_db()
        
        # Check if username exists
        existing = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        
        if existing:
            db.close()
            flash("Username already exists", "error")
            return render_template("register.html")
        
        # Insert new user
        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )
        db.commit()
        db.close()
        
        flash("Registration successful! Please log in.", "success")
        return redirect("/login")
    
    return render_template("register.html")

@app.route("/add_habit", methods=["GET", "POST"])
@login_required
def add_habit():
    """Add a new habit."""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description", "")
        frequency = request.form.get("frequency", "daily")
        target_count = request.form.get("target_count", 1)
        color = request.form.get("color", "#4CAF50")
        
        if not name:
            flash("Must provide habit name", "error")
            return render_template("add_habit.html")
        
        db = get_db()
        db.execute(
            """INSERT INTO habits (user_id, name, description, frequency, target_count, color) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session["user_id"], name, description, frequency, target_count, color)
        )
        db.commit()
        db.close()
        
        flash("Habit added successfully!", "success")
        return redirect("/")
    
    return render_template("add_habit.html")

@app.route("/toggle_habit", methods=["POST"])
@login_required
def toggle_habit():
    """Toggle habit completion for today."""
    data = request.get_json()
    habit_id = data.get('habit_id')
    today = datetime.now().strftime('%Y-%m-%d')
    
    if not habit_id:
        return jsonify({'success': False, 'error': 'No habit ID provided'})
    
    db = get_db()
    
    # Check if already completed today
    existing = db.execute(
        "SELECT * FROM habit_logs WHERE habit_id = ? AND user_id = ? AND completed_at = ?",
        (habit_id, session["user_id"], today)
    ).fetchone()
    
    if existing:
        # Remove completion
        db.execute(
            "DELETE FROM habit_logs WHERE habit_id = ? AND user_id = ? AND completed_at = ?",
            (habit_id, session["user_id"], today)
        )
        completed = False
    else:
        # Add completion
        db.execute(
            "INSERT INTO habit_logs (habit_id, user_id, completed_at) VALUES (?, ?, ?)",
            (habit_id, session["user_id"], today)
        )
        completed = True
    
    # Update streaks
    current_streak, longest_streak = calculate_streaks(db, habit_id, session["user_id"])
    
    db.execute(
        """INSERT OR REPLACE INTO streaks (habit_id, user_id, current_streak, longest_streak, last_updated)
           VALUES (?, ?, ?, ?, ?)""",
        (habit_id, session["user_id"], current_streak, longest_streak, today)
    )
    
    db.commit()
    db.close()
    
    return jsonify({
        'success': True,
        'completed': completed,
        'current_streak': current_streak,
        'longest_streak': longest_streak
    })

@app.route("/history")
@login_required
def history():
    """Show habit history."""
    db = get_db()
    
    # Get user's habits
    habits = db.execute(
        "SELECT * FROM habits WHERE user_id = ? ORDER BY created_at",
        (session["user_id"],)
    ).fetchall()
    
    # Get date range (last 30 days by default)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=29)
    
    # Get all logs for the date range
    logs = db.execute(
        """SELECT hl.* FROM habit_logs hl
           JOIN habits h ON hl.habit_id = h.id
           WHERE hl.user_id = ? AND hl.completed_at BETWEEN ? AND ?
           ORDER BY hl.completed_at DESC""",
        (session["user_id"], start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    ).fetchall()
    
    db.close()
    
    return render_template("history.html", habits=habits, logs=logs, 
                         start_date=start_date, end_date=end_date)

@app.route("/delete_habit", methods=["POST"])
@login_required
def delete_habit():
    """Delete a habit."""
    data = request.get_json()
    habit_id = data.get('habit_id')
    
    if not habit_id:
        return jsonify({'success': False, 'error': 'No habit ID provided'})
    
    db = get_db()
    
    # Verify habit belongs to user
    habit = db.execute(
        "SELECT * FROM habits WHERE id = ? AND user_id = ?",
        (habit_id, session["user_id"])
    ).fetchone()
    
    if not habit:
        db.close()
        return jsonify({'success': False, 'error': 'Habit not found'})
    
    # Delete related data
    db.execute("DELETE FROM streaks WHERE habit_id = ?", (habit_id,))
    db.execute("DELETE FROM habit_logs WHERE habit_id = ?", (habit_id,))
    db.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    db.commit()
    db.close()
    
    return jsonify({'success': True})

@app.route("/stats/<int:habit_id>")
@login_required
def habit_stats(habit_id):
    """Get habit statistics as JSON."""
    db = get_db()
    
    habit = db.execute(
        "SELECT * FROM habits WHERE id = ? AND user_id = ?",
        (habit_id, session["user_id"])
    ).fetchone()
    
    if not habit:
        db.close()
        return jsonify({'success': False, 'error': 'Habit not found'})
    
    current_streak, longest_streak = calculate_streaks(db, habit_id, session["user_id"])
    
    # Get completion data for the last 30 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=29)
    
    logs = db.execute(
        """SELECT completed_at, COUNT(*) as count 
           FROM habit_logs 
           WHERE habit_id = ? AND completed_at BETWEEN ? AND ?
           GROUP BY completed_at""",
        (habit_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    ).fetchall()
    
    # Calculate completion rate
    total_days = (end_date - start_date).days + 1
    completion_rate = (len(logs) / total_days) * 100
    
    db.close()
    
    return jsonify({
        'success': True,
        'name': habit['name'],
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'completion_rate': round(completion_rate, 1),
        'logs': [{'date': log['completed_at'], 'count': log['count']} for log in logs]
    })

if __name__ == "__main__":
    app.run(debug=True)

import os
from functools import wraps
from flask import redirect, session
from datetime import datetime, timedelta

def login_required(f):
    """Decorate routes to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def get_week_dates():
    """Get dates for the current week (Monday to Sunday)."""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    return [monday + timedelta(days=i) for i in range(7)]

def get_month_dates():
    """Get dates for the current month."""
    today = datetime.now().date()
    first_day = today.replace(day=1)
    if today.month == 12:
        last_day = today.replace(year=today.year+1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = today.replace(month=today.month+1, day=1) - timedelta(days=1)
    return [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]

def calculate_streaks(db, habit_id, user_id):
    """Calculate current and longest streak for a habit."""
    cursor = db.cursor()
    cursor.execute(
        "SELECT completed_at FROM habit_logs WHERE habit_id = ? AND user_id = ? ORDER BY completed_at DESC",
        (habit_id, user_id)
    )
    logs = cursor.fetchall()
    
    if not logs:
        return 0, 0
    
    dates = [datetime.strptime(log['completed_at'], '%Y-%m-%d').date() for log in logs]
    dates.sort(reverse=True)
    
    # Calculate current streak
    current_streak = 0
    today = datetime.now().date()
    check_date = today
    
    for date in dates:
        if date == check_date:
            current_streak += 1
            check_date -= timedelta(days=1)
        elif date == check_date - timedelta(days=1):
            current_streak += 1
            check_date = date - timedelta(days=1)
        else:
            break
    
    # Calculate longest streak
    longest_streak = 1
    current_longest = 1
    
    for i in range(1, len(dates)):
        if (dates[i-1] - dates[i]).days == 1:
            current_longest += 1
        else:
            longest_streak = max(longest_streak, current_longest)
            current_longest = 1
    
    longest_streak = max(longest_streak, current_longest)
    
    return current_streak, longest_streak

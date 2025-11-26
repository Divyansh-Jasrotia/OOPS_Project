from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import date, timedelta
from abc import ABC, abstractmethod
import math
from db import DB
from mysql.connector import Error

# initialize DB
db = DB()

app = Flask(__name__)
CORS(app)

from flask import send_from_directory
import os

FRONTEND_FOLDER = os.path.join(os.path.dirname(__file__), "..", "Frontend")







class BaseEntity(ABC):
    @abstractmethod
    def to_dict(self):
        pass

class User(BaseEntity):
    def __init__(self, db: DB, username: str, id: int = None):
        self.db = db
        self.id = id
        self.username = username

    def save(self):
        r = self.db.query("SELECT * FROM users WHERE username=%s", (self.username,), fetchone=True)
        if r:
            self.id = r['id']
            return self
        self.db.execute("INSERT INTO users (username) VALUES (%s)", (self.username,))
        r = self.db.query("SELECT * FROM users WHERE username=%s", (self.username,), fetchone=True)
        self.id = r['id']
        self.db.execute("INSERT IGNORE INTO stats (user_id, total_points, current_streak_weeks, current_goal) VALUES (%s,%s,%s,%s)",
                        (self.id, 0, 0, 100))
        return self

    def to_dict(self):
        return {"id": self.id, "username": self.username}

class Admin(User):
    def delete_user(self, user_id):
        self.db.execute("DELETE FROM users WHERE id=%s", (user_id,))

class Habit(BaseEntity):
    def __init__(self, db: DB, user_id: int, name: str, htype: str, importance: str, id: int = None):
        self.db = db
        self.id = id
        self.user_id = user_id
        self.name = name
        self.type = htype
        self.importance = importance

    def save(self):
        if self.id:
            self.db.execute("UPDATE habits SET name=%s, type=%s, importance=%s WHERE id=%s",
                            (self.name, self.type, self.importance, self.id))
        else:
            self.db.execute("INSERT INTO habits (user_id, name, type, importance) VALUES (%s,%s,%s,%s)",
                            (self.user_id, self.name, self.type, self.importance))
            r = self.db.query("SELECT * FROM habits WHERE user_id=%s AND name=%s ORDER BY id DESC LIMIT 1", (self.user_id, self.name), fetchone=True)
            self.id = r['id']
        return self

    def to_dict(self):
        return {"id": self.id, "user_id": self.user_id, "name": self.name, "type": self.type, "importance": self.importance}

class GoodHabit(Habit):
    def score(self, result: str):
        return 10 if result == 'completed' else 0

class BadHabit(Habit):
    def score(self, result: str):
        return 10 if result == 'completed' else 0

class Report(BaseEntity):
    def __init__(self, db: DB, habit_id: int, report_date: date, result: str, id: int = None):
        self.db = db
        self.id = id
        self.habit_id = habit_id
        self.report_date = report_date
        self.result = result

    def save(self):
        self.db.execute("INSERT INTO reports (habit_id, report_date, result) VALUES (%s,%s,%s)",
                        (self.habit_id, self.report_date, self.result))
        r = self.db.query("SELECT * FROM reports WHERE habit_id=%s AND report_date=%s", (self.habit_id, self.report_date), fetchone=True)
        self.id = r['id']
        return self

    def to_dict(self):
        return {"id": self.id, "habit_id": self.habit_id, "report_date": str(self.report_date), "result": self.result}

class WeeklyStats(BaseEntity):
    def __init__(self, db: DB, user_id: int):
        self.db = db
        self.user_id = user_id
        r = self.db.query("SELECT * FROM stats WHERE user_id=%s", (self.user_id,), fetchone=True)
        if not r:
            self.db.execute("INSERT INTO stats (user_id, total_points, current_streak_weeks, current_goal) VALUES (%s,%s,%s,%s)",
                            (self.user_id, 0, 0, 100))
            r = self.db.query("SELECT * FROM stats WHERE user_id=%s", (self.user_id,), fetchone=True)
        self._row = r

    @property
    def total_points(self):
        return int(self._row['total_points'] or 0)

    @property
    def current_streak(self):
        return int(self._row['current_streak_weeks'] or 0)

    @property
    def current_goal(self):
        return int(self._row['current_goal'] or 100)

    @property
    def last_processed_week_start(self):
        return self._row['last_processed_week_start']

    def save(self, total_points=None, streak=None, goal=None, last_week_start=None):
        tp = total_points if total_points is not None else self.total_points
        st = streak if streak is not None else self.current_streak
        gl = goal if goal is not None else self.current_goal
        lw = last_week_start
        self.db.execute("UPDATE stats SET total_points=%s, current_streak_weeks=%s, current_goal=%s, last_processed_week_start=%s WHERE user_id=%s",
                        (tp, st, gl, lw, self.user_id))
        r = self.db.query("SELECT * FROM stats WHERE user_id=%s", (self.user_id,), fetchone=True)
        self._row = r

    def to_dict(self):
        return {"user_id": self.user_id, "total_points": self.total_points, "current_streak_weeks": self.current_streak, "current_goal": self.current_goal, "last_processed_week_start": str(self.last_processed_week_start) if self.last_processed_week_start else None}

class StreakManager:
    def __init__(self, db: DB, user_id: int):
        self.db = db
        self.user_id = user_id
        self.stats = WeeklyStats(db, user_id)

    @staticmethod
    def week_start(date_obj: date):
        weekday = date_obj.weekday()
        return date_obj - timedelta(days=weekday)

    def points_for_week(self, week_start: date):
        week_end = week_start + timedelta(days=6)
        rows = self.db.query("SELECT r.*, h.type FROM reports r JOIN habits h ON r.habit_id=h.id WHERE r.report_date BETWEEN %s AND %s AND h.user_id=%s",
                             (week_start, week_end, self.user_id))
        total = 0
        if rows:
            for r in rows:
                total += 10 if r['result'] == 'completed' else 0
        return total

    def process_week(self, week_start: date = None):
        if week_start is None:
            week_start = self.week_start(date.today())
        if self.stats.last_processed_week_start and str(self.stats.last_processed_week_start) == str(week_start):
            return {"processed": False, "reason": "already processed", "stats": self.stats.to_dict()}

        week_points = self.points_for_week(week_start)
        goal = self.stats.current_goal
        res = {"week_start": str(week_start), "week_points": week_points, "goal": goal}

        if week_points >= goal:
            new_streak = self.stats.current_streak + 1
            new_goal = math.ceil(self.stats.current_goal * 1.2)
            bonus = math.ceil(new_goal * 0.1)
            new_total = self.stats.total_points + bonus
            self.stats.save(total_points=new_total, streak=new_streak, goal=new_goal, last_week_start=week_start)
            reward_info = RewardFactory.issue_reward(self.db, self.user_id, new_streak)
            res.update({"success": True, "bonus": bonus, "new_goal": new_goal, "new_streak": new_streak, "reward": reward_info})
        else:
            self.stats.save(total_points=self.stats.total_points, streak=0, goal=100, last_week_start=week_start)
            res.update({"success": False, "reason": "failed to reach goal", "new_goal": 100, "new_streak": 0})
        return res

class Reward:
    def __init__(self, db: DB, user_id: int, reward_type: str, details: str):
        self.db = db
        self.user_id = user_id
        self.reward_type = reward_type
        self.details = details

    def give(self):
        self.db.execute("INSERT INTO rewards (user_id, reward_type, details) VALUES (%s,%s,%s)", (self.user_id, self.reward_type, self.details))
        return {"user_id": self.user_id, "reward_type": self.reward_type, "details": self.details}

class SmallReward(Reward): pass
class MediumReward(Reward): pass
class LargeReward(Reward): pass

class RewardFactory:
    @staticmethod
    def issue_reward(db: DB, user_id: int, streak_weeks: int):
        if streak_weeks >= 8:
            r = LargeReward(db, user_id, "8-week", "Big milestone reward")
        elif streak_weeks >= 6:
            r = LargeReward(db, user_id, "6-week", "Large reward")
        elif streak_weeks >= 4:
            r = MediumReward(db, user_id, "4-week", "Medium reward")
        elif streak_weeks >= 2:
            r = SmallReward(db, user_id, "2-week", "Small reward")
        else:
            return {"issued": False, "reason": "no reward for <2 weeks"}
        info = r.give()
        return {"issued": True, "info": info}

class GoalManager:
    BASE = 100
    @staticmethod
    def increase(goal):
        return math.ceil(goal * 1.2)

class APIService:
    def __init__(self, db: DB):
        self.db = db

    def ensure_user(self, username: str = "default_user"):
        u = User(self.db, username).save()
        return u

    def add_habit(self, username, name, htype, importance):
        user = self.ensure_user(username)
        if htype == 'good':
            habit = GoodHabit(self.db, user.id, name, htype, importance)
        else:
            habit = BadHabit(self.db, user.id, name, htype, importance)
        habit.save()
        return habit.to_dict()

    def get_habits(self, username):
        user = self.ensure_user(username)
        rows = self.db.query("SELECT * FROM habits WHERE user_id=%s ORDER BY id DESC", (user.id,))
        return rows

    def submit_report(self, username, habit_id, result, report_date=None):
        user = self.ensure_user(username)
        h = self.db.query("SELECT * FROM habits WHERE id=%s AND user_id=%s", (habit_id, user.id), fetchone=True)
        if not h:
            raise ValueError("habit not found")
        if report_date is None:
            report_date = date.today()
        rep = Report(self.db, habit_id, report_date, result)
        rep.save()
        sc = 10 if result == 'completed' else 0
        stats = self.db.query("SELECT * FROM stats WHERE user_id=%s", (user.id,), fetchone=True)
        if not stats:
            self.db.execute("INSERT INTO stats (user_id, total_points, current_streak_weeks, current_goal) VALUES (%s,%s,%s,%s)",
                            (user.id, sc, 0, GoalManager.BASE))
        else:
            new_total = (stats['total_points'] or 0) + sc
            self.db.execute("UPDATE stats SET total_points=%s WHERE user_id=%s", (new_total, user.id))
        sm = StreakManager(self.db, user.id)
        week_start = StreakManager.week_start(date.today())
        wp = sm.process_week(week_start)
        return {"report": rep.to_dict(), "week_processing": wp}

    def get_stats(self, username):
        user = self.ensure_user(username)
        stats = self.db.query("SELECT * FROM stats WHERE user_id=%s", (user.id,), fetchone=True)
        last_reward = self.db.query("SELECT * FROM rewards WHERE user_id=%s ORDER BY id DESC LIMIT 1", (user.id,), fetchone=True)
        return {"total_points": int(stats['total_points'] or 0), "current_goal": int(stats['current_goal'] or GoalManager.BASE), "streak_weeks": int(stats['current_streak_weeks'] or 0), "last_reward": last_reward}

    def weekly_info(self):
        return {"base_goal": GoalManager.BASE, "increase_pct": 20, "checkpoints": [2,4,6,8], "notes":"Complete a week to increase streak; fail resets streak and goal."}

api = APIService(db)




@app.route("/")
def serve_home():
    return send_from_directory(FRONTEND_FOLDER, "index.html")



@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(FRONTEND_FOLDER, path)





# Flask endpoints


@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify({"pong": True})

@app.route("/api/add_habit", methods=["POST"])
def add_habit():
    data = request.get_json() or {}
    username = data.get("username", "default_user")
    name = data.get("habit_name")
    htype = data.get("habit_type")
    importance = data.get("importance", "medium")
    if not name or not htype:
        return jsonify({"error":"habit_name and habit_type required"}), 400
    try:
        out = api.add_habit(username, name, htype, importance)
        return jsonify({"success": True, "habit": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/get_habits", methods=["GET"])
def get_habits():
    username = request.args.get("username", "default_user")
    try:
        rows = api.get_habits(username)
        return jsonify({"habits": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/submit_report", methods=["POST"])
def submit_report():
    data = request.get_json() or {}
    username = data.get("username", "default_user")
    habit_id = data.get("habit_id")
    result = data.get("result")
    if not habit_id or result not in ('completed','failed'):
        return jsonify({"error":"habit_id and valid result required"}), 400
    try:
        out = api.submit_report(username, int(habit_id), result)
        return jsonify({"success": True, "detail": out})
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    except Error as me:
        return jsonify({"error": str(me)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/get_stats", methods=["GET"])
def get_stats():
    username = request.args.get("username", "default_user")
    try:
        s = api.get_stats(username)
        return jsonify({"total_points": s["total_points"], "current_goal": s["current_goal"], "streak_weeks": s["streak_weeks"], "last_reward": s["last_reward"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/get_weekly_reward_info", methods=["GET"])
def get_weekly_reward_info():
    try:
        return jsonify(api.weekly_info())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)

from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from mysql.connector import errors as mysql_errors

app = Flask(__name__)

# Pattern matching the PDF structure
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root123",
    database="levelup_ai"
)
cursor = db.cursor(dictionary=True)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/user_list", methods=["GET", "POST"])
def user_list():
    search_query = request.args.get('search', '')
    if search_query:
        cursor.execute("""
            SELECT u.*, COUNT(w.workout_id) AS workout_count
            FROM users u
            LEFT JOIN workouts w ON u.user_id = w.user_id
            WHERE u.username LIKE %s OR u.email LIKE %s OR u.full_name LIKE %s
            GROUP BY u.user_id
            ORDER BY u.user_id
        """, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute("""
            SELECT u.*, COUNT(w.workout_id) AS workout_count
            FROM users u
            LEFT JOIN workouts w ON u.user_id = w.user_id
            GROUP BY u.user_id
            ORDER BY u.user_id
        """)
    users = cursor.fetchall()
    return render_template("user_list.html", users=users)

@app.route("/user_registration", methods=["GET", "POST"])
def user_registration():
    error = None
    form_data = {}

    if request.method == "POST":
        username = request.form["username"].strip()
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip()
        age = request.form.get("age") or None
        weight = request.form.get("weight") or None
        height = request.form.get("height") or None
        fitness_level = request.form["fitness_level"]
        form_data = {
            "username": username,
            "full_name": full_name,
            "email": email,
            "age": age,
            "weight": weight,
            "height": height,
            "fitness_level": fitness_level,
        }

        cursor.execute("SELECT user_id FROM users WHERE email = %s OR username = %s", (email, username))
        if cursor.fetchone():
            error = "A user with that email or username already exists. Please choose a different one."
        else:
            insert_query = "INSERT INTO users (username, email, full_name, age, weight, height, fitness_level) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            try:
                cursor.execute(insert_query, (username, email, full_name, age, weight, height, fitness_level))
                db.commit()
                return redirect(url_for('user_list'))
            except mysql_errors.IntegrityError:
                db.rollback()
                error = "A user with that email or username already exists. Please choose a different one."

    return render_template("user_registration.html", error=error, form_data=form_data)

@app.route("/user_delete/<int:id>")
def user_delete(id):
    cursor.execute("DELETE FROM users WHERE user_id = %s", (id,))
    db.commit()
    return redirect(url_for('user_list'))

@app.route("/workout", methods=["GET", "POST"])
def workout():
    if request.method == "POST":
        user_id = request.form["user_id"]
        workout_name = request.form["exercise_name"]
        muscle = request.form["muscle_group"]
        weight = request.form.get("weight_kg") or None
        reps = request.form["reps"]
        sets = request.form["sets"]
        
        insert_workout = "INSERT INTO workouts (user_id, workout_name, muscle_group, weight_used, reps, sets, workout_date) VALUES (%s, %s, %s, %s, %s, %s, CURDATE())"
        cursor.execute(insert_workout, (user_id, workout_name, muscle, weight, reps, sets))
        db.commit()
        
    cursor.execute("SELECT w.*, u.username FROM workouts w JOIN users u ON w.user_id = u.user_id ORDER BY workout_date DESC")
    workouts = cursor.fetchall()
    
    # Stats logic for Chart.js
    cursor.execute("SELECT muscle_group, COUNT(*) as count FROM workouts GROUP BY muscle_group")
    chart_data = cursor.fetchall()
    
    return render_template("workout.html", workouts=workouts, chart_data=chart_data)

@app.route("/workout_delete/<int:id>")
def workout_delete(id):
    cursor.execute("DELETE FROM workouts WHERE workout_id = %s", (id,))
    db.commit()
    return redirect(url_for('workout'))

@app.route("/workout_aggregation", methods=["GET", "POST"])
def workout_aggregation():
    result = None
    group_col = None
    agg_header = None
    group_columns = ["user_id", "muscle_group", "workout_name"]
    agg_columns = ["weight_used", "reps", "sets"]
    if request.method == "POST":
        group_col = request.form["group_col"]
        agg_col = request.form["agg_col"]
        agg_func = request.form["agg_func"]
        agg_header = agg_func + " of " + agg_col
        if group_col == "user_id":
            query = f"SELECT u.user_id, u.username, {agg_func}({agg_col}) as agg_value FROM workouts w JOIN users u ON w.user_id = u.user_id GROUP BY u.user_id, u.username"
        else:
            query = f"SELECT {group_col}, {agg_func}({agg_col}) as agg_value FROM workouts GROUP BY {group_col}"
        cursor.execute(query)
        result = cursor.fetchall()
    return render_template(
        "workout_aggregation.html",
        result=result,
        gc=group_col,
        ag=agg_header,
        group_columns=group_columns,
        agg_columns=agg_columns
    )

@app.route("/posts", methods=["GET", "POST"])
def posts():
    if request.method == "POST":
        user_id = request.form["user_id"]
        content = request.form["content"]
        
        insert_post = "INSERT INTO posts (user_id, content) VALUES (%s, %s)"
        cursor.execute(insert_post, (user_id, content))
        db.commit()
        
    cursor.execute("SELECT p.*, u.username FROM posts p JOIN users u ON p.user_id = u.user_id ORDER BY created_at DESC")
    posts = cursor.fetchall()
    return render_template("posts.html", posts=posts)

@app.route("/post_delete/<int:id>")
def post_delete(id):
    cursor.execute("DELETE FROM posts WHERE post_id = %s", (id,))
    db.commit()
    return redirect(url_for('posts'))

@app.route("/goals", methods=["GET", "POST"])
def goals():
    if request.method == "POST":
        user_id = request.form["user_id"]
        goal_name = request.form["goal_name"]
        target = request.form["target_value"]
        deadline = request.form["deadline"]
        
        insert_goal = "INSERT INTO goals (user_id, goal_name, target_value, deadline) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_goal, (user_id, goal_name, target, deadline))
        db.commit()
        
    cursor.execute("SELECT g.*, u.username FROM goals g JOIN users u ON g.user_id = u.user_id")
    goals = cursor.fetchall()
    return render_template("goals.html", goals=goals)

@app.route("/goal_update/<int:id>", methods=["POST"])
def goal_update(id):
    current_val = request.form["current_value"]
    status = request.form["status"]
    cursor.execute("UPDATE goals SET current_value = %s, status = %s WHERE goal_id = %s", (current_val, status, id))
    db.commit()
    return redirect(url_for('goals'))

@app.route("/recommendations", methods=["GET", "POST"])
def recommendations():
    if request.method == "POST":
        user_id = request.form["user_id"]
        ai_tip = request.form["ai_tip"]
        category = request.form["category"]
        
        insert_rec = "INSERT INTO recommendations (user_id, ai_tip, category) VALUES (%s, %s, %s)"
        cursor.execute(insert_rec, (user_id, ai_tip, category))
        db.commit()
        
    cursor.execute("SELECT r.*, u.username FROM recommendations r JOIN users u ON r.user_id = u.user_id")
    recs = cursor.fetchall()
    return render_template("recommendations.html", recommendations=recs)

@app.route("/followers", methods=["GET", "POST"])
def followers():
    if request.method == "POST":
        user_id = request.form["user_id"]
        follower_id = request.form["follower_id"]
        
        insert_follow = "INSERT INTO followers (user_id, follower_id) VALUES (%s, %s)"
        cursor.execute(insert_follow, (user_id, follower_id))
        db.commit()
        
    cursor.execute("""
        SELECT f.*, u1.username as user_being_followed, u2.username as follower_name 
        FROM followers f 
        JOIN users u1 ON f.user_id = u1.user_id 
        JOIN users u2 ON f.follower_id = u2.user_id
    """)
    follow_list = cursor.fetchall()
    return render_template("followers.html", followers=follow_list)

@app.route("/follower_delete/<int:id>")
def follower_delete(id):
    cursor.execute("DELETE FROM followers WHERE follow_id = %s", (id,))
    db.commit()
    return redirect(url_for('followers'))

if __name__ == "__main__":
    app.run(debug=True)

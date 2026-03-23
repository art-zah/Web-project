from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mysqldb import MySQL
from decouple import config

app = Flask(__name__)
app.config['MYSQL_HOST'] = config('MYSQL_HOST')
app.config['MYSQL_USER'] = config('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = config('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = config('MYSQL_DB')
app.config['MYSQL_PORT'] = int(config('MYSQL_PORT', default=3306))
app.secret_key = config('FLASK_SECRET_KEY')

mysql = MySQL(app)

def is_admin():
    if 'user_id' not in session:
            return False
    with app.app_context():
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT admin_club_id FROM users WHERE id = %s", 
            (session['user_id'],)
        )
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else False

def get_all_clubs():
    with app.app_context():
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, name, address FROM clubs")
        i_clubs = cursor.fetchall()  # [(id, name, address), ...]
        cursor.close()
        return [
            {"id": row[0], "name": row[1], "address": row[2]}
            for row in i_clubs
        ]
    
def get_computers_by_club(club_id):
    with app.app_context():
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id, model, status FROM computers WHERE club_id = %s",
            (club_id,)
        )
        computers = cursor.fetchall()
        cursor.close()
        return [
            {"id": row[0], "model": row[1], "status": row[2]}
            for row in computers
        ]

def get_clubs_with_computers():
    clubs = get_all_clubs()
    for club in clubs:
        club["computers"] = get_computers_by_club(club["id"])
    return clubs

def search_email(i):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT email FROM users WHERE id = %s", (i,))
    user = cursor.fetchone()
    cursor.close()
    return user

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/clubs", methods=["GET"])
def get_clubs():
    clubs = get_clubs_with_computers()
    return jsonify(clubs)

@app.route("/api/clubs/<int:club_id>/computers", methods=["GET"])
def get_computers(club_id):
    computers = get_computers_by_club(club_id)
    return jsonify(computers)

@app.route("/api/bookings", methods=["POST"])
def create_bookings():
    if "user_id" not in session:
        return jsonify({"error": "Требуется вход в аккаунт"}), 401
    
    data = request.get_json()
    club_id = data["club_id"]
    computer_id = data["computer_id"]
    user_id = session["user_id"]
    hours = data["hours"]


    cursor = mysql.connection.cursor()

    # Проверяем что компьютер существует и свободен
    cursor.execute(
        "SELECT status FROM computers WHERE id = %s AND club_id = %s",
        (computer_id, club_id)
    )
    result = cursor.fetchone()

    if not result:
        cursor.close()
        return jsonify({"error": "Компьютер не найден"}), 404

    if result[0] != "free":
        cursor.close()
        return jsonify({"error": "Компьютер занят"}), 400

    # Получаем email
    cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        return jsonify({"error": "Пользователь не найден"}), 404
    user_name = user[0]

    start_time = datetime.now().isoformat()

    if not club_id or not computer_id or not hours:
            return jsonify({"error": "Некорректные данные"}), 400
    
    cursor.execute(
        """INSERT INTO bookings
           (user_name, club_id, computer_id, start_time, hours, status)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (user_name, club_id, computer_id, start_time, hours, "confirmed")
    )

    cursor.execute(
        "UPDATE computers SET status = 'busy' WHERE id = %s",
        (computer_id,)
    )

    mysql.connection.commit()
    cursor.close()

    return jsonify({"success": True}), 201

@app.route('/admin')
def admin_panel():
    club_id = is_admin()
    if not club_id:
        return redirect(url_for('login'))
    
    # Получаем компьютеры клуба
    with app.app_context():
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT * FROM computers WHERE club_id = %s",
            (club_id,)
        )
        computers = cursor.fetchall()
        cursor.close()
    
    return render_template('admin.html', computers=computers)

@app.route('/api/admin/update_status', methods=['POST'])
def update_computer_status():
    if not is_admin():
        return jsonify({'error': 'Доступ запрещён'}), 403

    data = request.get_json()
    computer_id = data['computer_id']
    new_status = data['status']

    with app.app_context():
        cursor = mysql.connection.cursor()
        cursor.execute(
            "UPDATE computers SET status = %s WHERE id = %s",
            (new_status, computer_id)
        )
        mysql.connection.commit()
        cursor.close()

    return jsonify({'success': True})

@app.route('/api/admin/add_computer', methods=['POST'])
def add_computer():
    club_id = is_admin()

    if not club_id:
        return jsonify({'error': 'Доступ запрещён'}), 403

    data = request.get_json()
    model = data['model'][:50]

    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO computers (club_id, model, status) VALUES (%s, %s, 'free')",
        (club_id, model)
    )
    mysql.connection.commit()
    new_id = cursor.lastrowid
    cursor.close()

    return jsonify({'success': True, 'id': new_id})

@app.route("/api/is-admin", methods=["GET"])
def check_admin():
    club_id = is_admin()
    if club_id != None and club_id != False:
        return jsonify({"is_admin": True})
    return jsonify({"is_admin": False})


if __name__ == "__main__":

    @app.route("/register", methods=["POST"])
    def register():
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email и пароль обязательны"}), 400

        # Хешируем пароль
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
                (email, hashed_password)
            )
            mysql.connection.commit()
            cursor.close()
            return jsonify({"message": "Регистрация прошла успешно"}), 201
        except Exception as er:
            return jsonify({"error": "Пользователь уже существует"}), 409

        
    
    @app.route("/login", methods=["POST"])
    def login():
        data = request.get_json()
        global email
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email и пароль обязательны"}), 400
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT id, password_hash, admin_club_id FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            cursor.close()

            if user and check_password_hash(user[1], password):
                session['user_id'] = user[0]
                session['admin_club_id'] = user[2]
                return jsonify({'message': 'Вход выполнен!'}), 200
            else:
                return jsonify({'error': 'Неверный email или пароль'}), 401
        except Exception as er:
            return jsonify({'error': "Ошибка"}), 500

    @app.route("/is-logged-in", methods=["GET"])
    def is_logged_in():
        if "user_id" in session:
            i = session["user_id"]
            user = search_email(i)
            return jsonify({"is_logged_in": True, "us": user}), 200
        else:
            return jsonify({"is_logged_in": False}), 401
    
    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return jsonify({"message": "Выход выполнен"}), 200


    app.run(debug=True, port = 5093)
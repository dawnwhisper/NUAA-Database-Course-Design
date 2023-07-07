from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from urllib.parse import unquote
from config import PASSWORD
from hashlib import md5
import datetime
import pymysql
import random

app = Flask(__name__, static_url_path='', static_folder='./', template_folder='templates')
app.secret_key = 'your_secret_key'
black_name_list = [';', 'union', 'select', '|', '#', '\'', '\"', '--', 'delete']

db = pymysql.connect(
    host='localhost',
    user='root',
    password=PASSWORD,
    database='CardDraw',
    cursorclass=pymysql.cursors.DictCursor
)

@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    else:
        return render_template('welcome.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password = md5(password.encode()).hexdigest()
        for i in black_name_list:
            if i in username:
                return render_template('login.html', error='Hacker!')
        cursor = db.cursor()
        query = "SELECT * FROM User WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        result = cursor.fetchone()
        cursor.close()
        # print(result)
        if result:
            session['username'] = username
            session['userid'] = result['UserID']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')
    else:
        return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password = md5(password.encode()).hexdigest()
        for i in black_name_list:
            if i in username:
                return render_template('register.html', error='Hacker!')
        cursor = db.cursor()
        query = "SELECT * FROM User WHERE username = %s"
        cursor.execute(query, username)
        result = cursor.fetchone()
        cursor.close()
        if result:
            return render_template('register.html', error='Username has been used')
        else:
            cursor = db.cursor()
            query = "select max(UserID) from User"
            cursor.execute(query)
            userid = cursor.fetchone()['max(UserID)'] + 1
            cursor.close()

            cursor = db.cursor()
            query = f"insert into User (UserID, Username, Password) value ({userid}, '{username}', '{password}');"
            print(query)
            cursor.execute(query)
            data = cursor.fetchone()
            db.commit()
            cursor.close()
            session['username'] = username
            session['userid'] = userid
            return render_template('login.html', error='Register successfully')
    else:
        return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/mycard')
def mycard():
    cursor = db.cursor()
    query = "select UC.UserCardID, C.Cardname, C.Rarity, C.Attribute, C.Destiny, UC.Level, C.Description from UserCard as UC, Card as C, User as U where UC.UserID = U.UserID and UC.CardID = C.CardID and U.UserID=%s order by Rarity desc"
    cursor.execute(query, (session['userid']))
    data = cursor.fetchall()
    cursor.close()
    # print(data)
    return render_template('mycard.html', data=data, username=session['username'])

@app.route("/upgrade-card", methods=["POST"])
def upgrade_card():
    user_card_id = request.json.get("user_card_id")
    sql = "UPDATE UserCard SET Level = Level + 1 WHERE UserCardID = %s"
    try:
        cursor = db.cursor()
        cursor.execute(sql, user_card_id)
        cursor.fetchone()
        db.commit()
        cursor.close()
        return "升级成功"
    except Exception as e:
        return str(e), 500

@app.route("/delete-card", methods=["POST"])
def delete_card():
    user_card_id = request.json.get("user_card_id")
    sql = "DELETE FROM UserCard WHERE UserCardID = %s"
    try:
        cursor = db.cursor()
        cursor.execute(sql, user_card_id)
        cursor.fetchone()
        db.commit()
        cursor.close()
        return "删除成功"
    except Exception as e:
        return str(e), 500

@app.route('/cardrecord', methods=["GET"])
def cardrecord():
    cursor = db.cursor()
    query = "select C.Cardname, C.Rarity, C.Attribute, C.Destiny, DR.DrawTime from Card as C, User as U, DrawRecord as DR where DR.UserID = U.UserID and DR.CardID = C.CardID and U.UserID=%s order by DrawTime asc"
    cursor.execute(query, (session['userid']))
    data = cursor.fetchall()
    cursor.close()
    # print(data)
    return render_template('cardrecord.html', data=data, username=session['username'])

def getCardData(page):
    cursor = db.cursor()
    query = "select Cardname, Rarity, Attribute, Destiny, Description from Card where CardID>=10*%s+1 and CardID<=10*%s+10;"
    cursor.execute(query, (page, page))
    data = cursor.fetchall()
    cursor.close()
    # print(data)
    return data

@app.route('/draw', methods=["GET"])
def draw():
    pagenum = request.args.get("page")
    pagenum = pagenum if pagenum else 1
    data = getCardData(int(pagenum)-1)
    return render_template('draw.html', data=data, username=session['username'], page=pagenum)

def Random_choice(seq, prob):
    p = random.random()
    for i in range(len(seq)):
        if sum(prob[:i]) < p <= sum(prob[:i+1]):
            return seq[i]

def GetAllCardID(Rary):
    cursor = db.cursor()
    cursor.execute(f"SELECT CardID FROM Card where Rarity={Rary};")
    data = cursor.fetchall()
    cursor.close()
    res = [i['CardID'] for i in data]
    return res

def Solve(userid, ids):
    names = []
    cursor = db.cursor()
    query = "select count(RecordID) from DrawRecord;"
    cursor.execute(query)
    maxnum = cursor.fetchone()['count(RecordID)']
    cursor.close()
    time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for id in ids:
        cursor = db.cursor()
        query = f"insert into UserCard (UserCardID, UserID, CardID, Level, AcquisitionTime) VALUES ({maxnum+1}, {userid}, {id}, 1, '{time}')"
        # print(query)
        cursor.execute(query)
        cursor.fetchone()
        db.commit()
        cursor.close()

        cursor = db.cursor()
        query = f"INSERT INTO DrawRecord (RecordID, UserID, CardID, DrawTime) VALUES ({maxnum+1}, {userid}, {id}, '{time}')"
        # print(query)
        cursor.execute(query)
        cursor.fetchone()
        db.commit()
        cursor.close()

        maxnum += 1

    return names

@app.route('/drawcard', methods=["POST"])
def drawcard():
    res = []
    # print(request.json)
    num = int(request.json['num'])
    for i in range(num):
        rary = Random_choice([5,4,3], [0.006, 0.051, 0.943])
        res.append(random.choice(GetAllCardID(rary)))
    Solve(session['userid'], res)
    names = []
    for id in res:
        cursor = db.cursor()
        cursor.execute(f"SELECT Cardname FROM Card where CardID={id};")
        data = cursor.fetchone()
        cursor.close()
        names.append(data['Cardname'])
    # print(names)
    return jsonify(names)

if __name__ == '__main__':
    app.run(debug=True, port=8080)


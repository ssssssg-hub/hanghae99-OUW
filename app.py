from pymongo import MongoClient
import jwt
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'PROJECTOUW'

# AWS 업로드해야 localhost로 작동한다.
# client = MongoClient('13.209.15.57', 27017, username="test", password="test")
client = MongoClient('localhost', 27017, username="test", password="test")


db = client.project_ouw

@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        return render_template('postlist.html', user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))

# UPDATE PROFILE
@app.route('/update_profile', methods=['POST'])
def update_profile():
    # Cookies에서 Token을 받아온다.
    token_receive = request.cookies.get('mytoken')
    try:
        # Token 정보 복호화 후 ID를 저장한다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        username = payload["id"]
        # Client로부터 파일을 받았을 때,
        if 'file_give' in request.files:
            # 파일확장자를 추출하여 Path 정보를 만든다.
            file = request.files["file_give"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]
            file_path = f"img_profile/{username}.{extension}"
            # Path 정보에 이미지 파일을 저장한다.
            file.save("./static/"+file_path)
            # DB에 저장할 Dict 변수를 만든다.
            new_doc = {
                'img': file_path
            }
        # DB업데이트한다.
        db.users.update_one({'username': payload['id']}, {'$set':new_doc})
        return jsonify({"result": "success", 'msg': '프로필을 업데이트했습니다.'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

# START : JOIN & LOGIN -----------------------------------------------------------
@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)

@app.route('/sign_in', methods=['POST'])
def sign_in():
    # 로그인
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
         'id': username_receive,
         'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        # token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})

@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,                               # 아이디
        "password": password_hash,                                  # 비밀번호
        "profile_pic": "",                                          # 프로필 사진 파일 이름
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})

# END : JOIN & LOGIN -----------------------------------------------------------

@app.route("/get_posts", methods=['GET'])
def get_posts():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        username_receive = request.args.get("username_give")

        isTotal = username_receive == None;

        if isTotal:
            posts = list(db.posts.find({}).sort("date", -1))
            print(posts)
        else:
            posts = list(db.posts.find({"user": username_receive}).sort("date", -1))
            user_post_info = {
                'count_posts':0,
                'count_likes':0,
                'count_comments': 0,
            };

        for post in posts:
            post["_id"] = str(post["_id"])
            post["count_likes"] = db.likes.count_documents({"postid": post["_id"]})
            post["count_comments"] = db.comments.count_documents({"postid": post["_id"]})
            
            if not isTotal:
                user_post_info['count_posts'] += 1
                user_post_info['count_likes'] += int(post["count_likes"])
                user_post_info['count_comments'] += int(post["count_comments"])
                print(user_post_info)

        if isTotal:
            return jsonify({"result": "success", "msg": "포스팅을 가져왔습니다.", "posts": posts})
        else:
            return jsonify({"result": "success", "msg": "포스팅을 가져왔습니다.", "posts": posts, 'user_post_info':user_post_info})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/mypost/<username>')
def mypost(username):
    # 각 사용자의 프로필과 글을 모아볼 수 있는 공간
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print(payload['id'])
        status = (username == payload["id"])  # 내 프로필이면 True, 다른 사람 프로필 페이지면 False
        user_info = db.users.find_one({"username": username}, {"_id": False})
        return render_template('mypost.html', username=payload['id'], user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route("/post/<postid>", methods=['GET'])
def get_post(postid):
    print(postid)
    return redirect(url_for("home"))

@app.route("/newpost")
def new_post():
    print('new_post 실행!')
    return redirect(url_for("home"))

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
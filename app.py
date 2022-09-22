from pymongo import MongoClient
import jwt
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import certifi

from bson.objectid import ObjectId

ca = certifi.where()

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'PROJECTOUW'

# AWS 업로드 시 경로 'localhost' 로 바꾸기!
# client = MongoClient('localhost', 27017, username="test", password="test")
client = MongoClient('13.209.15.57', 27017, username="test", password="test")
db = client.project_ouw


@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        return redirect(url_for("postlist", username=payload["id"]))
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route("/postlist")
def postlist():
    # Cookie로부터 token을 받아온다.
    token_receive = request.cookies.get('mytoken')
    try:
        # token 복호화하여  DB로부터 user 정보를 가져온다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # user_info = db.users.find_one({"username": payload["id"]})
        print(payload["id"])
        return render_template('postlist.html', username=payload["id"])
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        # token 복호화 오류 즉, login 상태가 아닌 경우 user_info 공란으로 돌려준다.
        print('오류페이지')
        return render_template('postlist.html', username='')

@app.route('/mypost/<pickuser>')
def mypost(pickuser):
    # 각 사용자의 프로필과 글을 모아볼 수 있는 공간
    # 나는 user, 픽한 사람, 매개변수의 username은 pick_user
    token_receive = request.cookies.get('mytoken')
    status = False
    user_info = db.users.find_one({"username": pickuser}, {"_id": False})
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        status = (pickuser == payload["id"])  # 내 프로필이면 True, 다른 사람 프로필 페이지면 False
        return render_template('mypost.html', username=payload['id'], user_info=user_info, status=status)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        # token 복호화 오류 즉, login 상태가 아닌 경우 username 공란으로 돌려준다.
        return render_template('mypost.html', username='', user_info=user_info, status=status)

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
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        # token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')

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
        "img": "",                                          # 프로필 사진 파일 이름
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
    # cookie에서 token을 받아온다.
    # token_receive = request.cookies.get('mytoken')
    try:
        # payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # username이 전달되었는지 여부를 확인한다.
        username_receive = request.args.get("username_give")
        isTotal = username_receive == None;
        
        # username이 전달되지 않았다면
        if isTotal:
            # DB 내 모든 post를 가져온다.
            posts = list(db.posts.find({}).sort("date", -1))
        # username이 전달되었다면
        else:
            # DB 내 해당 user의 post만 가져온다.
            posts = list(db.posts.find({"user": username_receive}).sort("date", -1))
            # User 소개 정보를 Client에 전달하기 위해 dict 변수를 만든다.
            user_post_info = {
                'count_posts': 0,
                'count_likes': 0,
                'count_comments': 0,
            };

        # 가져온 post DB 전체 반복
        for post in posts:
            # post _id
            post["_id"] = str(post["_id"])
            post["count_likes"] = db.likes.count_documents({"postid": post["_id"]})
            post["count_comments"] = db.comments.count_documents({"postid": post["_id"]})

            if not isTotal:
                user_post_info['count_posts'] += 1
                user_post_info['count_likes'] += int(post["count_likes"])
                user_post_info['count_comments'] += int(post["count_comments"])

        if isTotal:
            return jsonify({"result": "success", "msg": "포스팅을 가져왔습니다.", "posts": posts})
        else:
            return jsonify({"result": "success", "msg": "포스팅을 가져왔습니다.", "posts": posts, 'user_post_info':user_post_info})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route("/post/<postid>", methods=['GET'])
def get_post(postid):
    print(postid);
    return redirect(url_for("home"))

@app.route("/newpost")
def new_post():
    # Cookie에서 Login Token을 가져온다.
    token_receive = request.cookies.get('mytoken')
    try:
        # Token 복호화 후 DB로부터 user 정보를 가져온다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        return render_template('newpost.html', username=payload["id"])
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        # token 복호화 오류 즉, login 상태가 아닌 경우 user_info 공란으로 돌려준다.
        return redirect(url_for("login", msg="로그인 해주세요."))

# @app.route('/newpost', methods=['GET'])
# def show_newpost():
#     newposts = list(db.diary.find({}, {'_id': False}))
#     return jsonify({'all_newpost':newposts})

@app.route('/newpost', methods=['POST'])
def save_newpost():
    token_receive = request.cookies.get('mytoken')
    try:
        # token 복호화 후 DB로부터 user 정보를 가져온다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})

        # title_receive = request.form['title_give'] 타이틀대신 주소
        content_receive = request.form['content_give']

        file = request.files["file_give"]

        extension = file.filename.split('.')[-1]

        today = datetime.now()
        mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

        filename = f'file-{mytime}'

        save_to = f'static/img_post/{filename}.{extension}'
        file.save(save_to)

        doc = {
            # 'title':title_receive, 타이틀대신 주소
            'user': user_info['username'],
            'content': content_receive,
            'img': f'{filename}.{extension}',
            'date': today.strftime('%Y년%m월%d일 %H시%M분%S초')
        }

        db.posts.insert_one(doc)

        return jsonify({'msg': '저장 완료!'})
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        # token 복호화 오류 즉, login 상태가 아닌 경우 user_info 공란으로 돌려준다.
        return redirect(url_for("login", msg="로그인 해주세요."))

@app.route("/detail/<postid>")
def detail_post(postid):
    print(postid)
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    myid = payload["id"]

    post = db.posts.find_one({"_id": ObjectId(postid)})
    print(post)

    likes = list(db.likes.find({"postid": postid }))
    print(likes)
    count_likes = 0
    alreadylike = False
    for like in likes:
        count_likes += 1

        if like['user'] == myid:
            alreadylike = True

    comments = list(db.comments.find({"postid": postid}))
    return render_template('detail.html', username=payload["id"], post=post, comments=comments, count_likes=count_likes, alreadylike=alreadylike)


@app.route("/write_comment", methods=['POST'])
def write_comment():
    token_receive = request.cookies.get('mytoken')
    try:
        # token 복호화 후 DB로부터 user 정보를 가져온다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        comment_receive = request.form['comment_give']
        postid_receive = request.form['postid_give']

        doc = {
            'user': payload['id'],
            'postid': postid_receive,
            'content': comment_receive
        }
        db.comments.insert_one(doc)
        return jsonify({'msg': '저장 완료!'})
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        # token 복호화 오류 즉, login 상태가 아닌 경우 user_info 공란으로 돌려준다.
        return redirect(url_for("login", msg="로그인 해주세요."))

@app.route("/update_like", methods=['POST'])
def update_like():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        user_info = db.users.find_one({"username": payload["id"]})
        post_id_receive = request.form["post_id_give"]
        action_receive = request.form["action_give"]

        doc = {
            "postid": post_id_receive,
            "user": user_info["username"],
        }
        if action_receive == "like":
            db.likes.insert_one(doc)
        else:
            db.likes.delete_one(doc)
        count = db.likes.count_documents({"postid": post_id_receive})
        print(count)
        return jsonify({"result": "success", 'msg': 'updated', "count": count})

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


# @app.route("/get_comments", methods=['GET'])
# def get_comments():
#     # 전달받은 POST ID 저장
#     postid_receive = request.args.get("postid_give")
#     # DB검색
#     comments = list(db.comments.find({"postid": postid_receive}))
#     print(comments)
#     return jsonify({'comments': comments, 'postid': postid_receive})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
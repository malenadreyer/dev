from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import x 
import requests
import time
import uuid
import os
import dictionary
import csv
import io
import json


from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

app = Flask(__name__)

# Set the maximum file size to 10 MB
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024   # 1 MB

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Sørg for mappen eksisterer
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS ={"png", "jpg", "jpeg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

##############################
##############################
##############################
def _____USER_____(): pass 
##############################
##############################
##############################

@app.get("/file")
def view_file_preview():
    return render_template("file_preview.html")



@app.get("/")
def view_index():
    return render_template("index.html")


##############################
@app.context_processor
def global_variables():
    return dict (
        dictionary = dictionary,
        x = x
    )
 

##############################
@app.route("/login", methods=["GET", "POST"])
@app.route("/login/<lan>", methods=["GET", "POST"])
@x.no_cache
def login(lan = "english"):
 
    lan_map = {
        "english": "en",
        "danish": "dk",
        "spanish": "sp",
    }

    lan = lan_map.get(lan, "en")
 
    if lan not in dictionary.allowed_languages: lan = "english"
    x.default_language = lan
    dictionary.default_language = lan

   

    if request.method == "GET":
        if session.get("user", ""): return redirect(url_for("home"))
        return render_template("login.html", lan=lan)

    if request.method == "POST":
        try:
            # Validate           
            user_email = x.validate_user_email(lan)
            user_password = x.validate_user_password(lan)
            # Connect to the database
            q = "SELECT * FROM users WHERE user_email = %s"
            db, cursor = x.db()
            cursor.execute(q, (user_email,))
            user = cursor.fetchone()
            if not user: raise Exception(dictionary.user_not_found[lan], 400)

            if not check_password_hash(user["user_password"], user_password):
                 raise Exception(dictionary.invalid_credentials[lan], 400)

            if user["user_verification_key"] != "":
                raise Exception(dictionary.user_not_verified[lan], 400)

            user.pop("user_password")
            # TODO: add the default langauge to the user
            user["user_language"] = lan
            session["user"] = user
            return f"""<browser mix-redirect="/home"></browser>"""

        except Exception as ex:
            ic(ex)

            # User errors
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<browser mix-update="#toast">{ toast_error }</browser>""", 400

            # System or developer error
            toast_error = render_template("___toast_error.html", message="System under maintenance")
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()




##############################
@app.route("/signup", methods=["GET", "POST"])
@app.route("/signup/<lan>", methods=["GET", "POST"])
def signup(lan = "english"):

    lan_map = {
        "english": "en",
        "danish": "dk",
        "spanish": "sp",
    }

    lan = lan_map.get(lan, "en")
 
    if lan not in dictionary.allowed_languages: lan = "english"
    x.default_language = lan
    dictionary.default_language = lan
  


    if request.method == "GET":
        return render_template("signup.html", lan=lan)

    if request.method == "POST":
        try:
            # Validate
            user_email = x.validate_user_email(lan)
            user_password = x.validate_user_password(lan)
            user_username = x.validate_user_username(lan)
            user_first_name = x.validate_user_first_name(lan)

            user_pk = uuid.uuid4().hex
            user_last_name = ""
            user_avatar_path = ""
            user_verification_key = uuid.uuid4().hex
            user_verified_at = 0
            user_deleted_at = 0

            user_hashed_password = generate_password_hash(user_password)

            # Connect to the database
            q = "INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s,%s)"
            db, cursor = x.db()
            cursor.execute(q, (user_pk, user_email, user_hashed_password, user_username, 
            user_first_name, user_last_name, user_avatar_path, user_verification_key, user_verified_at, user_deleted_at))
            db.commit()

            # send verification email
            email_verify_account = render_template("_email_verify_account.html", user_verification_key=user_verification_key)
            ic(email_verify_account)
            x.send_email(user_email, "Verify your account", email_verify_account)

            return f"""<mixhtml mix-redirect="{ url_for('login') }"></mixhtml>""", 400
        except Exception as ex:
            ic(ex)
            # User errors
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            
            # Database errors
            if "Duplicate entry" and user_email in str(ex): 
                toast_error = render_template("___toast_error.html", message="Email already registered")
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            if "Duplicate entry" and user_username in str(ex): 
                toast_error = render_template("___toast_error.html", message="Username already registered")
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            
            # System or developer error
            toast_error = render_template("___toast_error.html", message="System under maintenance")
            return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()



##############################
@app.get("/home")
@x.no_cache
def home():
    try:
        user = session.get("user", "")
        if not user: return redirect(url_for("login"))
        db, cursor = x.db()
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk ORDER BY RAND() LIMIT 5"
        cursor.execute(q)
        tweets = cursor.fetchall()
        ic(tweets)

        q = "SELECT * FROM trends ORDER BY RAND() LIMIT 3"
        cursor.execute(q)
        trends = cursor.fetchall()
        ic(trends)

        q = "SELECT * FROM users WHERE user_pk != %s ORDER BY RAND() LIMIT 3"
        cursor.execute(q, (user["user_pk"],))
        suggestions = cursor.fetchall()
        ic(suggestions)

        lan = session["user"]["user_language"]

        return render_template("home.html", dictionary=dictionary, lan=lan, tweets=tweets, trends=trends, suggestions=suggestions, user=user)
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.route("/verify-account", methods=["GET"])
def verify_account():
    try:
        lan = session.get("user",{}).get("user_language","en")
        user_verification_key = x.validate_uuid4_without_dashes(request.args.get("key", ""), lan)
        user_verified_at = int(time.time())
        db, cursor = x.db()
        q = "UPDATE users SET user_verification_key = '', user_verified_at = %s WHERE user_verification_key = %s"
        cursor.execute(q, (user_verified_at, user_verification_key))
        db.commit()
        if cursor.rowcount != 1: raise Exception("Invalid key", 400)
        return redirect( url_for('login') )
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        # User errors
        if ex.args[1] == 400: return ex.args[0], 400    

        # System or developer error
        return "Cannot verify user"

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/logout")
def logout():
    try:
        session.clear()
        return redirect(url_for("login"))
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        pass



##############################
@app.get("/home-comp")
@x.no_cache
def home_comp():
    try:
        user = session.get("user", "")
        if not user: return redirect(url_for("login"))
        
        db, cursor = x.db()
        
        q = """
            SELECT 
                posts.*,
                users.user_first_name,
                users.user_last_name,
                users.user_username,
                users.user_avatar_path,
                CASE WHEN likes.like_pk IS NOT NULL THEN 1 ELSE 0 END as user_has_liked
            FROM posts
            JOIN users ON posts.post_user_fk = users.user_pk
            LEFT JOIN likes ON posts.post_pk = likes.like_post_fk AND likes.like_user_fk = %s
            ORDER BY posts.post_created_at DESC
            LIMIT 20
        """
        cursor.execute(q, (user["user_pk"],))
        tweets = cursor.fetchall()

        lan = session["user"]["user_language"]
        
        home_html = render_template("_home_comp.html", dictionary=dictionary, lan=lan, tweets=tweets, user=user)
        return f"""<browser mix-update="main">{home_html}</browser>"""
        
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/profile")
def profile():
    try:
        user = session.get("user", "")

        if not user: return "error"
        q = "SELECT * FROM users WHERE user_pk = %s"
        db, cursor = x.db()
        cursor.execute(q, (user["user_pk"],))
        user = cursor.fetchone()
        lan = session["user"]["user_language"]
        profile_html = render_template("_profile.html", x=x, user=user, dictionary=dictionary, lan=lan)
        return f"""<browser mix-update="main">{ profile_html }</browser>"""
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        pass

############################################
@app.get("/profile-watch")
@x.no_cache
def profile_watch():
    try:
        user = session.get("user", "")
        if not user: 
            return redirect(url_for("login"))
        
        db, cursor = x.db()
        
        # Hent bruger info
        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user["user_pk"],))
        user = cursor.fetchone()
        
        lan = session.get("user", {}).get("user_language", "english")
        
        profile_html = render_template("_profile_watch.html", 
                                      user=user, 
                                      dictionary=dictionary, 
                                      lan=lan)
        return f"""<browser mix-update="main">{profile_html}</browser>"""
        
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()  

##############################
# @app.patch("/like-tweet")
# @x.no_cache
# def api_like_tweet():
#     try:
#         button_unlike_tweet = render_template("___button_unlike_tweet.html")
#         return f"""
#             <mixhtml mix-replace="#button_1">
#                 {button_unlike_tweet}
#             </mixhtml>
#         """
#     except Exception as ex:
#         ic(ex)
#         return "error"
#     finally:
#         if "cursor" in locals(): cursor.close()
#         if "db" in locals(): db.close()


##############################
@app.route("/api-create-post", methods=["POST"])
def api_create_post():
    try:
        user = session.get("user", "")
        if not user: return "invalid user"
        user_pk = user["user_pk"]        
        post = x.validate_post(request.form.get("post", ""))
        post_pk = uuid.uuid4().hex
        db, cursor = x.db()
        q = "INSERT INTO posts VALUES(%s, %s, %s, %s,%s)"
        cursor.execute(q, (post_pk, user_pk, post, 0,0))
        db.commit()
        toast_ok = render_template("___toast_ok.html", message="The world is reading your post !")
        tweet = {
            "user_first_name": user["user_first_name"],
            "user_last_name": user["user_last_name"],
            "user_username": user["user_username"],
            "user_avatar_path": user["user_avatar_path"],
            "post_message": post,
        }
        html_post_container = render_template("___post_container.html")
        html_post = render_template("_tweet.html", tweet=tweet)
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-top="#posts">{html_post}</browser>
            <browser mix-replace="#post_container">{html_post_container}</browser>
        """
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        # User errors
        if "x-error post" in str(ex):
            toast_error = render_template("___toast_error.html", message=f"Post - {x.POST_MIN_LEN} to {x.POST_MAX_LEN} characters")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # System or developer error
        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()    



##############################
@app.route("/api-update-profile", methods=["POST"])
def api_update_profile():

    try:
        lan = session["user"]["user_language"]
        

        user = session.get("user", "")
        if not user: return "invalid user"

        # Validate
        user_email = x.validate_user_email(lan)
        user_username = x.validate_user_username(lan)
        user_first_name = x.validate_user_first_name(lan)
        user_last_name=request.form.get("user_last_name", "").strip()
        user_avatar_path = user.get("user_avatar_path", "")
        uploaded_file = request.files.get("user_avatar_path")

        if uploaded_file and uploaded_file.filename != "" and allowed_file(uploaded_file.filename):
            ext = os.path.splitext(uploaded_file.filename)[1]
            new_name = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            uploaded_file.save(save_path)
            user_avatar_path = new_name


        # Connect to the database
        q = "UPDATE users SET user_email = %s, user_username = %s, user_first_name = %s, user_last_name = %s, user_avatar_path=%s WHERE user_pk = %s"
        db, cursor = x.db()
        cursor.execute(q, (user_email, user_username, user_first_name, user_last_name, user_avatar_path, user["user_pk"]))
        db.commit()
        
        user["user_avatar_path"]= user_avatar_path
        session["user"] = user

        
        # Response to the browser
        toast_ok = render_template("___toast_ok.html", message="Profile updated successfully")
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-update="#profile_tag .name">{user_first_name}</browser>
            <browser mix-update="#profile_tag .handle">{user_username}</browser>
            <browser mix-replace="#profil_tag img"><img src="/static/uploads/{user_avatar_path}" alt="profil"></browser>
            
        """, 200
    except Exception as ex:
        ic(ex)
        if len(ex.args) > 1 and ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        # User errors
      
        
        # Database errors
        if "Duplicate entry" and user_email in str(ex): 
            toast_error = render_template("___toast_error.html", message="Email already registered")
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        if "Duplicate entry" and user_username in str(ex): 
            toast_error = render_template("___toast_error.html", message="Username already registered")
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        
        # System or developer error
        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


# ##############################
# @app.post("/api-search")
# def api_search():
#     try:
#         # TODO: The input search_for must be validated
#         search_for = request.form.get("search_for", "")
#         if not search_for:
#             return """
#             <browser mix-remove="#search_results"></browser>
#             """
#         part_of_query = f"%{search_for}%"
#         ic(search_for)
#         db, cursor = x.db()
#         q = "SELECT * FROM users WHERE user_username LIKE %s"
#         cursor.execute(q, (part_of_query,))
#         users = cursor.fetchall()
#         orange_box = render_template("_orange_box.html", users=users)
#         return f"""
#             <browser mix-remove="#search_results"></browser>
#             <browser mix-bottom="#search_form">{orange_box}</browser>
#         """
#     except Exception as ex:
#         ic(ex)
#         return str(ex)
#     finally:
#         if "cursor" in locals(): cursor.close()
#         if "db" in locals(): db.close()


##############################
@app.post("/api-search")
def api_search():
    try:
        # TODO: The input search_for must be validated
        search_for = request.form.get("search_for", "")
        if not search_for: return """empty search field""", 400
        part_of_query = f"%{search_for}%"
        ic(search_for)
        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_username LIKE %s"
        cursor.execute(q, (part_of_query,))
        users = cursor.fetchall()
        return jsonify(users)
    except Exception as ex:
        ic(ex)
        return str(ex)
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

#####################################
@app.get("/get-data-from-sheet")
def get_data_from_sheet():
    try:

        # Check if the admin is running this end-point, else show error

        # flaskwebmail
        # Create a google sheet
        # share and make it visible to "anyone with the link"
        # In the link, find the ID of the sheet. Here: 1aPqzumjNp0BwvKuYPBZwel88UO-OC_c9AEMFVsCw1qU
        # Replace the ID in the 2 places bellow
        url= f"https://docs.google.com/spreadsheets/d/{x.google_spread_sheet_key}/export?format=csv&id={x.google_spread_sheet_key}"
        res=requests.get(url=url)
        # ic(res.text) # contains the csv text structure
        csv_text = res.content.decode('utf-8')
        csv_file = io.StringIO(csv_text) # Use StringIO to treat the string as a file
        
        # Initialize an empty list to store the data
        data = {}

        # Read the CSV data
        reader = csv.DictReader(csv_file)
        ic(reader)
        # Convert each row into the desired structure
        for row in reader:
            item = {
                    'english': row['english'],
                    'danish': row['danish'],
                    'spanish': row['spanish']
                
            }
            # Append the dictionary to the list
            data[row['key']] = (item)

        # Convert the data to JSON
        json_data = json.dumps(data, ensure_ascii=False, indent=4) 
        # ic(data)

        # Save data to the file
        with open("dictionary.json", 'w', encoding='utf-8') as f:
            f.write(json_data)

        return "ok"
    except Exception as ex:
        ic(ex)
        return str(ex)
    finally:
        pass

    ##############################
@app.post("/forgot-password")
def forgot_password():
    try:
        user_email = request.form.get("user_email").strip()
        if not user_email:
            raise Exception("Email is required", 400)

        # Fetch user by email
        db, cursor = x.db()
        q = "SELECT user_pk FROM users WHERE user_email = %s AND user_deleted_at = 0"
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()

        if not user:
            raise Exception ("User not found", 400)

        # Generate a reset token
        reset_token = str(uuid.uuid4())
        
        

        # Store the reset token in the database
        q = "UPDATE users SET user_verification_key = %s WHERE user_pk = %s"
        cursor.execute(q, (reset_token, user["user_pk"]))
        db.commit()

        # Send the reset email (pass only the reset token)
        x.send_reset_email(user_email, reset_token)

        toast = render_template("___toast_ok.html", message= "A reset link has been to your email.")
        return f"""<mixhtml mix-bottom="#toast">{toast}</mixhtml>""", 200

    except Exception as ex:
        if "db" in locals(): db.rollback()
        
        message = ex.args[0] if len(ex.args) > 0 else "Error occurred"
        toast = render_template("___toast_error.html", message=message)
        return f"""<mixhtml mix-bottom="#toast">{toast}</mixhtml>""", 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

########################################
@app.route("/reset-password", methods=["POST"])
def reset_password_post():
    #TODO: Make sure that you can only reset your password ones, 
    # or at least get a message if you should do it
    try:
        token = request.form.get("token", "")
        new_password = request.form.get("user_password", "").strip()

        if not token or not new_password:
            return "Missing data", 400
    
        new_password = x.validate_user_password()

        db, cursor = x.db()
        cursor.execute("SELECT user_pk FROM users WHERE user_verification_key = %s", (token,))
        user = cursor.fetchone()
        if not user:
            return "Invalid token", 400

    # Gem ny kode og nulstil token
        hashed = generate_password_hash(new_password)
        cursor.execute(
            "UPDATE users SET user_password = %s, user_verification_key = '' WHERE user_pk = %s",
            (hashed, user["user_pk"])
        )
        db.commit()
        toast = render_template("___toast_ok.html", message="Password updated successfully")
        return f"""<mixhtml mix-bottom="#toast">{toast}</mixhtml>""", 200

    except Exception as ex:
        message = ex.args[0] if len(ex.args) > 0 else "System error"
        toast = render_template("___toast_error.html", message=message)
        return f"""<mixhtml mix-bottom="#toast">{toast}</mixhtml>""", 400

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


########################################
@app.route("/reset-password", methods=["GET"])
def reset_password_page():
    token = request.args.get("token", "")
    if not token:
        return "Invalid or missing token", 400

    # Tjek om token findes i DB
    db, cursor = x.db()
    try:
        cursor.execute("SELECT user_pk FROM users WHERE user_verification_key = %s", (token,))
        user = cursor.fetchone()
        if not user:
            toast = render_template("___toast_error.html", message="Invalid or expired token")
            return f"""<mixhtml mix-bottom="#toast">{toast}</mixhtml>""", 400

        return render_template("reset_password.html", token=token)

    finally:
        cursor.close()
        db.close()

###############################################
@app.route("/forgot-password", methods=["GET"])
def forgot_password_page():
    return render_template("forgot_password.html")



##################################################
@app.route("/api-like-post", methods=["POST"])
def api_like_post():
 
    if request.method == "POST":
        try:
            user = session.get("user", "")
            if not user: return "Unauthorized", 401
            
            user_pk = user["user_pk"]
            post_pk = request.form.get("post_pk", "").strip()
            like_pk = uuid.uuid4().hex 
            like_created_at = datetime.now()
            q = "INSERT INTO likes VALUES(%s, %s, %s, %s)"
            db, cursor = x.db()
            cursor.execute(q, (like_pk, user_pk, post_pk, like_created_at))
            db.commit()
            ic(ex)

            return "error"
        except Exception as ex:
            ic(ex)
            return "error"
        
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()



################################################
# @app.post("/api-add-comment")
# def api_add_comment():
#     try:
#         user = session.get("user", "")
#         if not user: 
#             return "Unauthorized", 401
        
#         post_pk = request.form.get("post_pk", "").strip()
#         comment_message = request.form.get("comment_message", "").strip()
        
#         if not post_pk or not comment_message:
#             return "Invalid data", 400
        
#         if len(comment_message) < 1 or len(comment_message) > 280:
#             return "Comment must be 1-280 characters", 400
        
#         db, cursor = x.db()
        
#         comment_pk = uuid.uuid4().hex
#         comment_created_at = int(time.time())
        
#         q = "INSERT INTO comments VALUES(%s, %s, %s, %s, %s)"
#         cursor.execute(q, (comment_pk, user["user_pk"], post_pk, comment_message, comment_created_at))
#         db.commit()
        
#         # Hent opdateret antal comments
#         q = "SELECT post_comments FROM posts WHERE post_pk = %s"
#         cursor.execute(q, (post_pk,))
#         post = cursor.fetchone()
        
#         toast_ok = render_template("___toast_ok.html", message="Comment added!")
#         return f"""
#             <browser mix-bottom="#toast">{toast_ok}</browser>
#             <browser mix-update="[data-post-pk='{post_pk}'] .comment-count">{post['post_comments']}</browser>
#         """, 200
        
#     except Exception as ex:
#         ic(ex)
#         return "Error", 500
#     finally:
#         if "cursor" in locals(): cursor.close()
#         if "db" in locals(): db.close()

@app.route("/api-get-post")
def api_get_post():
    try:
        post_pk = request.args.get("post_pk", "")
        if not post_pk: return "invalid post"

        db, cursor = x.db()
        q = "SELECT post_message FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        post = cursor.fetchone()

        if not post:
            return "post not found"

        return post["post_message"]

    except Exception as ex:
        ic(ex)
        return "system error", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##################################################

@app.route("/api-edit-post", methods=["POST"])
def api_edit_post():
    try:
        user = session.get("user", "")
        if not user: 
            return "invalid user"
        user_pk = user["user_pk"]

        post_pk = request.form.get("post_pk", "").strip()
        if not post_pk:
            return "invalid post"

        new_text = x.validate_post(request.form.get("post", ""))

        db, cursor = x.db()

        # Check ownership
        q = "SELECT user_fk FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        post = cursor.fetchone()
        if not post or post["user_fk"] != user_pk:
            return "not allowed"

        # Update
        q = "UPDATE posts SET post_message = %s WHERE post_pk = %s"
        cursor.execute(q, (new_text, post_pk))
        db.commit()

        # Update frontend
        return f"""
            <browser mix-update="[data-post-pk='{post_pk}'] .post-text">{new_text}</browser>
        """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        if "x-error post" in str(ex):
            toast_error = render_template("___toast_error.html", message=f"Post - {x.POST_MIN_LEN} to {x.POST_MAX_LEN} characters")
            return f"<browser mix-bottom='#toast'>{toast_error}</browser>"

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"<browser mix-bottom='#toast'>{toast_error}</browser>", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
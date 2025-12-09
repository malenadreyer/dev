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
ALLOWED_EXTENSIONS ={"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


##############################
@app.context_processor
def global_variables():
    return dict (
        dictionary = dictionary,
        x = x,
        lans=x.lans,
        
    )
############################## SAVES LANGUAGE ###############
@app.before_request
def set_language():
    """Set language for every request"""
    user = session.get("user", "")
    if user:
        lan = user.get("user_language", "english")
    else:
        lan = session.get("lan", "english")
    
    x.default_language = lan
###############################
@app.get("/file")
def view_file_preview():
    return render_template("file_preview.html")

##############################
##############################
##############################
def _____USER_____(): pass 
##############################
##############################
##############################




@app.get("/")
def view_index():
    return render_template("index.html")


################################# LOGIN #####################################
@app.route("/login", methods=["GET", "POST"])
@app.route("/login/<lan>", methods=["GET", "POST"])
@x.no_cache 
def login(lan = "english"):
    # Validate language parameter
    if lan not in x.allowed_languages: 
        lan = "english"
    
    # Set default language in x module
    x.default_language = lan

    if request.method == "GET":
        return render_template("login.html", lan=lan, x=x)

    if request.method == "POST":
        try:
            # Validate user input
            user_email = x.validate_user_email(lan)
            user_password = x.validate_user_password(lan)
            
            db, cursor = x.db()

            # Query database for user
            q = "SELECT * FROM users WHERE user_email = %s"
            cursor.execute(q, (user_email,))
            user = cursor.fetchone()
            
            # Check if user exists
            if not user: 
                raise Exception(x.lans("user_not_found"), 400) 
            
            # Check if user is blocked
            if user["user_is_blocked"] == 1:
                raise Exception(x.lans("user_is_blocked"), 400)

            # Verify password hash
            if not check_password_hash(user["user_password"], user_password):
                raise Exception(x.lans("wrong_password_or_email"), 400) 

            # Check if user has verified email
            if user["user_verification_key"] != "":
                raise Exception(x.lans("user_not_verified"), 400) 

            # Store user in session
            session["user_pk"] = user["user_pk"]
            session["lan"] = lan
            user.pop("user_password")
            session["user"] = dict(user)
            session["user"]["user_language"] = lan
            session.modified = True 

            
            return f"""
                <browser mix-redirect="/home"></browser>
            """

        except Exception as ex:
            ic(ex)

            # User errors (validation, wrong password, etc.)
            if len(ex.args) > 1 and ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 400

            # System or developer error
            toast_error = render_template("___toast_error.html", message=x.lans("system_maintenance"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500
        
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()


################################# LOGOUT ####################################
@app.get("/logout")
def logout():
    try:
        # Save the user's language preference before clearing session
        lan = session.get("user", {}).get("user_language", "english")
        # Clear all session data (logs out the user)
        session.clear()

        # Restore the language preference in session
        session["lan"] = lan
        return redirect(url_for("login", lan=lan))
    except Exception as ex:
        ic(ex)
        return "error"


################################## SIGN UP ###################################
@app.route("/signup", methods=["GET", "POST"])
@app.route("/signup/<lan>", methods=["GET", "POST"])
@x.no_cache
def signup(lan = "english"):

    if lan not in x.allowed_languages: 
        lan = "english"
    
    # Set default language in x module
    x.default_language = lan

    if request.method == "GET":
        return render_template("signup.html", lan=lan, x=x)

    if request.method == "POST":
        try:
            # Validate
            user_email = x.validate_user_email(lan)
            user_password = x.validate_user_password(lan)
            user_username = x.validate_user_username(lan)
            user_first_name = x.validate_user_first_name(lan)

            user_hashed_password = generate_password_hash(user_password)
            
            # Connect to the database
            db, cursor = x.db()
            
            # Tjek om email allerede eksisterer (kun aktive brugere)
            q_check_email = "SELECT * FROM users WHERE user_email = %s AND (user_deleted_at = 0 OR user_deleted_at IS NULL)"
            cursor.execute(q_check_email, (user_email,))
            existing_email = cursor.fetchone()
            
            if existing_email:
                raise Exception(x.lans("email_already_registered"), 400)
            
            # Tjek om username allerede eksisterer (kun aktive brugere)
            q_check_username = "SELECT * FROM users WHERE user_username = %s AND (user_deleted_at = 0 OR user_deleted_at IS NULL)"
            cursor.execute(q_check_username, (user_username,))
            existing_username = cursor.fetchone()
            
            if existing_username:
                raise Exception(x.lans("username_already_registered"), 400)
            
            # Tjek om der er en soft deleted bruger med samme email
            q_check_deleted = "SELECT * FROM users WHERE user_email = %s AND user_deleted_at != 0"
            cursor.execute(q_check_deleted, (user_email,))
            deleted_user = cursor.fetchone()
            
            if deleted_user:
                # Genaktiver den slettede konto
                import time
                q_reactivate = """UPDATE users 
                                 SET user_deleted_at = 0, 
                                     user_password = %s,
                                     user_username = %s,
                                     user_first_name = %s
                                 WHERE user_email = %s"""
                cursor.execute(q_reactivate, (user_hashed_password, user_username, user_first_name, user_email))
                db.commit()
                
                toast_ok = render_template("___toast_ok.html", message=x.lans("account_reactivated"))
                return f"""
                    <browser mix-bottom="#toast">{toast_ok}</browser>
                    <browser mix-redirect="/login"></browser>
                """
            
            # Opret ny bruger
            user_pk = uuid.uuid4().hex
            user_last_name = ""
            user_avatar_path = ""
            user_verification_key = uuid.uuid4().hex
            user_verified_at = 0
            user_deleted_at = 0
            user_bio = ""  # Tilføjet
            user_followers = 0  # Tilføjet
            user_following = 0  # Tilføjet
            user_cover_path = ""  # Tilføjet
            user_admin = 0  # Tilføjet
            user_is_blocked = 0  # Tilføjet

            q = """INSERT INTO users VALUES(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )"""

            cursor.execute(q, (
    user_pk, 
    user_email, 
    user_hashed_password, 
    user_username, 
    user_first_name, 
    user_last_name, 
    user_avatar_path, 
    user_verification_key, 
    user_verified_at, 
    user_bio,  
    user_followers,  
    user_following,  
    user_cover_path,  
    user_admin,  
    user_is_blocked, 
    user_deleted_at
))
            db.commit()

            # Send verification email
            email_verify_account = render_template("_email_verify_account.html", user_verification_key=user_verification_key)
            x.send_email(user_email, "Verify your account", email_verify_account)

            toast_ok = render_template("___toast_ok.html", message=x.lans("account_created_check_email"))
            return f"""
                <browser mix-bottom="#toast">{toast_ok}</browser>
                <browser mix-redirect="/login"></browser>
            """
            
        except Exception as ex:
            ic(ex)
            if "db" in locals(): 
                db.rollback()
            
            # User errors
            if len(ex.args) > 1 and ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 400
            
            # System or developer error
            toast_error = render_template("___toast_error.html", message=x.lans("system_under_maintenance"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

############################## FORGOT PASSWORD ################################
@app.post("/forgot-password")
def forgot_password():
    try:
        # Get email from form
        user_email = request.form.get("user_email").strip()
        if not user_email:
            raise Exception("Email is required", 400)

        # Fetch user by email
        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s"
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

        # Send the reset email
        x.send_reset_email(user_email, reset_token)

        # Show success message
        toast = render_template("___toast_ok.html", message=x.lans("reset_link_sent"))
        return f"""<mixhtml mix-bottom="#toast">{toast}</mixhtml>""", 200

    except Exception as ex:
        if "db" in locals(): db.rollback()
        
        message = ex.args[0] if len(ex.args) > 0 else "Error occurred"
        toast = render_template("___toast_error.html", message=message)
        return f"""<mixhtml mix-bottom="#toast">{toast}</mixhtml>""", 400
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################################RESET PASSWORD ################################
@app.route("/reset-password", methods=["POST"])
def reset_password_post():

    try:
        # Get token and new password from form
        token = request.form.get("token", "")
        new_password = request.form.get("user_password", "").strip()

        if not token or not new_password:
            return "Missing data", 400
    
        # Validate new password
        new_password = x.validate_user_password()

        # finding the user by reset token
        db, cursor = x.db()
        cursor.execute("SELECT user_pk FROM users WHERE user_verification_key = %s", (token,))
        user = cursor.fetchone()
        if not user:
            return "Invalid token", 400

        #new password and clear reset token
        hashed = generate_password_hash(new_password)
        cursor.execute(
            "UPDATE users SET user_password = %s, user_verification_key = '' WHERE user_pk = %s",
            (hashed, user["user_pk"])
        )
        db.commit()
        toast = render_template("___toast_ok.html", message=x.lans("password_updated_successfully"))
        return f"""<mixhtml mix-bottom="#toast">{toast}</mixhtml>""", 200

    except Exception as ex:
        message = ex.args[0] if len(ex.args) > 0 else "System error"
        toast = render_template("___toast_error.html", message=message)
        return f"""<mixhtml mix-bottom="#toast">{toast}</mixhtml>""", 400

    final

###############################FORGOT PASSWORD ################################
@app.route("/forgot-password", methods=["GET"])
def forgot_password_page():
    return render_template("forgot_password.html")
################################## HOME #######################################
@app.get("/home")
@x.no_cache
def home():
    
    try:
        # Check if user is logged in
        user = session.get("user", "")
        if not user: return redirect(url_for("login"))
        
        db, cursor = x.db()
        
        # Fetch all posts with user data
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk "
        cursor.execute(q)
        tweets = cursor.fetchall()
        ic(tweets)

        # Fetch random trending topics
        q = "SELECT * FROM trends ORDER BY RAND() LIMIT 3"
        cursor.execute(q)
        trends = cursor.fetchall()
        ic(trends)

        # Fetch random user suggestions (excluding blocked/deleted users)
        q = """
            SELECT users.*, 
             (SELECT COUNT(*) FROM follows 
             WHERE follow_follower_fk = %s 
            AND follow_following_fk = users.user_pk) as is_following
            FROM users 
            WHERE user_pk != %s 
            AND user_is_blocked = 0
            AND (user_deleted_at = 0 OR user_deleted_at IS NULL)
            ORDER BY RAND() 
            LIMIT 3
            """
        cursor.execute(q, (user["user_pk"], user["user_pk"]))
        suggestions = cursor.fetchall()

        lan = session["user"]

        return render_template("home.html", dictionary=dictionary, lan=lan, tweets=tweets, trends=trends, suggestions=suggestions, user=user)
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
################################ VERIFY ACCOUNT ###############################
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

################################### HOME COMP #################################
@app.get("/home-comp")
@x.no_cache
def home_comp():
    try:
        user = session.get("user", "")
        if not user: return redirect(url_for("login"))
        
        db, cursor = x.db()
        
        is_admin = user.get("user_admin", 0)  # Tjek admin status
        
        if is_admin:
            # Admin ser alle posts
            q = """
                SELECT 
                    posts.*,
                    users.user_first_name,
                    users.user_last_name,
                    users.user_username,
                    users.user_avatar_path,
                    COUNT(DISTINCT likes.like_pk) as post_total_likes,
                    COUNT(DISTINCT comments.comment_pk) as post_comments
                FROM posts
                JOIN users ON posts.post_user_fk = users.user_pk
                LEFT JOIN likes ON posts.post_pk = likes.like_post_fk
                LEFT JOIN comments ON posts.comment_post_fk = posts.post_pk
                GROUP BY posts.post_pk
                ORDER BY posts.post_created_at
            """
        else:
            # Normale brugere ser kun ikke-blokerede posts fra ikke-blokerede brugere
            q = """
                SELECT 
                    posts.*,
                    users.user_first_name,
                    users.user_last_name,
                    users.user_username,
                    users.user_avatar_path,
                    COUNT(DISTINCT likes.like_pk) as post_total_likes,
                    COUNT(DISTINCT comments.comment_pk) as post_comments
                FROM posts
                JOIN users ON posts.post_user_fk = users.user_pk
                LEFT JOIN likes ON posts.post_pk = likes.like_post_fk
                LEFT JOIN comments ON posts.comment_post_fk = posts.post_pk
                WHERE posts.post_is_blocked = 0 
                AND users.user_is_blocked = 0
                GROUP BY posts.post_pk
            """
        
        cursor.execute(q)
        tweets = cursor.fetchall()

        lan = user.get("user_language", "english")
        
        home_html = render_template("_home_comp.html", tweets=tweets, user=user, lan=lan)
        return f"""<browser mix-update="main">{home_html}</browser>"""
        
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################################# PROFILE EDIT ################################
@app.get("/profile")
def profile():
    try:
        # Check if user is logged in
        user = session.get("user", "")
        if not user: return "error"
        
        # Fetch fresh user data from database
        q = "SELECT * FROM users WHERE user_pk = %s"
        db, cursor = x.db()
        cursor.execute(q, (user["user_pk"],))
        user = cursor.fetchone()
        lan = session["user"]
        
        # Render profile page
        profile_html = render_template("_profile.html", x=x, user=user, dictionary=dictionary, lan=lan)
        return f"""<browser mix-update="main">{ profile_html }</browser>"""
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################################# PROFIL WATCH ################################
@app.get("/profile-watch")
@x.no_cache
def profile_watch():
    try:
        user = session.get("user", "")
        if not user: 
            return redirect(url_for("login"))
        db, cursor = x.db()
        
        # Fetching user info
        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user["user_pk"],))
        user = cursor.fetchone()
        
        # fetch user's post and other data aswell
        q_tweets = """
            SELECT 
                posts.*,
                users.user_first_name,
                users.user_last_name,
                users.user_username,
                users.user_avatar_path
            FROM posts
            JOIN users ON posts.post_user_fk = users.user_pk
            WHERE posts.post_user_fk = %s
        """
        cursor.execute(q_tweets, (user["user_pk"],))
        tweets = cursor.fetchall()
        
        lan = session.get("user", {}).get("user_language", "english")
        
        # Render profil, with the post aswell
        profile_html = render_template("_profile_watch.html", 
                                      user=user, 
                                      tweets=tweets, 
                                      dictionary=dictionary, 
                                      lan=lan)
        return f"""<browser mix-update="main">{profile_html}</browser>"""
        
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


################################ CREATE POST ##################################
@app.route("/api-create-post", methods=["POST"])
def api_create_post():
    try:
        user = session.get("user", "")
        if not user: return "invalid user"
        user_pk = user["user_pk"]        
        post = x.validate_post(request.form.get("post", ""))
        post_pk = uuid.uuid4().hex
        post_created_at = int(time.time())
        db, cursor = x.db()
        q = "INSERT INTO posts VALUES(%s, %s, %s, %s,%s, NULL, %s, %s)"
        cursor.execute(q, (post_pk, user_pk, post, 0,0, post_created_at, 0))
        db.commit()
        toast_ok = render_template("___toast_ok.html", message=x.lans("the_world_is_reading_your_post"))
        tweet = {
            "user_first_name": user["user_first_name"],
            "user_last_name": user["user_last_name"],
            "user_username": user["user_username"],
            "user_avatar_path": user["user_avatar_path"],
            "post_message": post,
            "post_created_at": post_created_at

        }
        html_post = render_template("_tweet.html", tweet=tweet, user=user)
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-top="#posts">{html_post}</browser>
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



############################## UPDATE PROFIL ###################################
@app.route("/api-update-profile", methods=["POST"])
@app.route("/api-update-profile/<lan>", methods=["POST"])
def api_update_profile(lan="english"):
    
    
    try:
        if lan not in x.allowed_languages:
            lan = "english" 
        x.default_language = lan
        
        user = session.get("user", "")
        if not user: return "invalid user"
        
        lan = user.get("user_language", "english")

        # Validate
        user_email = x.validate_user_email(lan)
        user_username = x.validate_user_username(lan)
        user_first_name = x.validate_user_first_name(lan)
        user_last_name = request.form.get("user_last_name", "").strip()
        user_avatar_path = user.get("user_avatar_path", "")
        user_cover_path = user.get("user_cover_path", "")
        user_bio = x.validate_bio()
        uploaded_avatar = request.files.get("user_avatar_path")
        uploaded_cover = request.files.get("user_cover_path")

        if uploaded_avatar and uploaded_avatar.filename != "" and allowed_file(uploaded_avatar.filename):
            ext = os.path.splitext(uploaded_avatar.filename)[1]
            new_name = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            uploaded_avatar.save(save_path)
            user_avatar_path = new_name
            
        if uploaded_cover and uploaded_cover.filename != "" and allowed_file(uploaded_cover.filename):
            ext = os.path.splitext(uploaded_cover.filename)[1]
            new_name = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            uploaded_cover.save(save_path)
            user_cover_path = new_name

        # Connect to the database
        q = "UPDATE users SET user_email = %s, user_username = %s, user_first_name = %s, user_last_name = %s, user_avatar_path=%s, user_bio = %s, user_cover_path=%s WHERE user_pk = %s"
        db, cursor = x.db()
        cursor.execute(q, (user_email, user_username, user_first_name, user_last_name, user_avatar_path, user_bio, user_cover_path, user["user_pk"]))
        db.commit()
        
        # Update session
        user["user_avatar_path"] = user_avatar_path
        user["user_cover_path"] = user_cover_path
        user["user_email"] = user_email
        user["user_username"] = user_username
        user["user_first_name"] = user_first_name
        user["user_last_name"] = user_last_name
        user["user_bio"] = user_bio
        user["user_language"] = lan  
        session["user"] = user
        session.modified = True

        # Response to the browser
        profile_html = render_template("_profile.html", x=x, user=user, dictionary=dictionary, lan=lan)

        toast_ok = render_template("___toast_ok.html", message=x.lans("profile_updated_successfully"))
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-update="main">{ profile_html }</browser>
        """, 200
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): 
            db.rollback()
        
        # User errors
        if len(ex.args) > 1 and ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 400
        
        # Database errors (kun check hvis variablerne er defineret)
        if user_email and "Duplicate entry" in str(ex) and user_email in str(ex): 
            toast_error = render_template("___toast_error.html", message=x.lans("email_already_registered"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 400
            
        if user_username and "Duplicate entry" in str(ex) and user_username in str(ex): 
            toast_error = render_template("___toast_error.html", message=x.lans("username_already_registered"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 400
        
        # System or developer error
        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

############################## DELETE PROFILE ##################################
@app.route("/delete-profile", methods=["GET"])
def delete_profile():
    try:
        user = session.get("user")

        # Check if user is logged in
        if not user: 
            return "error"
        
        # Fetch fresh user data from database
        q = "SELECT * FROM users WHERE user_pk = %s"
        db, cursor = x.db()
        cursor.execute(q, (user["user_pk"],))
        row = cursor.fetchone()

        # Render delete profile template
        delete_profile_html = render_template("___delete_profile.html", row=row)
        return f"""<browser mix-top="main">{ delete_profile_html }</browser>"""

    except Exception as ex:
        ic(ex)
        return "error"
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

############################# API DELETE PROFILE ###############################
@app.delete("/api-delete-profile")
def api_delete_profile():
    try:
        user = session.get("user", "")
        if not user: 
            return "invalid user", 401
        
        db, cursor = x.db()
        
        # Soft delete: Set user_deleted_at timestamp
        import time
        timestamp = int(time.time())
        
        # Soft delete user
        q = "UPDATE users SET user_deleted_at = %s WHERE user_pk = %s"
        cursor.execute(q, (timestamp, user["user_pk"]))
        
        # Delete all user's posts (hard delete)
        q = "DELETE FROM posts WHERE post_user_fk = %s"
        cursor.execute(q, (user["user_pk"],))
        
        # Delete all user's comments
        q = "DELETE FROM comments WHERE comment_user_fk = %s"
        cursor.execute(q, (user["user_pk"],))
        
        # Delete all user's likes
        q = "DELETE FROM likes WHERE like_user_fk = %s"
        cursor.execute(q, (user["user_pk"],))
        
        # Delete all user's follows (both following and followers)
        q = "DELETE FROM follows WHERE follow_follower_fk = %s OR follow_following_fk = %s"
        cursor.execute(q, (user["user_pk"], user["user_pk"]))
        
        db.commit()
        
        # Clear session
        session.clear()
        
        toast_ok = render_template("___toast_ok.html", message=x.lans("account_deleted"))
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-redirect="/login"></browser>
        """
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): 
            db.rollback()
        
        toast_error = render_template("___toast_error.html", message="Could not delete account")
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500
        
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################################## SEARCH ######################################
@app.post("/api-search")
def api_search():
    try:
        user = session.get("user", "")      
        if not user:
            return "unauthorized", 401
        
        # Validate search input
        search_for = request.form.get("search_for", "").strip()
        ic(f"Searching for: {search_for}")
        
        if not search_for: 
            return "error"
        part_of_query = f"%{search_for}%"
        db, cursor = x.db()
    
        
        # Start med en simpel query
        q = """
            SELECT * FROM users 
            WHERE (user_username LIKE %s 
               OR user_first_name LIKE %s 
               OR user_last_name LIKE %s)
            AND user_is_blocked = 0
            AND (user_deleted_at = 0 OR user_deleted_at IS NULL)
            LIMIT 5
        """
        
        cursor.execute(q, (part_of_query, part_of_query, part_of_query))
        users = cursor.fetchall()
        
        ic(f"Found {len(users)} users")
        
        return jsonify(users)
        
    except Exception as ex:
        ic(ex)
        return str(ex), 500
        
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


################################ RESET PASSWORD ################################
@app.route("/reset-password", methods=["GET"])
def reset_password_page():
    token = request.args.get("token", "")
    if not token:
        return "Invalid or missing token", 400

    # Check if the token is in the db
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

################################### LIKE #######################################
@app.route("/api-toggle-like", methods=["POST"])
def api_toggle_like():
    try:
        user = session.get("user", "")
        if not user: 
            return "Unauthorized", 401
        
        user_pk = user["user_pk"]
        post_pk = request.form.get("post_pk", "").strip()
        
        if not post_pk:
            return "Invalid post", 400
        
        db, cursor = x.db()
        
        # Tjek om like eksisterer
        q_check = "SELECT * FROM likes WHERE like_user_fk = %s AND like_post_fk = %s"
        cursor.execute(q_check, (user_pk, post_pk))
        existing = cursor.fetchone()
        
        if existing:
            # Unlike - slet
            q = "DELETE FROM likes WHERE like_user_fk = %s AND like_post_fk = %s"
            cursor.execute(q, (user_pk, post_pk))
            db.commit()
            
            # Tæl likes direkte
            q_count = "SELECT COUNT(*) as total FROM likes WHERE like_post_fk = %s"
            cursor.execute(q_count, (post_pk,))
            result = cursor.fetchone()
            total_likes = result["total"]
            
            # Return like knappen (tomt hjerte)
            button = render_template("___button_unlike_tweet.html", tweet={"post_pk": post_pk, "post_total_likes": total_likes})
        else:
            # Like - opret
            like_pk = uuid.uuid4().hex 
            like_created_at = int(time.time())
            
            q = "INSERT INTO likes VALUES(%s, %s, %s, %s)"
            cursor.execute(q, (like_pk, user_pk, post_pk, like_created_at))
            db.commit()
            
            # Tæl likes direkte
            q_count = "SELECT COUNT(*) as total FROM likes WHERE like_post_fk = %s"
            cursor.execute(q_count, (post_pk,))
            result = cursor.fetchone()
            total_likes = result["total"]
            
            # Return unlike knappen (fyldt hjerte)
            button = render_template("___button_like_tweet.html", tweet={"post_pk": post_pk, "post_total_likes": total_likes})
        
        return f"""<mixhtml mix-replace="#like-form-{post_pk}">{button}</mixhtml>"""

    except Exception as ex:
        ic(ex)  
        if "db" in locals(): 
            db.rollback()
        return "error", 500
                    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################################ CREATE COMMENT ################################
@app.route("/api-create-comment", methods=["POST"])
def api_create_comment():
    try:
        user = session.get("user", "")
        if not user: 
            return "Unauthorized", 401
        
        user_pk = user["user_pk"]
        post_pk = request.form.get("post_pk", "").strip()
        comment_message = x.validate_comment(request.form.get("comment_message", ""))
        
        if not post_pk:
            return "Invalid post", 400
        
        if not comment_message or len(comment_message) < 1:
            return "Comment cannot be empty", 400
        
        db, cursor = x.db()
        
        comment_pk = uuid.uuid4().hex 
        comment_created_at = int(time.time())
        
        q = "INSERT INTO comments VALUES(%s, %s, %s, %s, %s)"
        cursor.execute(q, (comment_pk, user_pk, post_pk, comment_message, comment_created_at))
        db.commit()
        
        # Tæl comments direkte
        q_count = "SELECT COUNT(*) as total FROM comments WHERE comment_post_fk = %s"
        cursor.execute(q_count, (post_pk,))
        result = cursor.fetchone()
        total_comments = result["total"]
        
        # Hent comment med bruger info
        q_get = """
            SELECT comments.*, users.user_first_name, users.user_last_name, 
                   users.user_username, users.user_avatar_path
            FROM comments
            JOIN users ON comments.comment_user_fk = users.user_pk
            WHERE comments.comment_pk = %s
        """
        cursor.execute(q_get, (comment_pk,))
        comment = cursor.fetchone()
        
        # Return den nye comment
        comment_html = render_template("_comment.html", comment=comment, user=user)
        return f"""
            <mixhtml mix-top="#comments-{post_pk}">{comment_html}</mixhtml>
            <mixhtml mix-replace="#comment-count-{post_pk}"><span id="comment-count-{post_pk}">{total_comments}</span></mixhtml>
        """

    except Exception as ex:
        ic(ex)  
        if "db" in locals(): 
            db.rollback()
        
        if len(ex.args) > 1 and ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-bottom="#toast">{toast_error}</mixhtml>""", 400
        
        toast_error = render_template("___toast_error.html", message="Could not post comment")
        return f"""<mixhtml mix-bottom="#toast">{toast_error}</mixhtml>""", 500
           
            
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################################## DELETE COMMENT ##############################
@app.route("/api-delete-comment", methods=["POST"])
def api_delete_comment():
    try:
        user = session.get("user", "")
        if not user: 
            return "Unauthorized", 401
        
        user_pk = user["user_pk"]
        comment_pk = request.form.get("comment_pk", "").strip()
        post_pk = request.form.get("post_pk", "").strip()
        
        if not comment_pk:
            return "Invalid comment", 400
        
        db, cursor = x.db()
        
        # Tjek at det er brugerens egen comment
        q_check = "SELECT * FROM comments WHERE comment_pk = %s AND comment_user_fk = %s"
        cursor.execute(q_check, (comment_pk, user_pk))
        comment = cursor.fetchone()
        
        if not comment:
            return "Not your comment", 403
        
        # Slet comment
        q = "DELETE FROM comments WHERE comment_pk = %s"
        cursor.execute(q, (comment_pk,))
        db.commit()
        
        # Tæl comments direkte
        q_count = "SELECT COUNT(*) as total FROM comments WHERE comment_post_fk = %s"
        cursor.execute(q_count, (post_pk,))
        result = cursor.fetchone()
        total_comments = result["total"]
        
        return f"""
            <mixhtml mix-remove="#comment-{comment_pk}"></mixhtml>
            <mixhtml mix-replace="#comment-count-{post_pk}"><span id="comment-count-{post_pk}">{total_comments}</span></mixhtml>
        """

    except Exception as ex:
        ic(ex)  
        if "db" in locals(): 
            db.rollback()
        return "error", 500
                    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

############################### GET COMMENTS ###################################
@app.route("/api-get-comments", methods=["GET"])
def api_get_comments():
    try:
        user = session.get("user", "")
        if not user: 
            return "Unauthorized", 401
        
        post_pk = request.args.get("post_pk", "").strip()
        
        if not post_pk:
            return "Invalid post", 400
        
        db, cursor = x.db()
        
        # Hent alle comments for dette post
        q = """
            SELECT comments.*, 
                   users.user_first_name, 
                   users.user_last_name, 
                   users.user_username, 
                   users.user_avatar_path
            FROM comments
            JOIN users ON comments.comment_user_fk = users.user_pk
            WHERE comments.comment_post_fk = %s
            ORDER BY comments.comment_created_at DESC
        """
        cursor.execute(q, (post_pk,))
        comments = cursor.fetchall()
        
        
        # Render alle comments
        html = ""
        for comment in comments:
            html += render_template("_comment.html", comment=comment, user=user)
        
        return html

    except Exception as ex:
        ic(ex)
        return "error", 500
                    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


################################ API DELETE POST ################################
@app.route("/api-delete-post/<post_pk>", methods=["DELETE"])
def api_delete_post(post_pk):
    try:
        # Hent user fra session
        user = session.get("user")
        
        if not user: 
            return "unauthorized", 401
        
        db, cursor = x.db()
        
        # Tjek at brugeren ejer posten
        q_check = "SELECT * FROM posts WHERE post_pk = %s AND post_user_fk = %s"
        cursor.execute(q_check, (post_pk, user["user_pk"]))
        post = cursor.fetchone()
        
        if not post:
            return "Post not found or unauthorized", 404
        
        # Slet alle comments på posten først (foreign key constraint)
        q_delete_comments = "DELETE FROM comments WHERE comment_post_fk = %s"
        cursor.execute(q_delete_comments, (post_pk,))
        
        # Slet alle likes på posten
        q_delete_likes = "DELETE FROM likes WHERE like_post_fk = %s"
        cursor.execute(q_delete_likes, (post_pk,))
        
        # Slet posten
        q_delete = "DELETE FROM posts WHERE post_pk = %s"
        cursor.execute(q_delete, (post_pk,))
        db.commit()
        
        toast_ok = render_template("___toast_ok.html", message=x.lans("your_post_has_been_deleted"))

        # Fjern post elementet fra DOM
        return f"""<browser mix-remove="[data-post-pk='{post_pk}']"></browser>
        <browser mix-bottom="#toast">{toast_ok}</browser>"""
    
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        toast_error = render_template("___toast_error.html", message="Could not delete post")
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
############################### EDIT POST - GET #################################
@app.get("/edit-post/<post_pk>")
def edit_post(post_pk):
    try:
        # check if user is logged in
        user = session.get("user")

        if not user:
            return "error", 400
        
        # get post from db
        db, cursor = x.db()
        q = "SELECT * FROM posts WHERE post_pk = %s AND post_user_fk = %s "
        cursor.execute(q, (post_pk, user["user_pk"]))
        post = cursor.fetchone()

        if not post:
            toast_error = render_template("___toast_error.html", message="Post not found or you don't have permission")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 403
        
        edit_post_html = render_template("_edit_post.html", post=post, user=user)
        return f"""<browser mix-update="main">{edit_post_html}</browser>"""
    except Exception as ex:
        ic(ex) 
            
        toast_error = render_template("___toast_error.html", message="Could not load post")
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500
        
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
############################# API EDIT POST - POST ############################## 
@app.route("/api-update-post/<post_pk>", methods=["POST"])
def api_update_post(post_pk):
    try:
        # Check if user is logged in
        user = session.get("user")
        if not user: 
            return "invalid user", 401
        
        # Get and validate new post message
        post_message = request.form.get("post_message", "").strip()
        
        # Validate: must have text (can't be empty for edit)
        if not post_message:
            toast_error = render_template("___toast_error.html", message="Post cannot be empty")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 400
        
        # Validate post length
        post_message = x.validate_post(post_message)  # Fjernet allow_empty parameter
        
        # Update timestamp
        updated_at = int(time.time())
        
        # Update database
        db, cursor = x.db()
        q = "UPDATE posts SET post_message = %s, post_updated_at = %s WHERE post_pk = %s AND post_user_fk = %s"
        cursor.execute(q, (post_message, updated_at, post_pk, user["user_pk"]))        
        db.commit()
        
      
        # Fetch updated post with user data
        q = """
        SELECT 
            posts.*,
            users.user_first_name,
            users.user_last_name,
            users.user_username,
            users.user_avatar_path,
            COUNT(DISTINCT likes.like_pk) as post_total_likes,
            COUNT(DISTINCT comments.comment_pk) as post_comments
        FROM posts
        JOIN users ON users.user_pk = posts.post_user_fk
        LEFT JOIN likes ON likes.like_post_fk = posts.post_pk
        LEFT JOIN comments ON comments.comment_post_fk = posts.post_pk
        WHERE posts.post_pk = %s
        GROUP BY posts.post_pk
        """
        cursor.execute(q, (post_pk,))
        tweet = cursor.fetchone()
        
        # Send success response
        toast_ok = render_template("___toast_ok.html", message=x.lans("post_updated_successfully"))
        tweet_html = render_template("_tweet.html", tweet=tweet, user=user)
        
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-replace="[data-post-pk='{post_pk}']">{tweet_html}</browser>
        """
        
    except Exception as ex:
        ic(ex)
        
        if "db" in locals(): 
            db.rollback()
        
        # User validation error
        if len(ex.args) > 1 and ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 400
        
        # System error
        toast_error = render_template("___toast_error.html", message=x.lans("could_not_update_post"))
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
   

############################# FOLLOWERS AND FOLLOWING ###########################
################################### API FOLLOW USER #############################
@app.route("/api-toggle-follow", methods=["POST"])
def api_toggle_follow():
    try:
        user = session.get("user", "")
        if not user: 
            return "unauthorized", 401
        
        following_pk = request.form.get("following_pk", "").strip()
     
        
        if not following_pk:
            ic("ERROR: following_pk is empty!")
            return "Invalid user", 400
        
        # Kan ikke følge sig selv
        if user["user_pk"] == following_pk:
            return "Cannot follow yourself", 400
        
        db, cursor = x.db()
        
        # Tjek om man allerede følger
        q_check = "SELECT * FROM follows WHERE follow_follower_fk = %s AND follow_following_fk = %s"
        cursor.execute(q_check, (user["user_pk"], following_pk))
        existing_follow = cursor.fetchone()
        ic(f"Existing follow: {existing_follow}")
        
        if existing_follow:
            # Unfollow
            q = "DELETE FROM follows WHERE follow_follower_fk = %s AND follow_following_fk = %s"
            cursor.execute(q, (user["user_pk"], following_pk))
            db.commit()
            ic("Successfully unfollowed")
            
            button = render_template("___button_follow.html", target_user_pk=following_pk)
        else:
            # Follow
            follow_pk = uuid.uuid4().hex
            follow_created_at = int(time.time())
            
            q = "INSERT INTO follows VALUES(%s, %s, %s, %s)"
            cursor.execute(q, (follow_pk, user["user_pk"], following_pk, follow_created_at))
            db.commit()
            ic("Successfully followed")
            
            button = render_template("___button_unfollow.html", target_user_pk=following_pk)
        
        return f"""<mixhtml mix-replace="#follow-btn-{following_pk}">{button}</mixhtml>"""
    
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return "error", 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################################# GET FOLLOWERS #################################
@app.get("/followers-list")
def followers_list():
    try:
        user = session.get("user", "")
        if not user:
            return redirect(url_for("login"))
        
        db, cursor = x.db()
        
        # Hent alle der følger brugeren + tjek om du følger dem tilbage
        q = """
        SELECT 
            users.*,
            CASE 
                WHEN EXISTS (
                    SELECT 1 FROM follows 
                    WHERE follow_follower_fk = %s 
                    AND follow_following_fk = users.user_pk
                ) THEN 1 
                ELSE 0 
            END as is_following
        FROM follows
        JOIN users ON follows.follow_follower_fk = users.user_pk
        WHERE follows.follow_following_fk = %s
        """
        cursor.execute(q, (user["user_pk"], user["user_pk"]))
        followers = cursor.fetchall()
        
        followers_html = render_template("___followers_list.html", followers=followers, user=user)
        return f"""<browser mix-update="main">{followers_html}</browser>"""
        
    except Exception as ex:
        ic(ex)
        return "error", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
################################# GET FOLLOWING #################################
@app.get("/following-list")
def following_list():
    try:
        user = session.get("user", "")
        if not user:
            return redirect(url_for("login"))
        
        db, cursor = x.db()
        
        # Hent alle brugeren følger
        q = """
        SELECT users.*
        FROM follows
        JOIN users ON follows.follow_following_fk = users.user_pk
        WHERE follows.follow_follower_fk = %s
        """
        cursor.execute(q, (user["user_pk"],))
        following = cursor.fetchall()
        
        following_html = render_template("___following_list.html", following=following, user=user)
        return f"""<browser mix-update="main">{following_html}</browser>"""
        
    except Exception as ex:
        ic(ex)
        return "error", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



#################################################################################
#################################### ADMIN ######################################
@app.get("/admin")
def view_admin():
    try:
        user = session.get("user", "")
        if not user:
            return redirect(url_for("login"))
        # Check if user is admin
        if user.get("user_admin", 0) != 1:
            toast_error = render_template("___toast_error.html", message=x.lans("access_denied"))
            return f"""
                <browser mix-bottom="#toast">{toast_error}</browser>
                <browser mix-redirect="/home"></browser>
            """
        db, cursor = x.db()
        # Fetch all users
        q = "SELECT * FROM users ORDER BY user_username"
        cursor.execute(q)
        rows = cursor.fetchall()

        admin_html = render_template("_admin.html", rows=rows, user=user)
        return f"""<browser mix-update="main">{admin_html}</browser>"""
        
    except Exception as ex:
        ic(ex)
        toast_error = render_template("___toast_error.html", message="Error loading admin panel")
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500
        
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

        ############# ADMIN-BLOCK-USER #################
################################## BLOCK USER ###################################
@app.post("/admin-block-user/<user_pk>")
def admin_block_user(user_pk):
    try:
        db, cursor = x.db()
        
        # SQL query to toggle the 'user_is_blocked' status for a specific user
        q = "UPDATE users SET user_is_blocked = NOT user_is_blocked WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        db.commit()
        
        # SQL query to fetch the updated data for the specific user 
        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        row = cursor.fetchone()
        
        # Block/unblock all posts from this user
        if row["user_is_blocked"]:
            # User is now blocked - block all their posts
            q = "UPDATE posts SET post_is_blocked = 1 WHERE post_user_fk = %s"
            cursor.execute(q, (user_pk,))
        else:
            # User is now unblocked - unblock all their posts
            q = "UPDATE posts SET post_is_blocked = 0 WHERE post_user_fk = %s"
            cursor.execute(q, (user_pk,))
        
        db.commit()

        # SQL query to fetch all users who are NOT blocked
        q = "SELECT * FROM users WHERE user_is_blocked != 1"
        cursor.execute(q)
        rows = cursor.fetchall()

        # SQL query to fetch all users who are blocked
        q = "SELECT * FROM users WHERE user_is_blocked = 1"
        cursor.execute(q)
        blocked_rows = cursor.fetchall()

        # GET the user's email from the fetched row
        user_email = row["user_email"]

        # render templates for emails
        email_user_is_blocked = render_template("_email_user_is_blocked.html")
        email_user_is_unblocked = render_template("_email_user_is_unblocked.html")
        
        # Send an email to the user depending on their new blocked status
        if row["user_is_blocked"]:
            x.send_email(user_email, "You have been blocked from X", email_user_is_blocked)
        else:
            x.send_email(user_email, "You have been unblocked from X", email_user_is_unblocked)     

        block_unblock_html = render_template("___block_unblock_user.html", row=row)
        admin_html = render_template("_admin.html", rows=rows, blocked_rows=blocked_rows)
        
        toast_ok = render_template("___toast_ok.html", message=f"User {'blocked' if row['user_is_blocked'] else 'unblocked'} successfully")
        
        return f"""
        <browser mix-bottom="#toast">{toast_ok}</browser>
        <browser mix-replace="#block_unblock_user_{user_pk}">{block_unblock_html}</browser>
        <browser mix-update="main">{admin_html}</browser>
        """
    except Exception as ex:
        ic(ex)
        toast_error = render_template("___toast_error.html", message="Could not block/unblock user")
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################################# ADMIN-BLOCK-POST ##############################
@app.post("/admin-block-post/<post_pk>")
def admin_block_post(post_pk):
    try:
        db, cursor = x.db()
        q = "UPDATE posts SET post_is_blocked = NOT post_is_blocked WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        db.commit()

        # SQL query to fetch post with user data INCLUDING email
        q = """SELECT 
        posts.*,
        users.user_first_name,
        users.user_last_name,
        users.user_username,
        users.user_avatar_path,
        users.user_email
        FROM posts
        JOIN users ON posts.post_user_fk = users.user_pk
        WHERE posts.post_pk = %s"""

        cursor.execute(q, (post_pk,))
        tweet = cursor.fetchone()

        # Hent email direkte fra tweet
        user_email = tweet["user_email"]

        email_post_is_blocked = render_template("_email_post_is_blocked.html")
        email_post_is_unblocked = render_template("_email_post_is_unblocked.html")

        # Send email hvis posten er blokeret eller unblocked
        if tweet["post_is_blocked"]:
            x.send_email(user_email, "Your post has been blocked", email_post_is_blocked)
        else:
            x.send_email(user_email, "Your post has been unblocked", email_post_is_unblocked)

        user = session.get("user", "")
        block_unblock_html = render_template("___block_unblock_post.html", tweet=tweet)
        tweet_html = render_template("_tweet.html", tweet=tweet, user=user)
        return f"""
        <browser mix-replace="#block_unblock_post_{post_pk}">{block_unblock_html}</browser>
        <browser mix-replace="#post_container_{post_pk}">{tweet_html}</browser>
        """
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


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

        toast_ok = render_template("___toast_ok.html", message="Dictionary updated")
        return f"""
                <browser mix-bottom="#toast">{toast_ok}</browser>"""
    except Exception as ex:
        ic(ex)
        return str(ex)
    finally:
        pass

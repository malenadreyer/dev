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
 

################ LOGIN ##############
########################################################################################################################
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


################# LOGOUT ####################
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


############################ SIGN UP ################################
############################################################
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

            user_hashed_password = generate_password_hash(user_password)
            
            # Connect to the database
            db, cursor = x.db()
            
            # Tjek om email allerede eksisterer
            q_check = "SELECT * FROM users WHERE user_email = %s"
            cursor.execute(q_check, (user_email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                # Hvis kontoen er soft deleted, genaktiver den
                if existing_user["user_deleted_at"] != 0:
                    import time
                    q_reactivate = """UPDATE users 
                                     SET user_deleted_at = 0, 
                                         user_password = %s,
                                         user_username = %s,
                                         user_first_name = %s
                                     WHERE user_email = %s"""
                    cursor.execute(q_reactivate, (user_hashed_password, user_username, user_first_name, user_email))
                    db.commit()
                    
                    # Redirect til login
                    return f"""<mixhtml mix-redirect="{ url_for('login') }"></mixhtml>""", 200
                else:
                    # Email er allerede i brug af en aktiv konto
                    toast_error = render_template("___toast_error.html", message="Email already registered")
                    return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            
            # Hvis email ikke findes, opret ny bruger
            user_pk = uuid.uuid4().hex
            user_last_name = ""
            user_avatar_path = ""
            user_verification_key = uuid.uuid4().hex
            user_verified_at = 0
            user_deleted_at = 0
            
            q = "INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s,%s)"
            cursor.execute(q, (user_pk, user_email, user_hashed_password, user_username, 
            user_first_name, user_last_name, user_avatar_path, user_verification_key, user_verified_at, user_deleted_at))
            db.commit()

            # send verification email
            email_verify_account = render_template("_email_verify_account.html", user_verification_key=user_verification_key)
            ic(email_verify_account)
            x.send_email(user_email, "Verify your account", email_verify_account)

            return f"""<mixhtml mix-redirect="{ url_for('login') }"></mixhtml>""", 200
            
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

############################## FORGOT PASSWORD ##############################
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


################################RESET PASSWORD ################################
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

###############################FORGOT PASSWORD ################################
@app.route("/forgot-password", methods=["GET"])
def forgot_password_page():
    return render_template("forgot_password.html")

############################### HOME #########3######################
##########################################################################################
@app.get("/home")
@x.no_cache
def home():
    try:
        user = session.get("user", "")
        if not user: return redirect(url_for("login"))
        db, cursor = x.db()
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk "
        cursor.execute(q)
        tweets = cursor.fetchall()
        ic(tweets)

        q = "SELECT * FROM trends ORDER BY RAND() LIMIT 3"
        cursor.execute(q)
        trends = cursor.fetchall()
        ic(trends)

        q = """
            SELECT users.*, 
                   (SELECT COUNT(*) FROM follows 
                    WHERE follow_follower_fk = %s 
                    AND follow_following_fk = users.user_pk) as is_following
            FROM users 
            WHERE user_pk != %s 
            ORDER BY RAND() 
            LIMIT 3
        """
        cursor.execute(q, (user["user_pk"], user["user_pk"]))
        suggestions = cursor.fetchall()

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
            FROM posts
            JOIN users ON posts.post_user_fk = users.user_pk
            LEFT JOIN likes ON posts.post_pk = likes.like_post_fk AND likes.like_user_fk = %s
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


############################################PROFILE##############################################
##########################################################################################
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
        
        # Hent brugerens tweets (tilføj dette)
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


############################## CREATE POST ##############################
################################################################
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



############################## UPDATE PROFIL ###################################################
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





############### DELETE PROFILE ###############
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

############## API DELETE PROFILE ################
@app.route("/api-delete-profile", methods=["DELETE"])
def api_delete_profile():
    try:
        # Hent user fra session
        user = session.get("user")
        
        if not user: 
            return "invalid user", 401
        
        # Soft delete - set deleted timestamp
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Format til MySQL
        q = "UPDATE users SET user_deleted_at = %s WHERE user_pk = %s"
        db, cursor = x.db()
        cursor.execute(q, (now, user["user_pk"]))
        db.commit()

        # Clear session
        session.clear()

        # Redirect to index page
        return f"""<browser mix-redirect="/"></browser>"""
    
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

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




##################################################
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

################################################
@app.route("/api-create-comment", methods=["POST"])
def api_create_comment():
    try:
        user = session.get("user", "")
        if not user: 
            return "Unauthorized", 401
        
        user_pk = user["user_pk"]
        post_pk = request.form.get("post_pk", "").strip()
        comment_message = x.validate_post(request.form.get("comment_message", "").strip())
        
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
        return "error", 500
                    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

###################################################
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

#############################################################
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
        
        if not comments:
            return '<p style="padding: 20px; text-align: center; color: #666;">No comments yet. Be the first to comment!</p>'
        
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

##############################################################
############## API DELETE POST ################
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
        
        # Fjern post elementet fra DOM
        return f"""<browser mix-remove="[data-post-pk='{post_pk}']"></browser>"""
    
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        toast_error = render_template("___toast_error.html", message="Could not delete post")
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
########################################################
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


######################### FOLLOWERS AND FOLLOWING ###########################
############## API FOLLOW USER ################
############## API FOLLOW USER ################
@app.route("/api-toggle-follow", methods=["POST"])
def api_toggle_follow():
    try:
        user = session.get("user", "")
        if not user: 
            return "unauthorized", 401
        
        following_pk = request.form.get("following_pk", "").strip()
        
        if not following_pk:
            return "Invalid user", 400
        
        # Kan ikke følge sig selv
        if user["user_pk"] == following_pk:
            return "Cannot follow yourself", 400
        
        db, cursor = x.db()
        
        # Tjek om man allerede følger
        q_check = "SELECT * FROM follows WHERE follow_follower_fk = %s AND follow_following_fk = %s"
        cursor.execute(q_check, (user["user_pk"], following_pk))
        existing_follow = cursor.fetchone()
        
        if existing_follow:
            # Unfollow
            q = "DELETE FROM follows WHERE follow_follower_fk = %s AND follow_following_fk = %s"
            cursor.execute(q, (user["user_pk"], following_pk))
            db.commit()
            
            # Returnér Follow knap
            button = render_template("___button_follow.html", suggestion={"user_pk": following_pk})
        else:
            # Follow
            follow_pk = uuid.uuid4().hex
            follow_created_at = int(time.time())
            
            q = "INSERT INTO follows VALUES(%s, %s, %s, %s)"
            cursor.execute(q, (follow_pk, user["user_pk"], following_pk, follow_created_at))
            db.commit()
            
            # Returnér Following knap
            button = render_template("___button_unfollow.html", suggestion={"user_pk": following_pk})
        
        return f"""<mixhtml mix-replace="#follow-btn-{following_pk}">{button}</mixhtml>"""
    
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return "error", 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
#################################################################
############################ ADMIN ##############################
@app.get("/admin")
def view_admin():
    try:
        
        db, cursor = x.db()
        q = "SELECT * FROM users"
        cursor.execute(q)
        rows = cursor.fetchall()

        admin_html = render_template("_admin.html", rows=rows)
        return f"""<browser mix-update="main">{ admin_html }</browser>"""
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

        ############# ADMIN-BLOCK-USER #################
@app.post("/admin-block-user/<user_pk>")
def admin_block_user(user_pk):
    try:
        db, cursor = x.db()
        q = "UPDATE users SET user_is_blocked = NOT user_is_blocked WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        db.commit()

        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        row = cursor.fetchone()
        ic(row)

        user_email = row["user_email"]

        
        email_user_is_blocked = render_template("_email_user_is_blocked.html")
        email_user_is_unblocked = render_template("_email_user_is_unblocked.html")
        
        if row["user_is_blocked"]:
            x.send_email(user_email=user_email, subject="You have been blocked from X", template=email_user_is_blocked)
        else:
            x.send_email(user_email=user_email, subject="You have been unblocked from X", template=email_user_is_unblocked)     

        block_unblock_html = render_template("___block_unblock_user.html", row=row)
        return f"""<browser mix-replace="#block_unblock_user_{user_pk}">{block_unblock_html}</browser>"""
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


############# ADMIN-BLOCK-POST #################
@app.post("/admin-block-post/<post_pk>")
def admin_block_post(post_pk):
    try:
       db, cursor = x.db()
       q = "UPDATE posts SET post_is_blocked = NOT post_is_blocked WHERE post_pk = %s"
       cursor.execute(q, (post_pk,))
       db.commit()

       q = "SELECT * FROM posts WHERE post_pk = %s"
       cursor.execute(q, (post_pk,))
       tweet = cursor.fetchone()

       q = "SELECT * FROM users WHERE user_pk = %s"
       cursor.execute(q, (tweet["post_user_fk"],))
       row = cursor.fetchone()


       user_email = row["user_email"]

       email_post_is_blocked = render_template("_email_post_is_blocked.html")

       if tweet["post_is_blocked"]:
           x.send_email(user_email=user_email, subject="Your post has been blocked", template=email_post_is_blocked)

       block_unblock_html = render_template("___block_unblock_post.html", tweet=tweet)
       return f"""<browser mix-replace="#block_unblock_post_{post_pk}">{block_unblock_html}</browser>"""
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close() 
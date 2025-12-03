from flask import request, make_response, render_template
import mysql.connector
import re 
import dictionary
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from functools import wraps

from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

UPLOAD_ITEM_FOLDER = './images'


##############################
allowed_languages = ["english", "danish", "spanish"]
google_spread_sheet_key = "1BDCl5DoPFXWLiJhyJaQ3UMlS8TkF79ExiCGYgz7D0WM"
default_language = "en"

def lans(key):
    with open("dictionary.json", 'r', encoding='utf-8') as file:
        data = json.load(file)

    lang_map = {
        "en": "english",
        "dk": "danish",
        "sp": "spanish"
    }

    lang = lang_map.get(dictionary.default_language, "english")

    return data[key][lang]
############################## Database login #########################
def db():
    try:
        db = mysql.connector.connect(
            host = "mariadb",
            user = "root",  
            password = "password",
            database = "x"
        )
        cursor = db.cursor(dictionary=True)
        return db, cursor
    except Exception as e:
        print(e, flush=True)
        raise Exception("Twitter exception - Database under maintenance", 500)


############################## SECURITY & HELP ##############################
def no_cache(view):
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return no_cache_view


############################## Rules ################################
REGEX_EMAIL = "^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$"
def validate_user_email(lan = "en"):
    user_email = request.form.get("user_email", "").strip()
    if not re.match(REGEX_EMAIL, user_email): raise Exception(dictionary.invalid_email[lan], 400)
    return user_email

##############################
USER_USERNAME_MIN = 2
USER_USERNAME_MAX = 20
REGEX_USER_USERNAME = f"^.{{{USER_USERNAME_MIN},{USER_USERNAME_MAX}}}$"
def validate_user_username(lan="en"):
    user_username = request.form.get("user_username", "").strip()
    error = f"{dictionary.username[lan]} {USER_USERNAME_MIN} {dictionary.to[lan]} {USER_USERNAME_MAX} {dictionary.characters[lan]}"
    if len(user_username) < USER_USERNAME_MIN: raise Exception(error, 400)
    if len(user_username) > USER_USERNAME_MAX: raise Exception(error, 400)  
    return user_username

##############################
USER_FIRST_NAME_MIN = 2
USER_FIRST_NAME_MAX = 20
REGEX_USER_FIRST_NAME = f"^.{{{USER_FIRST_NAME_MIN},{USER_FIRST_NAME_MAX}}}$"
def validate_user_first_name(lan="en"):
    user_first_name = request.form.get("user_first_name", "").strip()
    error = f"{dictionary.first_name[lan]} {USER_FIRST_NAME_MIN} {dictionary.to[lan]} {USER_FIRST_NAME_MAX} {dictionary.characters[lan]}"
    if not re.match(REGEX_USER_FIRST_NAME, user_first_name): raise Exception(error, 400)
    return user_first_name


##############################
USER_PASSWORD_MIN = 6
USER_PASSWORD_MAX = 50
REGEX_USER_PASSWORD = f"^.{{{USER_PASSWORD_MIN},{USER_PASSWORD_MAX}}}$"
def validate_user_password(lan = "en"):
    user_password = request.form.get("user_password", "").strip()
    if not re.match(REGEX_USER_PASSWORD, user_password): raise Exception(dictionary.invalid_password[lan], 400)
    return user_password




##############################
def validate_user_password_confirm():
    user_password = request.form.get("user_password_confirm", "").strip()
    if not re.match(REGEX_USER_PASSWORD, user_password): raise Exception("Twitter exception - Invalid confirm password", 400)
    return user_password


##############################
REGEX_UUID4 = "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
def validate_uuid4(uuid4 = ""):
    if not uuid4:
        uuid4 = request.values.get("uuid4", "").strip()
    if not re.match(REGEX_UUID4, uuid4): raise Exception("Twitter exception - Invalid uuid4", 400)
    return uuid4


##############################
REGEX_UUID4_WITHOUT_DASHES = "^[0-9a-f]{8}[0-9a-f]{4}4[0-9a-f]{3}[89ab][0-9a-f]{3}[0-9a-f]{12}$"
def validate_uuid4_without_dashes(uuid4 = "", lan="english"):
    error = "Invalid uuid4 without dashes"
    if not uuid4: raise Exception(error, 400)
    uuid4 = uuid4.strip()
    if not re.match(REGEX_UUID4_WITHOUT_DASHES, uuid4): raise Exception(error, 400)
    return uuid4

##############################
POST_MIN_LEN = 2
POST_MAX_LEN = 250
REGEX_POST = f"^.{{{POST_MIN_LEN},{POST_MAX_LEN}}}$"
def validate_post(post = ""):
    post = post.strip()
    if not re.match(REGEX_POST, post): raise Exception("x-error post", 400)
    return post

##############################
COMMENT_MIN_LEN = 1
COMMENT_MAX_LEN = 200
REGEX_COMMENT = f"^.{{{COMMENT_MIN_LEN},{COMMENT_MAX_LEN}}}$"

###############################
BIO_MIN = 2
BIO_MAX = 250
REGEX_BIO = f"^.{{{BIO_MIN},{BIO_MAX}}}$"
def validate_bio():
    bio = request.form.get("user_bio","").strip()
    if not re.match(REGEX_BIO, bio): raise Exception("Bio must be between 2 and 250 characters", 400)
    return bio

###############################
def validate_comment(comment_message):
    comment_message = comment_message.strip()

    if len (comment_message) < 1:
        raise Exception("Comment must be at least 1 character", 400)
    
    if len (comment_message) > 250:
        raise Exception("Comment must be at least 1 and 250 characters", 400)

    return comment_message


##############################
def send_email(to_email, subject, template):
    try:
        # Create a gmail fullflaskdemomail
        # Enable (turn on) 2 step verification/factor in the google account manager
        # Visit: https://myaccount.google.com/apppasswords
        # Copy the key : pdru ctfd jdhk xxci

        # Email and password of the sender's Gmail account
        sender_email = "malenadreyer@gmail.com"
        password = "sxub ssjj qlrm dkhq"  # If 2FA is on, use an App Password instead

        # Receiver email address
        receiver_email = to_email
        
        # Create the email message
        message = MIMEMultipart()
        message["From"] = f"X Clone <{sender_email}>"
        message["To"] = to_email
        message["Subject"] = subject

        # Body of the email
        message.attach(MIMEText(template, "html"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        ic("Email sent successfully!")

        return "email sent"
       
    except Exception as ex:
        ic(ex)
        raise Exception("cannot send email", 500)
    finally:
        pass

    #################################
def send_reset_email(to_email, reset_token):
    try:
        # Sender email and app password
        sender_email = "malenadreyer@gmail.com"
        password = "sxub ssjj qlrm dkhq"  # App Password for Gmail (with 2FA enabled)

        # Construct the reset URL
        reset_url = f"http://127.0.0.1/reset-password?token={reset_token}"
        # Create the email message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = to_email
        message["Subject"] = "Reset Your Password"

        # Format the email body similarly to verify_email
        body = f"""
        <p>To reset your password, please click the link below:</p>
        <p><a href="{reset_url}">Reset Your Password</a></p>
        <p>If you did not request this, please ignore this email.</p>
        """
        message.attach(MIMEText(body, "html"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, password)
            server.sendmail(sender_email, to_email, message.as_string())
        print("Reset password email sent successfully!")

        return "email sent"

    except Exception as ex:
        raise Exception("Cannot send email", 500)
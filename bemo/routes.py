import json
import requests
import os
from os import environ as env
import secrets
from flask import render_template, flash, redirect, url_for, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from six.moves.urllib.parse import urlencode
from PIL import Image
from functools import wraps
from urllib.parse import urlparse, quote_plus
from bemo import app, db, session, oauth
from bemo.forms import Confirm, Picture, Create, Code
from bemo.models import User, Problem, Submission
import urllib.request


auth0 = oauth.register(
    'auth0',
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        'scope': 'openid profile email',
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)

def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    if 'id' not in session:
      # Redirect to Login page here
      return redirect('/')
    return f(*args, **kwargs)
  return decorated

#generate random (hopefully unique) filename for inputted picture
def save_picture(inp_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(inp_picture.filename)
    filename = random_hex + f_ext
    picture_path = os.path.join(app.config['UPLOAD_FOLDER']+'/pics', filename)
    i = Image.open(inp_picture)
    i.thumbnail((125, 125))
    i.save(picture_path)
    return filename

#homepage
@app.route("/")
@app.route("/home")
def home():
  user = None
  if 'id' in session:
    user = User.query.filter_by(id=session['id']).first()
  page = request.args.get('page', 1, type=int)
  problems = Problem.query.order_by(Problem.date_posted.desc()).paginate(page=page, per_page=5)
  topcontributors = User.query.order_by(User.contribution).limit(5).all()
  topsolvers = User.query.order_by(User.score).limit(5).all()
  return render_template('home.html', problems=problems, user=user, page=page, conts=topcontributors, solvs=topsolvers)

#list out problems in table format
@app.route("/problems")
@app.route("/problems/<int:page_num>")
def problems():
  user = None
  if 'id' in session:
    user = User.query.filter_by(id=session['id']).first()
  page = request.args.get('page', 1, type=int)
  problems = Problem.query.order_by(Problem.date_posted.desc()).paginate(page=page, per_page=5)
  topcontributors = User.query.order_by(User.contribution).limit(5).all()
  topsolvers = User.query.order_by(User.score).limit(5).all()
  return render_template('problems.html', problems=problems, user=user, page=page, conts=topcontributors, solvs=topsolvers)


#login route for redirects
@app.route("/login")
def login():
  if 'profile' in session:
    print("Already have profile")
    return redirect(url_for('home'))
  print("Calling auth0 for login")
  return oauth.auth0.authorize_redirect(redirect_uri='https://127.0.0.1:5000/callback', _external=True)

#configured to retrieve and store from auth0
@app.route('/callback', methods=["GET", "POST"])
def callback_handling():
    # Handles response from token endpoint
    token = oauth.auth0.authorize_access_token() #TODO: add handling for declines
    session["user"] = token #userinfo = token['userinfo']
    # Store the user information in flask session
    userinfo = token['userinfo']
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
       'picture': userinfo['picture'],
      'sub': userinfo['sub']
    }
    #redirect to new_login to create pair within database
    detectedusr = User.query.filter_by(sub=userinfo['sub']).first()
    print(detectedusr)
    if detectedusr is None:
      return redirect(url_for('new_login'))
    session['id'] = detectedusr.id
    print("Welcome "+detectedusr.username)
    return redirect('/dashboard')

#initializes user within database
@app.route('/newuser', methods=['GET','POST'])
def new_login():
  if 'id' in session or 'profile' not in session:
    return redirect('/')
  #stores user's or auth0's picture
  pic = Picture()
  if pic.submit2.data and pic.validate():
    filename=save_picture(pic.pic.data)
  else:
    filename=secrets.token_hex(8)
    with open(app.config['UPLOAD_FOLDER']+'pics/'+filename, 'wb') as f:
      f.write(requests.get(session['profile']['picture']).content) #connected default pic
  form = Confirm()
  if form.submit1.data and form.validate():
    user = User(
      username=form.username.data,
      firstname=form.firstname.data, 
      lastname=form.lastname.data,
      img_file=filename, 
      sub=session['profile']['sub'],
      verified=False)
    db.session.add(user)
    db.session.commit()
    session['id'] = User.query.filter_by(sub=session['profile']['sub']).first().id
    flash('Your account has been created! You are now able to log in', 'success')
    return redirect('/dashboard')
  #renders form with auth0's default values
  return render_template('editacct.html', 
    title='New User', 
    form=form,
    pic=pic, 
    name=session['profile']['name'],
    firstname="",
    lastname="",
    img=filename)

#displays information and settings
@app.route('/dashboard')
@requires_auth
def dashboard():
  user = User.query.filter_by(id=session['id']).first()
  return render_template('dashboard.html', user=user)

@app.route('/payment')
@requires_auth
def payment():
  user = User.query.filter_by(id=session['id']).first()
  return render_template('payment.html', user=user)

@app.route('/user/<username>')
def show_user(username):
    user = None
    if 'id' in session:
      user = User.query.filter_by(id=session['id']).first()
    # show the user profile for that user
    result = User.query.filter_by(username=username).first()
    if result is None:
      return "User Not Found"
    return f'User {escape(username)}'

def check_sub(sub_id):
  #TODO: check api for submission based on token stored in db and update
  #also add to user total if updated
  #daemon should periodically check for unupdated submissions
  print("check")

# show the problem with the given id
@app.route('/problem/<int:prob_id>', methods=['GET','POST'])
def show_prob(prob_id):
    user = None
    if 'id' in session:
      user = User.query.filter_by(id=session['id']).first()
    result = Problem.query.filter_by(id=prob_id).first()
    if result is None:
      return "Problem Not Found"
    form = Code()
    if form.submit4.data and form.validate():
      print("code recieved")
      #TODO: send code to api and generate id
      #check_sub(sub_id)
      return redirect('/')
    return render_template('problem.html',problem=result,form=form)    

@app.route('/submission/<int:sub_id>')
def show_sub(sub_id):
    user = None
    if 'id' in session:
      user = User.query.filter_by(id=session['id']).first()
    result = Submission.query.filter_by(id=sub_id).first()
    if result is None:
      return "Submission Not Found"
    if result.cases == -1:
      check_sub(sub_id)
      result = Submission.query.filter_by(id=sub_id).first()
      if result.cases == -1:
        return "Submission Processing, please come back"
    problem =  Problem.query.filter_by(id=result.prob_id).first() 
    user = User.query.filter_by(id=result.user_id).first() 
    msg1 = ""
    if problem.cases==result.cases:
      msg1 = "Correct!"
    else:
      msg1 = "Incorrect"
    msg2 = ""
    for i in range(result.cases):
      msg2+="✅"
    for i in range(problem.cases-result.cases):
      msg2+="❌"
    return render_template('submission.html',submission=result,problem=problem,user=user,msg1=msg1,msg2=msg2)

#updates user's columns
@app.route('/edit-account', methods=['GET','POST'])
@requires_auth
def editacct():
  user = User.query.filter_by(id=session['id']).first()
  pic = Picture()
  if pic.submit2.data and pic.validate():
    user.img_file = save_picture(pic.pic.data)
    db.session.commit()
  form = Confirm()
  if form.submit1.data and form.validate():
    user.username = form.username.data
    user.firstname = form.firstname.data
    user.lastname = form.lastname.data
    db.session.commit()
    flash('Your account has been updated!', 'success')
    return redirect('/dashboard')
  return render_template('editacct.html', title='Update User',
    form=form,
    pic=pic, 
    name=user.username,
    firstname=user.firstname,
    lastname=user.lastname,
    img=user.img_file)

@app.route('/delete-user',methods =["GET", "POST"])
@requires_auth
def deleteuser():
  if request.method == "POST":
    user = User.query.filter_by(id=session['id']).first()
    user.delete()
    db.commit()
    flash("User Deleted")
    return redirect('/logout')
  return render_template('delacct.html')

#clears session and redirects to auth0's logout endpoint
@app.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    flash('Logged out!')
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )
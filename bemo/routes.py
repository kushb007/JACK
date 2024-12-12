import json
import requests
import os
from os import environ as env
import secrets
from flask import render_template, flash, redirect, url_for, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from PIL import Image
from functools import wraps
from urllib.parse import urlparse, quote_plus
from bemo import app, db, session, oauth
from bemo.forms import Confirm, Picture, Create, Code
from bemo.models import User, Problem, Submission
import urllib.request
import random
import http.client
import base64
from datetime import datetime, timezone
from square.http.auth.o_auth_2 import BearerAuthCredentials
from square.client import Client

auth0 = oauth.register(
    'auth0',
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        'scope': 'openid profile email',
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)

headers = {
          'x-rapidapi-key': "477e10fe7dmsh5189385f45a93e1p171958jsn2102f60c1c61",
          'x-rapidapi-host': "judge0-ce.p.rapidapi.com",
          'Content-Type': "application/json"
}

#wraps functions to require auth0 token for access
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
  randommessage = random.choice(["Welcome to Bemo!","Solve problems and earn points!","Join the community!","Compete with others!","Improve your coding skills!","Get started now!"])
  return render_template('home.html', problems=problems, user=user, page=page, conts=topcontributors, solvs=topsolvers,randommessage=randommessage)

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
  return oauth.auth0.authorize_redirect(redirect_uri='https://127.0.0.1:5000/callback', _external=True) #TODO: change url_for after ssl

#configured to retrieve and store from auth0
@app.route('/callback', methods=["GET", "POST"])
def callback():
    # Handles response from token endpoint
    token = oauth.auth0.authorize_access_token()
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
  if pic.submit.data and pic.validate():
    filename=save_picture(pic.pic.data)
  else:
    filename=secrets.token_hex(8)
    with open(app.config['UPLOAD_FOLDER']+'pics/'+filename, 'wb') as f:
      f.write(requests.get(session['profile']['picture']).content) #connected default pic
  form = Confirm()
  if form.submit.data and form.validate():
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
    if form.submit.data and form.validate():
      if form.code.data is None and form.code_area.data is None:
        return "No code recieved"
      bytes_code = None
      if form.code.data is None and form.code_area.data is not None:
        bytes_code = base64.b64encode(bytes(form.code_area.data,'utf-8')).decode('ascii')
      else:
        bytes_code = base64.b64encode(form.code.data.read()).decode('ascii')
      print("code recieved")
      print(bytes_code)
      #TODO: submit all cases in batches
      conn = http.client.HTTPSConnection("judge0-ce.p.rapidapi.com")
      payload = "{\"language_id\":52,\"source_code\":\""+bytes_code+"\",\"stdin\":\"SnVkZ2Uw\"}"
      conn.request("POST", "/submissions?base64_encoded=true&wait=false&fields=*", payload, headers)
      res = conn.getresponse()
      data = res.read()
      print(data.decode("utf-8"))
      token = json.loads(data.decode("utf-8"))['token']
      print(token)
      submission = Submission(user_id=session['id'],problem_id=prob_id,token=token,cases=result.cases)
      db.session.add(submission)
      db.session.commit()
      submission_id = Submission.query.filter_by(token=token).first().id
      return redirect('/submission/'+str(submission_id))
    return render_template('problem.html',problem=result,form=form,user=user)    

@app.route('/submission/<int:sub_id>')
def show_sub(sub_id):
    user = None
    if 'id' in session:
      user = User.query.filter_by(id=session['id']).first()
    sub = Submission.query.filter_by(id=sub_id).first()
    if sub is None:
      return "Submission Not Found"
    if (datetime.utcnow()-sub.last_check).total_seconds()>60**sub.checks:
      print("sending request")
      sub.last_check = datetime.utcnow()
      sub.checks+=1
      conn = http.client.HTTPSConnection("judge0-ce.p.rapidapi.com")
      conn.request("GET", "/submissions/"+sub.token+"?base64_encoded=true&fields=*", headers=headers)
      res = conn.getresponse()
      submission_data = json.loads(res.read().decode("utf-8"))
      print(submission_data)
      sub.cases=0#TODO: update solved cases after switching to batch
      if(submission_data['status']['id']<3):
        sub.message = "Processing"
      if(submission_data['status']['id']==3):
        sub.message = "Accepted"
      if(submission_data['status']['id']==4):
        sub.message = "Wrong Answer"
      db.session.commit()
    problem =  Problem.query.filter_by(id=sub.problem_id).first() 
    user = None
    if 'id' in session:
      user = User.query.filter_by(id=session['id']).first()
    msg1 = sub.message
    msg2 = ""
    for i in range(sub.cases):
      msg2+="✅"
    for i in range(problem.cases-sub.cases):
      msg2+="❌"
    if sub.message=="Processing":
      msg2="❓"*problem.cases
    if sub.message=="Accepted" and user.id==sub.user_id:
      #if user.solved==0: TODO: many to many relationship between solved problems and users
      #  user.score+=1
      #  problem.solved+=1
      print("Accepted")
      if(problem.solved==1):
        problem.solver = user.id
      #if problem.solver==user.id and problem.gift_card=="": TODO: gift cards or paypal payouts 
        
    return render_template('submission.html',submission=sub,problem=problem,user=user,msg1=msg1,msg2=msg2)

#updates user's columns
@app.route('/edit-account', methods=['GET','POST'])
@requires_auth
def editacct():
  user = User.query.filter_by(id=session['id']).first()
  pic = Picture()
  if pic.submit.data and pic.validate():
    user.img_file = save_picture(pic.pic.data)
    db.session.commit()
  form = Confirm()
  if form.submit.data and form.validate():
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

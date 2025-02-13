import json
import requests
import os
from os import environ as env
import secrets
from flask import render_template, flash, redirect, url_for, request
from werkzeug.utils import secure_filename
from PIL import Image
from functools import wraps
from urllib.parse import quote_plus, urlencode
from bemo import app, db, session, oauth, cache
from bemo.forms import Confirm, Picture, Code
from bemo.models import User, Problem, Submission
import random
import http.client
import base64
from datetime import datetime
from re import escape

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
      pass
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
  return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

#configured to retrieve and store from auth0
@app.route('/callback', methods=["GET", "POST"])
def callback():
    # Handles response from token endpoint
    token = oauth.auth0.authorize_access_token()
    # Store the user information in flask session
    session["user"] = token
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
    if detectedusr is None or detectedusr.setup==False:
      return redirect(url_for('new_login'))
    session['id'] = detectedusr.id
    print("Welcome "+detectedusr.username)
    return redirect('/')

#initializes user within database
@app.route('/newlogin', methods=['GET','POST'])
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
        print("Recieved", form.code_area.data)
        bytes_code = base64.b64encode(bytes(form.code_area.data,'utf-8')).decode('ascii')
      else:
        print("Recieved", form.code.data)
        bytes_code = base64.b64encode(form.code.data.read()).decode('ascii')
      conn = http.client.HTTPSConnection("judge0-ce.p.rapidapi.com")
      cases = {}
      cases['submissions'] = []
      print(result.inputs)
      input_files = eval(result.inputs)
      for input_file in input_files:
          case = {}
          case['language_id']='52'
          case['source_code']=bytes_code
          with open(app.config['UPLOAD_FOLDER']+'txts/'+input_file,'r') as f:
              case['inputs']=f.read()
          cases['submissions'].append(case)
      payload = json.dumps(cases)
      conn.request("POST", "/submissions/batch?base64_encoded=true", payload, headers)
      res = conn.getresponse()
      data = res.read()
      print(data.decode("utf-8"))
      tokens = []
      for d in json.loads(data.decode("utf-8")):
          print(d)
          if 'token' in d:
              tokens.append(d['token'])
          else:
              tokens.append(None)
      tokens_string = json.dumps(tokens)
      submission = Submission(user_id=session['id'],problem_id=prob_id,tokens=tokens_string,cases=result.cases)
      db.session.add(submission)
      db.session.commit()
      submission_id = Submission.query.filter_by(token=tokens_string).first().id
      return redirect('/submission/'+str(submission_id))
    return render_template('problem.html',problem=result,form=form,user=user,tags=eval(result.tags))

@app.route('/submission/<int:sub_id>')
@cache.cached(timeout=60, query_string=True)
def show_sub(sub_id):
    user = None
    if 'id' in session:
      user = User.query.filter_by(id=session['id']).first()
    sub = Submission.query.filter_by(id=sub_id).first()
    problem = Problem.query.filter_by(id=sub.problem_id).first()
    if sub is None:
      return "Submission Not Found"
    backoff_time = min(60 ** sub.checks, 10000)
    if (datetime.utcnow()-sub.last_check).total_seconds()>backoff_time:
      print("sending request")
      sub.last_check = datetime.utcnow()
      sub.checks+=1
      tokens = eval(sub.tokens)
      if len(tokens) != problem.cases:
          tokens = [None] * problem.cases
      statuses = eval(sub.statuses)
      if len(statuses) != problem.cases:
          statuses = [None] * problem.cases
      results = []
      correct_cases = 0
      recieved_cases = 0
      for i in range(len(tokens)):
          token = tokens[i]
          if token is None:
              results.append('Compile error')
          else:
              if statuses[i] is None:
                  conn = http.client.HTTPSConnection("judge0-ce.p.rapidapi.com")
                  conn.request("GET", "/submissions/"+token+"?base64_encoded=true&fields=*", headers=headers)
                  res = conn.getresponse()
                  submission_data = json.loads(res.read().decode("utf-8"))
                  print(submission_data)
                  if(submission_data['status']['id']<3):
                    results.append(None)
                  else:
                    recieved_cases += 1
                    if(submission_data['status']['id']==3):
                      results.append('Accepted')
                      correct_cases+=1
                    if(submission_data['status']['id']==4):
                      results.append('Wrong Answer')
      sub.correct = correct_cases
      sub.recieved = recieved_cases
      sub.status = json.dumps(results)
      db.session.commit()
    cases_string = ""
    for status in eval(sub.status):
        if status == 'Accepted':
            cases_string += "✅"
        elif status == 'Wrong Answer':
            cases_string += "❌"
        elif status == 'Compile Error':
            cases_string += "💥"
        else:
            cases_string += "⚙️"
        cases_string += "\n"
    user = None
    if 'id' in session:
      user = User.query.filter_by(id=session['id']).first()
    if sub.correct == sub.cases and user.id==sub.user_id:#TODO: relationship should be many not single
        user_solved = json.loads(user.solved)
        if problem.id not in user_solved:
            user_solved.append(problem.id)
            user.solved = json.dumps(user_solved)
            db.session.commit()
        print("Accepted")
        problem.solved += 1
        db.session.commit()
        if(problem.solved==1):
            problem.solver = user.id
    #if problem.solver==user.id: TODO: gift cards or paypal payouts
        
    return render_template('submission.html',submission=sub,problem=problem,user=user,msg1=cases_string,msg2=sub.status)


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
    user.setup = True
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

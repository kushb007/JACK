import json
import requests
import os
import secrets
from flask import render_template, flash, redirect, url_for, jsonify, request
from bemo import app, oauth, db, session
from bemo.forms import Confirm, Picture, Create
from bemo.models import User, Problem
from functools import wraps
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from dotenv import load_dotenv, find_dotenv
from six.moves.urllib.parse import urlencode
from PIL import Image
from urllib.parse import urlparse

auth0 = oauth.register(
    'auth0',
    client_id='',
    client_secret='ucATeBwYlEAAoPyUDiFYVbrdGpBUIYe8LcGdNexoGUgZvDyHPSVWo42EjzKsNMF0',
    api_base_url='https://dev-h1cxd8ju.us.auth0.com',
    access_token_url='https://dev-h1cxd8ju.us.auth0.com/oauth/token',
    authorize_url='https://dev-h1cxd8ju.us.auth0.com/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
)

problems = [
  {
    'author':'Me',
    'title' : 'Very difficult one',
    'content': 'contextuals',
    #'date_posted': date(2003,12,12)
  },
  {
    'author':'You',
    'title' : 'ez problem',
    'content': 'no contextuals',
   # 'date_posted': date(2003,12,13)
  }
]

def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    if 'id' not in session:
      # Redirect to Login page here
      return redirect('/')
    return f(*args, **kwargs)
  return decorated

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
@app.route("/home/<int:page_num>")
def hello():
  user = None
  if 'id' in session:
    user = User.query.filter_by(id=session['id']).first()
  page = request.args.get('page', 1, type=int)
  problems = Problem.query.order_by(Problem.date_posted.desc()).paginate(page=page, per_page=5)
  topcontributors = User.query.order_by(User.contribution).limit(5).all()
  topsolvers = User.query.order_by(User.score).limit(5).all()
  return render_template('home.html', problems=problems, user=user, page=page, conts=topcontributors, solvs=topsolvers)

#login route for redirects
@app.route("/login")
def login():
  if 'profile' in session:
    print("Already have profile")
    return redirect(url_for('hello'))
  return auth0.authorize_redirect(redirect_uri='https://127.0.0.1:5000/callback')

#configured to retrieve and store from auth0
@app.route('/callback')
def callback_handling():
    # Handles response from token endpoint
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()
    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture'],
        'sub': userinfo['sub']
    }
    #redirect to new_login to create pair within database
    if User.query.filter_by(sub=userinfo['sub']).first() is None:
      return redirect(url_for('new_login'))
    session['id'] = User.query.filter_by(sub=userinfo['sub']).first().id
    return redirect('/dashboard')

#initializes user within database
@app.route('/newuser', methods=['GET','POST'])
def new_login():
  if 'id' in session or 'profile' not in session:
    return redirect('/')
  #saves default picture
  filename=secrets.token_hex(8)
  with open(app.config['UPLOAD_FOLDER']+'pics/'+filename, 'wb') as f:
    f.write(requests.get(session['profile']['picture']).content)
  #stores user's or auth0's picture
  pic = Picture()
  if pic.submit2.data and pic.validate():
      filename=save_picture(pic.pic.data)
  #creates user
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
  return render_template('acctform.html', 
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

@app.route('/problem/<int:prob_id>')
def show_prob(prob_id):
    user = None
    if 'id' in session:
      user = User.query.filter_by(id=session['id']).first()
    result = Problem.query.filter_by(id=prob_id).first()
    if result is None:
      return "Problem Not Found"
    return "Found"
    # show the post with the given id, the id is an integer

#updates user's columns
@app.route('/update-account', methods=['GET','POST'])
@requires_auth
def updateacct():
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
  return render_template('acctform.html', title='Update User',
    form=form,
    pic=pic, 
    name=user.username,
    firstname=user.firstname,
    lastname=user.lastname,
    img=user.img_file)

#create problem
@app.route('/upload-problem', methods=['GET','POST'])
@requires_auth
def uploadprob():
  user = User.query.filter_by(id=session['id']).first()
  pic = Picture()
  fns = []
  if pic.submit2.data and pic.validate():
    fns.append(save_picture(pic.pic.data))
  form = Create()
  if form.submit3.data and form.validate():
    prob = Problem(
      title=form.title.data,
      statement=form.statement.data,
      input_exp=form.input_exp.data,
      output_exp=form.output_exp.data,
      samplein=form.samplein.data,
      sampleout=form.sampleout.data,
      note = form.note.data,
      user_id = user.id
      )
    db.session.add(prob)
    db.session.commit()
    flash('Problem created!')
    return redirect('/')
  return render_template('probform.html', user=user, form=form, pic=pic, fns=fns,
    title="",
    statement="",
    input_exp="",
    outupt_exp="",
    samplein="",
    sampleout="",
    note="")

@app.route('/edit-problem/<int:prob_id>', methods=['GET','POST'])
@requires_auth
def editprob(prob_id):
  user = User.query.filter_by(id=session['id']).first()
  prob = Problem.query.filter_by(id=prob_id).first()
  if prob is None or prob.user_id is not user.id:
    return "Not Found"
  note = ""
  if prob.note:
    prob.note
  pic = Picture()
  fns = []
  if pic.submit2.data and pic.validate():
    fns.append(save_picture(pic.pic.data))
  form = Create()
  if form.submit3.data and form.validate():
    prob.title=form.title.data
    prob.statement=form.statement.data,
    prob.input_exp=form.input_exp.data,
    prob.output_exp=form.output_exp.data,
    prob.samplein=form.samplein.data,
    prob.sampleout=form.sampleout.data,
    prob.note = form.note.data,
    db.session.commit()
    flash('Problem edited!')
    return redirect('/problem/'+prob.id)
  return render_template('editprob.html', user=user, form=form, pic=pic, fns=fns,
    title=prob.title,
    statement=prob.statement,
    input_exp=prob.input_exp,
    outupt_exp=prob.output_exp,
    samplein=prob.samplein,
    sampleout=prob.sampleout,
    note=note)

@app.route('/delete-user')
@requires_auth
def deleteuser():
  user = User.query.filter_by(id=session['id']).first()
  user.delete()
  db.commit()
  flash("User Deleted")
  return redirect('/logout')

@app.route('/delete-problem/<int:prob_id>')
@requires_auth
def deleteprob(prob_id):
  user=User.query.filter_by(id=session['id']).first()
  prob=Problem.query.filter_by(id=prob_id).first()
  if prob is None or prob.author.id is not user.id:
    return "Not Found"
  prob.delete()
  db.commit()
  flash("Problem Deleted")
  return redirect('/')

#clears session and redirects to auth0's logout endpoint
@app.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    params = {'returnTo': url_for('hello', _external=True), 'client_id': ''}
    flash('Logged out!')
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))
from datetime import datetime
from bemo import db, app

class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  sub = db.Column(db.String(120), unique=True, nullable=False)
  username = db.Column(db.String(20), unique=True, nullable=False)
  firstname = db.Column(db.String(20), nullable=False)
  lastname = db.Column(db.String(20), nullable=False)
  verified = db.Column(db.Boolean, nullable=False)
  img_file = db.Column(db.Text, nullable=False, default='default.jpeg')
  score = db.Column(db.Integer, nullable=False, default=0)
  contribution = db.Column(db.Integer, nullable=False, default=0)
  #solved = db.relationship('Submission',backref='user_id', lazy=True)

class Problem(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(20), unique=True, nullable=False)
  date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
  statement = db.Column(db.Text, nullable=False)
  samplein = db.Column(db.Text)
  sampleout = db.Column(db.Text)
  note = db.Column(db.Text)
  category = db.Column(db.Text)
  rating = db.Column(db.Integer, nullable=False, default=0)
  cases = db.Column(db.Integer, nullable=False, default=0)
  #filenames semicolon seperated
  pics = db.Column(db.Text)
  inputs = db.Column(db.Text)
  outputs = db.Column(db.Text)
  solved = db.Column(db.Integer, nullable=False, default=0)

class Submission(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer,db.ForeignKey(User.id),nullable=False)
  problem_id = db.Column(db.Integer,db.ForeignKey(Problem.id),nullable=False)
  cases = db.Column(db.Integer, default=-1)
  correct = db.Column(db.Boolean)
  message = db.Column(db.Text, default="")
  errline = db.Column(db.Integer)
  #filenames semicolon seperated
  token = db.Column(db.Text)
  #ARRAY only work with postgre
  #tokens = db.Column(db.ARRAY(db.String(120)))


  def __repr__(self):
    return f"User('{self.message}','{self.id}')"
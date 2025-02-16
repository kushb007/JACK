from datetime import datetime, timezone
from bemo import db, app

class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  sub = db.Column(db.String(120), unique=True, nullable=False)
  username = db.Column(db.String(20), unique=True, nullable=False)
  firstname = db.Column(db.String(20), nullable=False)
  lastname = db.Column(db.String(20), nullable=False)
  email = db.Column(db.String(120), unique=True, nullable=False)
  verified = db.Column(db.Boolean, nullable=False)
  img_file = db.Column(db.Text, nullable=False, default='default.jpeg')
  score = db.Column(db.Integer, nullable=False, default=0)
  setup = db.Column(db.Boolean, nullable=False, default=False)
  #solved = db.Column(db.Text, nullable=False, default='[]')

class Problem(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(20), unique=True, nullable=False)
  date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())
  statement = db.Column(db.Text, nullable=False, default='')
  tags = db.Column(db.Text,nullable=False, default='[]')
  rating = db.Column(db.Integer, nullable=False, default=0)
  cases = db.Column(db.Integer, nullable=False, default=0)
  #filenames json formatted
  inputs = db.Column(db.Text,nullable=False, default='[]')
  outputs = db.Column(db.Text, nullable=False, default='[]')
  solved = db.Column(db.Integer, nullable=False, default=0)

class Submission(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer,db.ForeignKey(User.id),nullable=False)
  problem_id = db.Column(db.Integer,db.ForeignKey(Problem.id),nullable=False)
  correct = db.Column(db.Boolean, default=False)
  cases = db.Column(db.Integer, default=0)
  recieved = db.Column(db.Integer, default=0)
  last_check = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
  checks = db.Column(db.Integer, nullable=False, default=0)
  #json formatted tokens
  tokens = db.Column(db.Text, nullable=False, default='[]')
  status = db.Column(db.Text, nullable=False, default='[]')


  def __repr__(self):
    return f"User('{self.status}','{self.id}')"
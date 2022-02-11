from datetime import datetime
from bemo import db, app

class User(db.Model):
  #id = db.Column(db.Integer, primary_key=True)
  id = db.Column(db.Integer, primary_key=True)
  sub = db.Column(db.String(120), unique=True, nullable=False)
  username = db.Column(db.String(20), unique=True, nullable=False)
  firstname = db.Column(db.String(20), nullable=False)
  lastname = db.Column(db.String(20), nullable=False)
  verified = db.Column(db.Boolean, nullable=False)
  img_file = db.Column(db.Text, nullable=False, default='default.jpeg')
  score = db.Column(db.Integer, nullable=False, default=0)
  contribution = db.Column(db.Integer, nullable=False, default=0)
  problems = db.relationship('Problem', backref='author', lazy=True)

class Problem(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(20), unique=True, nullable=False)
  date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
  statement = db.Column(db.Text, nullable=False)
  input_exp = db.Column(db.Text)
  output_exp = db.Column(db.Text)
  samplein = db.Column(db.Text)
  sampleout = db.Column(db.Text)
  note = db.Column(db.Text)
  rating = db.Column(db.Integer, nullable=False, default=0)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  #ARRAY only work with postgre
  #pics = db.Column(db.ARRAY(db.String(120)))

  def __repr__(self):
    return f"User('{self.title}','{self.date_posted}')"
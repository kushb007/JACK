from flask import Flask, jsonify, redirect, render_template, session, url_for
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = ''
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = os.getcwd()+'/bemo/static/'
app.config['CLIENT_ID'] = ''
db = SQLAlchemy(app)
oauth = OAuth(app)

from bemo import routes
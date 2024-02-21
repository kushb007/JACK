from flask import Flask, jsonify, redirect, render_template, session, url_for
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from os import environ as env
import os
from dotenv import load_dotenv, find_dotenv
import io

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.config['SECRET_KEY'] = env.get("APP_SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = os.getcwd()+'/bemo/static/'
app.config['CLIENT_ID'] = env.get("AUTH0_CLIENT_ID")
db = SQLAlchemy(app)
oauth = OAuth(app)

app.app_context().push()

from bemo import routes
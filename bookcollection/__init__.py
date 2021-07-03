from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SECRET_KEY'] = '5e4cdfec62d41e54e046889d'
#app.config['IMG_DIR'] = os.path.join(os.getcwd(), 'bookcollection', 'static', 'images')
db = SQLAlchemy(app)

from dotenv import load_dotenv
load_dotenv()

import os
import dotenv

print('DEBUG: DATABASE_URL from os.environ:', os.environ.get('DATABASE_URL'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a hard to guess string'
    _env = dotenv.dotenv_values()
    SQLALCHEMY_DATABASE_URI = _env.get('DATABASE_URL') or \
        'postgresql://postgres:eurus@localhost:5432/vnexpress_analyzer_db'
    print('DEBUG: SQLALCHEMY_DATABASE_URI in Config:', SQLALCHEMY_DATABASE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

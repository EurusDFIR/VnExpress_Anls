from dotenv import load_dotenv
load_dotenv()

import os
import dotenv

print('DEBUG: DATABASE_URL from os.environ:', os.environ.get('DATABASE_URL'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a hard to guess string'
    _env = dotenv.dotenv_values()
    DATABASE_URL = os.environ.get('DATABASE_URL') or _env.get('DATABASE_URL') or \
        'postgresql://postgres:eurus@localhost:5432/vnexpress_analyzer_db'
    
    # Render uses postgres:// but SQLAlchemy requires postgresql://
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

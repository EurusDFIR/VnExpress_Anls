#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app import create_app, db
from app.models import Article, Comment, Topic
import os

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Article': Article,
        'Comment': Comment,
        'Topic': Topic
    }

if __name__ == '__main__':
    app.run(debug=True)
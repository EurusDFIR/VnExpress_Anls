from app import db
from app.models import Article, Comment
article = Article.query.get('https://vnexpress.net/vuot-o-diem-mu-xe-may-lao-thang-vao-xe-dau-keo-4885385.html')
Comment.query.filter_by(article_id=article.id).delete()
db.session.commit()
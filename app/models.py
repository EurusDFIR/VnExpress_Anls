from app import db
from datetime import datetime, timezone

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500),unique=True, nullable=False, index=True)
    title = db.Column(db.String(500),nullable=True)
    sapo = db.Column(db.Text,nullable=True)
    content = db.Column(db.Text,nullable=True)
    author = db.Column(db.String(200),nullable=True)
    published_date_str = db.Column(db.String(100),nullable=True)
    publish_datetime = db.Column(db.DateTime, nullable=True,index=True)
    category = db.Column(db.String(200),nullable = True, index = True)
    total_comment_count = db.Column(db.Integer, default =0)
    last_scraped_at = db.Column(db.DateTime, default=lambda: datetime.utcnow())
    sentiment_score = db.Column(db.Float, nullable=True)
    main_topic_id = db.Column(db.Integer,db.ForeignKey('topics.id'), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)

    comments = db.relationship('Comment', backref = 'article',lazy = 'dynamic', cascade="all, delete-orphan")
    article_topics = db.relationship('ArticleTopic', backref = 'article', lazy = 'dynamic', cascade="all, delete-orphan")   

    def __repr__(self):
        return f'<Article {self.title[:50]}...>'
    
class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=False, index=True)
    # Hoặc dùng article_url nếu bạn muốn tham chiếu qua URL
    # article_url_fk = db.Column(db.String(500), db.ForeignKey('articles.url'), nullable=False, index=True)
    comment_api_id = db.Column(db.String(100), unique=True, nullable=True) # ID từ API bình luận (nếu có)
    user_name = db.Column(db.String(200), nullable=True)
    comment_text = db.Column(db.Text, nullable=False)
    comment_date_str = db.Column(db.String(100), nullable=True)
    comment_datetime = db.Column(db.DateTime, nullable=True, index=True)
    likes_count = db.Column(db.Integer, default=0)
    replies_count = db.Column(db.Integer, default=0) # Số lượng trả lời trực tiếp
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True) # Tự tham chiếu
    sentiment_label = db.Column(db.String(50), nullable=True) # positive, negative, neutral
    sentiment_score_comment = db.Column(db.Float, nullable=True)

    # Mối quan hệ cho replies
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Comment by {self.user_name}: {self.comment_text[:30]}...>'

# Bảng Topics
class Topic(db.Model):
    __tablename__ = 'topics'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False) 
    keywords = db.Column(db.Text, nullable=True) # Các từ khóa chính của chủ đề, dạng JSON hoặc CSV

    # Mối quan hệ với bảng ArticleTopic
    topic_articles = db.relationship('ArticleTopic', backref='topic', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Topic {self.name}>'

#  Bảng liên kết nhiều-nhiều giữa Article và Topic
class ArticleTopic(db.Model):
    __tablename__ = 'article_topics'
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), primary_key=True)
    relevance_score = db.Column(db.Float, nullable=True) # Điểm
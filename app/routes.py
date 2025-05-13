# app/routes.py
from flask import render_template, request, redirect, url_for, flash, abort
from app import db
from app.models import Article
from scraper.vnexpress_scraper import scrape_article_details_and_save, get_article_urls_from_category_page 
from urllib.parse import urlparse
from datetime import datetime
from flask import Blueprint
import os
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    else:
        genai = None
except ImportError:
    genai = None
    GEMINI_API_KEY = None

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
def index():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    category_filter = request.args.get('category', 'All Categories')
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')
    sort_by_filter = request.args.get('sort_by', 'newest_first')
    query = Article.query
    if search_query:
        search = f"%{search_query}%"
        query = query.filter(
            (Article.title.ilike(search)) |
            (Article.category.ilike(search)) |
            (Article.author.ilike(search))
        )
    if category_filter and category_filter != "All Categories":
        query = query.filter(Article.category == category_filter)
    if date_from_str:
        try:
            date_from_obj = datetime.strptime(date_from_str, '%Y-%m-%d')
            query = query.filter(Article.publish_datetime >= date_from_obj)
        except ValueError:
            flash('Định dạng ngày bắt đầu không hợp lệ.', 'danger')
    if date_to_str:
        try:
            date_to_obj = datetime.strptime(date_to_str, '%Y-%m-%d')
            query = query.filter(Article.publish_datetime <= datetime(date_to_obj.year, date_to_obj.month, date_to_obj.day, 23, 59, 59))
        except ValueError:
            flash('Định dạng ngày kết thúc không hợp lệ.', 'danger')
    if sort_by_filter == 'newest_first':
        query = query.order_by(Article.publish_datetime.desc().nullslast())
    elif sort_by_filter == 'oldest_first':
        query = query.order_by(Article.publish_datetime.asc().nullsfirst())
    elif sort_by_filter == 'most_comments':
        query = query.order_by(Article.total_comments_count.desc().nullslast())
    categories_query = db.session.query(Article.category).distinct().order_by(Article.category).all()
    categories = ["All Categories"] + [cat[0] for cat in categories_query if cat[0]]
    articles_pagination = query.paginate(page=page, per_page=9, error_out=False)
    articles_on_page = articles_pagination.items
    return render_template('index.html', title='VnExpress Analyzer',
                           articles=articles_on_page, pagination=articles_pagination,
                           categories=categories,
                           current_category=category_filter,
                           current_date_from=date_from_str,
                           current_date_to=date_to_str,
                           current_sort_by=sort_by_filter,
                           current_year=datetime.utcnow().year
                           )

@main_bp.route('/article/<int:article_id>')
def article_detail(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)
    mock_sentiment_data = {"positive": 0, "negative": 0, "neutral": 0, "total_comments": 0}
    mock_discussion_topics = []
    mock_interaction_data = {
        "total_comments": article.total_comment_count if article.total_comment_count else 0,
        "original_comments": 0, "replies": 0, "active_threads": 0,
        "top_users": [], "most_liked_comment": None
    }
    comments_on_page = []
    comments_pagination = None
    return render_template('article_detail.html', title=article.title, article=article,
                           comments=comments_on_page, comment_pagination=comments_pagination,
                           sentiment_data=mock_sentiment_data,
                           discussion_topics=mock_discussion_topics,
                           interaction_data=mock_interaction_data)

@main_bp.route('/analyze-new', methods=['POST'])
def analyze_new_article():
    article_url = request.form.get('article_url')
    if not article_url:
        flash('Vui lòng nhập URL bài viết.', 'warning')
        return redirect(url_for('main.index'))
    parsed_url = urlparse(article_url)
    if not parsed_url.scheme or parsed_url.netloc != 'vnexpress.net' or not article_url.endswith('.html'):
        flash('URL không hợp lệ hoặc không phải từ VnExpress.', 'danger')
        return redirect(url_for('main.index'))
    existing_article = Article.query.filter_by(url=article_url).first()
    if existing_article:
        flash('Bài viết này đã được phân tích. Đang chuyển đến trang chi tiết.', 'info')
        return redirect(url_for('main.article_detail', article_id=existing_article.id))
    newly_scraped_article = scrape_article_details_and_save(article_url, db.session)
    if newly_scraped_article and newly_scraped_article.id:
        flash(f'Đã phân tích thành công bài viết: {newly_scraped_article.title}', 'success')
        return redirect(url_for('main.article_detail', article_id=newly_scraped_article.id))
    else:
        flash('Không thể phân tích bài viết. Vui lòng thử lại hoặc kiểm tra URL.', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/search-suggest')
def search_suggest():
    q = request.args.get('q', '').strip()
    suggestions = []
    if q and len(q) >= 2:
        keywords = [kw.strip() for kw in q.lower().split() if kw.strip()]
        if keywords:
            # Ưu tiên tiêu đề chứa từ khóa ở đầu, sau đó mới đến category/author
            title_matches = []
            category_matches = []
            author_matches = []
            for kw in keywords:
                like_kw = f"%{kw}%"
                title_matches += Article.query.filter(Article.title.ilike(like_kw)).order_by(Article.publish_datetime.desc()).all()
                category_matches += Article.query.filter(Article.category.ilike(like_kw)).order_by(Article.publish_datetime.desc()).all()
                author_matches += Article.query.filter(Article.author.ilike(like_kw)).order_by(Article.publish_datetime.desc()).all()
            # Loại trùng lặp, ưu tiên tiêu đề, sau đó category, author
            seen = set()
            for art in title_matches:
                if art.title and art.title not in seen:
                    suggestions.append({'type': 'title', 'value': art.title})
                    seen.add(art.title)
            for art in category_matches:
                if art.category and art.category not in seen:
                    suggestions.append({'type': 'category', 'value': art.category})
                    seen.add(art.category)
            for art in author_matches:
                if art.author and art.author not in seen:
                    suggestions.append({'type': 'author', 'value': art.author})
                    seen.add(art.author)
    return {"suggestions": suggestions[:15], "keywords": keywords}


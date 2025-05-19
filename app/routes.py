# app/routes.py
from flask import render_template, request, redirect, url_for, flash, abort, jsonify
from app import db
from app.models import Article
from scraper.vnexpress_scraper import scrape_article_details_and_save, get_article_urls_from_category_page 
from urllib.parse import urlparse
from datetime import datetime
from flask import Blueprint
import os
from dotenv import load_dotenv
import time
from collections import Counter

#TuanAnh_update
TEAM_INFO_PAGE = {
    "lecturer": "Nguyễn Thế Bảo", # Tên giảng viên
    "members": [
        {
            "name": "Lê Văn Hoàng", # Thay tên
            "mssv": "2224802010279", # Thay MSSV
            "avatar": "images/avatars/hoang.png", # Đường dẫn đến ảnh trong static/images/avatars/
            "role": "Project Lead & Backend Developer", # Vai trò
            "bio": "Đam mê giải quyết các bài toán khó bằng code và dữ liệu.", # Mô tả ngắn
            "google": "2224802010279@student.tdmu.edu.vn", # Link Goole
            "github": "https://github.com/EurusDFIR" # Link GitHub 
        },
        {
            "name": "Lê Nguyễn Hoàng", 
            "mssv": "222480201081", 
            "avatar": "images/avatars/hoang.png", 
            "role": "Backend Developer", 
            "bio": "Đam mê giải quyết các bài toán khó bằng code và dữ liệu.",
            "google": "2224802010814@student.tdmu.edu.vn", 
            "github": "https://github.com/CooloBi21" 
        },
        {
            "name": "Nguyễn Tuấn Anh", 
            "mssv": "2224802010328", 
            "avatar": "images/avatars/anh.png", 
            "role": "Frontend Developer & UI/UX Designer",
            "bio": "Yêu thích việc tạo ra những giao diện đẹp mắt và thân thiện với người dùng.",
            "google": "2224802010328@student.tdmu.edu.vn", 
            "github": "https://github.com/ALZPotato" 
        },
        # Thêm các thành viên khác vào đây theo cấu trúc tương tự
    ],
    "team_photo": "images/team_photo.png" # Tùy chọn: đường dẫn đến ảnh cả nhóm trong static/images/
}

load_dotenv()

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
    real_comment_count = article.comments.count()
    if article.total_comment_count != real_comment_count:
        article.total_comment_count = real_comment_count
        db.session.commit()
    all_comments = article.comments.order_by(
        Article.comments.property.mapper.class_.comment_datetime.asc().nullslast(),
        Article.comments.property.mapper.class_.id.asc()
    ).all()
    # Build a pure dict tree for template
    comment_dict = {}
    for c in all_comments:
        comment_dict[c.id] = {
            'id': c.id,
            'user_name': c.user_name,
            'comment_text': c.comment_text,
            'comment_datetime': c.comment_datetime,
            'comment_date_str': c.comment_date_str,
            'likes_count': c.likes_count,
            'children': [],
            'sentiment_label': c.sentiment_label,
            'sentiment_score_comment': c.sentiment_score_comment
        }
    tree = []
    for c in all_comments:
        node = comment_dict[c.id]
        if c.parent_comment_id and c.parent_comment_id in comment_dict:
            comment_dict[c.parent_comment_id]['children'].append(node)
        else:
            tree.append(node)
    # PHÂN TRANG comment gốc (không phải reply)
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Số comment gốc mỗi trang
    total_root_comments = len(tree)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_tree = tree[start:end]
    total_pages = (total_root_comments + per_page - 1) // per_page
    total_comments = len(all_comments)
    # Sentiment statistics
    sentiment_counter = Counter([c.sentiment_label for c in all_comments if c.sentiment_label])
    sentiment_data = {
        "positive": round(100 * sentiment_counter.get("Positive", 0) / total_comments, 1) if total_comments else 0,
        "negative": round(100 * sentiment_counter.get("Negative", 0) / total_comments, 1) if total_comments else 0,
        "neutral": round(100 * sentiment_counter.get("Neutral", 0) / total_comments, 1) if total_comments else 0,
        "total_comments": total_comments
    }
    mock_discussion_topics = []
    mock_interaction_data = {
        "total_comments": total_comments,
        "original_comments": len([c for c in all_comments if not c.parent_comment_id]),
        "replies": len([c for c in all_comments if c.parent_comment_id]),
        "active_threads": 0,
        "top_users": [], "most_liked_comment": None
    }
    return render_template('article_detail.html', title=article.title, article=article,
                           comment_tree=paginated_tree,
                           comment_pagination={
                               'page': page,
                               'per_page': per_page,
                               'total_pages': total_pages,
                               'total_root_comments': total_root_comments
                           },
                           sentiment_data=sentiment_data,
                           discussion_topics=mock_discussion_topics,
                           interaction_data=mock_interaction_data)

@main_bp.route('/analyze-new', methods=['POST'])
def analyze_new_article():
    article_url = request.form.get('article_url')
    scrape_comments = request.form.get('scrape_comments', 'off') == 'on'
    try:
        max_comments = int(request.form.get('max_comments', 100))
        if max_comments < 1: max_comments = 1
        if max_comments > 500: max_comments = 500
    except Exception:
        max_comments = 100
    parsed_url = urlparse(article_url)
    if not parsed_url.scheme or parsed_url.netloc != 'vnexpress.net' or not article_url.endswith('.html'):
        flash('URL không hợp lệ hoặc không phải từ VnExpress.', 'danger')
        return redirect(url_for('main.index'))
    existing_article = Article.query.filter_by(url=article_url).first()
    if existing_article:
        flash('Bài viết này đã được phân tích. Đang chuyển đến trang chi tiết.', 'info')
        return redirect(url_for('main.article_detail', article_id=existing_article.id))
 
    t0 = time.time()
    newly_scraped_article = scrape_article_details_and_save(article_url, db.session, scrape_comments=scrape_comments, max_comments=max_comments)
    t1 = time.time()
    scrape_article_time = t1 - t0
    if newly_scraped_article and newly_scraped_article.id:
        total_time = t1 - t0
        flash(f'Đã phân tích thành công bài viết: {newly_scraped_article.title}', 'success')
        flash(f'Thời gian scrape: {scrape_article_time:.2f}s', 'info')
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

@main_bp.route('/latest-articles')
def latest_articles():
    articles = Article.query.order_by(Article.publish_datetime.desc().nullslast()).limit(10).all()
    return render_template('latest_articles.html', title='Bài viết mới nhất', articles=articles)

#TuanAnh_update
# === START: Route cho trang About ===
@main_bp.route('/about')
def about():
    # Bạn có thể truyền thêm dữ liệu vào trang about nếu cần
    # Ví dụ: Lấy lại thông tin TEAM_INFO_PAGE để hiển thị chi tiết hơn trên trang About
    # Hoặc một mô tả dài hơn về dự án, công nghệ sử dụng, v.v.
    about_project_description = """
        VnExpress Analyzer là một dự án được xây dựng nhằm mục đích học tập và trình diễn khả năng
        phân tích dữ liệu từ các bài báo trên VnExpress. Ứng dụng cho phép người dùng không chỉ xem
        nội dung bài viết mà còn cung cấp các phân tích về cảm xúc (sentiment analysis) trong bình luận,
        các chủ đề chính được thảo luận, và một số thống kê tương tác khác. Dự án sử dụng Python, Flask,
        PostgreSQL, cùng với các thư viện xử lý ngôn ngữ tự nhiên và scraping dữ liệu.
    """
    technologies_used = [
        "Python", "Flask", "SQLAlchemy", "PostgreSQL",
        "Tailwind CSS", "JavaScript", "Font Awesome",
        "NLTK (hoặc thư viện NLP khác)", "BeautifulSoup / Scrapy / Playwright (cho scraping)"
    ]

    return render_template('about.html',
                           title='Giới Thiệu - VnExpress Analyzer',
                           project_description=about_project_description,
                           technologies=technologies_used,
                           page_team_info=TEAM_INFO_PAGE, # Truyền thông tin đội ngũ vào trang about
                           current_year=datetime.utcnow().year # Cần thiết nếu about.html không kế thừa base.html có sẵn current_year
                          )
# === END: Route cho trang About ===
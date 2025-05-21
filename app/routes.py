# --- moved Blueprint definition and imports to the top ---
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, abort, jsonify
from app import db
from app.models import Article, Category, Comment, Topic, ArticleTopic
from scraper.vnexpress_scraper import get_true_scrape_targets, get_article_urls_from_category_page, scrape_article_details_and_save, scrape_and_save_comments
from urllib.parse import urlparse
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import time
from collections import Counter
from sqlalchemy import or_, func
from sqlalchemy.orm import load_only
from concurrent.futures import ThreadPoolExecutor, as_completed

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

from analysis.lda_topic_model import LdaModel_Test
import pandas as pd
from collections import Counter
import re
import json
from random import shuffle

load_dotenv()

main_bp = Blueprint('main', __name__)

# Helper function to get article counts by category
def get_article_counts_by_category(session):
    counts = session.query(
        Article.category_id, 
        func.count(Article.id)
    ).group_by(Article.category_id).all()
    
    return {cat_id: count for cat_id, count in counts}

    # --- Scrape Center routes ---
@main_bp.route('/scrape-center')
def scrape_center_page():
    def get_category_tree(session):
        # Lấy tất cả các categories từ cơ sở dữ liệu
        all_cats = session.query(Category).options(
            load_only(Category.id, Category.name, Category.parent_id, Category.url, Category.is_active)
        ).all()
        
        # Tạo dictionary ánh xạ ID -> Category và parent_id -> [child categories]
        cat_dict = {c.id: c for c in all_cats}
        children_map = {}
        for cat in all_cats:
            if cat.parent_id:
                children_map.setdefault(cat.parent_id, []).append(cat)
        
        # Tạo cây phân cấp
        tree = []

        # Thêm thuộc tính article_count
        cat_counts = get_article_counts_by_category(session)
        
        # Hàm đệ quy để xây dựng cây
        def build_node(category, level=0):
            return {
                'id': category.id,
                'name': category.name,
                'url': category.url,
                'level': level,
                'article_count': cat_counts.get(category.id, 0),
                'children': [build_node(child, level + 1) for child in children_map.get(category.id, [])]
            }
        
        # Xây dựng cây bắt đầu từ các node gốc (không có parent)
        root_categories = [c for c in all_cats if not c.parent_id]
        for root_cat in root_categories:
            tree.append(build_node(root_cat))
        
        return tree

    # Get scrape status from session if available
    scrape_status = session.pop('scrape_status', None)
    scrape_message = session.pop('scrape_message', None)
    
    # Xây dựng cây phân cấp chuyên mục
    categories_tree = get_category_tree(db.session)
    
    return render_template('scrape_center.html', 
                           categories_tree=categories_tree,
                           scrape_status=scrape_status,
                           scrape_message=scrape_message)

@main_bp.route('/start-bulk-scrape', methods=['POST'])
def start_bulk_scrape():
    selected_ids = request.form.getlist('selected_categories')
    scrape_comments_flag = request.form.get('scrape_comments') == 'true'
    
    print("\n=== BẮT ĐẦU QUÁ TRÌNH SCRAPE ===")
    print(f"Các category được chọn: {selected_ids}")
    
    if not selected_ids:
        flash('Vui lòng chọn ít nhất một chuyên mục để scrape.', 'warning')
        session['scrape_status'] = 'warning'
        session['scrape_message'] = 'Vui lòng chọn ít nhất một chuyên mục để scrape.'
        return redirect(url_for('main.scrape_center_page'))
        
    selected_map = {}
    for cat_id_str in selected_ids:
        try:
            cat_id = int(cat_id_str)
            count_str = request.form.get(f'count_for_cat_{cat_id}')
            num_articles = int(count_str) if count_str and count_str.isdigit() else None
            selected_map[cat_id] = num_articles
            print(f"Category ID {cat_id}: sẽ scrape {num_articles if num_articles else 10} bài")
        except ValueError:
            flash(f"Giá trị không hợp lệ cho category ID {cat_id_str} hoặc số lượng.", "danger")
            session['scrape_status'] = 'error'
            session['scrape_message'] = f"Giá trị không hợp lệ cho category ID {cat_id_str} hoặc số lượng."
            return redirect(url_for('main.scrape_center_page'))
            
    default_cat = db.session.query(Category).filter(Category.name.ilike("Chưa phân loại")).first()
    default_cat_id = default_cat.id if default_cat else None
    
    flash('Bắt đầu quá trình scrape. Việc này có thể mất vài phút...', 'info')
    scrape_targets_list = get_true_scrape_targets(selected_map, db.session, default_article_count_if_not_set=10)
    
    print(f"\nCác mục tiêu scrape thực sự: {scrape_targets_list}")
    total_articles_scraped_session = 0
    total_comments_scraped_session = 0
    
    app = current_app._get_current_object()
    
    def scrape_with_app_context(url):
        with app.app_context():
            session = db.session()  # Create a new session for this thread
            try:
                # Use the session for this thread
                article_obj = scrape_article_details_and_save(
                    url, 
                    session, 
                    scrape_comments=scrape_comments_flag
                )
                
                if article_obj:
                    # Get all the data we need from the article while the session is still active
                    article_data = {
                        'id': article_obj.id,
                        'title': article_obj.title,
                        'url': article_obj.url,
                        'comment_count': session.query(Comment).filter_by(article_id=article_obj.id).count()
                    }
                    # Commit changes
                    session.commit()
                    return article_data
                else:
                    session.rollback()
                    return None
            except Exception as e:
                # Rollback on error
                session.rollback()
                print(f"Error in scrape_with_app_context: {e}")
                return None
            finally:
                session.close()  # Always close the session

    # Use a single ThreadPoolExecutor for scraping article details across all categories
    with ThreadPoolExecutor(max_workers=current_app.config.get('SCRAPE_MAX_WORKERS', 5)) as executor:
        for cat_name, cat_url, num_articles_to_get in scrape_targets_list:
            print(f"\n=== ĐANG SCRAPE CHUYÊN MỤC: {cat_name} ===")
            print(f"URL chuyên mục: {cat_url}")
            print(f"Số bài cần lấy: {num_articles_to_get}")
            
            flash(f"Đang xử lý chuyên mục: {cat_name} ({num_articles_to_get} bài)...", "info")
            
            # Stage 1: Get article URLs
            article_urls_from_cat = get_article_urls_from_category_page(
                cat_url, 
                max_articles=num_articles_to_get,
                db_session=db.session
            )
            
            if not article_urls_from_cat:
                print(f"Không tìm thấy URL bài viết mới nào cho {cat_name} từ {cat_url}")
                continue
                
            print(f"Tìm thấy {len(article_urls_from_cat)} URL bài viết mới. Bắt đầu scrape chi tiết...")
            
            # Stage 2: Scrape article details in parallel
            future_to_url = {
                executor.submit(scrape_with_app_context, url): url 
                for url in article_urls_from_cat
            }

            articles_scraped_this_category = 0
            comments_scraped_this_category = 0
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    article_data = future.result()
                    if article_data:
                        articles_scraped_this_category += 1
                        total_articles_scraped_session += 1
                        # Use count() method instead of len() for SQLAlchemy relationships
                        comments_count = article_data['comment_count']
                        comments_scraped_this_category += comments_count
                        total_comments_scraped_session += comments_count
                        print(f"[✓] Đã scrape bài viết: {article_data['title']}")
                        if comments_count > 0:
                            print(f"    └─ Đã scrape {comments_count} bình luận")
                    else:
                        print(f"Bài viết đã tồn tại hoặc không thể scrape chi tiết cho URL: {url}")
                except Exception as exc:
                    print(f'URL {url} tạo ra exception khi scrape chi tiết: {exc}')
            
            print(f"Hoàn tất xử lý {articles_scraped_this_category} bài cho chuyên mục {cat_name}.")
            if scrape_comments_flag:
                print(f"Đã scrape {comments_scraped_this_category} bình luận cho chuyên mục {cat_name}.")

    print(f"\n=== KẾT THÚC TOÀN BỘ QUÁ TRÌNH SCRAPE ===")
    print(f"Tổng số bài đã scrape: {total_articles_scraped_session}")
    print(f"Tổng số bình luận đã scrape: {total_comments_scraped_session}")
    
    if total_articles_scraped_session == 0:
        flash(f'Không tìm thấy bài viết mới nào để scrape trong các chuyên mục đã chọn.', 'warning')
        session['scrape_status'] = 'warning'
        session['scrape_message'] = 'Không tìm thấy bài viết mới nào để scrape trong các chuyên mục đã chọn.'
    else:
        flash(f'Hoàn tất scrape! Đã scrape được {total_articles_scraped_session} bài viết mới và {total_comments_scraped_session} bình luận (nếu có).', 'success')
        session['scrape_status'] = 'success'
        session['scrape_message'] = f'Hoàn tất scrape! Đã scrape được {total_articles_scraped_session} bài viết mới và {total_comments_scraped_session} bình luận (nếu có).'
    
    return redirect(url_for('main.index'))


@main_bp.route('/')
@main_bp.route('/index')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 12  # Số bài viết hiển thị trên mỗi trang
    
    # Filters
    category = request.args.get('category', 'All Categories')
    date_from = request.args.get('date_from', None)
    date_to = request.args.get('date_to', None)
    search_query = request.args.get('q', '')
    sort_by = request.args.get('sort_by', 'newest_first')
    
    # Query
    articles_query = Article.query
    
    # Apply search filter if provided
    if search_query:
        articles_query = articles_query.filter(
            or_(
                Article.title.ilike(f"%{search_query}%"),
                Article.sapo.ilike(f"%{search_query}%"),
                Article.content.ilike(f"%{search_query}%")
            )
        )
    
    # Apply category filter if not "All Categories"
    if category and category != 'All Categories':
        articles_query = articles_query.join(Article.category).filter(Category.name == category)
    
    # Apply date filters
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            articles_query = articles_query.filter(Article.publish_datetime >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Add a day to include the full end date
            date_to_obj = date_to_obj + timedelta(days=1)
            articles_query = articles_query.filter(Article.publish_datetime <= date_to_obj)
        except ValueError:
            pass
            
    # Apply sorting
    if sort_by == 'oldest_first':
        articles_query = articles_query.order_by(Article.publish_datetime.asc())
    elif sort_by == 'most_comments':
        articles_query = articles_query.order_by(Article.total_comment_count.desc())
    else:  # newest_first (default)
        articles_query = articles_query.order_by(Article.publish_datetime.desc())
    
    # Paginate results
    pagination = articles_query.paginate(page=page, per_page=per_page, error_out=False)
    articles = pagination.items
    
    # Get all categories for the filter
    categories = ['All Categories'] + [cat.name for cat in Category.query.order_by(Category.name).all()]
    
    # Get scrape process status from session if available
    scrape_status = session.pop('scrape_status', None)
    scrape_message = session.pop('scrape_message', None)
    
    return render_template(
        'index.html',
        title='Home',
        articles=articles,
        pagination=pagination,
        categories=categories,
        current_category=category,
        current_date_from=date_from,
        current_date_to=date_to,
        current_sort_by=sort_by,
        scrape_status=scrape_status,
        scrape_message=scrape_message
    )

@main_bp.route('/article/<int:article_id>')
def article_detail(article_id):
    from analysis.sentiment_analyzer import analyze_article_comments, get_comment_sentiment_counts
    import json
    
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
    
    # Analyze comments sentiment if needed
    run_analysis = request.args.get('analyze', 'false') == 'true'
    if run_analysis:
        sentiment_data = analyze_article_comments(article_id, db.session)
    
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
    
    # Get sentiment statistics
    sentiment_counts = get_comment_sentiment_counts(article_id, db.session)
    sentiment_data = {
        "positive": round(100 * sentiment_counts.get("Positive", 0) / total_comments, 1) if total_comments else 0,
        "negative": round(100 * sentiment_counts.get("Negative", 0) / total_comments, 1) if total_comments else 0,
        "neutral": round(100 * sentiment_counts.get("Neutral", 0) / total_comments, 1) if total_comments else 0,
        "total_comments": total_comments
    }
    
    # Prepare chart data
    sentiment_chart_data = {
        'labels': ['Tích cực', 'Tiêu cực', 'Trung lập'],
        'values': [
            sentiment_counts.get("Positive", 0),
            sentiment_counts.get("Negative", 0),
            sentiment_counts.get("Neutral", 0)
        ],
        'colors': ['#10B981', '#EF4444', '#F59E0B']  # Green, Red, Yellow/Orange
    }
    
    # Convert to JSON for JavaScript
    sentiment_chart_json = json.dumps(sentiment_chart_data)
    
    # Get topic analysis if analyze flag is set
    from analysis.topic_modeler import analyze_article_topics
    discussion_topics = []
    if run_analysis and total_comments > 0:
        try:
            topic_analysis = analyze_article_topics(article_id, db.session)
            if topic_analysis and 'topics' in topic_analysis:
                discussion_topics = topic_analysis['topics']
        except Exception as e:
            print(f"Lỗi khi phân tích chủ đề: {e}")
    
    # Interaction data
    interaction_data = {
        "total_comments": total_comments,
        "original_comments": len([c for c in all_comments if not c.parent_comment_id]),
        "replies": len([c for c in all_comments if c.parent_comment_id]),
        "active_threads": 0,
        "top_users": [],
        "most_liked_comment": None
    }
    
    # Get scrape status from session if available
    scrape_status = session.pop('scrape_status', None)
    scrape_message = session.pop('scrape_message', None)
    
    return render_template('article_detail.html',
        title=article.title,
        article=article,
        comment_tree=paginated_tree,
        comment_pagination={
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_root_comments': total_root_comments
        },
        sentiment_data=sentiment_data,
        sentiment_chart_json=sentiment_chart_json,
        discussion_topics=discussion_topics,
        interaction_data=interaction_data,
        scrape_status=scrape_status,
        scrape_message=scrape_message
    )

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
        session['scrape_status'] = 'error'
        session['scrape_message'] = 'URL không hợp lệ hoặc không phải từ VnExpress.'
        return redirect(url_for('main.index'))
    existing_article = Article.query.filter_by(url=article_url).first()
    if existing_article:
        flash('Bài viết này đã được phân tích. Đang chuyển đến trang chi tiết.', 'info')
        session['scrape_status'] = 'info'
        session['scrape_message'] = 'Bài viết này đã được phân tích. Đang chuyển đến trang chi tiết.'
        return redirect(url_for('main.article_detail', article_id=existing_article.id))
 
    t0 = time.time()
    newly_scraped_article = scrape_article_details_and_save(article_url, db.session, scrape_comments=scrape_comments, max_comments=max_comments)
    t1 = time.time()
    scrape_article_time = t1 - t0
    if newly_scraped_article:
        total_time = t1 - t0
        flash(f'Đã phân tích thành công bài viết: {newly_scraped_article.title}', 'success')
        flash(f'Thời gian scrape: {scrape_article_time:.2f}s', 'info')
        session['scrape_status'] = 'success'
        session['scrape_message'] = f'Đã phân tích thành công bài viết: {newly_scraped_article.title} (Thời gian: {scrape_article_time:.2f}s)'
        return redirect(url_for('main.article_detail', article_id=newly_scraped_article.id))
    else:
        flash('Không thể phân tích bài viết. Vui lòng thử lại hoặc kiểm tra URL.', 'danger')
        session['scrape_status'] = 'error'
        session['scrape_message'] = 'Không thể phân tích bài viết. Vui lòng thử lại hoặc kiểm tra URL.'
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
                # Search categories by Category.name, then get unique categories, then get articles in those categories
                matched_categories = Category.query.filter(Category.name.ilike(like_kw)).all()
                for cat in matched_categories:
                    # Add all articles in this category (recent first)
                    category_matches += Article.query.filter(Article.category_id == cat.id).order_by(Article.publish_datetime.desc()).all()
                author_matches += Article.query.filter(Article.author.ilike(like_kw)).order_by(Article.publish_datetime.desc()).all()
            # Loại trùng lặp, ưu tiên tiêu đề, sau đó category, author
            seen = set()
            for art in title_matches:
                if art.title and art.title not in seen:
                    suggestions.append({'type': 'title', 'value': art.title})
                    seen.add(art.title)
            # For category suggestions, show the category name (not the object)
            for art in category_matches:
                if art.category and art.category.name and art.category.name not in seen:
                    suggestions.append({'type': 'category', 'value': art.category.name})
                    seen.add(art.category.name)
            for art in author_matches:
                if art.author and art.author not in seen:
                    suggestions.append({'type': 'author', 'value': art.author})
                    seen.add(art.author)
    return {"suggestions": suggestions[:15], "keywords": keywords}

@main_bp.route('/latest-articles')
def latest_articles():
    articles = Article.query.order_by(Article.publish_datetime.desc().nullslast()).limit(10).all()
    return render_template('latest_articles.html', title='Bài viết mới nhất', articles=articles)

@main_bp.route('/about')
def about():
    technologies = [
        "Python", "Flask", "SQLAlchemy", "PostgreSQL", "Tailwind CSS", "BeautifulSoup", "Playwright"
    ]
    page_team_info = {
        "lecturer": "TS. Nguyễn Thế Bảo",
        "members": [
             {
            "name": "Lê Văn Hoàng", # Thay tên
            "mssv": "2224802010279", # Thay MSSV
            "avatar": "images/avatars/1_hoang.jpg", # Đường dẫn đến ảnh trong static/images/avatars/
            "role": "Project Lead & Backend Developer", # Vai trò
            "bio": "Đam mê giải quyết các bài toán khó bằng code và dữ liệu.", # Mô tả ngắn
            "google": "2224802010279@student.tdmu.edu.vn", # Link Goole
            "github": "https://github.com/EurusDFIR" # Link GitHub 
        },
        {
            "name": "Lê Nguyễn Hoàng", 
            "mssv": "222480201081", 
            "avatar": "images/avatars/2_nH.png", 
            "role": "Backend Developer", 
            "bio": "Đam mê giải quyết các bài toán khó bằng code và dữ liệu.",
            "google": "2224802010814@student.tdmu.edu.vn", 
            "github": "https://github.com/CooloBi21" 
        },
        {
            "name": "Nguyễn Tuấn Anh", 
            "mssv": "2224802010328", 
            "avatar": "images/avatars/3_tA.png", 
            "role": "Frontend Developer & UI/UX Designer",
            "bio": "Yêu thích việc tạo ra những giao diện đẹp mắt và thân thiện với người dùng.",
            "google": "2224802010328@student.tdmu.edu.vn", 
            "github": "https://github.com/ALZPotato" 
        },
            # Thêm các thành viên khác nếu có
        ]
    }
    project_description = "VnExpress Analyzer là dự án phân tích dữ liệu báo chí hiện đại."
    return render_template(
        'about.html',
        title="Giới Thiệu",
        technologies=technologies,
        page_team_info=page_team_info,
        project_description=project_description
    )


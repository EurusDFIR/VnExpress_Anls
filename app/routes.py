# --- moved Blueprint definition and imports to the top ---
from flask import render_template, request, redirect, url_for, flash, abort, jsonify
from app import db
from app.models import Article, Category
from scraper.vnexpress_scraper import get_true_scrape_targets, get_article_urls_from_category_page, scrape_article_details_and_save, scrape_and_save_comments
from urllib.parse import urlparse
from datetime import datetime
from flask import Blueprint, current_app
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
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

main_bp = Blueprint('main', __name__)

    # --- Scrape Center routes ---
@main_bp.route('/scrape-center')
def scrape_center_page():
    def get_category_tree(session):
        categories_tree = []
        root_categories = session.query(Category).filter_by(parent_id=None, is_active=True).order_by(Category.name).all()
        def build_children(parent_category_db_obj):
            children_data = []
            children_db = session.query(Category).filter_by(parent_id=parent_category_db_obj.id, is_active=True).order_by(Category.name).all()
            for child_db in children_db:
                children_data.append({
                    "id": child_db.id,
                    "name": child_db.name,
                    "url": child_db.url,
                    "children": build_children(child_db)
                })
            return children_data
        for root_cat in root_categories:
            categories_tree.append({
                "id": root_cat.id,
                "name": root_cat.name,
                "url": root_cat.url,
                "children": build_children(root_cat)
            })
        return categories_tree
    category_tree_data = get_category_tree(db.session)
    return render_template('scrape_center.html', title="Scrape Center", categories_tree=category_tree_data)

@main_bp.route('/start-bulk-scrape', methods=['POST'])
def start_bulk_scrape():
    selected_ids = request.form.getlist('selected_categories')
    scrape_comments_flag = request.form.get('scrape_comments') == 'true'
    
    print("\n=== BẮT ĐẦU QUÁ TRÌNH SCRAPE ===")
    print(f"Các category được chọn: {selected_ids}")
    
    if not selected_ids:
        flash('Vui lòng chọn ít nhất một chuyên mục để scrape.', 'warning')
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
            return redirect(url_for('main.scrape_center_page'))
            
    default_cat = db.session.query(Category).filter(Category.name.ilike("Chưa phân loại")).first()
    default_cat_id = default_cat.id if default_cat else None
    
    flash('Bắt đầu quá trình scrape. Việc này có thể mất vài phút...', 'info')
    scrape_targets_list = get_true_scrape_targets(selected_map, db.session, default_article_count_if_not_set=10)
    
    print(f"\nCác mục tiêu scrape thực sự: {scrape_targets_list}")
    total_articles_scraped_session = 0
    total_comments_scraped_session = 0
    
    app = current_app._get_current_object()
    
    # Create a wrapper function to handle app context in threads
    def scrape_with_app_context(url):
        try:
            with app.app_context():
                # Create a new session for this thread
                session = db.session()
                try:
                    result = scrape_article_details_and_save(
                        url, 
                        session,
                        scrape_comments=scrape_comments_flag
                    )
                    # If we have a result, get the article ID before committing
                    article_id = None
                    if result and hasattr(result, 'id'):
                        article_id = result.id
                        session.commit()
                        return article_id  # Return just the ID instead of the Article object
                    return None
                except Exception as e:
                    print(f"Lỗi khi scrape {url}: {e}")
                    if session.is_active:
                        session.rollback()
                    return None
                finally:
                    session.close()
        except Exception as e:
            print(f"Lỗi context khi scrape {url}: {e}")
            return None
    
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
                    article_id = future.result()
                    if article_id:
                        print(f"Đã xử lý xong chi tiết cho URL: {url}")
                        articles_scraped_this_category += 1
                        total_articles_scraped_session += 1

                        if scrape_comments_flag:
                            with app.app_context():
                                session = db.session()
                                try:
                                    # Get fresh Article object from database
                                    article_db_obj = session.get(Article, article_id)
                                    if article_db_obj:
                                        print(f"Bắt đầu scrape bình luận cho bài viết: {article_db_obj.title[:30]}...")
                                        num_new_comments = scrape_and_save_comments(article_db_obj, session, app)
                                        if num_new_comments > 0:
                                            comments_scraped_this_category += num_new_comments
                                            total_comments_scraped_session += num_new_comments
                                            print(f"Đã scrape được {num_new_comments} bình luận mới cho {article_db_obj.title[:30]}")
                                        else:
                                            print(f"Không có bình luận mới hoặc lỗi khi scrape bình luận cho {article_db_obj.title[:30]}")
                                        session.commit()
                                except Exception as e:
                                    print(f"Lỗi khi scrape bình luận cho {url}: {e}")
                                    if session.is_active:
                                        session.rollback()
                                finally:
                                    session.close()
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
    else:
        flash(f'Hoàn tất scrape! Đã scrape được {total_articles_scraped_session} bài viết mới và {total_comments_scraped_session} bình luận (nếu có).', 'success')
    return redirect(url_for('main.index'))


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
        # Join với Category để tìm theo tên chuyên mục
        query = query.join(Article.category, isouter=True).filter(
            (Article.title.ilike(search)) |
            (Category.name.ilike(search)) |
            (Article.author.ilike(search))
        )
    if category_filter and category_filter != "All Categories":
        # Lọc theo tên chuyên mục qua quan hệ category (relationship)
        query = query.join(Article.category).filter(Category.name == category_filter)
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
    # Lấy danh sách chuyên mục từ bảng Category, không join với Article để tránh cartesian product
    categories_query = db.session.query(Category).filter(Category.is_active == True).order_by(Category.name).all()
    categories = ["All Categories"] + [cat.name for cat in categories_query]
    articles_pagination = query.paginate(page=page, per_page=12, error_out=False)
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
    if newly_scraped_article:
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


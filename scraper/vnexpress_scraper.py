from app.models import Category, Article
from sqlalchemy import func
# --- CATEGORY SCRAPE LOGIC ---
def get_true_scrape_targets(selected_map, db_session, default_article_count_if_not_set=10):
    """
    selected_map: dict {category_id: num_articles or None}
    Trả về list (category_name, category_url, num_articles) thực sự cần scrape (không bị lồng nhau)
    """
    # Lấy toàn bộ categories từ DB
    all_categories = db_session.query(Category).all()
    id_to_cat = {c.id: c for c in all_categories}
    # Xây dựng map cha-con
    parent_to_children = {}
    for cat in all_categories:
        if cat.parent_id:
            parent_to_children.setdefault(cat.parent_id, []).append(cat.id)
    # Hàm đệ quy lấy tất cả con cháu của 1 category
    def get_all_descendants(cat_id):
        result = set()
        children = parent_to_children.get(cat_id, [])
        for child_id in children:
            result.add(child_id)
            result.update(get_all_descendants(child_id))
        return result
    # Xác định các category_id thực sự cần scrape
    true_targets = []
    selected_ids = set(selected_map.keys())
    for cat_id in selected_ids:
        descendants = get_all_descendants(cat_id)
        # Nếu không có con cháu nào được chọn riêng, hoặc là nút lá
        if not (descendants & selected_ids):
            num_articles = selected_map[cat_id] or default_article_count_if_not_set
            cat = id_to_cat[cat_id]
            true_targets.append((cat.name, cat.url, num_articles))
    # Loại bỏ trùng lặp url, giữ lại entry có count lớn hơn
    url_to_entry = {}
    for name, url, count in true_targets:
        if url not in url_to_entry or count > url_to_entry[url][2]:
            url_to_entry[url] = (name, url, count)
    return list(url_to_entry.values())

# --- CATEGORY ID MAPPING FOR ARTICLE ---
def get_category_id_from_scraped_info(category_name, category_url, db_session, default_category_id=None):
    """
    Tìm category_id dựa trên tên hoặc url. Nếu không có trả về default_category_id.
    So khớp tên chuyên mục không phân biệt hoa thường và loại bỏ khoảng trắng thừa.
    """
    if category_name:
        category_name = category_name.strip().lower()
    cat = db_session.query(Category).filter(
        (Category.url == category_url) |
        (func.lower(func.trim(Category.name)) == category_name)
    ).first()
    if cat:
        return cat.id
    return default_category_id
# scraper/vnexpress_scraper.py

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from app import db, create_app
from app.models import Article, Comment

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

@contextmanager
def app_context_session(flask_app):
    """Context manager that provides both app context and database session."""
    with flask_app.app_context():
        session = db.session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

def parse_datetime_from_str(date_str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        try:
            parts = date_str.split(',')
            if len(parts) >= 3:
                date_time_part = parts[1].strip() + "," + parts[2].split('(')[0].strip()
                return datetime.strptime(date_time_part, '%d/%m/%Y, %H:%M')
            return None
        except ValueError:
            print(f"Không thể parse chuỗi ngày: {date_str}")
            return None

def scrape_article_details_and_save(article_url, db_session, scrape_comments=False, max_comments=100):
    try:
        existing_article = db_session.query(Article).filter_by(url=article_url).first()
        if existing_article:
            now = datetime.utcnow()
            if not existing_article.last_scraped_at or (now - existing_article.last_scraped_at).total_seconds() > 3600:
                existing_article.last_scraped_at = now
                db_session.flush()
            print(f"Bài viết đã tồn tại trong DB: {article_url}")
            return existing_article

        print(f"Đang scrape: {article_url}")
        response = requests.get(article_url, headers=HEADERS, timeout=7)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title_tag = soup.find('h1', class_='title-detail')
        title = title_tag.get_text(strip=True) if title_tag else "N/A"
        sapo_tag = soup.find('p', class_='description')
        sapo = sapo_tag.get_text(strip=True) if sapo_tag else None
        content_container = soup.find('article', class_='fck_detail')
        content = ""
        if content_container:
            paragraphs = content_container.find_all('p', class_=lambda x: x != 'description' if x else True)
            content_parts = []
            for p_tag in paragraphs:
                for unwanted in p_tag.find_all(['figure', 'table', 'div', 'em', 'button', 'picture']):
                    unwanted.decompose()
                text = p_tag.get_text(separator='\n', strip=True)
                if text:
                    content_parts.append(text)
            while content_parts:
                last = content_parts[-1].strip()
                if (len(last) < 50 and not any(char.isdigit() for char in last) and not any(x in last for x in [":", "(", ")", ".com", "http"])):
                    content_parts.pop()
                    continue
                if last.lower().startswith('(theo') or last.lower().startswith('theo '):
                    content_parts.pop()
                    continue
                if last.strip() in {"", ".", "-", "–"}:
                    content_parts.pop()
                    continue
                break
            content = "\n\n".join(content_parts)

        date_str = None
        date_meta_tag = soup.find('meta', itemprop='datePublished')
        if date_meta_tag and 'content' in date_meta_tag.attrs:
            date_str = date_meta_tag['content']
        else:
            date_span_tag = soup.find('span', class_='date')
            if date_span_tag: date_str = date_span_tag.get_text(strip=True)
        publish_datetime_obj = parse_datetime_from_str(date_str)

        author = "Không rõ"
        author_elements = soup.select('p.author_mail strong, p[style*="text-align:right"] strong, article.fck_detail > p:last-child strong')
        if author_elements:
            author = author_elements[0].get_text(strip=True)
        elif content_container:
            last_p = content_container.find_all('p', recursive=False)
            if last_p and len(last_p[-1].get_text(strip=True)) < 50 and not last_p[-1].find('a'):
                potential_author = last_p[-1].get_text(strip=True)
                if potential_author and not any(char.isdigit() for char in potential_author):
                    author = potential_author

        category = "N/A"
        breadcrumb = soup.find('ul', class_='breadcrumb')
        if breadcrumb:
            categories = [li.get_text(strip=True) for li in breadcrumb.find_all('li') if li.find('a')]
            if categories and len(categories) > 1:
                category = categories[-1]
            elif categories:
                category = categories[0]
        image_url = None
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image['content']

        # Lấy category_id từ tên category
        category_id = get_category_id_from_scraped_info(category, article_url, db_session)

        new_article = Article(
            url=article_url,
            title=title,
            sapo=sapo,
            content=content,
            author=author,
            published_date_str=date_str,
            publish_datetime=publish_datetime_obj,
            category_id=category_id,
            last_scraped_at=datetime.utcnow(),
            image_url=image_url
        )
        
        db_session.add(new_article)
        db_session.flush()  # Get the ID assigned
        
        if scrape_comments:
            try:
                num_comments = scrape_and_save_comments(new_article, db_session)
                if num_comments <= 0:
                    print(f"Không tìm thấy bình luận cho bài viết: {article_url}")
            except Exception as e:
                print(f"Lỗi khi scrape comments: {e}")
                # Don't return None here as we still want to save the article
        
        # Make sure the article is loaded in the current session
        db_session.flush()
        
        # Refresh to get the updated comment count
        db_session.refresh(new_article)
        
        print(f"Đã scrape bài viết: {title[:50]}...")
        return new_article

    except requests.exceptions.RequestException as e:
        print(f"Lỗi Request khi scrape {article_url}: {e}")
        return None
    except Exception as ex:
        print(f"Lỗi không xác định khi scrape và lưu {article_url}: {ex}")
        return None

def get_article_urls_from_category_page(category_url, max_articles=10, db_session=None):
    urls = set()
    print(f"Đang lấy URL từ chuyên mục: {category_url}")
    try:
        response = requests.get(category_url, headers=HEADERS, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        article_selectors = [
            'article.item-news h3.title-news a',
            'article.item-news h2.title_news a',
            'article.item_list_cate h3.title_news a',
            'h1.title-news a, h2.title-news a, h3.title-news a, h4.title-news a',
            'div.item_major article.item-news h3.title-news a'
        ]
        found_links = set()
        for selector in article_selectors:
            link_tags = soup.select(selector)
            for link_tag in link_tags:
                if 'href' in link_tag.attrs:
                    article_url = link_tag['href']
                    if article_url.startswith('/'):
                        article_url = "https://vnexpress.net" + article_url
                    if article_url.startswith('https://vnexpress.net/') and article_url.endswith('.html'):
                        # Kiểm tra xem bài viết đã tồn tại trong DB chưa
                        if db_session:
                            existing_article = db_session.query(Article).filter_by(url=article_url).first()
                            if not existing_article:
                                found_links.add(article_url)
                        else:
                            found_links.add(article_url)
                if len(found_links) >= max_articles:
                    break
            if len(found_links) >= max_articles:
                break
        urls.update(list(found_links)[:max_articles])
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi lấy URL từ chuyên mục {category_url}: {e}")
    print(f"Tìm thấy {len(urls)} URL bài viết mới.")
    return list(urls)

try:
    from .playwright_comment_fetcher import fetch_comments_html_sync
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def fetch_comments_html(article_url, max_load_more_clicks=10, max_reply_clicks_per_comment=3, debug_save=False):
    return fetch_comments_html_sync(article_url, max_load_more_clicks, max_reply_clicks_per_comment, debug_save)

def parse_comments_from_html(comment_section_html, article_db_id, db_session):
    if not comment_section_html:
        return 0
    soup = BeautifulSoup(comment_section_html, 'html.parser')
    list_comment_items_data = []
    parsed_comment_api_ids = set()  # Thêm set để tránh lặp vô hạn
    def process_comment_element(comment_element_soup, parent_api_id_on_site=None):
        raw_data = {}
        try:
            # Lấy ID comment từ <a class="link_reply"> hoặc <a class="link_thich">
            link_reply = comment_element_soup.find('a', class_='link_reply')
            comment_api_id = None
            if link_reply and link_reply.has_attr('rel'):
                rel_val = link_reply['rel']
                comment_api_id = rel_val[0] if isinstance(rel_val, list) else rel_val
            if not comment_api_id:
                like_link = comment_element_soup.find('a', class_='link_thich')
                if like_link and like_link.has_attr('rel'):
                    rel_val = like_link['rel']
                    comment_api_id = rel_val[0] if isinstance(rel_val, list) else rel_val
            # Nếu đã parse comment này thì bỏ qua
            if comment_api_id and comment_api_id in parsed_comment_api_ids:
                return
            if comment_api_id:
                parsed_comment_api_ids.add(comment_api_id)
            # Gán parent_api_id_on_site truyền vào
            raw_data['comment_api_id'] = comment_api_id
            raw_data['parent_api_id_on_site'] = parent_api_id_on_site
            # Tên người dùng
            raw_data['user_name'] = comment_element_soup.select_one('a.nickname').get_text(strip=True) if comment_element_soup.select_one('a.nickname') else "Ẩn danh"
            # Nội dung
            full_content_tag = comment_element_soup.select_one('p.full_content')
            if full_content_tag:
                name_span = full_content_tag.find('span', class_='txt-name')
                if name_span: name_span.decompose()
                raw_data['comment_text'] = full_content_tag.get_text(strip=True)
            else:
                raw_data['comment_text'] = ""
            # Số lượt thích
            likes_tag = comment_element_soup.select_one('div.reactions-total a.number')
            if not likes_tag:
                likes_tag = comment_element_soup.select_one('span.total_like')
            likes_text = likes_tag.get_text(strip=True) if likes_tag else ''
            try:
                raw_data['likes_count'] = int(likes_text)
            except (ValueError, TypeError):
                raw_data['likes_count'] = 0
            # Thời gian
            time_tag = comment_element_soup.select_one('span.time-com')
            raw_data['comment_date_str'] = time_tag.get_text(strip=True) if time_tag else None
            list_comment_items_data.append(raw_data)

            # Đệ quy: tìm tất cả comment con trong mọi cấp .sub_comment
            sub_comment_divs = comment_element_soup.find_all('div', class_='sub_comment', recursive=False)
            for sub_div in sub_comment_divs:
                reply_elements = sub_div.find_all(['div'], class_=['comment_item', 'sub_comment_item'], recursive=False)
                for reply_el in reply_elements:
                    process_comment_element(reply_el, parent_api_id_on_site=comment_api_id)
            # Ngoài ra, parse các comment/reply cùng cấp tiếp theo
            next_sibling = comment_element_soup.find_next_sibling()
            while next_sibling:
                if (
                    next_sibling.name == 'div' and
                    ('sub_comment_item' in next_sibling.get('class', []) or 'comment_item' in next_sibling.get('class', []))
                ):
                    process_comment_element(next_sibling, parent_api_id_on_site=parent_api_id_on_site)
                    next_sibling = next_sibling.find_next_sibling()
                else:
                    break
        except Exception as e:
            print(f"Lỗi khi parse một comment element: {e}")
    
    # Parse các comment cha
    top_level_comment_elements = soup.select('#list_comment > div.comment_item')
    for el in top_level_comment_elements:
        process_comment_element(el, parent_api_id_on_site=None)
    
    saved_count = 0
    api_id_to_db_id_map = {}
    new_comments = []
    
    # Process existing comments first
    existing_comments = db_session.query(Comment).filter_by(article_id=article_db_id).all()
    for comment in existing_comments:
        if comment.comment_api_id:
            api_id_to_db_id_map[comment.comment_api_id] = comment.id
    
    # Process new comments
    for raw_data in list_comment_items_data:
        if not raw_data.get('comment_api_id'):
            continue
            
        comment_api_id = raw_data.get('comment_api_id')
        # Skip if already exists
        if comment_api_id in api_id_to_db_id_map:
            continue
            
        comment_dt = parse_datetime_from_str(raw_data['comment_date_str'])
        new_comment = Comment(
            article_id=article_db_id,
            comment_api_id=comment_api_id,
            user_name=raw_data['user_name'],
            comment_text=raw_data['comment_text'],
            comment_date_str=raw_data['comment_date_str'],
            comment_datetime=comment_dt,
            likes_count=raw_data['likes_count']
        )
        new_comments.append(new_comment)
        saved_count += 1
    
    # Add all comments to session and flush to get IDs
    if new_comments:
        for comment in new_comments:
            db_session.add(comment)
        db_session.flush()
        
        # Update the map with the new comment IDs
        for comment in new_comments:
            if comment.comment_api_id:
                api_id_to_db_id_map[comment.comment_api_id] = comment.id
    
    # Process parent-child relationships
    for raw_data in list_comment_items_data:
        current_api_id = raw_data.get('comment_api_id')
        parent_api_id = raw_data.get('parent_api_id_on_site')
        
        if current_api_id and parent_api_id and current_api_id in api_id_to_db_id_map and parent_api_id in api_id_to_db_id_map:
            current_comment_id = api_id_to_db_id_map[current_api_id]
            parent_comment_id = api_id_to_db_id_map[parent_api_id]
            
            # Get the comment object and update its parent
            comment = db_session.get(Comment, current_comment_id)
            if comment and comment.parent_comment_id != parent_comment_id:
                comment.parent_comment_id = parent_comment_id
    
    # Return the count of new comments saved
    return saved_count

def scrape_and_save_comments(article_db_object, db_session):
    if not article_db_object or not article_db_object.url:
        print("Đối tượng bài viết không hợp lệ cho scrape comments.")
        return 0
        
    comment_html_content = fetch_comments_html(
        article_db_object.url,
        max_load_more_clicks=20,
        max_reply_clicks_per_comment=5,
        debug_save=False
    )
    
    if not comment_html_content:
        print(f"Không lấy được HTML bình luận cho {article_db_object.url}")
        return 0

    soup = BeautifulSoup(comment_html_content, 'html.parser')
    comment_elements = soup.select('#list_comment > div.comment_item')
    if not comment_elements:
        return 0

    # Get existing comment IDs to avoid duplicates
    existing_comments = db_session.query(Comment.comment_api_id).filter_by(article_id=article_db_object.id).all()
    existing_api_ids = set(ec[0] for ec in existing_comments if ec[0])

    new_comments = []
    api_id_to_comment = {}
    
    def process_comment_element(el, parent_api_id=None):
        try:
            link_reply = el.find('a', class_='link_reply')
            comment_api_id = None
            if link_reply and link_reply.has_attr('rel'):
                rel_val = link_reply['rel']
                comment_api_id = rel_val[0] if isinstance(rel_val, list) else rel_val
            if not comment_api_id or comment_api_id in existing_api_ids:
                return
            user_name = el.select_one('a.nickname')
            user_name = user_name.get_text(strip=True) if user_name else "Ẩn danh"
            full_content_tag = el.select_one('p.full_content')
            if full_content_tag:
                name_span = full_content_tag.find('span', class_='txt-name')
                if name_span: name_span.decompose()
                comment_text = full_content_tag.get_text(strip=True)
            else:
                comment_text = ""
            likes_tag = el.select_one('div.reactions-total a.number') or el.select_one('span.total_like')
            try:
                likes_count = int(likes_tag.get_text(strip=True)) if likes_tag else 0
            except Exception:
                likes_count = 0
            time_tag = el.select_one('span.time-com')
            comment_date_str = time_tag.get_text(strip=True) if time_tag else None
            comment_dt = parse_datetime_from_str(comment_date_str)
            
            new_comment = Comment(
                article_id=article_db_object.id,
                comment_api_id=comment_api_id,
                user_name=user_name,
                comment_text=comment_text,
                comment_date_str=comment_date_str,
                comment_datetime=comment_dt,
                likes_count=likes_count,
                parent_comment_id=None  # sẽ cập nhật sau nếu cần
            )
            
            db_session.add(new_comment)
            new_comments.append(new_comment)
            api_id_to_comment[comment_api_id] = new_comment
            existing_api_ids.add(comment_api_id)
            
            # Xử lý reply (nếu có)
            sub_comment_divs = el.find_all('div', class_='sub_comment', recursive=False)
            for sub_div in sub_comment_divs:
                reply_elements = sub_div.find_all(['div'], class_=['comment_item', 'sub_comment_item'], recursive=False)
                for reply_el in reply_elements:
                    process_comment_element(reply_el, parent_api_id=comment_api_id)
        except Exception as e:
            print(f"Lỗi khi xử lý comment: {e}")

    # Process all comments
    for el in comment_elements:
        process_comment_element(el)

    # Flush to get IDs for all new comments
    if new_comments:
        db_session.flush()
        
        # Set parent relationships
        for comment_api_id, comment in api_id_to_comment.items():
            parent_links = soup.select(f'a.link_reply[rel="{comment_api_id}"]')
            for link in parent_links:
                parent_comment_div = link.find_parent('div', class_=['comment_item', 'sub_comment_item'])
                if parent_comment_div:
                    parent_link = parent_comment_div.find('a', class_='link_reply')
                    if parent_link and parent_link.has_attr('rel'):
                        parent_api_id = parent_link['rel']
                        parent_api_id = parent_api_id[0] if isinstance(parent_api_id, list) else parent_api_id
                        if parent_api_id in api_id_to_comment:
                            comment.parent_comment_id = api_id_to_comment[parent_api_id].id
        
        # Update the total comment count on the article
        db_session.flush()
        
        # Update the article's comment count
        article_db_object.total_comment_count = db_session.query(Comment).filter_by(article_id=article_db_object.id).count()
        
        print(f"Đã xử lý {len(new_comments)} bình luận mới.")
        return len(new_comments)
    
    return 0



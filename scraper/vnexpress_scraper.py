# scraper/vnexpress_scraper.py

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
# Import các model từ app của bạn và đối tượng db
# Để làm điều này, scraper cần biết về cấu trúc app
# Cách tốt là truyền session của db vào hoặc scraper sẽ chạy trong context của app Flask
# Tuy nhiên, để đơn giản ban đầu, chúng ta có thể import trực tiếp nếu cấu trúc sys.path cho phép
# Hoặc bạn sẽ tạo một script riêng để chạy scraper có thiết lập context Flask.

# Giả sử bạn sẽ chạy scraper thông qua một script có context Flask
# from app import db # Sẽ không hoạt động trực tiếp nếu chạy file này độc lập
# from app.models import Article # Tương tự

# --- CÁCH TIẾP CẬN BAN ĐẦU ĐỂ CHẠY ĐỘC LẬP (Cần điều chỉnh sys.path) ---
import sys
import os
# Thêm thư mục gốc của dự án vào sys.path để có thể import app
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# Bây giờ bạn có thể import
from app import db, create_app # Import create_app để tạo context
from app.models import Article, Comment

# --- Hoặc bạn sẽ tạo một script riêng để chạy scraper (ví dụ: run_scraper.py) ---
# (Xem phần "Chạy Scraper" ở dưới)


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def parse_datetime_from_str(date_str):
    """
    Chuyển đổi chuỗi ngày tháng từ VnExpress (hoặc meta tag) sang đối tượng datetime.
    Ví dụ: "Thứ sáu, 24/3/2023, 10:30 (GMT+7)" hoặc "2023-03-24T10:30:00+07:00"
    """
    if not date_str:
        return None
    try:
        # Thử định dạng ISO 8601 từ meta tag
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        try:
            # Thử định dạng "Thứ sáu, 24/3/2023, 10:30 (GMT+7)"
            # Loại bỏ phần (GMT+7) và ngày trong tuần
            parts = date_str.split(',')
            if len(parts) >= 3:
                date_time_part = parts[1].strip() + "," + parts[2].split('(')[0].strip()
                return datetime.strptime(date_time_part, '%d/%m/%Y, %H:%M')
            return None # Hoặc thử các định dạng khác nếu cần
        except ValueError:
            print(f"Không thể parse chuỗi ngày: {date_str}")
            return None

def scrape_article_details_and_save(article_url, db_session, scrape_comments=False, max_comments=100):
    """
    Scrape chi tiết một bài viết và lưu vào database.
    Nếu scrape_comments=True thì scrape cả bình luận (tối đa max_comments).
    db_session là session của SQLAlchemy.
    """
    try:
        # 1. Kiểm tra xem bài viết đã tồn tại trong DB chưa
        existing_article = db_session.query(Article).filter_by(url=article_url).first()
        if existing_article:
            print(f"Bài viết đã tồn tại trong DB: {article_url}")
            # Bạn có thể cập nhật `last_scraped_at` hoặc các thông tin khác nếu muốn
            existing_article.last_scraped_at = datetime.utcnow()
            db_session.commit()
            return existing_article # Trả về đối tượng đã có

        print(f"Đang scrape: {article_url}")
        response = requests.get(article_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- Trích xuất thông tin (tương tự như hướng dẫn trước) ---
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
            # Loại bỏ các đoạn <p> cuối không mong muốn (tác giả, nguồn, chú thích, rỗng)
            while content_parts:
                last = content_parts[-1].strip()
                # Nếu là tên tác giả (ngắn, không số, không nhiều ký tự đặc biệt)
                if (len(last) < 50 and not any(char.isdigit() for char in last) and not any(x in last for x in [":", "(", ")", ".com", "http"])):
                    content_parts.pop()
                    continue
                # Nếu là chú thích nguồn (theo ...)
                if last.lower().startswith('(theo') or last.lower().startswith('theo '):
                    content_parts.pop()
                    continue
                # Nếu là <p> rỗng hoặc chỉ chứa dấu chấm, xuống dòng
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

        author = "Không rõ" # Default
    
        author_elements = soup.select('p.author_mail strong, p[style*="text-align:right"] strong, article.fck_detail > p:last-child strong')
        if author_elements: # Lấy tác giả đầu tiên tìm thấy
            author = author_elements[0].get_text(strip=True)
        # Đôi khi tác giả nằm ở cuối cùng và không có thẻ strong
        elif content_container:
            last_p = content_container.find_all('p', recursive=False)
            if last_p and len(last_p[-1].get_text(strip=True)) < 50 and not last_p[-1].find('a'): # Giả định tên tác giả ngắn
                potential_author = last_p[-1].get_text(strip=True)
                if potential_author and not any(char.isdigit() for char in potential_author): # Không chứa số
                    author = potential_author


        category = "N/A"
        breadcrumb = soup.find('ul', class_='breadcrumb')
        if breadcrumb:
            categories = [li.get_text(strip=True) for li in breadcrumb.find_all('li') if li.find('a')]
            if categories and len(categories) > 1: # Bỏ "Trang chủ"
                category = categories[-1]
            elif categories:
                category = categories[0]
        
        image_url = None
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image['content']


        # --- Tạo đối tượng Article và lưu vào DB ---
        new_article = Article(
            url=article_url,
            title=title,
            sapo=sapo,
            content=content,
            author=author,
            published_date_str=date_str, # Lưu chuỗi gốc
            publish_datetime=publish_datetime_obj, # Lưu đối tượng datetime
            category=category,
            last_scraped_at=datetime.utcnow(),
            image_url = image_url
            # total_comments_count sẽ cập nhật sau nếu scrape bình luận
        )

        db_session.add(new_article)
        db_session.commit()
        print(f"Đã lưu bài viết: {title[:50]}...")
        # Nếu người dùng chọn scrape bình luận thì mới scrape
        if scrape_comments:
            # Gọi hàm scrape_and_save_comments với số lượng bình luận tối đa
            num_comments = scrape_and_save_comments(new_article, db_session, max_comments=max_comments)
            print(f"Đã scrape {num_comments} bình luận cho bài viết.")
        return new_article

    except requests.exceptions.RequestException as e:
        print(f"Lỗi Request khi scrape {article_url}: {e}")
        db_session.rollback() 
        return None
    except Exception as ex:
        print(f"Lỗi không xác định khi scrape và lưu {article_url}: {ex}")
        db_session.rollback()
        return None

def get_article_urls_from_category_page(category_url, max_articles=10):
    """Lấy danh sách URL bài viết từ một trang chuyên mục."""
    urls = set()
    print(f"Đang lấy URL từ chuyên mục: {category_url}")
    try:
        response = requests.get(category_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Selector này cần được kiểm tra và cập nhật thường xuyên cho VnExpress
        # Thử nhiều selector để bao quát các layout khác nhau trên trang chuyên mục
        article_selectors = [
            'article.item-news h3.title-news a',
            'article.item-news h2.title_news a', # Một số layout dùng h2
            'article.item_list_cate h3.title_news a', # Layout khác
            'h1.title-news a, h2.title-news a, h3.title-news a, h4.title-news a', # Selector chung hơn
            'div.item_major article.item-news h3.title-news a' # Cho các bài nổi bật
        ]

        found_links = set()
        for selector in article_selectors:
            link_tags = soup.select(selector)
            for link_tag in link_tags:
                if 'href' in link_tag.attrs:
                    article_url = link_tag['href']
                    if article_url.startswith('/'):
                        article_url = "https://vnexpress.net" + article_url
                    # Kiểm tra kỹ URL có đúng là của VnExpress và là bài viết không
                    if article_url.startswith('https://vnexpress.net/') and article_url.endswith('.html'):
                        found_links.add(article_url)
                if len(found_links) >= max_articles:
                    break
            if len(found_links) >= max_articles:
                break
        
        urls.update(list(found_links)[:max_articles]) # Giới hạn số lượng article

    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi lấy URL từ chuyên mục {category_url}: {e}")
    
    print(f"Tìm thấy {len(urls)} URL bài viết.")
    return list(urls)

# Hàm scrape bình luận (nếu bạn muốn thử - sẽ rất phức tạp)
# scraper/vnexpress_scraper.py
# ... (các import requests, BeautifulSoup, time, datetime, models, db đã có) ...

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

# ... (HEADERS, parse_datetime_from_str, scrape_article_details_and_save, get_article_urls_from_category_page đã có) ...


def click_element_if_exists(driver, by, value, timeout=5):
    """Hàm tiện ích để click một element nếu nó tồn tại và có thể click."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        # Thử cuộn element vào view trước khi click để tránh bị che khuất
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.5) # Chờ một chút sau khi cuộn
        element.click()
        print(f"Clicked element: {value}")
        return True
    except TimeoutException:
        # print(f"Timeout: Element {value} not clickable or not found within {timeout}s.")
        return False
    except ElementClickInterceptedException:
        print(f"ElementClickInterceptedException: Element {value} was obscured. Trying JS click.")
        try:
            # Thử click bằng JavaScript nếu click thông thường bị chặn
            driver.execute_script("arguments[0].click();", element)
            print(f"Clicked element (JS): {value}")
            return True
        except Exception as e_js:
            print(f"JS click failed for {value}: {e_js}")
            return False
    except Exception as e:
        print(f"Error clicking element {value}: {e}")
        return False

try:
    from .playwright_comment_fetcher import fetch_comments_html_sync
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def fetch_comments_html(article_url, max_load_more_clicks=10, max_reply_clicks_per_comment=3, debug_save=False, max_comments=100):
    if PLAYWRIGHT_AVAILABLE:
        return fetch_comments_html_sync(article_url, max_load_more_clicks, max_reply_clicks_per_comment, debug_save, max_comments)
    else:
        return fetch_raw_comments_html_with_selenium(article_url, max_load_more_clicks, max_reply_clicks_per_comment)

def fetch_raw_comments_html_with_selenium(article_url, max_load_more_clicks=5, max_reply_clicks_per_comment=2):
    # Deprecated: giữ lại để fallback nếu Playwright không có
    print(f"Selenium: Bắt đầu tải bình luận cho {article_url}")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage") # Quan trọng khi chạy trong container/server
    chrome_options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    # chrome_options.add_argument("window-size=1920,1080") # Kích thước cửa sổ có thể ảnh hưởng

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    comment_section_html = None

    try:
        driver.get(article_url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "box_comment_vne")) # Chờ khối comment chính xuất hiện
        )
        print("Selenium: Trang đã tải, khối comment chính đã xuất hiện.")

        # 1. Click "Xem thêm ý kiến" để tải các bình luận gốc
        for i in range(max_load_more_clicks):
            print(f"Selenium: Click 'Xem thêm ý kiến' lần {i+1}/{max_load_more_clicks}")
            # Sử dụng đúng selector ID cho nút "Xem thêm ý kiến"
            clicked_load_more = click_element_if_exists(driver, By.ID, "show_more_coment")
            if clicked_load_more:
                time.sleep(3) # Chờ bình luận tải thêm
            else:
                print("Selenium: Không tìm thấy hoặc không click được nút 'Xem thêm ý kiến'.")
                break
        print("Selenium: Đã click xong 'Xem thêm ý kiến' (hoặc đạt giới hạn).")

        # 2. (Nâng cao) Click "X trả lời" cho các bình luận đã tải
        # Cần cẩn thận để không click lặp lại vô hạn nếu cấu trúc phức tạp
        # Lấy các bình luận gốc đã hiển thị
        # Selector này phải chỉ đến nút "X trả lời" của các bình luận gốc
        # Ví dụ: a.view_all_reply trong mỗi div.comment_item mà không phải là reply
        
        # Lấy tất cả các nút "Xem trả lời" hiện có
        # Chúng ta sẽ chỉ click một số lượt nhất định để test
        # nếu việc tải reply lại sinh ra thêm nút "Xem trả lời" cho các reply cấp sâu hơn.
        
        # Lấy các comment gốc
        root_comment_elements = driver.find_elements(By.CSS_SELECTOR, "#list_comment > div.comment_item")
        print(f"Selenium: Tìm thấy {len(root_comment_elements)} bình luận gốc (ước lượng).")

        for comment_idx, root_comment_element in enumerate(root_comment_elements):
            # Chỉ click "Xem trả lời" cho một số bình luận đầu tiên để test
            # if comment_idx >= 3: # Giới hạn số bình luận gốc được mở reply để tránh quá lâu
            #     print(f"Selenium: Bỏ qua mở reply cho các bình luận gốc còn lại (đã đạt giới hạn test).")
            #     break

            print(f"Selenium: Đang xử lý reply cho bình luận gốc thứ {comment_idx + 1}")
            try:
                # Tìm nút "X trả lời" bên trong bình luận gốc hiện tại
                # Dùng `root_comment_element.find_elements` thay vì `driver.find_elements`
                # để giới hạn phạm vi tìm kiếm.
                view_reply_links = root_comment_element.find_elements(By.CSS_SELECTOR, "p.count-reply a.view_all_reply")
                if view_reply_links:
                    print(f"Selenium: Tìm thấy {len(view_reply_links)} nút 'Xem trả lời' cho bình luận gốc này.")
                    for reply_click_count in range(max_reply_clicks_per_comment):
                        # Chỉ click vào nút "Xem trả lời" đầu tiên tìm thấy trong mỗi bình luận gốc
                        # Vì sau khi click, DOM có thể thay đổi và các element khác không còn hợp lệ
                        # Cần chiến lược tốt hơn nếu muốn tải nhiều cấp reply
                        if view_reply_links and view_reply_links[0].is_displayed() and view_reply_links[0].is_enabled():
                            print(f"Selenium: Click 'Xem trả lời' lần {reply_click_count + 1} cho bình luận gốc {comment_idx + 1}")
                            # Click và chờ
                            # Cần đảm bảo element này vẫn còn hợp lệ sau các lần click trước
                            try:
                                current_reply_link = root_comment_element.find_element(By.CSS_SELECTOR, "p.count-reply a.view_all_reply")
                                if current_reply_link.is_displayed() and current_reply_link.is_enabled():
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", current_reply_link)
                                    time.sleep(0.5)
                                    current_reply_link.click()
                                    time.sleep(2.5) # Chờ reply tải
                                else: # Nút không còn hiển thị/enabled nữa
                                    break
                            except NoSuchElementException:
                                print(f"Selenium: Nút 'Xem trả lời' không còn tồn tại sau khi click.")
                                break # Thoát vòng lặp click reply của comment này
                            except Exception as e_reply_click:
                                print(f"Selenium: Lỗi khi click 'Xem trả lời': {e_reply_click}")
                                break # Thoát vòng lặp click reply của comment này
                        else:
                            print(f"Selenium: Nút 'Xem trả lời' không còn hiển thị hoặc không thể click.")
                            break # Thoát vòng lặp click reply của comment này
                else:
                    print(f"Selenium: Không tìm thấy nút 'Xem trả lời' cho bình luận gốc này.")
            except Exception as e_outer_reply:
                print(f"Selenium: Lỗi khi xử lý reply cho bình luận gốc {comment_idx + 1}: {e_outer_reply}")
        
        print("Selenium: Đã click xong các nút 'Xem trả lời' (hoặc đạt giới hạn).")

        # 3. Lấy HTML của phần bình luận
        # Bạn cần tìm selector của thẻ cha bao quanh tất cả bình luận
        # Dựa vào HTML bạn cung cấp, `#box_comment` có vẻ là một lựa chọn tốt
        comment_container_element = driver.find_element(By.ID, "box_comment")
        comment_section_html = comment_container_element.get_attribute('outerHTML')
        print("Selenium: Đã lấy HTML của khối bình luận.")

    except TimeoutException:
        print(f"Selenium: Timeout khi chờ element trên trang {article_url}")
    except Exception as e:
        print(f"Selenium: Lỗi không xác định trong quá trình tải bình luận cho {article_url}: {e}")
    finally:
        driver.quit()
        print("Selenium: Đã đóng trình duyệt.")
    
    return comment_section_html


def parse_comments_from_html(comment_section_html, article_db_id, db_session):
    """
    Parse HTML của khối bình luận và lưu vào DB.
    Trả về số lượng bình luận mới được thêm.
    """
    if not comment_section_html:
        return 0

    soup = BeautifulSoup(comment_section_html, 'html.parser')
    # `list_comment_items` sẽ chứa các đối tượng bình luận đã parse để xử lý parent_id
    list_comment_items_data = [] # list các dict chứa dữ liệu thô và db_id (sau khi flush)

    # Hàm đệ quy để parse bình luận và các reply lồng nhau
    def process_comment_element(comment_element_soup, current_parent_api_id_on_site=None):
        # Trích xuất dữ liệu của bình luận hiện tại (tương tự `extract_single_comment_data` trước đó)
        # Nhưng ở đây chúng ta sẽ trả về dict dữ liệu thô để xử lý lưu trữ sau
        raw_data = {}
        try:
            # Comment API ID
            like_link = comment_element_soup.find('a', class_='link_thich')
            raw_data['comment_api_id'] = None
            if like_link and 'rel' in like_link.attrs:
                rel_val = like_link['rel']
                if isinstance(rel_val, list):
                    raw_data['comment_api_id'] = rel_val[0]
                else:
                    raw_data['comment_api_id'] = rel_val
            if not raw_data['comment_api_id']:
                reply_link_for_id = comment_element_soup.find('a', class_='link_reply')
                if reply_link_for_id and 'rel' in reply_link_for_id.attrs:
                    rel_val = reply_link_for_id['rel']
                    if isinstance(rel_val, list):
                        raw_data['comment_api_id'] = rel_val[0]
                    else:
                        raw_data['comment_api_id'] = rel_val

            if not raw_data['comment_api_id']: # Nếu không có ID thì bỏ qua
                return

            raw_data['user_name'] = comment_element_soup.select_one('a.nickname').get_text(strip=True) if comment_element_soup.select_one('a.nickname') else "Ẩn danh"
            
            full_content_tag = comment_element_soup.select_one('p.full_content')
            if full_content_tag:
                name_span = full_content_tag.find('span', class_='txt-name')
                if name_span: name_span.decompose()
                raw_data['comment_text'] = full_content_tag.get_text(strip=True)
            else:
                raw_data['comment_text'] = ""

            likes_tag = comment_element_soup.select_one('div.reactions-total a.number')
            likes_text = likes_tag.get_text(strip=True) if likes_tag else ''
            try:
                raw_data['likes_count'] = int(likes_text)
            except (ValueError, TypeError):
                raw_data['likes_count'] = 0
            
            time_tag = comment_element_soup.select_one('span.time-com')
            raw_data['comment_date_str'] = time_tag.get_text(strip=True) if time_tag else None
            
            raw_data['parent_api_id_on_site'] = current_parent_api_id_on_site # ID của comment cha trên site

            list_comment_items_data.append(raw_data) # Thêm vào danh sách chung

            # Tìm các reply trực tiếp của bình luận này
            # sub_comment_div là thẻ div.sub_comment ngay sau div.content-comment của bình luận hiện tại
            # Tuy nhiên, dựa trên HTML bạn gửi, reply nằm trong div.sub_comment là sibling của comment_item cha
            
            # 1. Cách cũ: tìm div.sub_comment ngay sau comment_item hiện tại
            sub_comment_div = comment_element_soup.find_next_sibling('div', class_='sub_comment')
            if sub_comment_div:
                reply_elements = sub_comment_div.find_all('div', class_='comment_item', recursive=False) # Chỉ lấy reply trực tiếp
                for reply_el in reply_elements:
                    process_comment_element(reply_el, current_parent_api_id_on_site=raw_data['comment_api_id'])

            # 2. Cách mới: tìm các div.sub_comment_item.comment_item.width_common là sibling ngay sau comment_item hiện tại
            next_sibling = comment_element_soup.find_next_sibling()
            while next_sibling:
                if (
                    next_sibling.name == 'div' and
                    'sub_comment_item' in next_sibling.get('class', []) and
                    'comment_item' in next_sibling.get('class', [])
                ):
                    process_comment_element(next_sibling, current_parent_api_id_on_site=raw_data['comment_api_id'])
                    next_sibling = next_sibling.find_next_sibling()
                else:
                    break
        except Exception as e:
            print(f"Lỗi khi parse một comment element: {e}")


    # Bắt đầu parse từ các bình luận gốc trong #list_comment
    # Selector cho từng comment_item gốc
    top_level_comment_elements = soup.select('#list_comment > div.comment_item')
    for el in top_level_comment_elements:
        process_comment_element(el) # Gọi hàm đệ quy

    # Bây giờ `list_comment_items_data` chứa tất cả bình luận đã parse (gốc và reply)
    # Bước tiếp theo là lưu vào DB và xử lý parent_id
    saved_count = 0
    api_id_to_db_id_map = {} # Để map comment_api_id với comment.id trong DB

    # Lượt 1: Lưu tất cả bình luận vào DB để lấy DB ID
    for raw_data in list_comment_items_data:
        if not raw_data.get('comment_api_id'): continue # Bỏ qua nếu không có API ID

        # Kiểm tra xem comment_api_id đã tồn tại trong DB chưa
        existing_comment = db_session.query(Comment).filter_by(comment_api_id=raw_data['comment_api_id'], article_id=article_db_id).first()
        if existing_comment:
            # Cập nhật thông tin nếu cần (ví dụ: likes)
            existing_comment.likes_count = raw_data['likes_count']
            api_id_to_db_id_map[raw_data['comment_api_id']] = existing_comment.id
            # print(f"Comment API ID {raw_data['comment_api_id']} đã tồn tại, cập nhật likes.")
            continue

        comment_dt = parse_datetime_from_str(raw_data['comment_date_str'])
        new_cmt = Comment(
            article_id=article_db_id,
            comment_api_id=raw_data['comment_api_id'],
            user_name=raw_data['user_name'],
            comment_text=raw_data['comment_text'],
            comment_date_str=raw_data['comment_date_str'],
            comment_datetime=comment_dt,
            likes_count=raw_data['likes_count']
            # parent_comment_id sẽ được set ở lượt 2
        )
        try:
            db_session.add(new_cmt)
            db_session.flush() # Quan trọng để `new_cmt.id` được gán giá trị
            api_id_to_db_id_map[new_cmt.comment_api_id] = new_cmt.id
            saved_count += 1
        except Exception as e_add:
            print(f"Lỗi khi add comment {raw_data.get('comment_api_id')}: {e_add}")
            db_session.rollback()


    # Lượt 2: Cập nhật parent_comment_id (FK trỏ đến DB ID của comment cha)
    for raw_data in list_comment_items_data:
        current_api_id = raw_data.get('comment_api_id')
        parent_api_id_on_site = raw_data.get('parent_api_id_on_site')

        if current_api_id and parent_api_id_on_site and current_api_id in api_id_to_db_id_map:
            # Tìm comment con trong DB (dựa trên DB ID đã map)
            comment_to_update = db_session.get(Comment, api_id_to_db_id_map[current_api_id])
            if comment_to_update and parent_api_id_on_site in api_id_to_db_id_map:
                comment_to_update.parent_comment_id = api_id_to_db_id_map[parent_api_id_on_site]
            # else:
                # print(f"Không tìm thấy comment cha API ID {parent_api_id_on_site} trong map để cập nhật cho con {current_api_id}")

    try:
        db_session.commit()
        print(f"Đã lưu/cập nhật {saved_count} bình luận mới vào DB.")
    except Exception as e_commit:
        print(f"Lỗi khi commit comments: {e_commit}")
        db_session.rollback()
        return 0
        
    return saved_count


# Sửa đổi hàm `scrape_and_save_comments` để gọi các hàm Selenium và parse mới
def scrape_and_save_comments(article_db_object, db_session, max_comments=100):
    if not article_db_object or not article_db_object.url:
        print("Đối tượng bài viết không hợp lệ cho scrape comments.")
        return 0
    # 1. Dùng Playwright (hoặc Selenium fallback) để lấy HTML của khối bình luận đã tải đầy đủ
    comment_html_content = fetch_comments_html(article_db_object.url, max_load_more_clicks=10, max_reply_clicks_per_comment=3, debug_save=False, max_comments=max_comments)
    if not comment_html_content:
        print(f"Không lấy được HTML bình luận cho {article_db_object.url}")
        return 0
    # 2. Parse HTML và lưu vào DB
    num_saved = parse_comments_from_html(comment_html_content, article_db_object.id, db_session)
    # 3. Cập nhật total_comment_count cho bài viết
    if num_saved > 0 or article_db_object.total_comment_count is None:
        article_db_object.total_comment_count = (article_db_object.total_comment_count or 0) + num_saved
        try:
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            print(f"Lỗi khi cập nhật total_comment_count: {e}")
    return num_saved



from app import create_app, db
from scraper.vnexpress_scraper import (
    get_article_urls_from_category_page, 
    scrape_article_details_and_save, 
    scrape_and_save_comments,
    app_context_session
)
import time
from concurrent.futures import ThreadPoolExecutor

app = create_app()

def main_scrape_logic():
    categories_to_scrape = {
        "Thế giới": "https://vnexpress.net/the-gioi",
        "Kinh doanh": "https://vnexpress.net/kinh-doanh",
        "Công nghệ": "https://vnexpress.net/khoa-hoc-cong-nghe",
    }
    max_articles_per_category = 5
    max_workers = 3  # Limit concurrent threads

    with app.app_context():
        try:
            for category_name, category_url in categories_to_scrape.items():
                print(f"\n--- Bắt đầu scrape chuyên mục: {category_name} ---")
                
                # Get article URLs for the category
                article_urls = get_article_urls_from_category_page(
                    category_url,
                    max_articles=max_articles_per_category,
                    db_session=db.session
                )

                if not article_urls:
                    print(f"Không tìm thấy bài viết nào cho chuyên mục {category_name}.")
                    continue

                # Process articles in parallel with controlled concurrency
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    def process_article(url):
                        try:
                            print(f"Đang xử lý URL: {url}")
                            with app_context_session(app) as session:
                                article_object = scrape_article_details_and_save(
                                    url, 
                                    session,
                                    scrape_comments=True
                                )
                                if article_object:
                                    print(f"Hoàn tất xử lý: {article_object.title[:50]}...")
                                return article_object
                        except Exception as e:
                            print(f"Lỗi khi xử lý {url}: {e}")
                            return None

                    # Submit all articles for processing
                    future_to_url = {
                        executor.submit(process_article, url): url 
                        for url in article_urls
                    }

                    # Process results as they complete
                    for future in future_to_url:
                        url = future_to_url[future]
                        try:
                            article = future.result()
                            if article:
                                print(f"Đã lưu thành công bài viết: {article.title[:50]}...")
                            time.sleep(1)  # Brief pause between articles
                        except Exception as e:
                            print(f"Lỗi khi xử lý kết quả cho {url}: {e}")

                print(f"--- Hoàn tất scrape chuyên mục: {category_name} ---")

        except Exception as e:
            print(f"Lỗi trong quá trình scrape: {e}")
        finally:
            print("\n=== HOÀN TẤT TOÀN BỘ QUÁ TRÌNH SCRAPE ===")

if __name__ == "__main__":
    main_scrape_logic()

from app import create_app, db
from scraper.vnexpress_scraper import get_article_urls_from_category_page, scrape_article_details_and_save, scrape_and_save_comments
import time

app = create_app()  


def main_scrape_logic():
    categories_to_scrape = {
        "Thế giới": "https://vnexpress.net/the-gioi",
        "Kinh doanh": "https://vnexpress.net/kinh-doanh",
        "Công nghệ": "https://vnexpress.net/khoa-hoc-cong-nghe",
    
    }
    max_articles_per_category = 5  # Số lượng bài viết tối đa để scrape từ mỗi chuyên mục

    with app.app_context():  # Đặt code DB vào trong app_context
        for category_name, category_url in categories_to_scrape.items():
            print(f"\n--- Bắt đầu scrape chuyên mục: {category_name} ---")
            article_urls = get_article_urls_from_category_page(
                category_url, max_articles=max_articles_per_category
            )

            if not article_urls:
                print(f"Không tìm thấy bài viết nào cho chuyên mục {category_name}.")
                continue

            for i, url in enumerate(article_urls):
                print(
                    f"Đang xử lý URL ({i+1}/{len(article_urls)} của {category_name}): {url}"
                )
                article_object = scrape_article_details_and_save(url, db.session)
                time.sleep(3)  # Chờ giữa các request để tránh quá tải
                if article_object:
                    print(f"Bắt đầu scrape bình luận cho: {article_object.title[:50]}...")
                    scrape_and_save_comments(article_object, db.session)
                    print("Hoàn tất scrape bình luận.")

            print(f"--- Hoàn tất scrape chuyên mục: {category_name} ---")
        print("\n=== HOÀN TẤT TOÀN BỘ QUÁ TRÌNH SCRAPE ===")


if __name__ == "__main__":
    main_scrape_logic()

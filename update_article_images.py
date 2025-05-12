# update_article_images.py
"""
Script để cập nhật image_url cho các bài viết đã có trong DB nhưng chưa có ảnh.
Chạy: python update_article_images.py
"""
from app import create_app, db
from app.models import Article
import requests
from bs4 import BeautifulSoup

app = create_app()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_image_url(article_url):
    try:
        response = requests.get(article_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']
    except Exception as e:
        print(f"Lỗi khi lấy ảnh cho {article_url}: {e}")
    return None

with app.app_context():
    articles = Article.query.filter((Article.image_url == None) | (Article.image_url == '')).all()
    print(f"Có {len(articles)} bài chưa có image_url. Đang cập nhật...")
    for article in articles:
        img_url = fetch_image_url(article.url)
        if img_url:
            article.image_url = img_url
            print(f"Đã cập nhật ảnh cho: {article.title[:50]}...")
        else:
            print(f"Không tìm thấy ảnh cho: {article.title[:50]}...")
    db.session.commit()
    print("Đã cập nhật xong image_url cho các bài viết.")

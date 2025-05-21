# VnExpress_Anls

## Hướng dẫn chạy project VnExpress_Anls

### 1. Yêu cầu hệ thống

- Python 3.9 trở lên (khuyên dùng Python 3.10+)
- PostgreSQL (cài đặt và tạo database riêng)
- pip (Python package manager)
- Trình duyệt Chrome (nếu muốn scrape bình luận động)

### 2. Cài đặt môi trường

#### a. Clone project về máy

```bash
# Clone về thư mục của bạn
https://github.com/EurusDFIR/VnExpress_Anls.git
cd VnExpress_Anls
```

#### b. Tạo và kích hoạt virtual environment (khuyên dùng)

```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

#### c. Cài đặt các thư viện cần thiết

```bash
pip install -r requirements.txt
```

### 2.1. Cài đặt Playwright và browser driver (bắt buộc để scrape bình luận động)

```bash
pip install playwright  # Đã có trong requirements.txt, nhưng nên chạy lại để chắc chắn
python -m playwright install  # Cài Chromium/Firefox/Webkit driver cho Playwright
```

- **Yêu cầu Node.js:** Playwright cần Node.js để cài browser driver. Nếu chưa có, tải tại: https://nodejs.org/

### 2.2. Cài đặt NLTK data (bắt buộc cho phân tích chủ đề)

```bash
python -m analysis.download_nltk_data
```

### 2.3. File .env mẫu

Tạo file `.env` ở thư mục gốc với nội dung ví dụ:

```
DATABASE_URL=postgresql://username:password@localhost:5432/ten_database
FLASK_APP=run.py
FLASK_ENV=development
```

### 3. Cấu hình kết nối database

- Tạo file `.env` hoặc chỉnh sửa `config.py` để điền thông tin kết nối PostgreSQL:
  - Ví dụ biến môi trường:
    - `DATABASE_URL=postgresql://username:password@localhost:5432/ten_database`
- Đảm bảo database đã tồn tại và user có quyền truy cập.

### 4. Khởi tạo database (chạy migration)

```bash
flask db upgrade
```

### 4.1. Import database mẫu (nếu muốn có dữ liệu sẵn)

- Đã có file `vnexpress_analyzer_db.sql` (hoặc `.backup`) trong repo hoặc được chia sẻ kèm.
- Tạo database trống (nếu chưa có):

  ```powershell
  createdb -U postgres vnexpress_analyzer_db
  ```

- Import dữ liệu mẫu:

  ```powershell
  psql -U postgres -d vnexpress_analyzer_db -f vnexpress_analyzer_db.sql
  # hoặc nếu dùng file .backup:
  pg_restore -U postgres -d vnexpress_analyzer_db -v vnexpress_analyzer_db.backup
  ```

- Sau đó, cấu hình `.env` trỏ đúng database này và chạy app như bình thường.

### 4.2. Nếu muốn tạo database/migration từ đầu (không dùng file mẫu)

- Làm theo hướng dẫn cũ: chạy `flask db upgrade` để tạo schema mới.

### 5. Chạy ứng dụng Flask

```bash
# Chạy server Flask
python run.py
# Hoặc
flask run
```

- Truy cập: http://127.0.0.1:5000

### 6. Scrape dữ liệu bài viết

- Để lấy dữ liệu bài viết mới:

```bash
python run_scraper.py
```

- Để cập nhật ảnh cho các bài viết cũ:

```bash
python update_article_images.py
```

## Các chức năng chính

- Tìm kiếm bài viết theo tiêu đề, chuyên mục, tác giả (có gợi ý tự động)
- Xem chi tiết bài viết, hình ảnh, bình luận (nếu có)
- Lọc, sắp xếp bài viết theo ngày, chuyên mục, số bình luận
- Phân tích chủ đề bình luận
- Phân tích cảm xúc bình luận 
- Giao diện trực quan, responsive

## Phân tích chủ đề (Topic Modeling)

Module này cung cấp chức năng phân tích chủ đề cho bình luận trong bài viết VnExpress, sử dụng các phương pháp phân tích chủ đề khác nhau.

### Phương pháp phân tích chủ đề

#### 1. Phương pháp từ khóa (Keyword-based)

- Phân tích các bình luận dựa trên từ khóa đã định nghĩa trước
- Tìm kiếm sự xuất hiện của từ khóa trong bình luận
- Tạo ra kết quả chủ đề dựa trên tần suất xuất hiện của từ khóa

#### 2. Phương pháp LDA (Latent Dirichlet Allocation)

- Phương pháp phân tích chủ đề không giám sát, dựa trên mô hình xác suất
- Phân tích sự phân bố từ trong văn bản để tìm ra các nhóm chủ đề
- Hoạt động hoàn toàn offline và hiệu quả về mặt thời gian

### Cách sử dụng

#### 1. Phân tích chủ đề bài viết

Mô-đun `topic_modeler.py` cung cấp hàm `analyze_article_topics()` để phân tích chủ đề cho bài viết:

```python
from analysis.topic_modeler import analyze_article_topics

# Phân tích chủ đề cho một bài viết
topic_analysis = analyze_article_topics(article_id, db_session, num_topics=5)

# In ra các chủ đề
if topic_analysis and 'topics' in topic_analysis:
    for topic in topic_analysis['topics']:
        print(f"Chủ đề: {topic['name']}")
        print(f"Phần trăm: {topic['percentage']}%")
        print(f"Từ khóa: {', '.join(topic['keywords'])}")
        print()
```

#### 2. Gán chủ đề cho bình luận

Hàm `assign_topics_to_comments()` giúp gán chủ đề cho từng bình luận dựa trên kết quả phân tích:

```python
from analysis.topic_modeler import fallback_analyze_topics, assign_topics_to_comments

# Phân tích chủ đề
topics_result = fallback_analyze_topics(comments_data, num_topics=5)

# Gán chủ đề cho các bình luận
comments_with_topics = assign_topics_to_comments(comments_data, topics_result)
```

## Lưu ý chung

- Nếu scrape bình luận động, cần cài Chrome/Chromium hoặc Firefox/Webkit (Playwright sẽ tự động cài khi chạy lệnh trên).
- Nếu dùng Selenium fallback, ChromeDriver sẽ được tự động cài qua webdriver-manager.
- Nếu gặp lỗi kết nối database, kiểm tra lại thông tin trong `.env` hoặc `config.py`.
- **Sau khi pip install -r requirements.txt, luôn chạy:**
  ```
  python -m playwright install
  ```

## Demo

#### Trang chủ

![Trang chủ](static/images/image.png)

#### Danh sách bài viết

![Danh sách](static/images/image-1.png)

#### Chi tiết bài viết với bình luận

![Chi tiết 1](static/images/image-2.png)

![Chi tiết 2](static/images/image-3.png)

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

### 2.2. File .env mẫu

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

### 7. Các chức năng chính

- Tìm kiếm bài viết theo tiêu đề, chuyên mục, tác giả (có gợi ý tự động)
- Xem chi tiết bài viết, hình ảnh, bình luận (nếu có)
- Lọc, sắp xếp bài viết theo ngày, chuyên mục, số bình luận
- Giao diện trực quan, responsive

### 8. Lưu ý

- Nếu scrape bình luận động, cần cài Chrome/Chromium hoặc Firefox/Webkit (Playwright sẽ tự động cài khi chạy lệnh trên).
- Nếu dùng Selenium fallback, ChromeDriver sẽ được tự động cài qua webdriver-manager.
- Nếu gặp lỗi kết nối database, kiểm tra lại thông tin trong `.env` hoặc `config.py`.
- **Sau khi pip install -r requirements.txt, luôn chạy:**
  ```
  python -m playwright install
  ```
- Có thể cần chỉnh sửa `requirements.txt` nếu môi trường đặc biệt.

### Demo

#### Trang chủ

![Trang chủ](static/images/image.png)

#### Danh sách bài viết

![Danh sách](static/images/image-1.png)

#### Chi tiết bài viết với bình luận

![Chi tiết 1](static/images/image-2.png)

![Chi tiết 2](static/images/image-3.png)

# VnExpress Analyzer - Documentation

## 1. Tổng quan dự án
VnExpress Analyzer là hệ thống phân tích dữ liệu báo chí hiện đại, tập trung vào việc thu thập, phân tích, và trực quan hóa các bài viết và bình luận từ trang VnExpress.net. Dự án hướng tới việc cung cấp các insight về nội dung, cảm xúc, chủ đề, và tương tác cộng đồng trên báo điện tử.

---

## 2. Chức năng chính
- **Thu thập dữ liệu bài viết và bình luận** từ VnExpress theo từng chuyên mục hoặc từng URL cụ thể.
- **Phân tích cảm xúc** (sentiment analysis) cho từng bài viết và bình luận.
- **Thống kê, lọc, tìm kiếm, phân loại bài viết** theo chuyên mục, thời gian, số lượng bình luận, v.v.
- **Trực quan hóa dữ liệu**: hiển thị biểu đồ, số liệu tổng hợp, phân tích chuyên sâu.
- **Giao diện web hiện đại**: cho phép người dùng thao tác, tìm kiếm, xem chi tiết bài viết, bình luận, và các thống kê liên quan.
- **Trang Giới Thiệu**: thông tin về nhóm phát triển, công nghệ, mục tiêu dự án.

---

## 3. Kiến trúc & Công nghệ sử dụng
### Backend
- **Ngôn ngữ:** Python 3.x
- **Framework:** Flask (Flask-SQLAlchemy, Flask-Migrate, Flask-Bootstrap)
- **ORM:** SQLAlchemy
- **Database:** PostgreSQL (có thể dùng SQLite cho phát triển)
- **Scraping:** BeautifulSoup, requests, Playwright (cho scraping bình luận động)
- **Xử lý song song:** ThreadPoolExecutor
- **Quản lý môi trường:** python-dotenv

### Frontend
- **Template engine:** Jinja2
- **CSS Framework:** Tailwind CSS
- **Icons:** Font Awesome
- **Hiệu ứng động:** Animate On Scroll (AOS), custom CSS/JS
- **Responsive:** Thiết kế tối ưu cho cả desktop và mobile

### Khác
- **Quản lý phiên bản:** Git, GitHub
- **Quản lý gói:** pip, requirements.txt
- **Quản lý migration:** Alembic

---

## 4. Các khâu chính của hệ thống
### 4.1. Thu thập dữ liệu (Scraping)
- **Scrape theo chuyên mục:** Lấy danh sách bài viết mới nhất từ từng chuyên mục trên VnExpress.
- **Scrape theo URL:** Phân tích nhanh một bài viết bất kỳ qua URL.
- **Scrape bình luận:** Sử dụng Playwright để lấy bình luận động, BeautifulSoup để parse HTML.
- **Chống trùng lặp:** Kiểm tra bài viết đã tồn tại trong DB trước khi lưu.

### 4.2. Xây dựng Backend
- **API nội bộ:** Xử lý các route cho phân tích, tìm kiếm, thống kê, lấy dữ liệu mới nhất.
- **Xử lý đa luồng:** Dùng ThreadPoolExecutor để scrape nhiều bài viết song song.
- **Quản lý session DB:** Đảm bảo an toàn khi thao tác đa luồng.
- **Xử lý lỗi:** Log chi tiết, rollback khi có lỗi DB hoặc scraping.

### 4.3. Xây dựng Database
- **Thiết kế chuẩn hóa:**
  - Bảng Article: lưu thông tin bài viết, chuyên mục, thời gian, nội dung, cảm xúc, số bình luận...
  - Bảng Comment: lưu bình luận, liên kết với bài viết, cảm xúc, thời gian, người dùng...
  - Bảng Category: lưu chuyên mục, phân cấp cha-con.
- **Migration:** Quản lý thay đổi cấu trúc DB bằng Alembic.

### 4.4. Xây dựng Frontend
- **Trang chủ:** Hiển thị danh sách bài viết, filter, sort, tìm kiếm, phân trang.
- **Trang chi tiết bài viết:** Hiển thị nội dung, bình luận, thống kê cảm xúc, phân tích chuyên sâu.
- **Trang scrape center:** Chọn chuyên mục, số lượng bài viết cần scrape, scrape song song.
- **Trang about:** Thông tin nhóm, công nghệ, mục tiêu, thành viên.
- **Giao diện đẹp, hiện đại, responsive, nhiều hiệu ứng động.**

---

## 5. Thư viện & Công nghệ đã dùng
- **Flask**: Web framework chính
- **Flask-SQLAlchemy**: ORM cho database
- **Flask-Migrate/Alembic**: Quản lý migration
- **Jinja2**: Template engine
- **Tailwind CSS**: Thiết kế giao diện
- **Font Awesome**: Icon
- **BeautifulSoup**: Parse HTML
- **requests**: Gửi HTTP request
- **Playwright**: Scrape nội dung động (bình luận)
- **pandas, numpy**: Xử lý dữ liệu (nếu có)
- **python-dotenv**: Quản lý biến môi trường
- **ThreadPoolExecutor**: Đa luồng
- **pytest/unittest**: Kiểm thử (nếu có)

---

## 6. Phương pháp & điểm nổi bật
- **Chống trùng lặp dữ liệu** khi scrape
- **Tối ưu hiệu suất** với đa luồng và kiểm tra session DB
- **Tách biệt rõ backend/frontend**
- **Giao diện hiện đại, dễ dùng, nhiều hiệu ứng động**
- **Có trang About, thể hiện thông tin nhóm, công nghệ, mục tiêu rõ ràng**
- **Dễ mở rộng, dễ bảo trì**

---

## 7. Hướng dẫn cài đặt & chạy thử
1. Clone repo:
   ```bash
   git clone <repo_url>
   cd VnExpress_Anls
   ```
2. Tạo virtualenv và cài đặt:
   ```bash
   python -m venv venv
   source venv/bin/activate  # hoặc venv\Scripts\activate trên Windows
   pip install -r requirements.txt
   ```
3. Tạo file `.env` và cấu hình DB:
   ```env
   FLASK_APP=run.py
   FLASK_ENV=development
   DATABASE_URL=postgresql://user:password@localhost:5432/vnexpress_db
   SECRET_KEY=your_secret_key
   ```
4. Khởi tạo DB:
   ```bash
   flask db upgrade
   ```
5. Chạy app:
   ```bash
   flask run
   ```
6. Truy cập: http://localhost:5000

---

## 8. Đóng góp & phát triển
- Fork, tạo branch mới, pull request để đóng góp code.
- Đọc kỹ README và DOCUMENTATION trước khi phát triển thêm.
- Liên hệ nhóm phát triển qua trang About.


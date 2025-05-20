# populate_categories.py
import sys
import os

# Thêm thư mục gốc của dự án vào sys.path để có thể import app
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app, db
from app.models import Category # Đảm bảo bạn đã định nghĩa Category model

# Dữ liệu chuyên mục VnExpress (Cần kiểm tra và cập nhật URL chính xác)
# Key là tên hiển thị, value là dict chứa url và children (nếu có)
# URL ở đây là URL của trang chuyên mục đó trên VnExpress
VNEXPRESS_CATEGORIES_STRUCTURE = [
    {
        "name": "Thời sự", "url": "https://vnexpress.net/thoi-su", "slug": "thoi-su",
        "children": [
            {"name": "Chính trị", "url": "https://vnexpress.net/thoi-su/chinh-tri", "slug": "chinh-tri",
             "children": [
                 {"name": "Nhân sự", "url": "https://vnexpress.net/thoi-su/chinh-tri/nhan-su", "slug": "nhan-su-thoi-su"}
             ]},
            {"name": "Hướng tới Kỷ nguyên mới", "url": "https://vnexpress.net/thoi-su/huong-toi-ky-nguyen-moi", "slug": "huong-toi-ky-nguyen-moi",
             "children": [
                 {"name": "Tinh gọn bộ máy", "url": "https://vnexpress.net/thoi-su/huong-toi-ky-nguyen-moi/tinh-gon-bo-may", "slug": "tinh-gon-bo-may"}
             ]},
            {"name": "Dân sinh", "url": "https://vnexpress.net/thoi-su/dan-sinh", "slug": "dan-sinh"},
            {"name": "Việc làm", "url": "https://vnexpress.net/thoi-su/lao-dong-viec-lam", "slug": "lao-dong-viec-lam"},
            {"name": "Giao thông", "url": "https://vnexpress.net/thoi-su/giao-thong", "slug": "giao-thong"},
            {"name": "Mekong", "url": "https://vnexpress.net/thoi-su/mekong", "slug": "mekong"},
            {"name": "Quỹ Hy vọng", "url": "https://vnexpress.net/thoi-su/quy-hy-vong", "slug": "quy-hy-vong"}
        ]
    },
    {
        "name": "Thế giới", "url": "https://vnexpress.net/the-gioi", "slug": "the-gioi",
        "children": [
            {"name": "Tư liệu", "url": "https://vnexpress.net/the-gioi/tu-lieu", "slug": "tu-lieu"},
            {"name": "Phân tích", "url": "https://vnexpress.net/the-gioi/phan-tich", "slug": "phan-tich-tg"},
            {"name": "Người Việt 5 châu", "url": "https://vnexpress.net/the-gioi/nguoi-viet-5-chau", "slug": "nguoi-viet-5-chau"},
            {"name": "Cuộc sống đó đây", "url": "https://vnexpress.net/the-gioi/cuoc-song-do-day", "slug": "cuoc-song-do-day"},
            {"name": "Quân sự", "url": "https://vnexpress.net/the-gioi/quan-su", "slug": "quan-su"}
        ]
    },
    {
        "name": "Kinh doanh", "url": "https://vnexpress.net/kinh-doanh", "slug": "kinh-doanh",
        "children": [
            {"name": "Net Zero", "url": "https://vnexpress.net/kinh-doanh/net-zero", "slug": "net-zero"},
            {"name": "Quốc tế", "url": "https://vnexpress.net/kinh-doanh/quoc-te", "slug": "quoc-te-kd"},
            {"name": "Doanh nghiệp", "url": "https://vnexpress.net/kinh-doanh/doanh-nghiep", "slug": "doanh-nghiep"},
            {"name": "Chứng khoán", "url": "https://vnexpress.net/kinh-doanh/chung-khoan", "slug": "chung-khoan"},
            {"name": "Ebank", "url": "https://vnexpress.net/kinh-doanh/ebank", "slug": "ebank-kd"},
            {"name": "Vĩ mô", "url": "https://vnexpress.net/kinh-doanh/vi-mo", "slug": "vi-mo"},
            {"name": "Tiền của tôi", "url": "https://vnexpress.net/kinh-doanh/tien-cua-toi", "slug": "tien-cua-toi"},
            {"name": "Hàng hóa", "url": "https://vnexpress.net/kinh-doanh/hang-hoa", "slug": "hang-hoa"}
        ]
    },
    {
        "name": "Khoa học Công nghệ", "url": "https://vnexpress.net/khoa-hoc-cong-nghe", "slug": "khoa-hoc-cong-nghe",
        "children": [
            {"name": "Hoạt động Bộ KH&CN", "url": "https://vnexpress.net/khoa-hoc-cong-nghe/bo-khoa-hoc-va-cong-nghe", "slug": "bo-khoa-hoc-va-cong-nghe"},
            {"name": "Chuyển đổi số", "url": "https://vnexpress.net/khoa-hoc-cong-nghe/chuyen-doi-so", "slug": "chuyen-doi-so"},
            {"name": "Đổi mới sáng tạo", "url": "https://vnexpress.net/khoa-hoc-cong-nghe/doi-moi-sang-tao", "slug": "doi-moi-sang-tao"},
            {"name": "AI", "url": "https://vnexpress.net/khoa-hoc-cong-nghe/ai", "slug": "ai-khcn"},
            {"name": "Vũ trụ", "url": "https://vnexpress.net/khoa-hoc-cong-nghe/vu-tru", "slug": "vu-tru"},
            {"name": "Thế giới tự nhiên", "url": "https://vnexpress.net/khoa-hoc-cong-nghe/the-gioi-tu-nhien", "slug": "the-gioi-tu-nhien"},
            {"name": "Thiết bị", "url": "https://vnexpress.net/khoa-hoc-cong-nghe/thiet-bi", "slug": "thiet-bi-khcn"},
            {"name": "Cửa sổ tri thức", "url": "https://vnexpress.net/khoa-hoc-cong-nghe/cua-so-tri-thuc", "slug": "cua-so-tri-thuc"},
            {"name": "GameVerse 2025", "url": "https://vnexpress.net/khoa-hoc-cong-nghe/vgv-2025", "slug": "vgv-2025"},
            {"name": "Sáng kiến Khoa học 2025", "url": "https://vnexpress.net/khoa-hoc-cong-nghe/cuoc-thi-sang-kien-khoa-hoc", "slug": "cuoc-thi-sang-kien-khoa-hoc"}
        ]
    },
    {
        "name": "Góc nhìn", "url": "https://vnexpress.net/goc-nhin", "slug": "goc-nhin",
        "children": [
            {"name": "Chính trị & chính sách", "url": "https://vnexpress.net/goc-nhin/chinh-tri-chinh-sach", "slug": "chinh-tri-chinh-sach"},
            {"name": "Y tế & sức khỏe", "url": "https://vnexpress.net/goc-nhin/y-te-suc-khoe", "slug": "y-te-suc-khoe-gn"},
            {"name": "Kinh doanh & quản trị", "url": "https://vnexpress.net/goc-nhin/kinh-doanh-quan-tri", "slug": "kinh-doanh-quan-tri"},
            {"name": "Giáo dục & tri thức", "url": "https://vnexpress.net/goc-nhin/giao-duc-tri-thuc", "slug": "giao-duc-tri-thuc"},
            {"name": "Môi trường", "url": "https://vnexpress.net/goc-nhin/moi-truong", "slug": "moi-truong-gn"},
            {"name": "Văn hóa & lối sống", "url": "https://vnexpress.net/goc-nhin/van-hoa-loi-song", "slug": "van-hoa-loi-song"}
        ]
    },
    {
        "name": "Bất động sản", "url": "https://vnexpress.net/bat-dong-san", "slug": "bat-dong-san",
        "children": [
            {"name": "Chính sách", "url": "https://vnexpress.net/bat-dong-san/chinh-sach", "slug": "chinh-sach-bds"},
            {"name": "Thị trường", "url": "https://vnexpress.net/bat-dong-san/thi-truong", "slug": "thi-truong-bds"},
            {"name": "Dự án", "url": "https://vnexpress.net/bat-dong-san/du-an", "slug": "du-an"},
            {"name": "Không gian sống", "url": "https://vnexpress.net/bat-dong-san/khong-gian-song", "slug": "khong-gian-song"},
            {"name": "Tư vấn", "url": "https://vnexpress.net/bat-dong-san/tu-van", "slug": "tu-van-bds"}
        ]
    },
    {
        "name": "Sức khỏe", "url": "https://vnexpress.net/suc-khoe", "slug": "suc-khoe",
        "children": [
            {"name": "Tin tức", "url": "https://vnexpress.net/suc-khoe/tin-tuc", "slug": "tin-tuc-sk"},
            {"name": "Các bệnh", "url": "https://vnexpress.net/suc-khoe/cac-benh", "slug": "cac-benh"},
            {"name": "Sống khỏe", "url": "https://vnexpress.net/suc-khoe/song-khoe", "slug": "song-khoe"},
            {"name": "Vaccine", "url": "https://vnexpress.net/suc-khoe/vaccine", "slug": "vaccine"}
        ]
    },
    {
        "name": "Thể thao", "url": "https://vnexpress.net/the-thao", "slug": "the-thao",
        "children": [
            {"name": "Bóng đá", "url": "https://vnexpress.net/bong-da", "slug": "bong-da"},
            {"name": "Lịch thi đấu", "url": "https://vnexpress.net/the-thao/du-lieu-bong-da", "slug": "du-lieu-bong-da"},
            {"name": "Marathon", "url": "https://vnexpress.net/the-thao/marathon", "slug": "marathon"},
            {"name": "Tennis", "url": "https://vnexpress.net/the-thao/tennis", "slug": "tennis"},
            {"name": "Các môn khác", "url": "https://vnexpress.net/the-thao/cac-mon-khac", "slug": "cac-mon-khac"},
            {"name": "Hậu trường", "url": "https://vnexpress.net/the-thao/hau-truong", "slug": "hau-truong"},
            {"name": "Ảnh", "url": "https://vnexpress.net/the-thao/photo", "slug": "photo-tt"},
            {"name": "Esports", "url": "https://vnexpress.net/esport", "slug": "esport"}
        ]
    },
    {
        "name": "Giải trí", "url": "https://vnexpress.net/giai-tri", "slug": "giai-tri",
        "children": [
            {"name": "Giới sao", "url": "https://vnexpress.net/giai-tri/gioi-sao", "slug": "gioi-sao"},
            {"name": "Sách", "url": "https://vnexpress.net/giai-tri/sach", "slug": "sach"},
            {"name": "Phim", "url": "https://vnexpress.net/giai-tri/phim", "slug": "phim"},
            {"name": "Nhạc", "url": "https://vnexpress.net/giai-tri/nhac", "slug": "nhac"},
            {"name": "Thời trang", "url": "https://vnexpress.net/giai-tri/thoi-trang", "slug": "thoi-trang"},
            {"name": "Làm đẹp", "url": "https://vnexpress.net/giai-tri/lam-dep", "slug": "lam-dep"},
            {"name": "Sân khấu - Mỹ thuật", "url": "https://vnexpress.net/giai-tri/san-khau-my-thuat", "slug": "san-khau-my-thuat"}
        ]
    },
    {
        "name": "Pháp luật", "url": "https://vnexpress.net/phap-luat", "slug": "phap-luat",
        "children": [
            {"name": "Hồ sơ phá án", "url": "https://vnexpress.net/phap-luat/ho-so-pha-an", "slug": "ho-so-pha-an"},
            {"name": "Tư vấn", "url": "https://vnexpress.net/phap-luat/tu-van", "slug": "tu-van-pl"}
        ]
    },
    {
        "name": "Giáo dục", "url": "https://vnexpress.net/giao-duc", "slug": "giao-duc",
        "children": [
            {"name": "Tin tức", "url": "https://vnexpress.net/giao-duc/tin-tuc", "slug": "tin-tuc-gd"},
            {"name": "Tuyển sinh", "url": "https://vnexpress.net/giao-duc/tuyen-sinh", "slug": "tuyen-sinh"},
            {"name": "Chân dung", "url": "https://vnexpress.net/giao-duc/chan-dung", "slug": "chan-dung"},
            {"name": "Du học", "url": "https://vnexpress.net/giao-duc/du-hoc", "slug": "du-hoc"},
            {"name": "Thảo luận", "url": "https://vnexpress.net/giao-duc/thao-luan", "slug": "thao-luan"},
            {"name": "Học tiếng Anh", "url": "https://vnexpress.net/giao-duc/hoc-tieng-anh", "slug": "hoc-tieng-anh"},
            {"name": "Giáo dục 4.0", "url": "https://vnexpress.net/giao-duc/giao-duc-40", "slug": "giao-duc-40"},
            {"name": "VnExpress Youth Basketball", "url": "https://vnexpress.net/giao-duc/vnexpress-youth-basketball-ziaja-cup", "slug": "vnexpress-youth-basketball-ziaja-cup"}
        ]
    },
    {
        "name": "Đời sống", "url": "https://vnexpress.net/doi-song", "slug": "doi-song",
        "children": [
            {"name": "Nhịp sống", "url": "https://vnexpress.net/doi-song/nhip-song", "slug": "nhip-song"},
            {"name": "Tổ ấm", "url": "https://vnexpress.net/doi-song/to-am", "slug": "to-am"},
            {"name": "Bài học sống", "url": "https://vnexpress.net/doi-song/bai-hoc-song", "slug": "bai-hoc-song"},
            {"name": "Cooking", "url": "https://vnexpress.net/doi-song/cooking", "slug": "cooking"},
            {"name": "Tiêu dùng", "url": "https://vnexpress.net/doi-song/tieu-dung", "slug": "tieu-dung"}
        ]
    },
    {
        "name": "Xe", "url": "https://vnexpress.net/oto-xe-may", "slug": "oto-xe-may",
        "children": [
            {"name": "Thị trường", "url": "https://vnexpress.net/oto-xe-may/thi-truong", "slug": "thi-truong-xe"},
            {"name": "Diễn đàn", "url": "https://vnexpress.net/oto-xe-may/dien-dan", "slug": "dien-dan"},
            {"name": "V-Car", "url": "https://vnexpress.net/oto-xe-may/v-car", "slug": "v-car"},
            {"name": "V-Bike", "url": "https://vnexpress.net/oto-xe-may/v-bike", "slug": "v-bike"},
            {"name": "Cầm lái", "url": "https://vnexpress.net/oto-xe-may/cam-lai", "slug": "cam-lai"},
            {"name": "Thi lý thuyết", "url": "https://vnexpress.net/interactive/2016/thi-sat-hach-lai-xe", "slug": "thi-sat-hach-lai-xe"},
            {"name": "Thi mô phỏng", "url": "https://vnexpress.net/oto-xe-may/thi-bang-lai-oto-b1-b2/mo-phong", "slug": "thi-bang-lai-oto-mo-phong"}
        ]
    },
    {
        "name": "Du lịch", "url": "https://vnexpress.net/du-lich", "slug": "du-lich",
        "children": [
            {"name": "Điểm đến", "url": "https://vnexpress.net/du-lich/diem-den", "slug": "diem-den"},
            {"name": "Ẩm thực", "url": "https://vnexpress.net/du-lich/am-thuc", "slug": "am-thuc"},
            {"name": "Dấu chân", "url": "https://vnexpress.net/du-lich/dau-chan", "slug": "dau-chan"},
            {"name": "Tư vấn", "url": "https://vnexpress.net/du-lich/tu-van", "slug": "tu-van-dl"},
            {"name": "Cẩm nang", "url": "https://vnexpress.net/du-lich/cam-nang", "slug": "cam-nang"},
            {"name": "Ảnh", "url": "https://vnexpress.net/du-lich/anh-video", "slug": "anh-video-dl"}
        ]
    },
    {
        "name": "Ý kiến", "url": "https://vnexpress.net/y-kien", "slug": "y-kien",
        "children": [
            {"name": "Thời sự", "url": "https://vnexpress.net/y-kien/thoi-su", "slug": "thoi-su-yk"},
            {"name": "Đời sống", "url": "https://vnexpress.net/y-kien/doi-song", "slug": "doi-song-yk"}
        ]
    },
    {
        "name": "Tâm sự", "url": "https://vnexpress.net/tam-su", "slug": "tam-su",
        "children": [
            {"name": "Hẹn hò", "url": "https://vnexpress.net/tam-su/hen-ho", "slug": "hen-ho"}
        ]
    },
    {
        "name": "Thư giãn", "url": "https://vnexpress.net/thu-gian", "slug": "thu-gian",
        "children": [
            {"name": "Cười", "url": "https://vnexpress.net/thu-gian/cuoi", "slug": "cuoi"},
            {"name": "Đố vui", "url": "https://vnexpress.net/thu-gian/do-vui", "slug": "do-vui"},
            {"name": "Chuyện lạ", "url": "https://vnexpress.net/thu-gian/chuyen-la", "slug": "chuyen-la"},
            {"name": "Crossword", "url": "https://vnexpress.net/thu-gian/crossword", "slug": "crossword"},
            {"name": "Thú cưng", "url": "https://vnexpress.net/thu-gian/thu-cung", "slug": "thu-cung"}
        ]
    }
]


app = create_app()

def add_category_recursive(name, data, parent_id=None):
    """Thêm category và các con của nó vào DB một cách đệ quy."""
    # Kiểm tra xem category đã tồn tại chưa (dựa trên URL hoặc slug)
    existing_category = Category.query.filter_by(url=data['url']).first()
    if existing_category:
        print(f"Chuyên mục '{name}' với URL '{data['url']}' đã tồn tại. Bỏ qua.")
        current_category_id = existing_category.id
    else:
        category = Category(
            name=name,
            url=data['url'],
            vnexpress_slug=data.get('slug'), # Lấy slug nếu có
            parent_id=parent_id
        )
        db.session.add(category)
        try:
            db.session.flush() # Để lấy được category.id cho các con
            current_category_id = category.id
            print(f"Đã thêm chuyên mục: {name} (ID: {current_category_id})")
        except Exception as e:
            db.session.rollback()
            print(f"Lỗi khi thêm chuyên mục '{name}': {e}")
            return # Không tiếp tục với các con nếu cha lỗi

    if 'children' in data and data['children']:
        for child_data in data['children']:
            add_category_recursive(child_data['name'], child_data, parent_id=current_category_id)

if __name__ == "__main__":
    with app.app_context():
        print("Bắt đầu nhập liệu chuyên mục...")
        # Xóa dữ liệu cũ nếu muốn (cẩn thận!)
        # Category.query.delete()
        # db.session.commit()
        # print("Đã xóa dữ liệu categories cũ.")

        for cat_data in VNEXPRESS_CATEGORIES_STRUCTURE:
            add_category_recursive(cat_data['name'], cat_data)
        
        try:
            db.session.commit()
            print("Hoàn tất nhập liệu chuyên mục!")
        except Exception as e:
            db.session.rollback()
            print(f"Lỗi khi commit cuối cùng: {e}")
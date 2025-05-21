import os
import json
import time
import pickle
from collections import Counter, defaultdict
import numpy as np
import re
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Tải biến môi trường
load_dotenv()

# Cấu hình
DEFAULT_NUM_TOPICS = 5
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')

# Tạo thư mục cache nếu chưa tồn tại
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def clean_text_for_topic_modeling(text):
    """
    Làm sạch văn bản để phân tích chủ đề
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Chuyển thành chữ thường
    text = text.lower()
    
    # Loại bỏ URL
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    
    # Loại bỏ các ký tự đặc biệt
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Loại bỏ số
    text = re.sub(r'\d+', ' ', text)
    
    # Loại bỏ khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def balance_topic_distribution(topics, threshold=10.0):
    """
    Cân bằng phân phối chủ đề để tránh chênh lệch quá lớn
    
    Parameters:
    - topics: Danh sách các chủ đề với phần trăm
    - threshold: Ngưỡng chênh lệch cho phép giữa max và min (%)
    
    Returns:
    - Danh sách chủ đề với phần trăm đã được cân bằng
    """
    if not topics:
        return []
    
    # Tính tổng phần trăm hiện tại
    total_percentage = sum(topic.get('percentage', 0) for topic in topics)
    
    # Nếu tổng gần bằng 100, không cần cân bằng
    if abs(total_percentage - 100.0) < 0.1:
        # Kiểm tra nếu chênh lệch đã nằm trong ngưỡng
        percentages = [topic.get('percentage', 0) for topic in topics]
        max_pct = max(percentages)
        min_pct = min(percentages)
        
        if (max_pct - min_pct) <= threshold:
            return topics
    
    # Phân phối lại theo trọng số, bảo đảm không chênh lệch quá lớn
    n_topics = len(topics)
    
    # Ước tính phần trăm theo hình học
    base_percentage = 100.0 / (n_topics * (n_topics + 1) / 2)
    
    # Gán phần trăm theo thứ tự giảm dần
    for i, topic in enumerate(topics):
        # Chủ đề đầu tiên có phần trăm cao nhất
        weight = n_topics - i
        topic['percentage'] = round(base_percentage * weight, 1)
    
    # Điều chỉnh để tổng đúng bằng 100%
    total = sum(topic['percentage'] for topic in topics)
    if total != 100.0:
        # Điều chỉnh chủ đề cuối để tổng đúng bằng 100%
        topics[-1]['percentage'] += round(100.0 - total, 1)
    
    return topics

def fallback_analyze_topics(comments_data, num_topics=DEFAULT_NUM_TOPICS):
    """
    Phân tích chủ đề bằng phương pháp dự phòng dựa trên từ khóa
    
    Parameters:
    - comments_data: Danh sách các bình luận cần phân tích
    - num_topics: Số lượng chủ đề mong muốn
    
    Returns:
    - Dictionary chứa thông tin về các chủ đề
    """
    print("Sử dụng phương pháp phân tích chủ đề dự phòng...")
    
    if not comments_data:
        print("Không có bình luận để phân tích")
        return None
    
    # Tạo cache key từ comments và num_topics
    cache_key = f"fallback_topics_{hash(str(comments_data))}_{num_topics}"
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    
    # Kiểm tra cache
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                cached_result = pickle.load(f)
                print(f"Đã tải kết quả từ cache: {cache_file}")
                return cached_result
        except Exception as e:
            print(f"Lỗi khi đọc cache: {e}")
    
    # Định nghĩa các chủ đề với từ khóa tiếng Việt
    predefined_topics = [
        {
            "name": "Kinh tế & Tài chính",
            "keywords": ["giá", "tiền", "đồng", "tỷ", "triệu", "usd", "chi phí", "đắt", "rẻ", "kinh tế", "lãi", "lỗ", "đầu tư", "thị trường", "doanh nghiệp", "công ty", "tăng giá", "giảm giá", "lạm phát"]
        },
        {
            "name": "Chính trị & Chính sách",
            "keywords": ["chính phủ", "bộ", "quốc hội", "cơ quan", "nhà nước", "chính sách", "đảng", "lãnh đạo", "cải cách", "luật", "pháp luật", "quy định", "thủ tướng", "bộ trưởng", "chủ tịch", "tổng bí thư"]
        },
        {
            "name": "Y tế & Sức khỏe",
            "keywords": ["bệnh", "y tế", "sức khỏe", "thuốc", "bệnh viện", "bác sĩ", "điều trị", "covid", "dịch", "virus", "vắc xin", "khám", "chữa", "bảo hiểm y tế", "phẫu thuật", "chăm sóc"]
        },
        {
            "name": "Giáo dục & Đào tạo",
            "keywords": ["học", "trường", "sinh viên", "giáo dục", "đại học", "giảng viên", "học sinh", "thi", "điểm", "lớp", "giáo viên", "giảng dạy", "kỳ thi", "học phí", "đào tạo", "bằng cấp"]
        },
        {
            "name": "Công nghệ & Kỹ thuật",
            "keywords": ["công nghệ", "kỹ thuật", "internet", "mạng", "facebook", "google", "smartphone", "app", "máy tính", "thiết bị", "phần mềm", "AI", "robot", "số hóa", "online", "đổi mới"]
        },
        {
            "name": "Thể thao",
            "keywords": ["đội", "bóng", "cầu thủ", "trận", "thể thao", "huấn luyện viên", "thi đấu", "vô địch", "giải", "thắng", "thua", "huy chương", "olympic", "world cup", "bóng đá", "bóng rổ"]
        },
        {
            "name": "Du lịch & Dịch vụ",
            "keywords": ["du lịch", "khách", "dịch vụ", "hotel", "khách sạn", "resort", "tour", "phục vụ", "nghỉ dưỡng", "tham quan", "du khách", "điểm đến", "kỳ nghỉ", "đặt phòng", "check-in"]
        },
        {
            "name": "Giải trí & Nghệ thuật",
            "keywords": ["nghệ sĩ", "diễn viên", "ca sĩ", "âm nhạc", "phim", "hát", "điện ảnh", "giải trí", "game", "show", "concert", "album", "nghệ thuật", "sân khấu", "truyền hình", "tiktok"]
        },
        {
            "name": "Pháp luật & An ninh",
            "keywords": ["tai nạn", "cháy", "cảnh sát", "công an", "tội phạm", "pháp luật", "tòa án", "trộm", "cướp", "đâm", "hình sự", "vụ án", "điều tra", "xét xử", "phạt", "bị cáo"]
        },
        {
            "name": "Môi trường & Thiên nhiên",
            "keywords": ["môi trường", "ô nhiễm", "rác", "khí hậu", "thiên tai", "bão", "lũ", "lụt", "biến đổi", "xanh", "sinh thái", "bảo vệ", "tái chế", "tự nhiên", "động vật", "thực vật"]
        },
        {
            "name": "Giao thông & Vận tải",
            "keywords": ["giao thông", "đường", "xe", "ùn tắc", "tai nạn", "phương tiện", "ô tô", "xe máy", "đi lại", "vận tải", "cầu", "đường bộ", "chuyến bay", "hàng không", "tàu", "biển báo"]
        },
        {
            "name": "Bất động sản & Nhà ở",
            "keywords": ["đất", "nhà", "chung cư", "dự án", "bất động sản", "xây dựng", "căn hộ", "quy hoạch", "sở hữu", "mua nhà", "bán nhà", "thuê", "giá nhà", "giá đất", "mặt bằng", "khu đô thị"]
        },
        {
            "name": "Việc làm & Lao động",
            "keywords": ["lương", "việc làm", "công việc", "nghề", "nhân viên", "sếp", "thị trường", "lao động", "tuyển dụng", "ứng viên", "thất nghiệp", "nhân sự", "chức danh", "đãi ngộ", "nghỉ việc"]
        },
        {
            "name": "Gia đình & Nuôi dạy con",
            "keywords": ["gia đình", "con", "vợ", "chồng", "bố", "mẹ", "em", "nuôi", "dạy", "trẻ", "con cái", "cha mẹ", "giáo dục", "hôn nhân", "ly hôn", "tình cảm"]
        },
        {
            "name": "Quan hệ quốc tế",
            "keywords": ["trung quốc", "mỹ", "nga", "châu âu", "ngoại giao", "quốc tế", "chiến tranh", "hòa bình", "thế giới", "đàm phán", "hiệp định", "hợp tác", "xung đột", "liên minh", "biên giới"]
        }
    ]
    
    # Giới hạn số lượng chủ đề theo yêu cầu
    predefined_topics = predefined_topics[:num_topics]
    
    # Tạo từ điển chủ đề
    topic_matches = {topic["name"]: 0 for topic in predefined_topics}
    topic_keywords = {topic["name"]: topic["keywords"] for topic in predefined_topics}
    
    # Phân tích từng bình luận
    for comment in comments_data:
        # Lấy văn bản bình luận
        comment_text = clean_text_for_topic_modeling(comment.get('comment_text', ''))
        
        # Đếm số từ khóa khớp cho mỗi chủ đề
        for topic_name, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword.lower() in comment_text:
                    topic_matches[topic_name] += 1
    
    # Tính tổng số lần khớp
    total_matches = sum(topic_matches.values())
    
    # Tạo danh sách chủ đề với phần trăm
    topics = []
    for topic in predefined_topics:
        name = topic["name"]
        matches = topic_matches[name]
        percentage = round((matches / max(1, total_matches)) * 100, 1)
        
        topics.append({
            "name": name,
            "keywords": topic["keywords"],
            "percentage": percentage
        })
    
    # Sắp xếp chủ đề theo phần trăm giảm dần
    topics.sort(key=lambda x: x["percentage"], reverse=True)
    
    # Cân bằng phân phối nếu cần
    topics = balance_topic_distribution(topics)
    
    # Tạo kết quả
    result = {
        "topics": topics
    }
    
    # Lưu vào cache
    with open(cache_file, 'wb') as f:
        pickle.dump(result, f)
        print(f"Đã lưu kết quả vào cache: {cache_file}")
    
    return result

def assign_topics_to_comments(comments_data, topics_data):
    """
    Gán chủ đề cho từng bình luận dựa trên kết quả phân tích
    
    Parameters:
    - comments_data: Danh sách các bình luận
    - topics_data: Kết quả phân tích chủ đề từ LLM
    
    Returns:
    - Danh sách bình luận với thông tin chủ đề được gán
    """
    if not topics_data or 'topics' not in topics_data:
        return comments_data
    
    topics = topics_data['topics']
    
    # Chuẩn bị từ khóa cho mỗi chủ đề
    topics_keywords = {topic['name']: set(topic['keywords']) for topic in topics}
    
    # Gán chủ đề cho từng bình luận
    for comment in comments_data:
        comment_text = clean_text_for_topic_modeling(comment.get('comment_text', ''))
        
        # Tính điểm phù hợp với từng chủ đề
        topic_scores = {}
        for topic_name, keywords in topics_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in comment_text.lower():
                    score += 1
            topic_scores[topic_name] = score
        
        # Gán chủ đề có điểm cao nhất (nếu có)
        if topic_scores:
            max_score = max(topic_scores.values())
            if max_score > 0:  # Chỉ gán chủ đề nếu có ít nhất 1 từ khóa khớp
                top_topics = [topic for topic, score in topic_scores.items() if score == max_score]
                comment['topic'] = top_topics[0]  # Lấy chủ đề đầu tiên nếu có nhiều cùng điểm
            else:
                comment['topic'] = "Khác"  # Chủ đề mặc định nếu không khớp với từ khóa nào
        else:
            comment['topic'] = "Khác"
    
    return comments_data

def get_topic_distribution(comments_data):
    """
    Tính phân phối chủ đề từ bình luận đã gán nhãn
    
    Parameters:
    - comments_data: Danh sách bình luận đã gán chủ đề
    
    Returns:
    - Thông tin phân phối chủ đề
    """
    topic_counter = Counter()
    
    for comment in comments_data:
        topic = comment.get('topic', 'Khác')
        topic_counter[topic] += 1
    
    total_comments = len(comments_data)
    topic_distribution = [
        {
            'name': topic,
            'count': count,
            'percentage': round((count / total_comments) * 100, 1)
        }
        for topic, count in topic_counter.most_common()
    ]
    
    return topic_distribution

def analyze_article_topics(article_id, db_session, num_topics=DEFAULT_NUM_TOPICS, force_refresh=False):
    """
    Phân tích chủ đề cho một bài viết cụ thể
    
    Parameters:
    - article_id: ID của bài viết
    - db_session: Phiên làm việc cơ sở dữ liệu
    - num_topics: Số lượng chủ đề mong muốn
    - force_refresh: Có buộc cập nhật lại kết quả không
    
    Returns:
    - Kết quả phân tích chủ đề
    """
    from app.models import Article
    from analysis.lda_topic_modeler import analyze_article_topics_with_lda
    
    # Sử dụng LDA thay vì fallback
    return analyze_article_topics_with_lda(article_id, db_session, num_topics, force_refresh)

# Hàm chính để phân tích chủ đề - sử dụng LDA thay vì fallback
def analyze_topics(comments_data, num_topics=DEFAULT_NUM_TOPICS):
    """
    Phân tích chủ đề từ các bình luận 
    
    Parameters:
    - comments_data: Danh sách các bình luận cần phân tích
    - num_topics: Số lượng chủ đề mong muốn
    
    Returns:
    - Dictionary chứa thông tin về các chủ đề
    """
    from analysis.lda_topic_modeler import analyze_topics_with_lda
    return analyze_topics_with_lda(comments_data, num_topics)

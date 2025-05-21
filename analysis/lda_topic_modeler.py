#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import pickle
import numpy as np
from time import time
from collections import Counter

# Gensim
import gensim
from gensim import corpora
from gensim.models import LdaModel
from gensim.models.coherencemodel import CoherenceModel

# NLTK
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Scikit-learn
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

# Thư mục cache
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Tải dữ liệu cần thiết từ NLTK
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Danh sách stopwords tiếng Việt
VIETNAMESE_STOPWORDS = [
    'và', 'của', 'các', 'có', 'được', 'đã', 'trong', 'là', 'cho', 'này', 'những', 
    'với', 'không', 'về', 'như', 'một', 'để', 'đến', 'từ', 'phải', 'khi', 'cũng', 
    'theo', 'tại', 'vì', 'nhưng', 'ra', 'nếu', 'trên', 'đó', 'bị', 'vào', 'người', 
    'nên', 'sẽ', 'còn', 'năm', 'bởi', 'rằng', 'làm', 'thì', 'đi', 'mà', 'ở', 'lại', 
    'thế', 'tôi', 'mình', 'đây', 'có thể', 'chỉ', 'thôi', 'à', 'nào', 'vậy', 'ạ', 'cái',
    'ông', 'bà', 'anh', 'chị', 'em', 'hơn', 'quá', 'rồi', 'thật', 'rất', 'nữa', 'mới',
    'chưa', 'đang', 'nó', 'rồi', 'mấy', 'tất cả', 'thì', 'mới', 'lên', 'nhiều', 'hay',
    'cùng', 'vẫn', 'lúc', 'bao giờ', 'hiện'
]

def clean_text_for_lda(text):
    """
    Tiền xử lý văn bản cho mô hình LDA
    
    Parameters:
    - text: Văn bản cần tiền xử lý
    
    Returns:
    - Văn bản đã được tiền xử lý
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Chuyển về chữ thường
    text = text.lower()
    
    # Loại bỏ URL
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    
    # Loại bỏ email
    text = re.sub(r'\S+@\S+', ' ', text)
    
    # Loại bỏ ký tự đặc biệt và số
    text = re.sub(r'[^\w\s\.]', ' ', text)
    text = re.sub(r'\d+', ' ', text)
    
    # Loại bỏ khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def tokenize_text(text):
    """
    Tách từ cho văn bản tiếng Việt
    
    Parameters:
    - text: Văn bản cần tách từ
    
    Returns:
    - Danh sách các từ đã tách
    """
    if not text:
        return []
        
    # Tách từ đơn giản bằng khoảng trắng thay vì sử dụng NLTK
    # Điều này tránh các vấn đề với tokenize tiếng Việt
    words = text.split()
    
    # Loại bỏ stopwords
    words = [word for word in words if word not in VIETNAMESE_STOPWORDS and len(word) > 1]
    
    return words

def create_lda_model(texts, num_topics=5, passes=10):
    """
    Tạo mô hình LDA từ danh sách văn bản
    
    Parameters:
    - texts: Danh sách văn bản đã được tiền xử lý
    - num_topics: Số lượng chủ đề
    - passes: Số lần lặp trong quá trình huấn luyện
    
    Returns:
    - Mô hình LDA và từ điển
    """
    # Tokenize văn bản
    tokenized_texts = [tokenize_text(text) for text in texts]
    
    # Tạo từ điển
    dictionary = corpora.Dictionary(tokenized_texts)
    
    # Loại bỏ các từ xuất hiện quá ít hoặc quá nhiều
    dictionary.filter_extremes(no_below=2, no_above=0.9)
    
    # Tạo corpus
    corpus = [dictionary.doc2bow(text) for text in tokenized_texts]
    
    # Huấn luyện mô hình LDA
    lda_model = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=num_topics,
        passes=passes,
        alpha='auto',
        eta='auto',
        random_state=42
    )
    
    return lda_model, dictionary, corpus

def extract_topic_keywords(lda_model, num_words=10):
    """
    Trích xuất từ khóa cho mỗi chủ đề
    
    Parameters:
    - lda_model: Mô hình LDA
    - num_words: Số lượng từ khóa cho mỗi chủ đề
    
    Returns:
    - Danh sách từ khóa cho mỗi chủ đề
    """
    topics = []
    
    for topic_id in range(lda_model.num_topics):
        # Lấy các từ có trọng số cao nhất cho chủ đề
        top_words = lda_model.show_topic(topic_id, num_words)
        keywords = [word for word, _ in top_words]
        
        topics.append({
            'id': topic_id,
            'name': f"Chủ đề {topic_id + 1}",  # Tên mặc định
            'keywords': keywords,
            'percentage': 0  # Sẽ được cập nhật sau
        })
    
    return topics

def assign_topic_names(topics):
    """
    Gán tên có ý nghĩa cho các chủ đề dựa trên từ khóa
    
    Parameters:
    - topics: Danh sách chủ đề với từ khóa
    
    Returns:
    - Danh sách chủ đề với tên có ý nghĩa
    """
    # Từ điển ánh xạ các nhóm từ khóa với tên chủ đề
    # Có thể mở rộng danh sách này dựa trên kiến thức lĩnh vực
    topic_name_patterns = [
        {'keywords': ['giá', 'tiền', 'đồng', 'tỷ', 'triệu', 'usd', 'chi phí', 'đắt', 'rẻ', 'kinh tế', 'lãi', 'lỗ', 'đầu tư', 'thị trường'], 'name': 'Kinh tế & Tài chính'},
        {'keywords': ['chính', 'phủ', 'bộ', 'quốc hội', 'cơ quan', 'nhà nước', 'chính sách', 'đảng', 'lãnh đạo', 'cải cách', 'luật'], 'name': 'Chính trị & Chính sách'},
        {'keywords': ['bệnh', 'y tế', 'sức khỏe', 'thuốc', 'bệnh viện', 'bác sĩ', 'điều trị', 'covid', 'dịch', 'virus'], 'name': 'Y tế & Sức khỏe'},
        {'keywords': ['học', 'trường', 'sinh viên', 'giáo dục', 'đại học', 'giảng viên', 'học sinh', 'thi', 'điểm', 'lớp'], 'name': 'Giáo dục & Đào tạo'},
        {'keywords': ['công nghệ', 'kỹ thuật', 'internet', 'mạng', 'facebook', 'google', 'smartphone', 'app', 'máy tính', 'thiết bị'], 'name': 'Công nghệ & Kỹ thuật'},
        {'keywords': ['đội', 'bóng', 'cầu thủ', 'trận', 'thể thao', 'huấn luyện viên', 'thi đấu', 'vô địch', 'giải', 'thắng'], 'name': 'Thể thao'},
        {'keywords': ['du lịch', 'khách', 'dịch vụ', 'hotel', 'khách sạn', 'resort', 'tour', 'phục vụ', 'nghỉ dưỡng'], 'name': 'Du lịch & Dịch vụ'},
        {'keywords': ['nghệ sĩ', 'diễn viên', 'ca sĩ', 'âm nhạc', 'phim', 'hát', 'điện ảnh', 'giải trí', 'game', 'show'], 'name': 'Giải trí & Nghệ thuật'},
        {'keywords': ['tai nạn', 'cháy', 'cảnh sát', 'công an', 'tội phạm', 'pháp luật', 'tòa án', 'trộm', 'cướp', 'đâm'], 'name': 'Pháp luật & An ninh'},
        {'keywords': ['môi trường', 'ô nhiễm', 'rác', 'khí hậu', 'thiên tai', 'bão', 'lũ', 'lụt', 'biến đổi', 'xanh'], 'name': 'Môi trường & Thiên nhiên'},
        {'keywords': ['giao thông', 'đường', 'xe', 'ùn tắc', 'tai nạn', 'phương tiện', 'ô tô', 'xe máy', 'đi lại'], 'name': 'Giao thông & Vận tải'},
        {'keywords': ['đất', 'nhà', 'chung cư', 'dự án', 'bất động sản', 'xây dựng', 'căn hộ', 'quy hoạch', 'sở hữu'], 'name': 'Bất động sản & Nhà ở'},
        {'keywords': ['lương', 'việc làm', 'công việc', 'doanh nghiệp', 'công ty', 'nhân viên', 'sếp', 'thị trường', 'lao động'], 'name': 'Việc làm & Doanh nghiệp'},
        {'keywords': ['gia đình', 'con', 'vợ', 'chồng', 'bố', 'mẹ', 'em', 'nuôi', 'dạy', 'trẻ'], 'name': 'Gia đình & Nuôi dạy con'},
        {'keywords': ['trung quốc', 'mỹ', 'nga', 'châu âu', 'ngoại giao', 'quốc tế', 'chiến tranh', 'hòa bình', 'thế giới'], 'name': 'Quan hệ quốc tế'},
        {'keywords': ['facebook', 'tiktok', 'mạng xã hội', 'comment', 'chia sẻ', 'status', 'like', 'bình luận', 'viral'], 'name': 'Mạng xã hội'},
        {'keywords': ['thực phẩm', 'ăn', 'món', 'nhà hàng', 'quán', 'đồ ăn', 'nấu', 'ngon', 'hương vị'], 'name': 'Ẩm thực & Đồ ăn'},
        {'keywords': ['máy', 'hệ thống', 'lỗi', 'trục trặc', 'sự cố', 'bảo trì', 'cập nhật', 'vận hành'], 'name': 'Vấn đề kỹ thuật'},
        {'keywords': ['chất lượng', 'dịch vụ', 'khách hàng', 'phàn nàn', 'góp ý', 'phản hồi', 'trải nghiệm'], 'name': 'Dịch vụ khách hàng'},
        {'keywords': ['xin', 'giúp', 'hỏi', 'làm sao', 'vấn đề', 'thắc mắc', 'giải đáp', 'cần'], 'name': 'Hỏi đáp & Thắc mắc'}
    ]
    
    for topic in topics:
        best_match = None
        best_score = 0
        
        # Đếm số từ khóa trùng với mỗi mẫu
        for pattern in topic_name_patterns:
            # Đếm số từ khóa match
            matches = sum(1 for kw in topic['keywords'] if any(p_kw in kw for p_kw in pattern['keywords']))
            
            # Trọng số cho match (số match / tổng số từ khóa)
            score = matches / len(topic['keywords'])
            
            if score > best_score and score > 0.2:  # Yêu cầu ít nhất 20% match
                best_score = score
                best_match = pattern['name']
        
        # Nếu có match tốt, sử dụng tên đó
        if best_match:
            topic['name'] = best_match
    
    return topics

def update_topic_percentages(topics, document_topics):
    """
    Cập nhật thông tin phần trăm của mỗi chủ đề dựa trên phân phối tài liệu-chủ đề
    
    Parameters:
    - topics: Danh sách chủ đề
    - document_topics: Phân phối chủ đề trên các tài liệu
    
    Returns:
    - Danh sách chủ đề với phần trăm đã cập nhật
    """
    # Tính tổng phân phối cho mỗi chủ đề
    topic_counts = np.zeros(len(topics))
    
    for doc_topics in document_topics:
        # doc_topics là list các tuple (topic_id, probability)
        for topic_id, prob in doc_topics:
            topic_counts[topic_id] += prob
    
    # Chuẩn hóa để tổng bằng 100%
    total = np.sum(topic_counts)
    if total > 0:
        topic_percentages = (topic_counts / total) * 100
        
        # Cập nhật phần trăm cho mỗi chủ đề
        for i, topic in enumerate(topics):
            topic['percentage'] = round(topic_percentages[i], 1)
    
    return topics

def assign_topics_to_comments(comments_data, lda_model, dictionary, topics):
    """
    Gán chủ đề cho mỗi bình luận dựa trên mô hình LDA
    
    Parameters:
    - comments_data: Danh sách bình luận
    - lda_model: Mô hình LDA
    - dictionary: Từ điển Gensim
    - topics: Thông tin về các chủ đề
    
    Returns:
    - Danh sách bình luận với chủ đề được gán
    """
    # Ánh xạ topic_id sang tên chủ đề
    topic_id_to_name = {topic['id']: topic['name'] for topic in topics}
    
    for comment in comments_data:
        # Lấy nội dung bình luận
        text = comment.get('comment_text', '')
        if not text:
            comment['topic'] = 'Khác'
            continue
        
        # Tiền xử lý văn bản
        cleaned_text = clean_text_for_lda(text)
        
        # Tokenize
        tokens = tokenize_text(cleaned_text)
        
        # Chuyển đổi thành bow
        bow = dictionary.doc2bow(tokens)
        
        # Dự đoán chủ đề
        doc_topics = lda_model.get_document_topics(bow)
        
        # Nếu không có chủ đề nào được gán
        if not doc_topics:
            comment['topic'] = 'Khác'
            continue
        
        # Lấy chủ đề với xác suất cao nhất
        top_topic_id = max(doc_topics, key=lambda x: x[1])[0]
        
        # Gán tên chủ đề
        comment['topic'] = topic_id_to_name.get(top_topic_id, f'Chủ đề {top_topic_id + 1}')
    
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

def analyze_topics_with_lda(comments_data, num_topics=5):
    """
    Phân tích chủ đề từ bình luận sử dụng LDA
    
    Parameters:
    - comments_data: Danh sách bình luận
    - num_topics: Số lượng chủ đề
    
    Returns:
    - Kết quả phân tích chủ đề
    """
    if not comments_data:
        print("Không có bình luận để phân tích")
        return None
    
    # Tạo cache key
    cache_key = f"lda_topics_{hash(str(comments_data))}_{num_topics}"
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
    
    # Tiền xử lý dữ liệu
    print(f"Tiền xử lý {len(comments_data)} bình luận...")
    texts = [clean_text_for_lda(comment.get('comment_text', '')) for comment in comments_data]
    
    # Huấn luyện mô hình LDA
    print(f"Huấn luyện mô hình LDA với {num_topics} chủ đề...")
    t0 = time()
    lda_model, dictionary, corpus = create_lda_model(texts, num_topics=num_topics)
    print(f"Hoàn thành huấn luyện mô hình LDA trong {time() - t0:.2f} giây")
    
    # Trích xuất các từ khóa cho mỗi chủ đề
    topics = extract_topic_keywords(lda_model)
    
    # Gán tên có ý nghĩa cho các chủ đề
    topics = assign_topic_names(topics)
    
    # Cập nhật phần trăm cho mỗi chủ đề
    document_topics = [lda_model.get_document_topics(doc) for doc in corpus]
    topics = update_topic_percentages(topics, document_topics)
    
    # Tạo kết quả
    result = {
        'topics': topics
    }
    
    # Lưu vào cache
    with open(cache_file, 'wb') as f:
        pickle.dump(result, f)
        print(f"Đã lưu kết quả vào cache: {cache_file}")
    
    return result

def analyze_article_topics_with_lda(article_id, db_session, num_topics=5, force_refresh=False):
    """
    Phân tích chủ đề cho một bài viết sử dụng LDA
    
    Parameters:
    - article_id: ID của bài viết
    - db_session: Phiên làm việc cơ sở dữ liệu
    - num_topics: Số lượng chủ đề mong muốn
    - force_refresh: Có buộc cập nhật lại kết quả không
    
    Returns:
    - Kết quả phân tích chủ đề
    """
    from app.models import Article
    
    # Tạo cache key cho article
    cache_key = f"article_lda_topics_{article_id}_{num_topics}"
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    
    # Kiểm tra cache nếu không buộc làm mới
    if not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                cached_result = pickle.load(f)
                print(f"Đã tải kết quả phân tích chủ đề LDA cho bài viết {article_id} từ cache")
                return cached_result
        except Exception as e:
            print(f"Lỗi khi đọc cache: {e}")
    
    # Lấy bài viết và các bình luận
    article = db_session.get(Article, article_id)
    if not article:
        print(f"Không tìm thấy bài viết với ID {article_id}")
        return None
    
    # Lấy tất cả bình luận
    comments = article.comments.all()
    
    if not comments:
        print(f"Bài viết {article_id} không có bình luận để phân tích")
        return None
    
    # Chuyển đổi bình luận sang định dạng phù hợp để phân tích
    comments_data = []
    for comment in comments:
        comment_data = {
            'id': comment.id,
            'comment_text': comment.comment_text,
            'user_name': comment.user_name,
            'likes_count': comment.likes_count,
            'sentiment_label': comment.sentiment_label
        }
        comments_data.append(comment_data)
    
    print(f"Phân tích chủ đề LDA cho bài viết {article_id} với {len(comments_data)} bình luận...")
    
    # Phân tích chủ đề bằng LDA
    t0 = time()
    topics_result = analyze_topics_with_lda(comments_data, num_topics)
    
    if not topics_result:
        print(f"Không thể phân tích chủ đề cho bài viết {article_id}")
        return None
    
    # Tạo mô hình LDA để gán chủ đề cho các bình luận
    texts = [clean_text_for_lda(comment.get('comment_text', '')) for comment in comments_data]
    lda_model, dictionary, corpus = create_lda_model(texts, num_topics=num_topics)
    
    # Gán chủ đề cho các bình luận
    comments_with_topics = assign_topics_to_comments(
        comments_data, lda_model, dictionary, topics_result['topics']
    )
    
    # Tính phân phối chủ đề
    topic_distribution = get_topic_distribution(comments_with_topics)
    
    # Tạo kết quả cuối cùng
    final_result = {
        'article_id': article_id,
        'num_topics': num_topics,
        'topics': topics_result.get('topics', []),
        'topic_distribution': topic_distribution,
        'comments_with_topics': comments_with_topics,
        'processing_time': time() - t0,
        'timestamp': time()
    }
    
    # Lưu vào cache
    with open(cache_file, 'wb') as f:
        pickle.dump(final_result, f)
        print(f"Đã lưu kết quả phân tích chủ đề LDA cho bài viết {article_id} vào cache")
    
    return final_result

if __name__ == "__main__":
    # Test code sẽ được thêm ở đây
    print("LDA Topic Modeler cho VnExpress Analyzer") 
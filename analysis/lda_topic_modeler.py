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
from gensim.models import KeyedVectors

# NLTK
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Scikit-learn
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Thư mục cache
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Đường dẫn đến thư mục cache cho model
MODEL_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
if not os.path.exists(MODEL_CACHE_DIR):
    os.makedirs(MODEL_CACHE_DIR)

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

# Mô hình word embeddings tiếng Việt
WORD_EMBEDDING_MODEL = None
# Biến để theo dõi xem đã hiển thị thông báo chưa
MODEL_NOT_FOUND_MESSAGE_SHOWN = False

def load_word_embedding_model():
    """
    Tải mô hình word embeddings tiếng Việt
    """
    global WORD_EMBEDDING_MODEL, MODEL_NOT_FOUND_MESSAGE_SHOWN
    
    # Kiểm tra xem mô hình đã được tải chưa
    if WORD_EMBEDDING_MODEL is not None:
        return WORD_EMBEDDING_MODEL
    
    model_path = os.path.join(MODEL_CACHE_DIR, 'word2vec_vi.model')
    
    # Kiểm tra xem có file model đã lưu không
    if os.path.exists(model_path):
        try:
            print("Đang tải mô hình word embeddings tiếng Việt từ bộ nhớ cache...")
            WORD_EMBEDDING_MODEL = KeyedVectors.load(model_path)
            print(f"Đã tải mô hình với {len(WORD_EMBEDDING_MODEL.key_to_index)} từ vựng")
            return WORD_EMBEDDING_MODEL
        except Exception as e:
            if not MODEL_NOT_FOUND_MESSAGE_SHOWN:
                print(f"Lỗi khi tải mô hình: {e}")
                MODEL_NOT_FOUND_MESSAGE_SHOWN = True
    
    # Nếu không thể tạo được, dùng từ điển danh mục mặc định
    if not MODEL_NOT_FOUND_MESSAGE_SHOWN:
        print("Không tìm thấy mô hình word embeddings, sử dụng từ điển danh mục mặc định")
        MODEL_NOT_FOUND_MESSAGE_SHOWN = True
    
    WORD_EMBEDDING_MODEL = None
    return None

# Danh sách chủ đề cơ bản
TOPIC_CATEGORIES = [
    {"name": "Kinh tế & Tài chính", "keywords": ["giá", "tiền", "đồng", "tỷ", "triệu", "usd", "chi phí", "kinh tế", "đầu tư", "thị trường", "doanh nghiệp"]},
    {"name": "Chính trị & Chính sách", "keywords": ["chính phủ", "bộ", "quốc hội", "nhà nước", "chính sách", "đảng", "lãnh đạo", "pháp luật", "quy định"]},
    {"name": "Y tế & Sức khỏe", "keywords": ["bệnh", "y tế", "sức khỏe", "thuốc", "bệnh viện", "bác sĩ", "điều trị", "covid", "dịch", "virus"]},
    {"name": "Giáo dục & Đào tạo", "keywords": ["học", "trường", "sinh viên", "giáo dục", "đại học", "học sinh", "thi", "giáo viên", "đào tạo"]},
    {"name": "Công nghệ & Kỹ thuật", "keywords": ["công nghệ", "kỹ thuật", "internet", "mạng", "thiết bị", "phần mềm", "AI", "robot", "số hóa"]},
    {"name": "Thể thao", "keywords": ["đội", "bóng", "cầu thủ", "trận", "thể thao", "thi đấu", "vô địch", "giải", "thắng", "thua"]},
    {"name": "Du lịch & Dịch vụ", "keywords": ["du lịch", "khách", "dịch vụ", "khách sạn", "tour", "nghỉ dưỡng", "du khách", "điểm đến", "kỳ nghỉ"]},
    {"name": "Giải trí & Nghệ thuật", "keywords": ["nghệ sĩ", "diễn viên", "ca sĩ", "âm nhạc", "phim", "hát", "điện ảnh", "giải trí", "game", "show"]},
    {"name": "Pháp luật & An ninh", "keywords": ["tai nạn", "cảnh sát", "công an", "tội phạm", "pháp luật", "tòa án", "vụ án", "điều tra", "phạt"]},
    {"name": "Môi trường & Thiên nhiên", "keywords": ["môi trường", "ô nhiễm", "rác", "khí hậu", "thiên tai", "sinh thái", "bảo vệ", "tái chế", "tự nhiên"]},
    {"name": "Giao thông & Vận tải", "keywords": ["giao thông", "đường", "xe", "ùn tắc", "tai nạn", "phương tiện", "ô tô", "xe máy", "đi lại", "vận tải"]},
    {"name": "Bất động sản & Nhà ở", "keywords": ["đất", "nhà", "chung cư", "dự án", "bất động sản", "xây dựng", "căn hộ", "quy hoạch", "mua nhà", "giá đất"]},
    {"name": "Việc làm & Doanh nghiệp", "keywords": ["lương", "việc làm", "công việc", "doanh nghiệp", "công ty", "nhân viên", "lao động", "tuyển dụng", "nhân sự"]},
    {"name": "Gia đình & Nuôi dạy con", "keywords": ["gia đình", "con", "vợ", "chồng", "nuôi", "dạy", "trẻ", "con cái", "cha mẹ", "hôn nhân"]},
    {"name": "Quan hệ quốc tế", "keywords": ["trung quốc", "mỹ", "nga", "châu âu", "ngoại giao", "quốc tế", "thế giới", "hiệp định", "hợp tác", "xung đột"]},
    {"name": "Mạng xã hội", "keywords": ["facebook", "tiktok", "mạng xã hội", "chia sẻ", "like", "bình luận", "viral", "youtube", "video", "online"]},
    {"name": "Ẩm thực & Đồ ăn", "keywords": ["thực phẩm", "ăn", "món", "nhà hàng", "quán", "đồ ăn", "nấu", "ngon", "hương vị", "ẩm thực"]},
    {"name": "Vấn đề kỹ thuật", "keywords": ["máy", "hệ thống", "lỗi", "trục trặc", "sự cố", "bảo trì", "cập nhật", "vận hành", "kỹ thuật", "hỏng"]},
    {"name": "Dịch vụ khách hàng", "keywords": ["chất lượng", "dịch vụ", "khách hàng", "phàn nàn", "góp ý", "phản hồi", "trải nghiệm", "khiếu nại", "hài lòng"]},
    {"name": "Hỏi đáp & Thắc mắc", "keywords": ["xin", "giúp", "hỏi", "làm sao", "vấn đề", "thắc mắc", "giải đáp", "tư vấn", "câu hỏi"]},
    {"name": "Hàng không", "keywords": ["máy bay", "bay", "phi công", "hành khách", "sân bay", "cất cánh", "hạ cánh", "độ cao", "chuyến bay", "hàng không"]},
    {"name": "Thiết bị công nghệ", "keywords": ["điện thoại", "smartphone", "apple", "màn hình", "watch", "đồng hồ", "thông minh", "laptop", "tablet", "thiết bị"]}
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
    
    # Tách từ đơn giản bằng khoảng trắng vì không có underthesea
    words = text.split()
    
    # Lọc stopwords và từ ngắn
    result_tokens = []
    for word in words:
        if len(word) > 1 and word.lower() not in VIETNAMESE_STOPWORDS:
            result_tokens.append(word.lower())
    
    # Danh sách các cụm từ quan trọng cần giữ nguyên
    important_bigrams = []
    
    # Tự động tạo danh sách cụm từ quan trọng từ danh mục chủ đề
    for category in TOPIC_CATEGORIES:
        for keyword in category["keywords"]:
            if ' ' in keyword:
                important_bigrams.append(keyword.lower())
    
    # Bổ sung thêm một số cụm từ quan trọng khác
    additional_bigrams = [
        'độ cao', 'áp suất', 'điều áp', 'khí quyển', 'bình phi', 'sân bay',
        'đường băng', 'hộp đen', 'an toàn', 'bộ lạc', 'tín hiệu', 'nhà ga',
        'trạm thu phí', 'kẹt xe', 'đèn đỏ', 'đèn xanh', 'làn đường'
    ]
    
    important_bigrams.extend(additional_bigrams)
    
    # Kiểm tra nguyên văn bản ban đầu để tìm các cụm từ quan trọng
    for bigram in important_bigrams:
        if bigram in text.lower() and bigram not in result_tokens:
            result_tokens.append(bigram)
    
    return result_tokens

def create_lda_model(texts, num_topics=5, passes=15):
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
    dictionary.filter_extremes(no_below=2, no_above=0.85)
    
    # Tạo corpus
    corpus = [dictionary.doc2bow(text) for text in tokenized_texts]
    
    # Huấn luyện mô hình LDA với cấu hình tốt hơn cho việc phân biệt chủ đề
    lda_model = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=num_topics,
        passes=passes,
        alpha='asymmetric',  # Alpha không đối xứng giúp phân biệt chủ đề tốt hơn
        eta=0.01,            # Eta thấp hơn giúp các chủ đề rõ ràng hơn
        random_state=42,
        minimum_probability=0.0,  # Ngưỡng tối thiểu cho xác suất chủ đề
        iterations=100,           # Tăng số lần lặp để mô hình hội tụ tốt hơn
        decay=0.7                 # Tỷ lệ giảm dần của learning rate
    )
    
    return lda_model, dictionary, corpus

def extract_topic_keywords(lda_model, num_words=15):
    """
    Trích xuất từ khóa cho mỗi chủ đề
    
    Parameters:
    - lda_model: Mô hình LDA
    - num_words: Số lượng từ khóa cho mỗi chủ đề
    
    Returns:
    - Danh sách từ khóa cho mỗi chủ đề
    """
    topics = []
    all_keywords = []
    
    # Trích xuất từ khóa cho mỗi chủ đề
    for topic_id in range(lda_model.num_topics):
        # Lấy các từ có trọng số cao nhất cho chủ đề
        top_words = lda_model.show_topic(topic_id, num_words)
        keywords = [word for word, _ in top_words]
        all_keywords.extend(keywords)
        
        topics.append({
            'id': topic_id,
            'name': f"Chủ đề {topic_id + 1}",  # Tên mặc định
            'keywords': keywords,
            'raw_weights': [weight for _, weight in top_words],  # Lưu trọng số gốc
            'percentage': 0  # Sẽ được cập nhật sau
        })
    
    # Tìm từ khóa độc đáo cho mỗi chủ đề
    keyword_counts = Counter(all_keywords)
    
    for topic in topics:
        # Tính điểm độc đáo cho mỗi từ khóa
        unique_scores = []
        for i, word in enumerate(topic['keywords']):
            # Điểm độc đáo = trọng số gốc * (1 / số lần xuất hiện)
            uniqueness = topic['raw_weights'][i] * (1 / keyword_counts[word])
            unique_scores.append((word, uniqueness))
        
        # Sắp xếp lại từ khóa theo điểm độc đáo
        unique_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Lấy 10 từ khóa độc đáo nhất
        unique_keywords = [word for word, _ in unique_scores[:10]]
        
        # Kết hợp với 5 từ khóa có trọng số cao nhất
        top_weighted = [word for word, _ in sorted(zip(topic['keywords'], topic['raw_weights']), 
                                                 key=lambda x: x[1], reverse=True)[:5]]
        
        # Kết hợp hai danh sách và loại bỏ trùng lặp
        final_keywords = []
        for word in unique_keywords + top_weighted:
            if word not in final_keywords:
                final_keywords.append(word)
        
        # Cập nhật từ khóa
        topic['keywords'] = final_keywords[:num_words]
        
        # Xóa trọng số gốc khỏi kết quả cuối cùng
        del topic['raw_weights']
    
    return topics

def get_topic_vector(keywords):
    """
    Tạo vector biểu diễn cho một chủ đề dựa trên từ khóa
    
    Parameters:
    - keywords: Danh sách từ khóa của chủ đề
    
    Returns:
    - Vector biểu diễn chủ đề
    """
    model = load_word_embedding_model()
    if model is None:
        return None
        
    # Tạo vector cho chủ đề bằng cách trung bình các vector của từ khóa
    vectors = []
    for keyword in keywords:
        # Xử lý từ ghép (nhiều từ)
        if ' ' in keyword:
            words = keyword.split()
            word_vectors = []
            for word in words:
                if word in model:
                    word_vectors.append(model[word])
            if word_vectors:
                vectors.append(np.mean(word_vectors, axis=0))
        else:
            if keyword in model:
                vectors.append(model[keyword])
    
    if not vectors:
        return None
    
    # Trung bình các vector
    return np.mean(vectors, axis=0)

def get_auto_topic_name(keywords):
    """
    Tự động đề xuất tên chủ đề dựa trên từ khóa
    
    Parameters:
    - keywords: Danh sách từ khóa của chủ đề
    
    Returns:
    - Tên chủ đề
    """
    # Thêm tên chủ đề dự phòng đa dạng
    fallback_topic_names = [
        "Thời sự", "Thảo luận chung", "Ý kiến", "Đánh giá", "Nhận xét",
        "Góc nhìn", "Cộng đồng", "Tranh luận", "Quan điểm", "Phản hồi",
        "Bàn luận", "Tìm hiểu", "Đề xuất", "Câu chuyện", "Kinh nghiệm"
    ]
    
    # Đầu tiên, thử dùng word embeddings nếu có
    topic_vector = get_topic_vector(keywords)
    if topic_vector is not None:
        # Tính độ tương đồng cosine với các chủ đề đã biết
        similarities = []
        
        for category in TOPIC_CATEGORIES:
            category_vector = get_topic_vector(category["keywords"])
            if category_vector is not None:
                similarity = cosine_similarity([topic_vector], [category_vector])[0][0]
                similarities.append((category["name"], similarity))
        
        # Sắp xếp theo độ tương đồng giảm dần
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Lấy tên chủ đề có độ tương tự cao nhất nếu vượt ngưỡng
        if similarities and similarities[0][1] > 0.6:  # Tăng ngưỡng độ tương đồng
            return similarities[0][0]
    
    # Nếu không có mô hình word embeddings hoặc không tìm thấy chủ đề phù hợp
    # Sử dụng phương pháp tính điểm dựa trên từ khóa trùng lặp
    category_scores = []
    
    for category in TOPIC_CATEGORIES:
        matches = 0
        category_keywords = category["keywords"]
        
        # Tích lũy điểm khớp
        keyword_match_found = False
        for kw in keywords:
            if kw in category_keywords:
                matches += 3  # Tăng điểm cho trùng khớp chính xác
                keyword_match_found = True
            else:
                # Kiểm tra trùng một phần
                for cat_kw in category_keywords:
                    if kw in cat_kw or cat_kw in kw:
                        matches += 1
                        keyword_match_found = True
                        break
        
        # Nếu có ít nhất một từ khóa khớp, thêm vào danh sách ứng viên
        if keyword_match_found:
            # Tính điểm dựa trên tỷ lệ khớp và độ nổi bật của từ khóa
            score = matches / (len(keywords) + len(category_keywords))
            category_scores.append((category["name"], score))
    
    # Sắp xếp theo điểm giảm dần
    category_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Nếu có ít nhất một chủ đề với điểm đủ cao, sử dụng chủ đề đó
    if category_scores and category_scores[0][1] > 0.15:  # Tăng ngưỡng điểm tối thiểu
        return category_scores[0][0]
    
    # Nếu không tìm thấy chủ đề phù hợp, tạo tên từ từ khóa hoặc dùng tên dự phòng
    if len(keywords) >= 3:
        # Tạo tên từ 3 từ khóa đầu tiên nếu chúng đủ đa dạng
        if len(set([len(kw) for kw in keywords[:3]])) > 1:  # Kiểm tra độ đa dạng
            return f"Thảo luận: {', '.join(keywords[:3])}"
    
    # Sử dụng một tên dự phòng ngẫu nhiên
    import random
    return random.choice(fallback_topic_names)

def assign_topic_names(topics):
    """
    Gán tên có ý nghĩa cho các chủ đề dựa trên từ khóa
    
    Parameters:
    - topics: Danh sách chủ đề với từ khóa
    
    Returns:
    - Danh sách chủ đề với tên có ý nghĩa
    """
    # Tạo bản sao topics để lưu kết quả cuối cùng
    assigned_topics = []
    used_topic_names = set()
    topic_name_counter = {}
    
    # Danh sách hậu tố để đa dạng hóa tên chủ đề
    diverse_suffixes = [
        "chung", "nổi bật", "phổ biến", "thảo luận", "quan tâm", 
        "tranh luận", "đánh giá", "góc nhìn", "phản hồi", "bình luận"
    ]
    
    # Sắp xếp topics theo % giảm dần để ưu tiên đặt tên cho chủ đề nổi bật nhất
    sorted_topics = sorted(topics, key=lambda x: x.get('percentage', 0), reverse=True)
    
    # Phân tích trước các từ khóa phổ biến trong tất cả các chủ đề
    all_keywords = []
    for topic in sorted_topics:
        all_keywords.extend(topic['keywords'])
    
    keyword_counts = Counter(all_keywords)
    common_keywords = {word for word, count in keyword_counts.items() if count > 1}
    
    for idx, topic in enumerate(sorted_topics):
        # Lấy danh sách từ khóa của chủ đề, ưu tiên từ khóa độc đáo
        keywords = topic['keywords']
        unique_keywords = [kw for kw in keywords if kw not in common_keywords]
        
        # Ưu tiên sử dụng từ khóa độc đáo nếu có
        if unique_keywords:
            primary_keywords = unique_keywords
        else:
            primary_keywords = keywords
        
        # Tìm tên tự động cho chủ đề
        suggested_name = get_auto_topic_name(primary_keywords)
        
        # Theo dõi số lần sử dụng mỗi tên chủ đề
        if suggested_name not in topic_name_counter:
            topic_name_counter[suggested_name] = 0
        topic_name_counter[suggested_name] += 1
        
        # Đảm bảo tên không trùng lặp
        if suggested_name in used_topic_names:
            base_name = suggested_name
            
            # Nếu là lần thứ 2, thử sửa tên thứ nhất
            if topic_name_counter[suggested_name] == 2:
                # Tìm chủ đề đầu tiên có cùng tên và sửa
                for t in assigned_topics:
                    if t['name'] == base_name:
                        # Đổi tên chủ đề đầu tiên
                        suffix1 = diverse_suffixes[0]
                        t['name'] = f"{base_name} - {suffix1}"
                        used_topic_names.remove(base_name)
                        used_topic_names.add(t['name'])
                        break
                
                # Đặt tên cho chủ đề hiện tại
                suffix2 = diverse_suffixes[1] if len(diverse_suffixes) > 1 else "khác"
                suggested_name = f"{base_name} - {suffix2}"
            else:
                # Từ lần thứ 3 trở đi, sử dụng một tên khác hoàn toàn
                if idx < len(diverse_suffixes):
                    suggested_name = f"{base_name} - {diverse_suffixes[idx]}"
                else:
                    # Tạo tên từ các từ khóa độc đáo
                    suggested_name = f"Chủ đề: {', '.join(primary_keywords[:2])}"
        
        # Nếu tên vẫn trùng lặp, thêm số thứ tự
        counter = 1
        original_name = suggested_name
        while suggested_name in used_topic_names:
            suggested_name = f"{original_name} ({counter})"
            counter += 1
        
        # Tạo bản sao topic để thêm vào assigned_topics
        new_topic = topic.copy()
        new_topic['name'] = suggested_name
        used_topic_names.add(suggested_name)
        assigned_topics.append(new_topic)
    
    # Trả lại danh sách topics đã được gán tên theo thứ tự ban đầu
    result = []
    topic_id_to_assigned = {topic['id']: topic for topic in assigned_topics}
    
    for original_topic in topics:
        result.append(topic_id_to_assigned[original_topic['id']])
    
    return result

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
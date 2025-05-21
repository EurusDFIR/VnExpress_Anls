# Đã loại bỏ toàn bộ code liên quan đến phân tích sentiment và model học máy.
# File này hiện chỉ là placeholder, không còn chức năng nào.

# Nếu cần dùng lại sentiment, hãy khôi phục code từ phiên bản trước.

import numpy as np
from collections import Counter
from app.models import Comment
import os
import pickle

# Đường dẫn đến mô hình đã lưu
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "sentiment_svm.pkl")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl")

# Biến lưu trữ toàn cục cho model và vectorizer
model = None
vectorizer = None

def load_model():
    """
    Nạp mô hình và vectorizer đã huấn luyện
    """
    global model, vectorizer
    
    try:
        # Kiểm tra file mô hình tồn tại
        if not (os.path.exists(MODEL_PATH) and os.path.exists(VECTORIZER_PATH)):
            print("Chưa huấn luyện mô hình. Sử dụng phương pháp dựa trên từ điển.")
            return False
        
        # Nạp mô hình đã huấn luyện
        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)
        with open(VECTORIZER_PATH, 'rb') as f:
            vectorizer = pickle.load(f)
        
        print("Đã nạp mô hình phân loại cảm xúc thành công")
        return True
    except Exception as e:
        print(f"Lỗi khi nạp mô hình: {e}")
        return False

# Nạp mô hình khi module được import
use_model = load_model()

# Danh sách từ khoá cảm xúc (sử dụng khi không có mô hình)
POSITIVE_WORDS = [
    'tốt', 'hay', 'tuyệt', 'thích', 'đẹp', 'tuyệt vời', 'xuất sắc', 'rất hay',
    'tuyệt hảo', 'đúng', 'tuyệt đẹp', 'đúng đắn', 'hài lòng', 'ủng hộ', 'nên', 
    'yêu thích', 'đồng ý', 'tốt nhất', 'trọn vẹn', 'hữu ích', 'ấn tượng', 'hiệu quả',
    'chất lượng', 'ngon', 'ổn', 'hoàn hảo', 'suôn sẻ', 'mừng', 'vui', 'hạnh phúc'
]

NEGATIVE_WORDS = [
    'kém', 'tệ', 'dở', 'không thích', 'xấu', 'tệ hại', 'không hay', 'không tốt',
    'kém chất lượng', 'thất vọng', 'buồn', 'sai', 'không đúng', 'không đáng', 'không nên',
    'không đồng ý', 'phản đối', 'vô lý', 'tồi tệ', 'chán', 'không hài lòng', 'không ổn',
    'không hiệu quả', 'yếu kém', 'lỗi', 'không phù hợp', 'không đáng tin', 'không suôn sẻ',
    'lộn xộn', 'không xứng đáng', 'không đáng giá', 'vô dụng', 'phí phạm'
]

def analyze_lexicon_based(comment_text):
    """
    Phân tích cảm xúc dựa trên từ điển từ khoá
    """
    try:
        comment_text = comment_text.lower()
        
        # Đếm số từ tích cực và tiêu cực
        positive_count = sum(1 for word in POSITIVE_WORDS if word in comment_text)
        negative_count = sum(1 for word in NEGATIVE_WORDS if word in comment_text)
        
        # Tính điểm cảm xúc
        if positive_count > negative_count:
            label = 'Positive'
            score = min(0.9, 0.5 + (positive_count - negative_count) * 0.1)
        elif negative_count > positive_count:
            label = 'Negative'
            score = max(-0.9, -0.5 - (negative_count - positive_count) * 0.1)
        else:
            # Nếu số lượng bằng nhau hoặc không tìm thấy từ cảm xúc
            label = 'Neutral'
            score = 0.0
            
        return label, score
    except Exception as e:
        print(f"Lỗi khi phân tích cảm xúc (lexicon): {e}")
        return 'Neutral', 0.0

def preprocess_text(text):
    """
    Tiền xử lý văn bản đơn giản
    """
    if not isinstance(text, str):
        return ""
    
    # Chuyển về chữ thường
    text = text.lower()
    
    # Các bước tiền xử lý khác có thể thêm vào sau
    
    return text

def analyze_comment_sentiment(comment_text):
    """
    Phân tích cảm xúc của văn bản bình luận
    Sử dụng mô hình đã huấn luyện nếu có, ngược lại sử dụng phương pháp từ điển
    """
    try:
        # Nếu mô hình đã được nạp, sử dụng mô hình
        if use_model and model is not None and vectorizer is not None:
            # Tiền xử lý văn bản
            text = preprocess_text(comment_text)
            
            # Chuyển văn bản thành vector TF-IDF
            text_tfidf = vectorizer.transform([text])
            
            # Dự đoán nhãn cảm xúc
            label = model.predict(text_tfidf)[0]
            
            # Tính điểm cảm xúc từ decision_function hoặc predict_proba
            if hasattr(model, 'predict_proba'):
                probas = model.predict_proba(text_tfidf)[0]
                class_indices = {cls: idx for idx, cls in enumerate(model.classes_)}
                
                # Sử dụng các điểm cố định cho từng lớp để giảm thiểu lỗi phân loại
                if label == "Positive":
                    score = 0.7  # Điểm cố định cho tích cực
                elif label == "Negative":
                    score = -0.7  # Điểm cố định cho tiêu cực
                else:
                    score = 0.0  # Điểm cố định cho trung lập
            else:
                # Fallback nếu model không có predict_proba
                if label == "Positive":
                    score = 0.7
                elif label == "Negative":
                    score = -0.7
                else:
                    score = 0.0
                
            return label, score
        else:
            # Nếu không có mô hình, sử dụng phương pháp dựa trên từ điển
            return analyze_lexicon_based(comment_text)
    except Exception as e:
        print(f"Lỗi khi phân tích cảm xúc: {e}")
        return 'Neutral', 0.0

def analyze_article_comments(article_id, db_session):
    """
    Phân tích tất cả bình luận cho một bài viết và cập nhật trong cơ sở dữ liệu
    Trả về thống kê cảm xúc
    """
    comments = db_session.query(Comment).filter_by(article_id=article_id).all()
    
    if not comments:
        return {
            "positive": 0,
            "negative": 0,
            "neutral": 100,
            "total_comments": 0
        }
    
    # Phân tích từng bình luận và cập nhật trong cơ sở dữ liệu
    for comment in comments:
        if not comment.sentiment_label:  # Chỉ phân tích nếu chưa có nhãn
            label, score = analyze_comment_sentiment(comment.comment_text)
            comment.sentiment_label = label
            comment.sentiment_score_comment = score
    
    # Lưu thay đổi vào cơ sở dữ liệu
    db_session.commit()
    
    # Tính toán thống kê
    sentiment_counter = Counter([c.sentiment_label for c in comments if c.sentiment_label])
    total_comments = len(comments)
    
    sentiment_data = {
        "positive": round(100 * sentiment_counter.get("Positive", 0) / total_comments, 1) if total_comments else 0,
        "negative": round(100 * sentiment_counter.get("Negative", 0) / total_comments, 1) if total_comments else 0,
        "neutral": round(100 * sentiment_counter.get("Neutral", 0) / total_comments, 1) if total_comments else 0,
        "total_comments": total_comments
    }
    
    return sentiment_data

def get_comment_sentiment_counts(article_id, db_session):
    """
    Lấy số lượng bình luận cho mỗi nhãn cảm xúc của một bài viết
    """
    comments = db_session.query(Comment).filter_by(article_id=article_id).all()
    
    if not comments:
        return {
            "Positive": 0,
            "Negative": 0,
            "Neutral": 0,
            "total": 0
        }
    
    # Đếm cảm xúc
    sentiment_counter = Counter([c.sentiment_label for c in comments if c.sentiment_label])
    
    return {
        "Positive": sentiment_counter.get("Positive", 0),
        "Negative": sentiment_counter.get("Negative", 0),
        "Neutral": sentiment_counter.get("Neutral", 0),
        "total": len(comments)
    }


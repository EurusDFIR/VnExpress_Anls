#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import classification_report, accuracy_score
import matplotlib.pyplot as plt

# Đường dẫn đến mô hình đã lưu
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, "sentiment_svm.pkl")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl")
EXCEL_FILE_PATH = os.path.join(os.path.dirname(__file__), "sentiment.xlsx")

def preprocess_text(text):
    """
    Tiền xử lý văn bản đơn giản
    """
    if not isinstance(text, str):
        return ""
    
    # Chuyển về chữ thường
    text = text.lower()
    
    # Các bước tiền xử lý khác có thể thêm vào sau (loại bỏ dấu câu, stopwords, v.v.)
    
    return text

def train_sentiment_model():
    """
    Huấn luyện mô hình phân loại cảm xúc từ dữ liệu được gán nhãn
    """
    try:
        # Đọc file Excel chứa dữ liệu gán nhãn
        print(f"Đang đọc dữ liệu từ {EXCEL_FILE_PATH}")
        try:
            data = pd.read_excel(EXCEL_FILE_PATH)
            
            # Kiểm tra và hiển thị thông tin dữ liệu
            if 'comment_text' not in data.columns or 'sentiment_label' not in data.columns:
                print("Lỗi: File Excel không có cột 'comment_text' hoặc 'sentiment_label'")
                print(f"Các cột hiện có: {data.columns.tolist()}")
                # Tạo dữ liệu mẫu thay thế
                data = create_sample_data()
        except Exception as e:
            print(f"Không thể đọc file Excel: {e}")
            # Tạo dữ liệu mẫu thay thế
            data = create_sample_data()
        
        # Loại bỏ các hàng không có văn bản hoặc nhãn
        data = data.dropna(subset=['comment_text', 'sentiment_label'])
        
        # Nếu dữ liệu quá ít, thêm dữ liệu mẫu
        if len(data) < 30:
            print("Dữ liệu quá ít, thêm dữ liệu mẫu...")
            sample_data = create_sample_data()
            data = pd.concat([data, sample_data], ignore_index=True)
        
        print(f"Số lượng mẫu dữ liệu: {len(data)}")
        
        # Hiển thị phân phối nhãn
        label_counts = data['sentiment_label'].value_counts()
        print("Phân phối nhãn:")
        print(label_counts)
        
        # Tiền xử lý dữ liệu
        X = data['comment_text'].apply(preprocess_text)
        y = data['sentiment_label']
        
        # Xác định test_size dựa trên kích thước dữ liệu
        test_size = 0.2  # Mặc định 20%
        if len(data) < 20:  # Nếu dữ liệu quá nhỏ
            test_size = 1 / len(data)  # Chỉ lấy 1 mẫu để kiểm tra
        
        # Chia tập dữ liệu
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y if len(data) >= 10 else None
        )
        
        print(f"Số lượng mẫu huấn luyện: {len(X_train)}, Số lượng mẫu kiểm tra: {len(X_test)}")
        
        # Vectorize dữ liệu sử dụng TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=5000,
            min_df=1,  # Đổi thành 1 vì dữ liệu ít
            max_df=0.95,
            ngram_range=(1, 2)
        )
        
        X_train_tfidf = vectorizer.fit_transform(X_train)
        X_test_tfidf = vectorizer.transform(X_test)
        
        # Huấn luyện mô hình SVM
        model = SVC(
            kernel='linear',
            C=1.0,
            class_weight='balanced',
            probability=True
        )
        
        print("Đang huấn luyện mô hình SVM...")
        model.fit(X_train_tfidf, y_train)
        
        # Đánh giá mô hình
        y_pred = model.predict(X_test_tfidf)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Độ chính xác: {accuracy:.4f}")
        
        # In báo cáo phân loại
        print("\nBáo cáo phân loại:")
        print(classification_report(y_test, y_pred, zero_division=0))
        
        # Lưu mô hình và vectorizer
        print(f"Lưu mô hình vào {MODEL_PATH}")
        with open(MODEL_PATH, 'wb') as f:
            pickle.dump(model, f)
        
        print(f"Lưu vectorizer vào {VECTORIZER_PATH}")
        with open(VECTORIZER_PATH, 'wb') as f:
            pickle.dump(vectorizer, f)
        
        print("Đã huấn luyện và lưu mô hình thành công!")
        return True
        
    except Exception as e:
        print(f"Lỗi khi huấn luyện mô hình: {e}")
        return False

def create_sample_data():
    """
    Tạo dữ liệu mẫu cho huấn luyện mô hình
    """
    # Mẫu tích cực
    positive_samples = [
        'Sản phẩm tuyệt vời, tôi rất thích',
        'Dịch vụ rất tốt, nhân viên thân thiện',
        'Bài viết hay, cảm ơn tác giả',
        'Tuyệt vời quá',
        'Tôi rất thích sản phẩm này',
        'Chất lượng tốt, đáng mua',
        'Tôi sẽ mua lại lần nữa',
        'Đáng đồng tiền bát gạo',
        'Sản phẩm vượt quá mong đợi của tôi',
        'Chất lượng tuyệt hảo',
        'Rất hài lòng với trải nghiệm',
        'Phục vụ chu đáo, nhiệt tình',
        'Giá cả hợp lý, chất lượng tốt',
        'Tôi sẽ giới thiệu cho bạn bè',
        'Rất hài lòng về dịch vụ',
        'Đúng với những gì được quảng cáo',
        'Sản phẩm xứng đáng với giá tiền',
        'Nhân viên rất chuyên nghiệp và tận tâm',
        'Trải nghiệm mua sắm tuyệt vời',
        'Giao hàng nhanh, đóng gói cẩn thận'
    ]
    
    # Mẫu tiêu cực
    negative_samples = [
        'Dịch vụ quá tệ, không bao giờ quay lại nữa',
        'Thật là thất vọng với chất lượng',
        'Giá quá đắt so với chất lượng',
        'Sản phẩm tệ quá',
        'Không nên mua',
        'Chất lượng kém',
        'Dịch vụ tồi tệ',
        'Thất vọng với sản phẩm',
        'Không đáng giá tiền',
        'Tôi sẽ không bao giờ quay lại',
        'Trải nghiệm tệ hại',
        'Phí thời gian và tiền bạc',
        'Nhân viên thô lỗ và không nhiệt tình',
        'Sản phẩm giao không đúng với mô tả',
        'Chất lượng quá tệ so với giá tiền',
        'Dịch vụ khách hàng kém',
        'Không đáp ứng được yêu cầu cơ bản',
        'Sản phẩm hỏng ngay sau khi mua',
        'Tôi cảm thấy bị lừa',
        'Không bao giờ tin tưởng nữa'
    ]
    
    # Mẫu trung lập
    neutral_samples = [
        'Hôm nay thời tiết khá mát mẻ',
        'Bạn nói sao chứ ba mẹ tôi không bao giờ ngồi kể tôi chỉ học bài. Ba mẹ cũng không mỗi ngày cằn dằn ra đường không được vứt rác bữa bãi, nhưng từ nhỏ đến lớn tôi đều tự ý thức học, ra đường từ nhỏ đến lớn đều không vứt rác, giữ gìn môi trường. Nên đừng nói do phụ huynh dạy, do bản tính con người nữa.',
        'Sản phẩm bình thường',
        'Không có gì đặc biệt',
        'Tạm được',
        'Có ưu điểm và nhược điểm',
        'Cần cải thiện thêm',
        'Đang cân nhắc',
        'Không tốt không xấu',
        'Chưa có ý kiến rõ ràng',
        'Cần thêm thời gian để đánh giá',
        'Sản phẩm ở mức trung bình',
        'Không thể nói tốt hay xấu',
        'Giá cả phải chăng, chất lượng trung bình',
        'Không có gì nổi bật để khen ngợi hay phàn nàn',
        'Dịch vụ cơ bản đáp ứng nhu cầu',
        'Tôi có một số thắc mắc chưa được giải đáp',
        'Mới dùng nên chưa thể đánh giá chi tiết',
        'Cần thêm tính năng để tốt hơn',
        'Không trên kỳ vọng nhưng cũng không dưới'
    ]
    
    # Tạo DataFrame
    comments = []
    labels = []
    
    # Thêm mẫu tích cực
    comments.extend(positive_samples)
    labels.extend(['Positive'] * len(positive_samples))
    
    # Thêm mẫu tiêu cực
    comments.extend(negative_samples)
    labels.extend(['Negative'] * len(negative_samples))
    
    # Thêm mẫu trung lập
    comments.extend(neutral_samples)
    labels.extend(['Neutral'] * len(neutral_samples))
    
    # Tạo DataFrame
    sample_data = pd.DataFrame({
        'comment_text': comments,
        'sentiment_label': labels
    })
    
    return sample_data

def test_sentiment_model():
    """
    Kiểm tra mô hình đã huấn luyện với một số ví dụ
    """
    try:
        # Nạp mô hình và vectorizer
        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)
        with open(VECTORIZER_PATH, 'rb') as f:
            vectorizer = pickle.load(f)
        
        # Một số ví dụ để kiểm tra
        test_comments = [
            "Sản phẩm tuyệt vời, tôi rất thích",
            "Dịch vụ quá tệ, không bao giờ quay lại nữa",
            "Bạn nói sao chứ ba mẹ tôi không bao giờ ngồi kể tôi chỉ học bài. Ba mẹ cũng không mỗi ngày cằn dằn ra đường không được vứt rác bữa bãi, nhưng từ nhỏ đến lớn tôi đều tự ý thức học, ra đường từ nhỏ đến lớn đều không vứt rác, giữ gìn môi trường. Nên đừng nói do phụ huynh dạy, do bản tính con người nữa.",
            "Hôm nay thời tiết khá mát mẻ"
        ]
        
        # Tiền xử lý và dự đoán
        processed_comments = [preprocess_text(comment) for comment in test_comments]
        X_test_tfidf = vectorizer.transform(processed_comments)
        
        # Lấy nhãn dự đoán
        y_pred = model.predict(X_test_tfidf)
        
        # Lấy điểm xác suất
        probas = model.predict_proba(X_test_tfidf)
        
        # Decision function (khoảng cách đến hyperplane)
        distances = model.decision_function(X_test_tfidf)
        
        # Hiển thị kết quả
        print("\nKết quả kiểm tra mô hình:")
        for i, comment in enumerate(test_comments):
            print(f"\nBình luận: {comment}")
            print(f"Nhãn dự đoán: {y_pred[i]}")
            
            # Tính điểm sentiment từ decision function
            # Nếu mô hình nhị phân, chuyển đổi giá trị decision function
            # Nếu mô hình đa lớp, lấy giá trị cao nhất
            if hasattr(model, 'classes_') and len(model.classes_) > 2:
                class_indices = {cls: idx for idx, cls in enumerate(model.classes_)}
                if 'Positive' in class_indices and 'Negative' in class_indices:
                    pos_idx = class_indices['Positive']
                    neg_idx = class_indices['Negative']
                    
                    if y_pred[i] == 'Positive':
                        sentiment_score = max(0.3, min(0.9, probas[i][pos_idx]))
                    elif y_pred[i] == 'Negative':
                        sentiment_score = max(-0.9, min(-0.3, -probas[i][neg_idx]))
                    else:  # Neutral
                        # Nếu xác suất của positive và negative gần nhau, thì là neutral
                        sentiment_score = 0.0
                else:
                    # Fallback nếu không có các nhãn chuẩn
                    sentiment_score = 0.0
            else:
                # Chuẩn hóa giá trị decision function
                if len(distances.shape) > 1:
                    dist = distances[i][0]  # Lấy giá trị đầu tiên nếu là ma trận
                else:
                    dist = distances[i]
                
                sentiment_score = max(-0.9, min(0.9, dist / 3))  # Chuẩn hóa giá trị
            
            print(f"Điểm cảm xúc: {sentiment_score:.2f}")
            
            # Hiển thị xác suất của từng lớp
            if hasattr(model, 'classes_'):
                for cls, prob in zip(model.classes_, probas[i]):
                    print(f"  {cls}: {prob:.4f}")
        
        return True
    except Exception as e:
        print(f"Lỗi khi kiểm tra mô hình: {e}")
        return False

if __name__ == "__main__":
    train_sentiment_model()
    test_sentiment_model() 
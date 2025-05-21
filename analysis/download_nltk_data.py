#!/usr/bin/env python
# -*- coding: utf-8 -*-

import nltk
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

print("Bắt đầu tải xuống dữ liệu NLTK cần thiết...")

# Tải xuống punkt cho phân đoạn văn bản
print("Đang tải xuống punkt...")
nltk.download('punkt')

# Tải xuống stopwords chuẩn
print("Đang tải xuống stopwords...")
nltk.download('stopwords')

print("Hoàn thành tải xuống dữ liệu NLTK!") 
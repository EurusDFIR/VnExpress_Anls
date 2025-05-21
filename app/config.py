import os

# Kiểm tra xem đang chạy trên Render.com không
IS_PRODUCTION = os.environ.get('RENDER') == 'true'

# Cấu hình tính năng
ENABLE_SCRAPING = not IS_PRODUCTION  # Tắt scraping trên production

# Thông báo khi scraping bị vô hiệu hóa
SCRAPING_DISABLED_MESSAGE = "Tính năng scraping bị vô hiệu hóa trên môi trường production. Sử dụng phiên bản chạy cục bộ để sử dụng tính năng này." 
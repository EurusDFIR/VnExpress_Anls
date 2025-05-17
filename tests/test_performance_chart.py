import matplotlib.pyplot as plt
import pandas as pd

# Dữ liệu thử nghiệm hiệu suất
# Các cột: Lần thử nghiệm, Cấu hình chính, Tổng thời gian (s), Số lượng bình luận đã lưu, Bài viết
perf_data = [
    ["Lần 1 (Ban đầu)", "Click trả lời tuần tự, Chờ đợi cố định", 28.75, 134, "ban-gai-khong-chi..."],
    ["Lần 2 (Lỗi chờ)", "Click trả lời song song, Chờ số lượng comment_item (sai)", 32.06, 142, "vo-cu-muon-cham-dut..."],
    ["Lần 3 (Nhanh nhất)", "Click trả lời song song, Chờ số lượng nút giảm", 9.69, 167, "bi-nghi-phan-boi..."],
    ["Lần 4 (Ổn định)", "Click trả lời song song, Chờ số lượng nút giảm", 18.33, 233, "thay-chet-ma-khong-the-cuu..."]
]

df = pd.DataFrame(perf_data, columns=["Lần thử nghiệm", "Cấu hình chính", "Tổng thời gian (s)", "Số lượng bình luận", "Bài viết"])

# Vẽ biểu đồ cột so sánh thời gian
plt.figure(figsize=(10, 6))
bars = plt.bar(df["Lần thử nghiệm"], df["Tổng thời gian (s)"], color=['#8888ff', '#ff8888', '#88ff88', '#ffd700'])
plt.ylabel("Tổng thời gian Playwright (giây)")
plt.title("So sánh hiệu suất các lần tối ưu scraping bình luận VnExpress")
for i, (v, c) in enumerate(zip(df["Tổng thời gian (s)"], df["Số lượng bình luận"])):
    plt.text(i, v + 0.5, f"{v}\n({c} cmt)", ha='center', va='bottom', fontsize=10)
plt.tight_layout()
plt.savefig("performance_comparison.png")
plt.show()

# Vẽ biểu đồ đường so sánh số lượng bình luận đã lưu
plt.figure(figsize=(10, 6))
plt.plot(df["Lần thử nghiệm"], df["Số lượng bình luận"], marker='o', color='tab:blue')
plt.ylabel("Số lượng bình luận đã lưu")
plt.title("Số lượng bình luận đã lưu qua các lần tối ưu")
for i, v in enumerate(df["Số lượng bình luận"]):
    plt.text(i, v + 2, f"{v}", ha='center', va='bottom', fontsize=10)
plt.tight_layout()
plt.savefig("comment_count_comparison.png")
plt.show()

# In bảng dữ liệu
print(df.to_markdown(index=False))

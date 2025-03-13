import requests
from collections import Counter
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from datetime import datetime
import pytz
import os

from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# Token của bạn
TOKEN = "7629529039:AAGd6Ul3xyZoyzrJ0WyVdG-iWsNgcUFgqgc"

# Danh sách API
API_URLS = {
    "Hà Nội": "http://vip.manycai.com/K267d27554a0f78/hnc-100.json",
    "Quảng Ninh": "http://vip.manycai.com/K267d27554a0f78/gnic-100.json",
    "Bắc Ninh": "http://vip.manycai.com/K267d27554a0f78/bnc-100.json",
    "Hải Phòng": "http://vip.manycai.com/K267d27554a0f78/hfc-100.json",
    "Nam Định": "http://vip.manycai.com/K267d27554a0f78/ndc-100.json",
    "Thái Bình": "http://vip.manycai.com/K267d27554a0f78/tpc-100.json"
}

WEEKDAY_TO_PROVINCE = {
    0: "Hà Nội",
    1: "Quảng Ninh",
    2: "Bắc Ninh",
    3: "Hà Nội",
    4: "Hải Phòng",
    5: "Nam Định",
    6: "Thái Bình"
}

# Lấy dữ liệu từ API
def get_lottery_data():
    all_data = []
    seen_issues = set()
    for province, url in API_URLS.items():
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for entry in response.json():
                    if entry["issue"] not in seen_issues:
                        all_data.append(entry)
                        seen_issues.add(entry["issue"])
            else:
                print(f"Lỗi: Không thể truy cập API {province} (mã lỗi: {response.status_code})")
        except Exception as e:
            print(f"Lỗi khi gọi API {province}: {e}")
    return all_data

# Phân tích dữ liệu
def analyze_data(data):
    if not data:
        return "000", []

    # Sắp xếp dữ liệu theo ngày mở thưởng (mới nhất -> cũ nhất)
    data_sorted = sorted(data, key=lambda x: x["opendate"], reverse=True)

    # Lấy toàn bộ 3 số cuối từ tất cả các kỳ quay
    all_tails = [''.join(entry["code"]["code"].split(','))[-3:] for entry in data_sorted]

    # Đếm tần suất xuất hiện
    freq_all = Counter(all_tails)

    # Lưu lại lịch sử xuất hiện của từng số theo thứ tự ngày
    history = {}
    for idx, tail in enumerate(all_tails):
        if tail not in history:
            history[tail] = []
        history[tail].append(idx)  # Lưu vị trí của lần xuất hiện

    # Tính khoảng cách trung bình giữa các lần xuất hiện của từng số
    avg_gaps = {}
    for tail, indices in history.items():
        if len(indices) > 1:  # Phải xuất hiện ít nhất 2 lần để tính khoảng cách
            gaps = [indices[i] - indices[i - 1] for i in range(1, len(indices))]
            avg_gaps[tail] = sum(gaps) / len(gaps)  # Trung bình khoảng cách giữa các lần xuất hiện
        else:
            avg_gaps[tail] = float('inf')  # Nếu chỉ xuất hiện 1 lần, đặt khoảng cách rất lớn

    # Kết hợp tần suất và chu kỳ lặp lại để tính điểm dự đoán
    scores = {tail: freq_all[tail] / (avg_gaps[tail] + 1) for tail in freq_all}

    # Tìm điểm cao nhất trong tất cả các số
    max_score = max(scores.values()) if scores else 0

    # Lấy tất cả các số có điểm cao nhất
    top_numbers = [tail for tail, score in scores.items() if score == max_score]

    # Nếu không có số nào, trả về "000"
    predicted_tail = top_numbers[0] if top_numbers else "000"

    return predicted_tail, top_numbers


# Lệnh /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Chào bạn! Tôi là bot dự đoán xổ số miền Bắc.\n"
        "Gửi /predict để nhận 5 số 3 chữ số dự đoán cho giải đặc biệt hôm nay."
    )

# Lệnh /predict
async def predict(update: Update, context: CallbackContext):
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    today = datetime.now(tz)
    today_province = WEEKDAY_TO_PROVINCE[today.weekday()]
    today_date = today.strftime("%Y-%m-%d")
    
    data = get_lottery_data()
    predicted_tail, top_numbers = analyze_data(data)
    
    response = (
        f"Dự đoán cho {today_province} ({today_date}):\n"
        f"3 chữ số cuối giải đặc biệt chính: {predicted_tail}\n"
        "số 3 chữ số dự đoán tiềm năng:\n" + "\n".join(top_numbers) + "\n"   )
    await update.message.reply_text(response)

# Chạy bot
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("predict", predict))
    
    print("Bot đã khởi động!")
    application.run_polling()


if __name__ == "__main__":
    # Chạy bot Telegram
    main()
    
    # Lấy PORT từ biến môi trường (Render yêu cầu PORT)
    port = int(os.environ.get("PORT", 5000))
    
    # Chạy Flask trên cổng PORT (để Render nhận diện)
    app.run(host="0.0.0.0", port=port)

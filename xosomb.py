import math
import requests
from collections import Counter
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from datetime import datetime
import pytz
import os
import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

TOKEN = "7629529039:AAGd6Ul3xyZoyzrJ0WyVdG-iWsNgcUFgqgc"

API_URLS = {
    "Hà Nội": "http://vip.manycai.com/K267d27554a0f78/hnc-100.json",
    "Quảng Ninh": "http://vip.manycai.com/K267d27554a0f78/gnic-100.json",
    "Bắc Ninh": "http://vip.manycai.com/K267d27554a0f78/bnc-100.json",
    "Hải Phòng": "http://vip.manycai.com/K267d27554a0f78/hfc-100.json",
    "Nam Định": "http://vip.manycai.com/K267d27554a0f78/ndc-100.json",
    "Thái Bình": "http://vip.manycai.com/K267d27554a0f78/tpc-100.json"
}

WEEKDAY_TO_PROVINCE = {
    0: "Hà Nội", 1: "Quảng Ninh", 2: "Bắc Ninh", 3: "Hà Nội",
    4: "Hải Phòng", 5: "Nam Định", 6: "Thái Bình"
}

# Lấy dữ liệu từ API cho tỉnh cụ thể
def get_lottery_data(province):
    data = []
    url = API_URLS[province]
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
        else:
            print(f"Lỗi: Không thể truy cập API {province} (mã lỗi: {response.status_code})")
    except Exception as e:
        print(f"Lỗi khi gọi API {province}: {e}")
    return data

# Phân tích dữ liệu
def analyze_data(data, decay_rate=0.2):
    if not data:
        return "000", []

    data_sorted = sorted(data, key=lambda x: x["opendate"], reverse=True)
    all_tails = [''.join(entry["code"]["code"].split(','))[-3:] for entry in data_sorted]

    # Tần suất có trọng số
    weighted_freq = Counter()
    for idx, tail in enumerate(all_tails):
        weight = math.exp(-decay_rate * idx)
        weighted_freq[tail] += weight

    # Khoảng cách trung bình
    history = {}
    for idx, tail in enumerate(all_tails):
        if tail not in history:
            history[tail] = []
        history[tail].append(idx)

    avg_gaps = {}
    for tail, indices in history.items():
        if len(indices) > 1:
            gaps = [indices[i] - indices[i - 1] for i in range(1, len(indices))]
            avg_gaps[tail] = sum(gaps) / len(gaps)
        else:
            avg_gaps[tail] = float('inf')

    # Tính điểm
    scores = {tail: weighted_freq[tail] / (avg_gaps[tail] + 1) for tail in weighted_freq}

    # Top 3 số nóng (dựa trên weighted_freq)
    hot_numbers = [tail for tail, _ in weighted_freq.most_common(3)]
    # Top 2 số lạnh (dựa trên avg_gaps lớn)
    cold_numbers = [tail for tail, gap in sorted(avg_gaps.items(), key=lambda x: x[1], reverse=True) if tail in weighted_freq][:2]
    
    top_numbers = hot_numbers + cold_numbers
    predicted_tail = hot_numbers[0] if hot_numbers else "000"
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
    
    data = get_lottery_data(today_province)  # Chỉ lấy dữ liệu tỉnh hôm nay
    predicted_tail, top_numbers = analyze_data(data, decay_rate=0.2)
    
    response = (
        f"Dự đoán cho {today_province} ({today_date}):\n"
        f"3 chữ số cuối giải đặc biệt chính: {predicted_tail}\n"
        "Số 3 chữ số dự đoán tiềm năng:\n" + "\n".join(top_numbers) + "\n"
    )
    await update.message.reply_text(response)

# Chạy bot
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("predict", predict))
    print("Bot đã khởi động!")
    application.run_polling()

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    main()
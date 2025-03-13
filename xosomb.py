import requests
from collections import Counter
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from datetime import datetime
import pytz

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
            avg_gaps[tail] = 1000  # Gán số lớn nếu chỉ xuất hiện 1 lần (ít có khả năng lặp lại)

    # Kết hợp tần suất và chu kỳ lặp lại để tính điểm dự đoán
    scores = {}
    for tail in freq_all:
        scores[tail] = freq_all[tail] / (avg_gaps[tail] + 1)  # Tránh chia cho 0

    # Chọn ra 5 số có điểm cao nhất
    top_five = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]

    # Lấy số có điểm cao nhất làm số dự đoán chính
    predicted_tail = top_five[0][0] if top_five else "000"

    return predicted_tail, [tail for tail, _ in top_five]


# Tạo 5 số 3 chữ số
def generate_three_digit_numbers(predicted_tail, top_five):
    numbers = [predicted_tail]
    for tail in top_five:
        if tail != predicted_tail and len(numbers) < 5:
            numbers.append(tail)
    
    digits = list(predicted_tail)
    while len(numbers) < 5:
        new_number = digits.copy()
        pos = random.randint(0, 2)
        new_digit = str(random.randint(0, 9))
        new_number[pos] = new_digit
        new_number = ''.join(new_number)
        if new_number not in numbers:
            numbers.append(new_number)
    
    return numbers

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
    predicted_tail, top_five = analyze_data(data)
    numbers = generate_three_digit_numbers(predicted_tail, top_five)
    
    response = (
        f"Dự đoán cho {today_province} ({today_date}):\n"
        f"3 chữ số cuối giải đặc biệt chính: {predicted_tail}\n"
        "5 số 3 chữ số dự đoán:\n" + "\n".join(numbers) +
        f"\n\nTop 5 dãy 3 số tiềm năng: {', '.join(top_five)}"
    )
    await update.message.reply_text(response)

# Chạy bot
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("predict", predict))
    
    print("Bot đã khởi động!")
    application.run_polling()

if __name__ == "__main__":
    main()

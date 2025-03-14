import random
import requests
from collections import Counter
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from datetime import datetime
import pytz
import os
import threading
from flask import Flask
from openai import OpenAI

app = Flask(__name__)

TOKEN = "7629529039:AAGd6Ul3xyZoyzrJ0WyVdG-iWsNgcUFgqgc"
XAI_API_KEY = "xai-bCAnQDsXHUDJbxk5H0tg5dklrk9zgNckG8uHHBXsPiSmso7XFmDFfAfkJCma1T5ncevsv1xudih5fj8z"

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

client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

TAROT_CARDS = [
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
    "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
    "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance",
    "The Devil", "The Tower", "The Star", "The Moon", "The Sun",
    "Judgement", "The World"
]

def get_lottery_data():
    combined_data = []
    for province, url in API_URLS.items():
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                combined_data.extend(data)  # Kết hợp dữ liệu từ tất cả các tỉnh
                print(f"Đã lấy dữ liệu từ {province}")
            else:
                print(f"Lỗi: Không thể truy cập API {province} (mã lỗi: {response.status_code})")
        except Exception as e:
            print(f"Lỗi khi gọi API {province}: {e}")
    return combined_data


def analyze_data(data, recent_exclusion=2, num_predictions=5):
    if not data:
        return "000", []

    # Sắp xếp dữ liệu theo ngày, mới nhất trước
    data_sorted = sorted(data, key=lambda x: x["opendate"], reverse=True)
    all_tails = [''.join(entry["code"]["code"].split(','))[-3:] for entry in data_sorted]

    # Loại bỏ các kết quả từ `recent_exclusion` kỳ gần nhất
    recent_tails = set(all_tails[:recent_exclusion])
    analysis_tails = all_tails[recent_exclusion:]  # Dữ liệu phân tích

    if not analysis_tails:
        return "000", []

    # Tính lịch sử xuất hiện và khoảng cách
    history = {}
    for idx, tail in enumerate(all_tails):
        if tail not in history:
            history[tail] = []
        history[tail].append(idx)

    # Tính khoảng cách trung bình và độ lệch (variance) của khoảng cách
    stats = {}
    for tail, indices in history.items():
        if len(indices) > 1:
            gaps = [indices[i] - indices[i - 1] for i in range(1, len(indices))]
            avg_gap = sum(gaps) / len(gaps)
            variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps) if len(gaps) > 1 else 0
            stats[tail] = {
                "avg_gap": avg_gap,
                "variance": variance,
                "last_appearance": min(indices),  # Lần xuất hiện gần nhất
                "frequency": len(indices)
            }
        else:
            stats[tail] = {"avg_gap": float('inf'), "variance": 0, "last_appearance": indices[0], "frequency": 1}

    # Lọc các số tiềm năng dựa trên tiêu chí
    candidates = [tail for tail in stats if tail not in recent_tails]

    # Điểm số (score) cho mỗi số dựa trên các yếu tố
    scored_candidates = []
    for tail in candidates:
        s = stats[tail]
        # Điểm dựa trên: 
        # - Khoảng cách trung bình (lâu chưa về thì điểm cao hơn)
        # - Độ lệch thấp (chu kỳ ổn định thì đáng tin hơn)
        # - Tần suất vừa phải (không quá ít, không quá nhiều)
        score = (s["avg_gap"] / (max([stats[t]["avg_gap"] for t in candidates]) + 1)) * 0.4 + \
                (1 / (s["variance"] + 1)) * 0.3 + \
                (min(s["frequency"], 10) / 10) * 0.3  # Giới hạn tần suất tối đa để tránh bias
        scored_candidates.append((tail, score))

    # Sắp xếp theo điểm số
    scored_candidates.sort(key=lambda x: x[1], reverse=True)

    # Chọn top candidates
    top_candidates = [tail for tail, _ in scored_candidates[:max(10, num_predictions * 2)]]

    # Chọn ngẫu nhiên từ top candidates để tránh thiên kiến quá mức
    random.seed()  # Có thể dùng thời gian hiện tại làm seed nếu muốn
    top_numbers = random.sample(top_candidates, min(num_predictions, len(top_candidates)))
    predicted_tail = top_numbers[0] if top_numbers else "000"

    return predicted_tail, top_numbers


async def tarot(update: Update, context: CallbackContext):
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    # Chọn ngẫu nhiên 3 lá bài
    random.seed()
    drawn_cards = random.sample(TAROT_CARDS, 3)
    
    # Tạo prompt cho xAI
    prompt = (
        f"Tôi đã rút 3 lá bài Tarot cho một người dùng vào lúc {current_time}:\n"
        f"- Quá khứ: {drawn_cards[0]}\n"
        f"- Hiện tại: {drawn_cards[1]}\n"
        f"- Tương lai: {drawn_cards[2]}\n"
        "Hãy giải thích ngắn gọn nhưng sâu sắc ý nghĩa của các lá bài này theo từng vị trí, "
        "kèm theo lời khuyên tích cực cho người nhận. Viết bằng tiếng Việt, mỗi phần khoảng 2-3 câu."
    )
    
    try:
        # Gọi API xAI
        completion = client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {"role": "system", "content": "Bạn là một chuyên gia Tarot thông thái và tích cực."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        # Lấy phản hồi từ xAI
        response = completion.choices[0].message.content
        
        # Gửi phản hồi cho người dùng
        await update.message.reply_text(response)
        
    except Exception as e:
        await update.message.reply_text(
            f"Rút bài Tarot thành công nhưng giải thích gặp lỗi: {str(e)}\n"
            f"Các lá bài của bạn:\n"
            f"Quá khứ: {drawn_cards[0]}\n"
            f"Hiện tại: {drawn_cards[1]}\n"
            f"Tương lai: {drawn_cards[2]}"
        )

@app.route('/')
def web_predict():
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    today = datetime.now(tz)
    today_province = WEEKDAY_TO_PROVINCE[today.weekday()]
    today_date = today.strftime("%Y-%m-%d")
    
    data = get_lottery_data()
    if not data:
        return "<h1>Lỗi: Không lấy được dữ liệu!</h1>"

    predicted_tail, top_numbers = analyze_data(data)
    
    html = f"""
    <h1>Dự đoán xổ số {today_province} ({today_date})</h1>
    <h2>3 chữ số cuối giải đặc biệt chính: {predicted_tail}</h2>
    <h3>Số 3 chữ số dự đoán tiềm năng:</h3>
    <ul>
    """
    for num in top_numbers:
        html += f"<li>{num}</li>"
    html += "</ul>"
    return html

# Telegram bot
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Chào bạn! Tôi là bot dự đoán xổ số và bói bài Tarot miền Bắc.\n"
        "Gửi /predict để nhận 5 số 3 chữ số dự đoán cho giải đặc biệt hôm nay.\n"
        "Gửi /tarot để xem bói bài Tarot (Quá khứ - Hiện tại - Tương lai)."
    )

async def predict(update: Update, context: CallbackContext):
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    today = datetime.now(tz)
    today_province = WEEKDAY_TO_PROVINCE[today.weekday()]
    today_date = today.strftime("%Y-%m-%d")
    
    data = get_lottery_data()
    if not data:
        await update.message.reply_text(f"Không lấy được dữ liệu cho {today_province} hôm nay!")
        return
    
    predicted_tail, top_numbers = analyze_data(data)
    
    response = (
        f"Dự đoán cho {today_province} ({today_date}):\n"
        f"3 chữ số cuối giải đặc biệt chính: {predicted_tail}\n"
        "Số 3 chữ số dự đoán tiềm năng:\n" + "\n".join(top_numbers) + "\n"
    )
    await update.message.reply_text(response)

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("predict", predict))
    application.add_handler(CommandHandler("tarot", tarot))
    print("Bot đã khởi động!")
    application.run_polling()

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    main()
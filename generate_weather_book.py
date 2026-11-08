import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont

# 1. 取得新北中和天氣 (座標: 24.998, 121.503)
url = "https://api.open-meteo.com/v1/forecast?latitude=24.998&longitude=121.503&current=temperature_2m,weather_code&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto"
res = requests.get(url, timeout=10).json()

cur_temp = round(res["current"]["temperature_2m"])
cur_code = res["current"]["weather_code"]

def get_desc(code):
    if code == 0: return "晴朗"
    if code <= 3: return "多雲"
    if 51 <= code <= 67: return "降雨"
    if 80 <= code <= 82: return "短暫陣雨"
    if code >= 95: return "雷陣雨"
    return "陰天"

# 2. 建立符合 Kindle 螢幕解析度的黑白畫布 (以常見的 1072x1448 為例，支援大部分 300ppi 機型)
WIDTH, HEIGHT = 1072, 1448
img = Image.new("L", (WIDTH, HEIGHT), color=255)
draw = ImageDraw.Draw(img)

# 下載開源思源黑體 (確保中文正常顯示)
font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Bold.otf"
if not os.path.exists("font.otf"):
    font_data = requests.get(font_url).content
    with open("font.otf", "wb") as f:
        f.write(font_data)

font_xl = ImageFont.truetype("font.otf", 130)
font_lg = ImageFont.truetype("font.otf", 64)
font_md = ImageFont.truetype("font.otf", 44)
font_sm = ImageFont.truetype("font.otf", 34)

# 繪製日期與當前天氣
now = datetime.now()
days = ["一", "二", "三", "四", "五", "六", "日"]
date_str = f"{now.month}月{now.day}日 星期{days[now.weekday()]}"

draw.text((80, 100), "新北中和", fill=0, font=font_lg)
draw.text((80, 190), date_str, fill=0, font=font_md)

draw.text((80, 280), f"{cur_temp}°C", fill=0, font=font_xl)
draw.text((450, 340), get_desc(cur_code), fill=0, font=font_lg)

# 分隔線
draw.line([(80, 480), (WIDTH - 80, 480)], fill=0, width=4)
draw.text((80, 520), "未來一週天氣預報", fill=0, font=font_md)

# 繪製未來一週列表
daily = res["daily"]
y = 600
for i in range(len(daily["time"])):
    d_obj = datetime.strptime(daily["time"][i], "%Y-%m-%d")
    day_label = "今天" if i == 0 else f"週{days[d_obj.weekday()]}"
    date_label = f"{d_obj.month}/{d_obj.day}"
    desc = get_desc(daily["weather_code"][i])
    t_min = round(daily["temperature_2m_min"][i])
    t_max = round(daily["temperature_2m_max"][i])

    draw.text((80, y), f"{day_label} ({date_label})", fill=0, font=font_sm)
    draw.text((480, y), desc, fill=0, font=font_sm)
    draw.text((820, y), f"{t_min}° ~ {t_max}°C", fill=0, font=font_sm)
    draw.line([(80, y + 65), (WIDTH - 80, y + 65)], fill=200, width=1)
    y += 95

img.save("cover.jpg", "JPEG", quality=95)

# 3. 打包成極簡 EPUB (將 cover.jpg 設為唯一封面)
from ebooklib import epub
book = epub.EpubBook()
book.set_identifier("kindle-weather-zhonghe")
book.set_title("今日中和天氣")
book.set_language("zh-TW")
book.add_author("Weather Bot")

with open("cover.jpg", "rb") as f:
    book.set_cover("cover.jpg", f.read())

c1 = epub.EpubHtml(title="Weather", file_name="chap_1.xhtml", lang="zh-TW")
c1.content = '<html><body><img src="cover.jpg" style="width:100%;height:100%;" /></body></html>'
book.add_item(c1)
book.spine = ["cover", c1]

epub.write_epub("weather.epub", book)

# 4. 寄出信件至 Kindle
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PASS = os.environ["GMAIL_APP_PASS"]
KINDLE_MAIL = os.environ["KINDLE_EMAIL"]

msg = EmailMessage()
msg["Subject"] = "今日中和天氣更新"
msg["From"] = GMAIL_USER
msg["To"] = KINDLE_MAIL

with open("weather.epub", "rb") as f:
    msg.add_attachment(f.read(), maintype="application", subtype="epub+zip", filename="weather.epub")

with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
    server.login(GMAIL_USER, GMAIL_PASS)
    server.send_message(msg)

print("天氣 EPUB 已成功寄送至 Kindle！")

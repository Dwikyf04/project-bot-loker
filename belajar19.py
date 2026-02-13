import pandas as pd
import os
import requests
import sqlite3
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
TOKEN_BOT = os.environ.get("TOKEN_BOT")
if not TOKEN_BOT:
    TOKEN_BOT = "8229915508:AAHPlilEvzoPcDYusI2vKTxPeXFk5pWtG0A" 
ID_CHAT = os.environ.get("ID_CHAT")
if not ID_CHAT:    
    ID_CHAT = "1180963687"
def kirim_telegram(judul, perusahaan, link, lokasi):
    """
    Fungsi untuk mengirim pesan ke Telegram
    """
    try:
        pesan = f"🔥 <b>LOKER BARU TERDETEKSI!</b> 🔥\n\n" \
                f"💼 <b>Posisi:</b> {judul}\n" \
                f"🏢 <b>PT:</b> {perusahaan}\n" \
                f"📍 <b>Lokasi:</b> {lokasi}\n" \
                f"🔗 <a href='{link}'>Lamar Disini</a>"
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        data = {
            "chat_id": ID_CHAT,
            "text": pesan,
            "parse_mode": "HTML" # Supaya bisa pakai huruf tebal/link
        }
        requests.post(url, data=data)
        print(f"📨 Pesan terkirim: {judul}")
    except Exception as e:
        print(f"❌ Gagal kirim Telegram: {e}")
        
conn = sqlite3.connect("loker_data_scientist.db")
cursor = conn.cursor()
cursor.execute(""" CREATE TABLE IF NOT EXISTS loker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    link TEXT,
    company TEXT,
    lokasi TEXT
    );
""")
conn.commit()

url = "https://www.loker.id/cari-lowongan-kerja?q=perpustakaan+HR+data"
response = requests.get(url)
# print(response.text)

header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0;x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
response = requests.get(url, headers=header)

print(response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

# print(soup.prettify()[:2000])
# print(soup.prettify())

quote_boxes = soup.find_all("article")
print(f"Ditemukan {len(quote_boxes)} lowongan!")
data_loker = []
for box in quote_boxes:    
    element_judul = box.find("h3")
    title = element_judul.text.strip()
    
    element_link = box.find("a")
    if element_link:
            link_raw = element_link["href"]
            # Jika link diawali garis miring (/), kita tambahkan domain utamanya
            if link_raw.startswith("/"):
                link = "https://www.loker.id" + link_raw
            else:
                link = link_raw
    else:
            link = "No Link"

    element_company = box.find("span", class_='text-sm text-secondary-500')
    company = element_company.text.strip() if element_company else "Perusahaan tidak tersedia"

    element_lokasi = box.find("span", class_="mt-0.5")
    lokasi = element_lokasi.text.strip() if element_lokasi else "Lokasi tidak tersedia"
    data_loker.append({"title": title, "link": link, "company": company, "lokasi": lokasi})
    # Cek apakah loker sudah ada di database
    cursor.execute("SELECT link FROM loker WHERE link = ?", (link,))
    result = cursor.fetchone()
   
# df = pd.DataFrame(data_loker)
# df.to_csv("loker_data_scientist.csv", index=False)
# print(df)
    if result is None:
        print(f"Save: {title}")
        cursor.execute("INSERT INTO loker (title, link, company, lokasi) VALUES (?, ?, ?, ?)", (title, link, company, lokasi))
        # Simpan ke DB (INSERT INTO...)
        conn.commit()
        kirim_telegram(title, company, link, lokasi)
        # Masukkan ke list untuk dikirim notif nanti
        data_loker.append({
            "title": title, "link": link, "company": company, "lokasi": lokasi})
        time.sleep(2)  # Delay 2 detik antara pengiriman pesan    
    else:
        print(f"Loker lama dilewati: {title}")

print("="*30)
print(f"Total Loker yang AKAN dikirim ke Telegram:: {len(data_loker)}")
conn.close()

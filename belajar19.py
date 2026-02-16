import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
import time
import sys
import os

# Konfigurasi agar log aman
sys.stdout.reconfigure(encoding='utf-8')

# --- KONFIGURASI ---
TOKEN_BOT = os.environ.get("TOKEN_BOT") # Pastikan token aman di Secrets
DB_NAME = "loker_data_scientist.db"

# --- 1. FUNGSI DATABASE (Loker & Pelanggan) ---
def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabel 1: Untuk menyimpan Loker agar tidak duplikat
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judul TEXT,
            perusahaan TEXT,
            link TEXT UNIQUE,
            tanggal_scrape TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabel 2: Untuk menyimpan User/Pelanggan (BARU!)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id TEXT PRIMARY KEY,
            tanggal_join TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    return conn

# --- 2. FUNGSI CEK PELANGGAN BARU (Kotak Surat) ---
def cek_pelanggan_baru(conn):
    print("📬 Mengecek pelanggan baru...")
    url = f"https://api.telegram.org/bot{TOKEN_BOT}/getUpdates"
    
    try:
        response = requests.get(url).json()
        if "result" in response:
            cursor = conn.cursor()
            jumlah_baru = 0
            
            for update in response["result"]:
                # Cek apakah ini pesan chat biasa
                if "message" in update and "chat" in update["message"]:
                    chat_id = str(update["message"]["chat"]["id"])
                    nama = update["message"]["chat"].get("first_name", "User")
                    
                    # Masukkan ke Database (IGNORE kalau sudah ada)
                    try:
                        cursor.execute("INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)", (chat_id,))
                        if cursor.rowcount > 0:
                            print(f"➕ Pelanggan Baru: {nama} ({chat_id})")
                            jumlah_baru += 1
                    except Exception as e:
                        print(f"Error database user: {e}")
            
            conn.commit()
            print(f"✅ Total pelanggan baru hari ini: {jumlah_baru}")
            
    except Exception as e:
        print(f"⚠️ Gagal cek updates: {e}")

# --- 3. FUNGSI KIRIM KE SEMUA PELANGGAN ---
def kirim_telegram_massal(conn, judul, perusahaan, link, lokasi):
    cursor = conn.cursor()
    # Ambil semua ID dari tabel subscribers
    cursor.execute("SELECT chat_id FROM subscribers")
    users = cursor.fetchall()
    
    if not users:
        print("❌ Belum ada pelanggan terdaftar.")
        return

    pesan = f"🔥 <b>LOKER BARU TERDETEKSI!</b> 🔥\n\n" \
            f"💼 <b>Posisi:</b> {judul}\n" \
            f"🏢 <b>PT:</b> {perusahaan}\n" \
            f"📍 <b>Lokasi:</b> {lokasi}\n" \
            f"🔗 <a href='{link}'>Lamar Disini</a>"

    print(f"🚀 Mengirim info ke {len(users)} orang...")
    
    for user in users:
        chat_id = user[0]
        url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": pesan,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, data=data)
        except Exception as e:
            print(f"Gagal kirim ke {chat_id}: {e}")

# --- 4. MAIN PROGRAM ---
def job_hunter():
    conn = setup_database()
    
    # Langkah A: Cek dulu siapa yang chat bot kemarin
    cek_pelanggan_baru(conn) 
    
    # Langkah B: Mulai Scraping
    print("🕵️‍♂️ Memulai pencarian kerja...")
    url = "https://www.loker.id/cari-lowongan-kerja?q=data%20analyst&lokasi=0"
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        job_boxes = soup.find_all("div", class_="job-box")

        cursor = conn.cursor()
        
        for box in job_boxes:
            try:
                title = box.find("h3", class_="media-heading").text.strip()
                company = box.find("div", class_="company-name").text.strip()
                table = box.find("table")
                location = table.find_all("tr")[1].find_all("td")[1].text.strip()
                
                element_link = box.find("a")
                if element_link:
                    link_raw = element_link["href"]
                    link = "https://www.loker.id" + link_raw if link_raw.startswith("/") else link_raw
                else:
                    link = "No Link"

                # Cek Database Loker
                cursor.execute("SELECT link FROM loker WHERE link = ?", (link,))
                result = cursor.fetchone()

                if result is None:
                    print(f"✨ Loker Baru: {title}")
                    # Simpan Loker
                    cursor.execute("INSERT INTO loker (judul, perusahaan, link) VALUES (?, ?, ?)", (title, company, link))
                    conn.commit()
                    
                    # Kirim ke SEMUA Pelanggan
                    kirim_telegram_massal(conn, title, company, link, location)
                else:
                    print(f"⏭️ SKIP: {title} (Sudah ada)")
                    
            except Exception as e:
                print(f"Error per box: {e}")
                continue
                
    except Exception as e:
        print(f"Error utama scraping: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    job_hunter()
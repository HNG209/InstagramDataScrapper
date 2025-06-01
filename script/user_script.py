import instaloader
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import json
import threading
from dotenv import load_dotenv
import os

# Tải thông tin từ file .env
load_dotenv()

# Cài đặt Instaloader
L = instaloader.Instaloader()

# Đăng nhập
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")
L.login(USERNAME, PASSWORD)

# Biến toàn cục lưu đường dẫn file được chọn
selected_file = None


# Hàm lấy dữ liệu profile
def get_profile_data(username):
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        data = {
            "username": profile.username,
            "fullname": profile.full_name,
            "followers": profile.followers,
            "followees": profile.followees,
            "posts": profile.mediacount,
            "is_private": profile.is_private,
            "is_verified": profile.is_verified
        }
        return data
    except Exception as e:
        print(f"Failed to get data for {username}: {e}")
        return None


# Hàm chọn file bằng filedialog
def choose_file():
    global selected_file
    file_path = filedialog.askopenfilename(
        title="Chọn file usernames",
        filetypes=(("Text Files", "*.txt"), ("All Files", "*.*"))
    )
    if file_path:
        selected_file = file_path
        file_label.config(text=f"Đã chọn file: {file_path}")  # Hiển thị đường dẫn file đã chọn
    else:
        file_label.config(text="Chưa chọn file nào.")


# Hàm xử lý chạy chính
def process_usernames():
    try:
        global selected_file
        if not selected_file:
            progress_label.config(text="Lỗi: Chưa chọn file usernames!")
            return
        
        # Đọc danh sách usernames từ file đã chọn
        with open(selected_file, 'r') as f:
            usernames = f.read().splitlines()
        
        num_users = min(len(usernames), 10000)  # Lấy tối đa 10,000 usernames
        results = []

        # Vòng lặp xử lý từng username
        for i, user in enumerate(usernames[:num_users]):
            data = get_profile_data(user)
            if data:
                results.append(data)

            # Tính toán % hoàn thành
            progress = int((i + 1) / num_users * 100)
            progress_var.set(progress)
            progress_label.config(text=f"Đang xử lý: {i+1}/{num_users} ({progress}%)")
            progress_bar.update()  # Cập nhật giao diện

        # Lưu kết quả vào file JSON
        with open('user_data.json', 'w') as f:
            json.dump(results, f, indent=4)
        
        progress_label.config(text="Hoàn thành!")
    
    except Exception as e:
        progress_label.config(text=f"Lỗi: {e}")


# Hàm xử lý chạy script trong thread (để không treo GUI)
def start_processing():
    threading.Thread(target=process_usernames).start()


# Tạo giao diện Tkinter
root = tk.Tk()
root.title("Instagram Data Scraper")
root.geometry("500x300")

# Nhãn tiêu đề
title_label = tk.Label(root, text="Instagram Scraper", font=("Arial", 16))
title_label.pack(pady=10)

# Nút để chọn file
file_button = tk.Button(root, text="Chọn file usernames", command=choose_file)
file_button.pack(pady=5)

# Nhãn hiển thị file đã chọn
file_label = tk.Label(root, text="Chưa chọn file nào.", font=("Arial", 10))
file_label.pack(pady=5)

# Thanh tiến trình
progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate", variable=progress_var)
progress_bar.pack(pady=10)

# Nhãn trạng thái
progress_label = tk.Label(root, text="Bấm 'Bắt đầu' để chạy", font=("Arial", 12))
progress_label.pack(pady=10)

# Nút bắt đầu
start_button = tk.Button(root, text="Bắt đầu", command=start_processing)
start_button.pack(pady=10)

# Chạy giao diện
root.mainloop()
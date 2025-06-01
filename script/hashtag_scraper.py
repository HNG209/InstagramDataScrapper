import time
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os
import threading
import tkinter as tk
from tkinter import ttk
import pickle

# Tải thông tin từ file .env
load_dotenv()

# Lấy thông tin từ file .env
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

HASHTAG = os.getenv("HASHTAG")
MAX_USERS = int(os.getenv("MAX_USERS", 10))  # Lấy giá trị mặc định là 10

# Biến toàn cục cho thread và trạng thái hủy
driver = None
stop_requested = False


def save_cookies(driver, filepath="cookies.pkl"):
    with open(filepath, "wb") as file:
        pickle.dump(driver.get_cookies(), file)

def load_cookies(driver, filepath="cookies.pkl"):
    with open(filepath, "rb") as file:
        cookies = pickle.load(file)
        for cookie in cookies:
            driver.add_cookie(cookie)

def login(driver):
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)

    # Kiểm tra nếu đã có cookie thì nạp để bỏ qua bước đăng nhập
    try:
        load_cookies(driver)
        driver.refresh()
        time.sleep(5)
        # Nếu có cookie đúng, thì đã đăng nhập thành công
        if "instagram.com" in driver.current_url:
            print("Đăng nhập bằng cookie thành công!")
            return
    except Exception as e:
        print("Không tìm thấy cookie hoặc cookie không hợp lệ.")

    # Thực hiện đăng nhập nếu không có cookie hoặc cookie hết hạn
    username_input = driver.find_element(By.NAME, "username")
    password_input = driver.find_element(By.NAME, "password")

    username_input.send_keys(USERNAME)
    password_input.send_keys(PASSWORD)
    password_input.submit()
    time.sleep(7)

    # Lưu cookie sau khi đăng nhập thành công
    save_cookies(driver)


def scroll_and_collect(gui_progress_var, gui_progress_label):
    global stop_requested
    usernames = set()

    try:
        # Click vào bài viết đầu tiên
        first_post = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/p/')]"))
        )
        first_post.click()
        time.sleep(2)

        # Tìm username trong modal bài viết
        user_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@role='dialog']//header//a[contains(@href, '/')]")
            )
        )
        username = user_elem.get_attribute("href").split("/")[-2]
        if username not in usernames:
            usernames.add(username)
            gui_progress_label.config(
                text=f"Đã tìm thấy: {len(usernames)} / {MAX_USERS} username"
            )
            gui_progress_var.set((len(usernames) / MAX_USERS) * 100)

        # Click nút mũi tên sang phải, trường hợp bài viết đầu tiên chỉ có 1 nút mũi tên
        next_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@class, '_abl-') and not(@aria-label)]")
            )
        )
        next_button.click()
        time.sleep(2)

        while len(usernames) < MAX_USERS:
            if stop_requested:
                gui_progress_label.config(text="Đã hủy quy trình.")
                return

            try:
                # Tìm username trong modal bài viết
                user_elem = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@role='dialog']//header//a[contains(@href, '/')]")
                    )
                )
                username = user_elem.get_attribute("href").split("/")[-2]
                if username not in usernames:
                    usernames.add(username)
                    gui_progress_label.config(
                        text=f"Đã tìm thấy: {len(usernames)} / {MAX_USERS} username"
                    )
                    gui_progress_var.set((len(usernames) / MAX_USERS) * 100)

                # Lấy modal dialog chứa các nút
                modal_xpath = "//div[@role='dialog']"

                # Nút mũi tên phải, các trường hợp còn lại sẽ có 2 nút mũi tên, tìm nút bên phải để click
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, modal_xpath + "//div/div/div[2]/button")
                    )
                )
                next_button.click()
                time.sleep(2)

            except Exception as e:
                print(f"Không thể lấy thêm bài viết hoặc username: {e}")
                break

    except Exception as e:
        print(f"Lỗi khởi tạo: {e}")

    if not stop_requested:
        with open("usernames.txt", "w", encoding="utf-8") as f:
            for u in sorted(usernames):
                f.write(u + "\n")
        gui_progress_label.config(text=f"✅ Đã lưu {len(usernames)} username vào usernames.txt")


def start_scraper(gui_progress_var, gui_progress_label):
    global driver, stop_requested
    stop_requested = False  # Reset trạng thái hủy

    gui_progress_label.config(text="Đang khởi động...")
    options = uc.ChromeOptions()
    options.add_argument("--no-first-run --no-service-autorun --password-store=basic")
    driver = uc.Chrome(options=options)
    try:
        login(driver)
        time.sleep(5)
        driver.get(f"https://www.instagram.com/explore/tags/{HASHTAG}/")
        time.sleep(5)

        scroll_and_collect(gui_progress_var, gui_progress_label)

    finally:
        if driver:
            driver.quit()


def start_scraping_thread(gui_progress_var, gui_progress_label):
    threading.Thread(
        target=start_scraper, args=(gui_progress_var, gui_progress_label)
    ).start()


def stop_scraping(gui_progress_label):
    global stop_requested
    stop_requested = True
    gui_progress_label.config(text="Đang hủy quy trình... Vui lòng chờ.")

def normalize_url(url):
    if "/p/" in url:
        return url.split("/c/")[0]
    return url

# Tạo giao diện chính với Tkinter
def main():
    global stop_requested
    stop_requested = False

    root = tk.Tk()
    root.title("Instagram Scraper")
    root.geometry("500x300")

    # Nhãn tiêu đề
    title_label = tk.Label(root, text="Instagram Scraper", font=("Arial", 16))
    title_label.pack(pady=10)

    # Thanh tiến trình
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(
        root, orient="horizontal", length=400, mode="determinate", variable=progress_var
    )
    progress_bar.pack(pady=10)

    # Nhãn hiển thị trạng thái
    progress_label = tk.Label(root, text="Bấm 'Bắt đầu' để chạy!", font=("Arial", 12))
    progress_label.pack(pady=10)

    # Nút bắt đầu
    start_button = tk.Button(
        root,
        text="Bắt đầu",
        command=lambda: start_scraping_thread(progress_var, progress_label),
    )
    start_button.pack(pady=5)

    # Nút hủy
    stop_button = tk.Button(
        root, text="Hủy", command=lambda: stop_scraping(progress_label)
    )
    stop_button.pack(pady=5)

    # Chạy giao diện
    root.mainloop()


if __name__ == "__main__":
    main()
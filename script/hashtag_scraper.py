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
import random
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import cloudinary.uploader
import json
from pymongo import MongoClient
import random
import string

# Import Cloudinary
import cloudinary

# Tải thông tin từ file .env
load_dotenv()

def generate_random_email():
    """Tạo email ngẫu nhiên."""
    domain = random.choice(["example.com", "test.com", "demo.com"])
    username = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{username}@{domain}"

def generate_random_password():
    """Tạo mật khẩu ngẫu nhiên."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=12))

def generate_random_gender():
    """Tạo giới tính ngẫu nhiên."""
    return random.choice(["male", "female", "other"])

MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "instagram")

# Cấu hình Cloudinary từ file .env
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# Lấy thông tin từ file .env
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

HASHTAG = os.getenv("HASHTAG")
MAX_USERS = int(os.getenv("MAX_USERS", 10))  # Lấy giá trị mặc định là 10

# Biến toàn cục cho thread và trạng thái hủy
driver = None
stop_requested = False

# Kết nối tới MongoDB
def get_database():
    """Kết nối tới MongoDB và trả về đối tượng database."""
    try:
        # Kết nối tới MongoDB
        client = MongoClient(MONGO_CONNECTION_STRING)

        # Kết nối tới database (xác định bằng tên trong .env)
        db = client[MONGO_DB_NAME]
        print(f"Đã kết nối tới database: {MONGO_DB_NAME}")
        return db
    except Exception as e:
        print(f"Lỗi khi kết nối MongoDB: {e}")
        return None


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
        random_delay()

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

            # Mô phỏng việc click vào username và chuyển sang tab mới
            action = ActionChains(driver)
            action.key_down(Keys.CONTROL).click(user_elem).key_up(Keys.CONTROL).perform()
            driver.switch_to.window(driver.window_handles[-1])  # Chuyển tới tab mới
            random_delay()

            # Lấy thông tin người dùng từ tab mới
            user_info = get_user_info(driver)
            if user_info:
                print(user_info)

            # Đóng tab và chuyển về tab gốc
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        # Click nút mũi tên sang phải, trường hợp bài viết đầu tiên chỉ có 1 nút mũi tên
        next_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@class, '_abl-') and not(@aria-label)]")
            )
        )
        next_button.click()
        random_delay()

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

                    # Mô phỏng việc click vào username và chuyển đến tab mới
                    href = user_elem.get_attribute("href")
                    # Mô phỏng CTRL + Click
                    action = ActionChains(driver)
                    action.key_down(Keys.CONTROL).click(user_elem).key_up(Keys.CONTROL).perform()
                    driver.switch_to.window(driver.window_handles[-1])  # Chuyển tới tab mới
                    random_delay()

                    # Lấy thông tin người dùng từ tab mới
                    user_info = get_user_info(driver)
                    if user_info:
                        print(user_info)

                    # Đóng tab và chuyển về tab gốc
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

                # Lấy modal dialog chứa các nút
                modal_xpath = "//div[@role='dialog']"

                # Nút mũi tên phải, các trường hợp còn lại sẽ có 2 nút mũi tên, tìm nút bên phải để click
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, modal_xpath + "//div/div/div[2]/button")
                    )
                )
                next_button.click()
                random_delay()

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

# Thay thế các XPATH cũ bằng các XPATH mới được cung cấp
# Hàm tải ảnh lên Cloudinary
def upload_to_cloudinary(image_url):
    """Tải ảnh lên Cloudinary và trả về link ảnh đã được lưu."""
    try:
        response = cloudinary.uploader.upload(image_url)
        return response.get("url")  # Trả về URL của ảnh đã lưu trên Cloudinary
    except Exception as e:
        print(f"Lỗi khi tải ảnh lên Cloudinary: {e}")
        return None

def save_to_mongo(user_data):
    """Lưu thông tin người dùng vào MongoDB."""
    try:
        db = get_database()
        if db is not None:  # So sánh rõ ràng với None
            # Truy cập collection "users"
            users_collection = db["users"]
            # Thêm tài liệu mới vào collection
            result = users_collection.insert_one(user_data)
            print(f"Đã lưu người dùng vào MongoDB với _id: {result.inserted_id}")
        else:
            print("Không thể lưu vào MongoDB: Database không khả dụng.")
    except Exception as e:
        print(f"Lỗi khi lưu vào MongoDB: {e}")

def get_user_info(driver):
    """Lấy thông tin người dùng từ trang hiện tại."""
    
    def convert_to_number(value):
        """Chuyển chuỗi có K / M / B thành số thực."""
        value = value.strip().replace(",", "")
        if value.endswith("K"):
            return int(float(value[:-1]) * 1000)
        elif value.endswith("M"):
            return int(float(value[:-1]) * 1000000)
        elif value.endswith("B"):
            return int(float(value[:-1]) * 1000000000)
        else:
            return int(value)

    try:
        # Lấy username và fullname từ meta title
        og_title = driver.find_element(By.XPATH, "//meta[@property='og:title']").get_attribute("content")
        fullname = og_title.split("(@")[0].strip()
        username = og_title.split("(@")[1].split(")")[0].strip()

        # Lấy thông tin số lượng bài post, followers và following từ meta description
        og_description = driver.find_element(By.XPATH, "//meta[@property='og:description']").get_attribute("content")
        details = og_description.split("-")[0].strip()

        followers = convert_to_number(details.split("Followers")[0].strip())
        following = convert_to_number(details.split("Followers")[1].split("Following")[0].strip())
        posts = convert_to_number(details.split("Following")[1].split("Posts")[0].strip())

        # Lấy bio từ meta[@name="description"]
        bio_content = driver.find_element(By.XPATH, "//meta[@name='description']").get_attribute("content")
        bio = bio_content.split("on Instagram:")[-1].strip()  # Lấy phần sau 'on Instagram:'

        # Lấy URL ảnh đại diện từ thẻ meta[@property='og:image']
        avatar_url = driver.find_element(By.XPATH, "//meta[@property='og:image']").get_attribute("content")

        # Tải ảnh đại diện lên Cloudinary và nhận URL của ảnh
        cloudinary_url = upload_to_cloudinary(avatar_url)

        # Tạo tài liệu (document) người dùng cho MongoDB
        user_data = {
            "username": username,
            "email": generate_random_email(),
            "password": generate_random_password(),
            "fullname": fullname,
            "profile": {
                "bio": bio,
                "avatar": cloudinary_url or avatar_url,  # Dùng link trên Cloudinary nếu có
                "gender": generate_random_gender()
            },
            "role": "user",
            "posts": posts,
            "followers": followers,
            "following": following
        }

        # Lưu tài liệu vào MongoDB
        save_to_mongo(user_data)

        return user_data
    except Exception as e:
        print(f"Lỗi khi lấy thông tin người dùng: {e}")
        return None


def start_scraper(gui_progress_var, gui_progress_label):
    global driver, stop_requested
    stop_requested = False  # Reset trạng thái hủy

    gui_progress_label.config(text="Đang khởi động...")
    options = uc.ChromeOptions()
    options.add_argument("--no-first-run --no-service-autorun --password-store=basic")
    driver = uc.Chrome(options=options)
    try:
        login(driver)
        random_delay()
        driver.get(f"https://www.instagram.com/explore/tags/{HASHTAG}/")
        random_delay()

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

def random_delay():
    """Hàm tạo độ trễ ngẫu nhiên trong khoảng từ 4 đến 7 giây."""
    delay = random.uniform(2, 5)
    time.sleep(delay)

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

def save_to_json_file(data, filename="user_data.json"):
    """Thêm một mục dữ liệu vào file JSON."""
    try:
        # Đọc nội dung JSON hiện tại, nếu có
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as file:
                existing_data = json.load(file)
        else:
            existing_data = []

        # Thêm dữ liệu mới vào
        existing_data.append(data)

        # Ghi lại toàn bộ dữ liệu
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(existing_data, file, indent=4, ensure_ascii=False)

    except Exception as e:
        print(f"Lỗi khi ghi dữ liệu vào file JSON: {e}")

if __name__ == "__main__":
    main()
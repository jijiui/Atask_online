import time
import random
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

def human_like_wait(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    wait_time = random.uniform(min_seconds, max_seconds)
    time.sleep(wait_time)

def human_like_scroll(driver, target_y: int) -> None:
    current_y = driver.execute_script("return window.pageYOffset;")
    distance = target_y - current_y
    steps = random.randint(8, 15)
    
    for i in range(steps):
        progress = i / steps
        ease_progress = 1 - (1 - progress) ** 3
        scroll_y = current_y + (distance * ease_progress)
        driver.execute_script(f"window.scrollTo(0, {scroll_y});")
        human_like_wait(0.05, 0.15)

DEBUG_HTML_PATH = "debug.html"
PREVIOUS_RESULTS_FILE = "previous_results.json"

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TARGET_URL = os.getenv('TARGET_URL')
CITIES_STRING = os.getenv('TARGET_CITY') 

required_secrets = {
    "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
    "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    "TARGET_URL": TARGET_URL,
    "TARGET_CITY": CITIES_STRING
}
missing_secrets = [key for key, value in required_secrets.items() if not value]
if missing_secrets:
    sys.exit(1)

def send_telegram_notification(message: str) -> bool:
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(api_url, data=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        return False

def save_all_results(all_cities_data: Dict[str, Any]) -> None:
    try:
        with open(PREVIOUS_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_cities_data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        pass

def load_all_previous_results() -> Dict[str, Any]:
    if not os.path.exists(PREVIOUS_RESULTS_FILE):
        return {}
    try:
        with open(PREVIOUS_RESULTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except (IOError, json.JSONDecodeError) as e:
        return {}

def find_new_items(current_results: List[Dict[str, str]], previous_city_data: Dict[str, Any]) -> List[Dict[str, str]]:
    if not previous_city_data or "results" not in previous_city_data:
        return current_results
    
    previous_item_ids = {item.get('id') for item in previous_city_data.get("results", [])}
    
    new_items = [
        item for item in current_results if item.get('id') not in previous_item_ids
    ]
    return new_items

def setup_driver() -> uc.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--disable-ipc-flooding-protection')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-ignore-certificate-errors')
    options.add_argument('--disable-single-click-autofill')
    options.add_argument('--disable-autofill-keyboard-accessory-view')
    options.add_argument('--disable-full-form-autofill-ios')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
    ]
    selected_ua = random.choice(user_agents)
    options.add_argument(f'--user-agent={selected_ua}')
    
    window_sizes = [
        (1920, 1080),
        (1366, 768),
        (1440, 900),
        (1536, 864),
        (1280, 720)
    ]
    width, height = random.choice(window_sizes)
    options.add_argument(f'--window-size={width},{height}')
    
    if os.getenv('GITHUB_ACTIONS'):
        options.add_argument('--display=:99')
        options.add_argument('--headless')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-setuid-sandbox')
    
    service = None
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = uc.Chrome(service=service, options=options, version_main=138)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        try:
            from selenium import webdriver as selenium_webdriver
            if service is None:
                service = Service(ChromeDriverManager().install())
            driver = selenium_webdriver.Chrome(service=service, options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except Exception as e2:
            raise Exception(f"无法启动浏览器: {e2}")

def get_all_items_after_filter(url: str) -> List[Dict[str, str]]:
    driver = setup_driver()
    all_items_found = []
    card_xpath = "//div[contains(@class, 'card') and contains(@class, 'card-style')]"
    
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "city")))
        
        if random.random() < 0.4:
            observe_time = random.uniform(1.0, 3.0)
            time.sleep(observe_time)
        
        try:
            page_height = driver.execute_script("return document.body.scrollHeight")
            initial_cards = driver.find_elements(By.XPATH, card_xpath)
            scroll_steps = random.randint(2, 5)
            
            for i in range(scroll_steps):
                progress = (i + 1) / scroll_steps
                random_offset = random.uniform(-0.1, 0.1)
                progress = max(0.1, min(0.9, progress + random_offset))
                
                scroll_to = int(page_height * progress)
                human_like_scroll(driver, scroll_to)
                
                if random.random() < 0.7:
                    pause_time = random.uniform(1.0, 3.5)
                    time.sleep(pause_time)
                else:
                    human_like_wait(0.5, 1.0)
                
                current_cards = driver.find_elements(By.XPATH, card_xpath)
                if len(current_cards) > len(initial_cards):
                    initial_cards = current_cards
            
            if random.random() < 0.8:
                human_like_scroll(driver, 0)
                human_like_wait(1.5, 3.0)
            else:
                human_like_wait(1.0, 2.0)
            
        except Exception as e:
            pass
        
        try:
            old_card_ref = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, card_xpath))
            )
            
            cards_before_filter = driver.find_elements(By.XPATH, card_xpath)
            
            code_select_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "unlock_key"))
            )
            
            if random.random() < 0.6:
                human_like_wait(0.5, 1.5)
            
            select = Select(code_select_element)
            select.select_by_visible_text("Without code")
            
            human_like_wait(0.8, 2.0)
            
            try:
                selected_option = select.first_selected_option
                selected_text = selected_option.text.strip()
                selected_value = code_select_element.get_attribute("value")
            except Exception as e:
                pass
            
            WebDriverWait(driver, 30).until(EC.staleness_of(old_card_ref))

        except TimeoutException:
            pass
        
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, card_xpath)))
        except TimeoutException:
            return []

        cards = driver.find_elements(By.XPATH, card_xpath)
        
        try:
            cards = driver.find_elements(By.XPATH, card_xpath)
        except Exception as e:
            cards = []
        
        for i, card in enumerate(cards):
            try:
                card_text = card.text
                if "Book now!" not in card_text or not card_text.strip():
                    continue
                    
                try:
                    link_element = card.find_element(By.XPATH, ".//a[contains(text(), 'Book now!')]")
                    link = link_element.get_attribute("href")
                except NoSuchElementException:
                    link = f"未找到预订链接_{random.random()}"
                
                all_items_found.append({
                    "id": link,
                    "full_text": f"{card_text}\n🔗 链接: {link}"
                })
                
                progress_interval = random.randint(8, 15)
                if (i + 1) % progress_interval == 0:
                    if random.random() < 0.3:
                        rest_time = random.uniform(0.5, 1.5)
                        time.sleep(rest_time)
                    
            except Exception as e:
                continue
        
        browse_time = random.uniform(3, 8)
        time.sleep(browse_time)

    except Exception as e:
        pass
    finally:
        try:
            with open(DEBUG_HTML_PATH, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        except Exception as e:
            pass
        driver.quit()
    return all_items_found

def main():
    start_time = time.time()
    
    target_cities = [city.strip() for city in CITIES_STRING.split(',') if city.strip()]

    all_items_on_site = get_all_items_after_filter(TARGET_URL)
    
    all_previous_results = load_all_previous_results()
    
    all_current_results = all_previous_results.copy()

    any_new_items_found_overall = False
    any_successful_crawl = False

    for city in target_cities:
        current_city_items = [item for item in all_items_on_site if city.lower() in item['full_text'].lower()]
        
        previous_city_data = all_previous_results.get(city, {})
        
        if current_city_items:
            any_successful_crawl = True
            
            new_items = find_new_items(current_city_items, previous_city_data)
            
            if new_items:
                any_new_items_found_overall = True
                message = f"🏠 <b>在 {city} 发现 {len(new_items)} 个新项目！</b>\n\n"
                for i, item in enumerate(new_items, 1):
                    safe_item_text = item['full_text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    message += f"<b>{i}. 新项目:</b>\n<pre>{safe_item_text}</pre>\n\n"
                send_telegram_notification(message)

            all_current_results[city] = {
                "timestamp": datetime.now().isoformat(),
                "results": current_city_items
            }

    if any_successful_crawl:
        save_all_results(all_current_results)
    
    end_time = time.time()
    print(f"✨ 处理完成，耗时 {end_time - start_time:.2f} 秒。")

if __name__ == "__main__":
    main() 
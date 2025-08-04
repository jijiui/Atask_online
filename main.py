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

def HLW(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    wait_time = random.uniform(min_seconds, max_seconds)
    time.sleep(wait_time)

def HLS(driver, target_y: int) -> None:
    current_y = driver.execute_script("return window.pageYOffset;")
    distance = target_y - current_y
    steps = random.randint(8, 15)
    
    for i in range(steps):
        progress = i / steps
        ease_progress = 1 - (1 - progress) ** 3
        scroll_y = current_y + (distance * ease_progress)
        driver.execute_script(f"window.scrollTo(0, {scroll_y});")
        HLW(0.05, 0.15)

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
    print(f"Error: Missing required environment variables: {', '.join(missing_secrets)}")
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
    except requests.exceptions.RequestException:
        return False

def save_all_results(all_cities_data: Dict[str, Any]) -> None:
    try:
        with open(PREVIOUS_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_cities_data, f, ensure_ascii=False, indent=4)
    except IOError:
        pass

def load_all_previous_results() -> Dict[str, Any]:
    if not os.path.exists(PREVIOUS_RESULTS_FILE):
        return {}
    try:
        with open(PREVIOUS_RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
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
    
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
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
    
    driver = uc.Chrome(options=options)
    return driver

def get_all_items_after_filter(url: str) -> List[Dict[str, str]]:
    driver = setup_driver()
    all_items_found = []
    card_xpath = "//div[contains(@class, 'card') and contains(@class, 'card-style')]"
    
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "city")))
        
        if random.random() < 0.4:
            time.sleep(random.uniform(1.0, 3.0))
        
        try:
            page_height = driver.execute_script("return document.body.scrollHeight")
            initial_cards = driver.find_elements(By.XPATH, card_xpath)
            scroll_steps = random.randint(2, 5)
            
            for i in range(scroll_steps):
                progress = (i + 1) / scroll_steps
                random_offset = random.uniform(-0.1, 0.1)
                progress = max(0.1, min(0.9, progress + random_offset))
                
                scroll_to = int(page_height * progress)
                
                HLS(driver, scroll_to)
                
                if random.random() < 0.7:
                    time.sleep(random.uniform(1.0, 3.5))
                else:
                    HLW(0.5, 1.0)
                
                current_cards = driver.find_elements(By.XPATH, card_xpath)
                if len(current_cards) > len(initial_cards):
                    initial_cards = current_cards
            
            if random.random() < 0.8:
                HLS(driver, 0)
                HLW(1.5, 3.0)
            else:
                HLW(1.0, 2.0)
            
        except Exception:
            pass
        
        try:
            old_card_ref = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, card_xpath))
            )
            
            code_select_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "unlock_key"))
            )
            
            if random.random() < 0.6:
                HLW(0.5, 1.5)
            
            select = Select(code_select_element)
            select.select_by_visible_text("Without code")
            
            HLW(0.8, 2.0)
            
            WebDriverWait(driver, 30).until(EC.staleness_of(old_card_ref))

        except TimeoutException:
            pass
        
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, card_xpath)))
        except TimeoutException:
            return []

        try:
            cards = driver.find_elements(By.XPATH, card_xpath)
        except Exception:
            cards = []
        
        for card in cards:
            try:
                card_text = card.text
                if "Book now!" not in card_text or not card_text.strip():
                    continue
                    
                try:
                    link_element = card.find_element(By.XPATH, ".//a[contains(text(), 'Book now!')]")
                    link = link_element.get_attribute("href")
                except NoSuchElementException:
                    link = f"not_found_link_{random.random()}"
                
                all_items_found.append({
                    "id": link,
                    "full_text": f"{card_text}\n Link: {link}"
                })
                
            except Exception:
                continue
        
        time.sleep(random.uniform(3, 8))

    except Exception:
        pass
    finally:
        try:
            with open(DEBUG_HTML_PATH, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        except Exception:
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
                message = f"<b>New items in {city}: {len(new_items)}</b>\n\n"
                for i, item in enumerate(new_items, 1):
                    safe_item_text = item['full_text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    message += f"<b>{i}. New item:</b>\n<pre>{safe_item_text}</pre>\n\n"
                send_telegram_notification(message)

            all_current_results[city] = {
                "timestamp": datetime.now().isoformat(),
                "results": current_city_items
            }

    if any_successful_crawl:
        save_all_results(all_current_results)
    
    end_time = time.time()
    print(f"Finished in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    main()
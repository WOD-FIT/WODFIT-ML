import csv
import time
import os
import paths
import re
from lxml import html
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 드라이브 설정
def setup_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(), options=options)

# 페이지 로드 대기
def wait_for_element(driver, by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


# 링크 날짜순 정렬
def extract_date_from_url(url: str) -> int:
    """
    Extracts 6-digit date from URL, e.g., /250503 → 250503 (int)
    """
    match = re.search(r'/(\d{6})$', url)
    return int(match.group(1)) if match else -1

# article 링크 수집
def get_articles(driver, max_links=2300, scroll_pause=2, target_year=None, descending=True):
    links = set()

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)

        elems = driver.find_elements(By.XPATH, '//*[@id="archives"]//h3/a')

        new_links_found = 0
        for el in elems:
            href = el.get_attribute("href")
            if href and href.startswith(paths.urls['base']) and href not in links:
                links.add(href)
                new_links_found += 1

        print(f"Collected {len(links)} links so far... (+{new_links_found})")

        if len(links) >= max_links or new_links_found == 0:
            break

    # 날짜 필터링 (예: 2024년만)
    if target_year:
        prefix = str(target_year)[-2:]  # 2024 → '24'
        links = {url for url in links if re.search(rf'/{prefix}\d{{4}}$', url)}

    # 날짜순 정렬
    sorted_links = sorted(links, key=extract_date_from_url, reverse=descending)

    return sorted_links

def get_setting_xpath(driver, p_start):
    first_p = 'article_p' + str(p_start)
    second_p = 'article_p' + str(p_start+1)
    if '♀' in driver.find_element(By.XPATH, paths.xpaths[first_p]).get_attribute('innerHTML'):
        setting_xpath = paths.xpaths[first_p]
    elif '♀' in driver.find_element(By.XPATH, paths.xpaths[second_p]).get_attribute('innerHTML'):
        setting_xpath = paths.xpaths[second_p]
    else:
        setting_xpath = ''
    return setting_xpath

# 제목, wod, setting xpath 추출
def get_wod_setting_xpath(driver):

    p1_element = driver.find_element(By.XPATH, paths.xpaths['article_p1']).get_attribute('innerHTML')

    if 'Rest Day' in p1_element:
        return 0

    # if ('<strong>' not in p1_element) and ('<a href' not in p1_element): #25
    if 1: #24 #23
    # if '<a href' not in p1_element: #22
        if driver.find_element(By.XPATH, paths.xpaths['article_p1']).text.strip().endswith(":"):
            wod_xpath = [paths.xpaths['article_p1'], paths.xpaths['article_p2']]
            setting_xpath = get_setting_xpath(driver, 3)
        else:
            wod_xpath = [paths.xpaths['article_p1']]
            setting_xpath = get_setting_xpath(driver, 2)            
    else:
        if driver.find_element(By.XPATH, paths.xpaths['article_p2']).text.strip().endswith(":"):
            wod_xpath = [paths.xpaths['article_p2'], paths.xpaths['article_p3']]
            setting_xpath = get_setting_xpath(driver, 4)
        else:
            wod_xpath = [paths.xpaths['article_p2']]
            setting_xpath = get_setting_xpath(driver, 3)
    
    return wod_xpath, setting_xpath

# 댓글 크롤링
def get_comments_with_athletes(driver):

    wait_for_element(driver, By.XPATH, paths.xpaths['comments'])

    try:
        comment_blocks = driver.find_elements(By.XPATH, paths.xpaths['comments'])
        comment_data = []

        for block in comment_blocks:
            try:
                # 작성자
                athlete_elem = block.find_element(By.XPATH, paths.xpaths['comment_athlete'])
                athlete_html = athlete_elem.get_attribute("outerHTML")
                athlete_text = ' '.join(html.fromstring(athlete_html).itertext()).strip()

                # 댓글 내용
                content_elem = block.find_element(By.XPATH, paths.xpaths['comment_content'])
                content_html = content_elem.get_attribute("outerHTML")
                content_text = ' '.join(html.fromstring(content_html).itertext()).strip()

                if re.search(r"\brx\b|\brx['’]?d\b", content_text, re.IGNORECASE):
                    comment_data.append((athlete_text, content_text))

            except Exception:
                continue

        return comment_data

    except Exception as e:
        print(f"⚠️ 댓글/작성자 추출 실패: {e}")
        return []

def scrape_article(driver, url):
    try:
        driver.get(url)
        wait_for_element(driver, By.XPATH, paths.xpaths['article_p1'])

        result = get_wod_setting_xpath(driver)
        if result == 0:
            return 0
        wod_xpaths, setting_xpath = result

        # WOD 본문 추출
        wod_text = ''
        for xpath in wod_xpaths:
            wod_elem = driver.find_element(By.XPATH, xpath)
            wod_html = wod_elem.get_attribute("outerHTML")
            wod_tree = html.fromstring(wod_html)
            wod_text += ' ' + ''.join(wod_tree.itertext()).strip()
        wod_text = wod_text.strip().replace('\n', ' ')

        # Setting 추출
        if setting_xpath:
            setting_elem = driver.find_element(By.XPATH, setting_xpath)
            setting_html = setting_elem.get_attribute("outerHTML")
            setting_tree = html.fromstring(setting_html)
            setting_text = ''.join(setting_tree.itertext()).strip()
            if '\n' in setting_text:
                woman_setting_text, man_setting_text = setting_text.split('\n', 1)
                man_setting_text = man_setting_text[2:]
                woman_setting_text = woman_setting_text[2:]
            else:
                woman_setting_text, man_setting_text = setting_text.split('♂', 1)
                woman_setting_text = woman_setting_text.replace('♀', '').strip()
                man_setting_text = man_setting_text.strip()
        else:
            man_setting_text, woman_setting_text = '', ''

        # 날짜 추출
        date_elem = driver.find_element(By.XPATH, paths.xpaths['date'])
        date_text = date_elem.text.strip()
        
        # 댓글 추출
        comment_data = get_comments_with_athletes(driver)

        return date_text, wod_text, man_setting_text, woman_setting_text, comment_data

    except Exception as e:
        print(f"Error on {url}: {e}")
        return "", "", "", "", []


def load_checkpoint(filename="wod_data.csv"):
    if not os.path.exists(filename):
        return set()
    with open(filename, mode="r", encoding="utf-8") as f:
        return set(row["url"] for row in csv.DictReader(f))


def save_to_csv(data, filename="wod_data.csv"):
    file_exists = os.path.exists(filename)
    with open(filename, mode="a", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "wod", "man_setting", "woman_setting", "athlete", "comment", "url"])
        if not file_exists:
            writer.writeheader()
        for row in data:
            writer.writerow(row)


def crawl(year):
    csv_file = 'wod_data' + str(year) + '.csv'
    driver = setup_driver(headless=False)
    base_url = paths.urls['workout']

    try:
        print("▶ Opening main workout page...")
        driver.get(base_url)
        wait_for_element(driver, By.ID, "archives")

        print("▶ Scrolling to load workouts...")
        workout_links = get_articles(driver, max_links=2300, target_year=year)

        # Checkpoint 로딩
        done_urls = load_checkpoint(filename='wod_data2025.csv')
        for i in range(2025-year):
            checkpoint = 'wod_data' + str(2024-i) + '.csv'
            done_urls.update(load_checkpoint(filename=checkpoint))
        print(f"▶ {len(done_urls)} already scraped URLs loaded from checkpoint.")

        count = 0
        for link in workout_links:

            if link in done_urls:
                continue

            result = scrape_article(driver, link)

            if result == 0:
                continue

            date, wod, man_setting, woman_setting, comments = result

            if not comments:
                comments = [('', '')]

            rows_to_save = []
            for athlete, comment in comments:
                rows_to_save.append({
                    "date": date,
                    "wod": wod,
                    "man_setting": man_setting,
                    "woman_setting": woman_setting,
                    "athlete": athlete,
                    "comment": comment,
                    "url": link
                })
            save_to_csv(rows_to_save, filename=csv_file)
            print(f"[{count+1}] ✅ Scraped: {link}")
            time.sleep(0.5)
            count += 1

    finally:
        driver.quit()

    print("✅✅✅ Done. All data saved to wod_data.csv ✅✅✅")



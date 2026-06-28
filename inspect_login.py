"""더빌 로그인 페이지 구조 분석 (로그인 제출은 하지 않음).

입력칸/버튼/링크의 식별자(id, name 등)를 출력해 셀렉터를 찾는다.
"""
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

URL = "https://www.thebill.co.kr/main.jsp"


def desc(el):
    return {
        "tag": el.tag_name,
        "type": el.get_attribute("type"),
        "id": el.get_attribute("id"),
        "name": el.get_attribute("name"),
        "placeholder": el.get_attribute("placeholder"),
        "class": el.get_attribute("class"),
        "text": (el.text or "").strip()[:30],
        "value": (el.get_attribute("value") or "")[:30],
        "onclick": (el.get_attribute("onclick") or "")[:60],
    }


def main():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(URL)
        time.sleep(3)
        print("제목:", driver.title)
        print("URL :", driver.current_url)

        print("\n===== INPUT =====")
        for el in driver.find_elements(By.TAG_NAME, "input"):
            print(desc(el))

        print("\n===== BUTTON =====")
        for el in driver.find_elements(By.TAG_NAME, "button"):
            print(desc(el))

        print("\n===== a (로그인 관련 링크) =====")
        for el in driver.find_elements(By.TAG_NAME, "a"):
            d = desc(el)
            if any(k in (d["text"] + d["onclick"] + (d["id"] or "")).lower()
                   for k in ["login", "로그인", "submit"]):
                print(d)

        driver.save_screenshot("login_page.png")
        print("\n스크린샷 저장: login_page.png")
        with open("login_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("HTML 저장: login_page.html")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()

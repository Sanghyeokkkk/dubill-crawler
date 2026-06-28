"""Selenium 동작 확인용 데모 크롤러.

크롤링 '연습 전용' 사이트(quotes.toscrape.com)에서 명언 목록을 긁어와 출력한다.
이 사이트는 누구나 크롤링 연습용으로 만들어 둔 곳이라 마음껏 써도 된다.

실행:
    python demo_crawl.py

흐름:
    1) 크롬 브라우저를 띄운다 (headless = 창 없이 백그라운드)
    2) 페이지를 연다
    3) 원하는 요소들을 찾아서(텍스트/작가/태그) 추출한다
    4) 보기 좋게 출력한다
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def main() -> None:
    # 1) 브라우저 옵션 설정
    options = Options()
    options.add_argument("--headless=new")   # 창을 띄우고 싶으면 이 줄을 주석 처리
    options.add_argument("--window-size=1280,900")

    # 2) 크롬 실행 (Selenium 4.6+ 는 드라이버를 자동으로 받아준다)
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://quotes.toscrape.com/")
        print("페이지 제목:", driver.title)
        print("-" * 50)

        # 3) 페이지 안의 모든 명언 박스를 찾는다 (CSS 선택자 사용)
        quote_boxes = driver.find_elements(By.CSS_SELECTOR, "div.quote")

        for i, box in enumerate(quote_boxes, start=1):
            text = box.find_element(By.CSS_SELECTOR, "span.text").text
            author = box.find_element(By.CSS_SELECTOR, "small.author").text
            tags = [t.text for t in box.find_elements(By.CSS_SELECTOR, "a.tag")]

            print(f"[{i}] {text}")
            print(f"     - {author}  (태그: {', '.join(tags)})")
            print()

        print(f"총 {len(quote_boxes)}개의 명언을 수집했습니다.")

    finally:
        # 4) 반드시 브라우저를 닫아 메모리 누수를 막는다
        driver.quit()


if __name__ == "__main__":
    main()

"""로그인 후 화면 구조 분석.

크롬 창이 뜨면 사용자가 직접 2단계 인증을 완료한다.
로그인이 되면(또는 최대 대기시간이 지나면) 메뉴/프레임 구조를 덤프한다.

목표: 가상계좌 / 입금내역관리 / 입금내역조회(VAS4010) / 날짜칸 / 조회 / 엑셀다운로드
      에 해당하는 요소의 셀렉터를 찾는다.

실행:
    python inspect_after_login.py
"""
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import config

MAX_WAIT = 240   # 로그인(2FA 포함) 완료까지 최대 대기(초)
KEYWORDS = ["가상계좌", "입금내역", "입금내역관리", "입금내역조회",
            "조회", "엑셀", "VAS4010", "시작일", "종료일", "검색"]


def dump_elements(driver, where):
    """현재 컨텍스트(프레임)에서 관심 요소를 출력."""
    found = 0
    tags = ["a", "button", "input", "li", "span", "td", "div"]
    for tag in tags:
        for el in driver.find_elements(By.TAG_NAME, tag):
            try:
                txt = (el.text or "").strip()
                eid = el.get_attribute("id") or ""
                onclick = el.get_attribute("onclick") or ""
                href = el.get_attribute("href") or ""
                value = el.get_attribute("value") or ""
                blob = f"{txt} {eid} {onclick} {href} {value}"
                if any(k in blob for k in KEYWORDS):
                    info = {
                        "where": where, "tag": tag, "id": eid,
                        "text": txt[:25], "value": value[:20],
                        "onclick": onclick[:70], "href": href[:70],
                        "class": (el.get_attribute("class") or "")[:30],
                        "name": el.get_attribute("name") or "",
                    }
                    # 빈 컨테이너성 div/span/td 과다 출력 방지: 식별자 있는 것 위주
                    if eid or onclick or value or tag in ("a", "button", "input"):
                        print(info)
                        found += 1
            except Exception:
                continue
    return found


def scan_all_frames(driver):
    """메인 + 모든 iframe 안을 스캔."""
    driver.switch_to.default_content()
    print("\n##### [메인 문서] #####")
    dump_elements(driver, "main")

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"\n(iframe {len(frames)}개 발견)")
    for i in range(len(frames)):
        driver.switch_to.default_content()
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        try:
            driver.switch_to.frame(frames[i])
            fid = frames[i].get_attribute("id") or frames[i].get_attribute("name") or f"#{i}"
            print(f"\n##### [iframe: {fid}] #####")
            dump_elements(driver, f"iframe:{fid}")
        except Exception as e:
            print(f"  (iframe {i} 접근 실패: {e})")
    driver.switch_to.default_content()


def main():
    options = Options()
    options.add_argument("--window-size=1500,1000")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(config.THEBILL_MAIN_URL)
        time.sleep(2)

        # 자동 입력
        driver.find_element(By.ID, "loginid").send_keys(config.THEBILL_ID)
        driver.find_element(By.ID, "loginpw").send_keys(config.THEBILL_PW)
        driver.find_element(By.ID, "btnLogin").click()

        print("=" * 60)
        print(" 크롬 창에서 2단계 인증을 완료해 로그인하세요.")
        print(f" 로그인 감지까지 최대 {MAX_WAIT}초 기다립니다...")
        print("=" * 60)

        # '가상계좌' 텍스트가 페이지(또는 프레임)에 나타나면 로그인 완료로 판단
        logged_in = False
        deadline = time.time() + MAX_WAIT
        while time.time() < deadline:
            # 비밀번호 변경 팝업이 뜨면 '다음에변경' 클릭 시도
            try:
                btn = driver.find_element(By.ID, "btnNextRenew")
                if btn.is_displayed():
                    btn.click()
                    print("[안내] 비밀번호 변경 팝업 → '다음에변경' 클릭")
            except Exception:
                pass
            # 메인/프레임 어디든 '가상계좌'가 보이는지
            page = driver.page_source
            if "가상계좌" in page or "입금내역" in page:
                logged_in = True
                break
            time.sleep(2)

        print(f"\n로그인 감지: {logged_in}")
        print("현재 URL:", driver.current_url)
        print("현재 제목:", driver.title)
        driver.save_screenshot("after_login.png")
        with open("after_login.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("스크린샷: after_login.png / HTML: after_login.html\n")

        scan_all_frames(driver)
        print("\n분석 완료. 창은 5초 후 닫힙니다.")
        time.sleep(5)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()

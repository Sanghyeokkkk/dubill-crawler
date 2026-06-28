"""로그인 후 '입금내역조회' 화면까지 사용자가 직접 이동 → 전체 구조 캡처.

더빌은 frame/iframe 중첩 구조라, 모든 프레임을 재귀적으로 훑는다.
'엑셀다운로드' 또는 '입금내역조회'가 보이는 순간을 감지해 덤프한다.

실행:
    python inspect_v2.py
사용:
    1) 크롬 창이 뜨면 2단계 인증으로 로그인
    2) 직접 [가상계좌 → 입금내역관리 → 입금내역조회] 까지 이동
    3) '엑셀다운로드' 버튼이 보이면 자동으로 분석/저장 후 종료
"""
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import config

MAX_WAIT = 300
TARGET = ["엑셀다운로드", "엑셀 다운로드", "입금내역조회", "VAS4010"]
KEYWORDS = ["가상계좌", "입금내역", "조회", "엑셀", "VAS", "시작일", "종료일",
            "기간", "검색", "다운로드", "date", "Date"]


def has_target_here(driver) -> bool:
    src = driver.page_source
    return any(t in src for t in TARGET)


def search_frames(driver, depth=0) -> bool:
    """현재 컨텍스트와 하위 프레임에서 TARGET 존재 여부."""
    if has_target_here(driver):
        return True
    if depth > 4:
        return False
    frames = driver.find_elements(By.CSS_SELECTOR, "frame, iframe")
    for i in range(len(frames)):
        try:
            driver.switch_to.frame(i)
            if search_frames(driver, depth + 1):
                driver.switch_to.parent_frame()
                return True
            driver.switch_to.parent_frame()
        except Exception:
            try:
                driver.switch_to.parent_frame()
            except Exception:
                pass
    return False


def desc(el):
    return {
        "tag": el.tag_name,
        "id": el.get_attribute("id") or "",
        "name": el.get_attribute("name") or "",
        "type": el.get_attribute("type") or "",
        "text": (el.text or "").strip()[:25],
        "value": (el.get_attribute("value") or "")[:25],
        "onclick": (el.get_attribute("onclick") or "")[:80],
        "href": (el.get_attribute("href") or "")[:80],
        "class": (el.get_attribute("class") or "")[:30],
    }


def dump_frame(driver, path):
    """현재 프레임에서 관심 요소 출력."""
    printed = 0
    for tag in ["a", "button", "input", "select", "img", "li", "span", "td"]:
        for el in driver.find_elements(By.TAG_NAME, tag):
            try:
                d = desc(el)
                blob = " ".join([d["text"], d["id"], d["name"], d["value"],
                                 d["onclick"], d["href"], d["class"]])
                if any(k in blob for k in KEYWORDS):
                    if d["id"] or d["onclick"] or d["value"] or tag in ("a", "button", "input", "select"):
                        print(f"  [{path}] {d}")
                        printed += 1
            except Exception:
                continue
    if printed == 0:
        print(f"  [{path}] (관심 요소 없음)")


def dump_all_frames(driver, path="main", depth=0):
    print(f"\n##### 프레임: {path} (url={driver.current_url[:60]}) #####")
    dump_frame(driver, path)
    if depth > 4:
        return
    frames = driver.find_elements(By.CSS_SELECTOR, "frame, iframe")
    for i in range(len(frames)):
        try:
            fid = frames[i].get_attribute("id") or frames[i].get_attribute("name") or f"#{i}"
        except Exception:
            fid = f"#{i}"
        try:
            driver.switch_to.frame(i)
            dump_all_frames(driver, f"{path}>{fid}", depth + 1)
            driver.switch_to.parent_frame()
        except Exception:
            try:
                driver.switch_to.parent_frame()
            except Exception:
                pass


def main():
    options = Options()
    options.add_argument("--window-size=1500,1000")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(config.THEBILL_MAIN_URL)
        time.sleep(2)
        driver.find_element(By.ID, "loginid").send_keys(config.THEBILL_ID)
        driver.find_element(By.ID, "loginpw").send_keys(config.THEBILL_PW)
        driver.find_element(By.ID, "btnLogin").click()

        print("=" * 64)
        print(" 1) 크롬 창에서 2단계 인증으로 로그인")
        print(" 2) [가상계좌 → 입금내역관리 → 입금내역조회] 화면까지 직접 이동")
        print(" 3) '엑셀다운로드' 버튼이 보이면 자동으로 분석합니다.")
        print(f" (최대 {MAX_WAIT}초 대기)")
        print("=" * 64)

        found = False
        deadline = time.time() + MAX_WAIT
        while time.time() < deadline:
            for h in driver.window_handles:
                driver.switch_to.window(h)
                driver.switch_to.default_content()
                if search_frames(driver):
                    found = True
                    target_handle = h
                    break
            if found:
                break
            time.sleep(2)

        if not found:
            print("\n[시간초과] 입금내역조회 화면을 감지하지 못했습니다.")
            print("현재 열린 창들의 구조라도 덤프합니다.")

        # 타깃(또는 마지막) 창 전체 덤프
        if found:
            driver.switch_to.window(target_handle)
        driver.switch_to.default_content()
        print("\n현재 URL:", driver.current_url, "| 제목:", driver.title)
        driver.save_screenshot("inquiry_page.png")
        with open("inquiry_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        dump_all_frames(driver)
        print("\n저장: inquiry_page.png / inquiry_page.html")
        print("분석 완료. 10초 후 창을 닫습니다.")
        time.sleep(10)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()

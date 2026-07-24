# USB로 다른 PC에서 실행하기

이 폴더를 USB에 담아 다른 PC에서 실행하는 방법입니다.
(쿠팡 크롤러와 같은 방식 — 소스코드 + 인증파일을 USB에 두고, 그 PC의 Python으로 실행)

## 처음 쓰는 PC에서 (1회만)

### 1) Python 설치 확인
- 이미 있으면 건너뜀
- 없으면 https://www.python.org/downloads/ 에서 설치
- ⚠️ 설치 화면에서 **"Add Python to PATH" 반드시 체크**

### 2) Chrome 설치 확인
- 크롤러가 크롬을 띄우므로 필요 (없으면 https://www.google.com/chrome/)

### 3) USB_설치.bat 더블클릭
- 필요한 패키지(selenium, pandas, gspread 등)를 그 PC에 자동 설치
- "Setup complete" 뜨면 완료

## 실행 (매번)
**`더빌_입금내역_수집.bat` 더블클릭**
- 크롬이 뜨면 로그인(필요시 2단계 인증)만 하면 나머지는 자동
- 최근 7일 입금 → 구글시트 자동 적재

## 중요한 파일 (USB에 반드시 함께 있어야 함)
| 파일 | 역할 |
|------|------|
| `config.py` | 더빌 로그인/시트 설정 ⚠️ 비밀 |
| `service_account.json` | 구글 접근 키 ⚠️ 비밀 |
| `requirements.txt` | 설치할 패키지 목록 |
| `*.py` | 프로그램 본체 |

> ⚠️ **보안**: `config.py`와 `service_account.json`에는 더빌 비밀번호와 구글 인증키가 들어있습니다.
> USB를 분실하지 않도록 주의하세요.

## 자주 묻는 것

**Q. 실행하면 "python을 찾을 수 없습니다"**
→ Python이 없거나 PATH에 없음. Python 재설치 시 "Add Python to PATH" 체크

**Q. 크롬 오류가 나요**
→ 크롬이 설치돼 있는지 확인. 크롤러가 자동으로 좀비 크롬을 정리하고 재시도합니다.

**Q. 원래 PC에서는 어떻게 되나요?**
→ 원래 PC엔 `.venv` 폴더가 있어서 그걸 우선 사용합니다. USB엔 `.venv`가 없어서 시스템 Python을 씁니다.
   (실행 .bat이 자동으로 판단하므로 신경 안 쓰셔도 됩니다.)

**Q. 코드가 업데이트되면?**
→ GitHub(https://github.com/Sanghyeokkkk/dubill-crawler)에서 최신본을 받거나,
   원래 PC의 폴더를 USB로 다시 복사하세요.

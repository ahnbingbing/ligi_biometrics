# Setup: Google Sheets 백엔드 + Slack 일일 알림

GitHub CSV 저장 방식에서 **Google Sheets 저장 + GitHub Actions로 매일 8시 Slack 알림** 구조로 전환하는 가이드입니다.

전체 작업은 약 20–30분이며, 다음 순서로 진행합니다.

1. Google Sheet 생성
2. Google Cloud 서비스 계정 생성 + Sheets API 활성화
3. 시트를 서비스 계정에 공유
4. Slack incoming webhook 생성
5. Streamlit Cloud secrets 설정
6. GitHub repo secrets 설정
7. (선택) 로컬 `.env` 설정
8. 데이터 마이그레이션 실행

---

## 1. Google Sheet 생성

1. https://sheets.new 접속해서 새 시트 생성
2. 시트 이름을 `ligi_biometrics` (혹은 원하는 이름)으로 변경
3. 첫 번째 행에 헤더를 추가 (한 셀에 한 컬럼명):

   ```
   date | weight_kg | sleep_quality | sleep_hours | alcohol_intake | salty_carb_heavy_meal | allergy_histamine_score | bowel_status | exercise | non_exercise_kcal | bloating_swelling | gas_distension | stress_level | overall_condition | night_sweat_score | notes
   ```

   (헤더는 마이그레이션 스크립트가 자동으로 만들어주니 비워둬도 됩니다.)

4. **시트 ID 복사**: URL이 `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`인데, 이 `{SHEET_ID}` 부분을 메모.

---

## 2. Google Cloud 서비스 계정 생성

1. https://console.cloud.google.com/ 접속
2. 새 프로젝트 생성 (이름 예: `ligi-biometrics`)
3. 좌측 메뉴 → **APIs & Services → Library**
4. "Google Sheets API" 검색 → **Enable**
5. 좌측 메뉴 → **APIs & Services → Credentials**
6. **Create Credentials → Service Account**
   - 이름: `ligi-biometrics-sa` (아무거나 OK)
   - Role 단계는 건너뜀 (Skip)
   - Done
7. 생성된 서비스 계정 클릭 → **Keys 탭 → Add Key → Create New Key → JSON**
8. 다운로드된 JSON 파일을 안전한 곳에 보관 (이후 단계에서 사용)
9. JSON 파일 안의 `"client_email"` 값을 복사 (예: `ligi-biometrics-sa@xxx.iam.gserviceaccount.com`)

---

## 3. 시트를 서비스 계정에 공유

1. 1단계에서 만든 Google Sheet로 돌아가기
2. 우측 상단 **Share** 클릭
3. 위에서 복사한 `client_email`을 입력
4. 권한을 **Editor**로 설정
5. "Notify people" 체크 해제 → Send

이제 서비스 계정이 시트에 read/write 가능합니다.

---

## 4. Slack incoming webhook 생성

1. https://api.slack.com/apps → **Create New App → From scratch**
2. 앱 이름: `ligi-biometrics-reminder`, 워크스페이스 선택
3. 좌측 메뉴 → **Incoming Webhooks → Activate**
4. 하단 **Add New Webhook to Workspace** 클릭
5. 메시지를 받을 채널 선택 (DM은 본인 이름 검색)
6. 생성된 webhook URL 복사 (`https://hooks.slack.com/services/T.../B.../...`)

---

## 5. Streamlit Cloud secrets 설정

Streamlit Community Cloud 대시보드 → 앱 선택 → **Settings → Secrets** 에 아래 내용 붙여넣기.

`secrets.toml` 형식:

```toml
sheet_id = "여기에_1단계의_SHEET_ID"
worksheet_name = "Sheet1"

# 2단계에서 다운로드한 JSON의 내용을 그대로 옮김
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "ligi-biometrics-sa@xxx.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
universe_domain = "googleapis.com"
```

> **주의**: `private_key` 값에 있는 줄바꿈을 `\n`으로 escape해야 합니다. JSON 원본에서는 이미 `\n`으로 되어 있으니 그대로 옮기면 됩니다. 다만 큰따옴표로 감쌌는지 꼭 확인.

저장 → 앱 자동 재시작 → 정상 동작 확인.

---

## 6. GitHub repo secrets 설정

GitHub Actions에서 매일 새벽에 실행될 때 필요한 값들입니다.

리포 → **Settings → Secrets and variables → Actions → New repository secret** 으로 아래 3개 추가:

| 이름 | 값 |
|---|---|
| `GOOGLE_SHEETS_CREDS` | 2단계에서 다운로드한 JSON 파일 **전체 내용**을 그대로 붙여넣기 (한 줄로 미니파이 안 해도 됨) |
| `SHEET_ID` | 1단계의 SHEET_ID |
| `SLACK_WEBHOOK_URL` | 4단계의 webhook URL |
| `OPENAI_API_KEY` | (이미 .env에 있는 그 값) — 추세 분석 batch 돌릴 때만 필요. 알림만 하면 생략 가능 |

---

## 7. (선택) 로컬 `.env` 파일 업데이트

로컬에서 `streamlit run app.py` 또는 `python batch_reminder.py`를 돌릴 거라면 `.env`에 다음 추가:

```bash
# 기존 OPENAI_API_KEY 등은 그대로 둠

# 새로 추가
SHEET_ID=여기에_SHEET_ID
WORKSHEET_NAME=Sheet1
GOOGLE_APPLICATION_CREDENTIALS=/절대경로/service_account.json
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# GitHub 관련 환경변수 (GITHUB_TOKEN 등)는 더 이상 필요 없음 — 삭제해도 OK
```

서비스 계정 JSON 파일은 `.gitignore`에 반드시 포함시키세요 (`service_account.json` 같은 이름으로). `.gitignore`는 자동 업데이트됨.

---

## 8. 데이터 마이그레이션

기존 `data/biometrics.csv`의 3행을 시트로 옮깁니다.

```bash
cd ligi_biometrics
source .venv/bin/activate
pip install -r requirements.txt   # gspread 등 새 패키지 설치
python migrate_csv_to_sheet.py
```

스크립트는:
- 시트가 비어있으면 헤더 + 모든 행 추가
- 시트에 이미 같은 날짜가 있으면 skip
- 결과를 stdout에 출력

성공하면 시트를 새로고침해서 데이터가 들어왔는지 확인.

---

## 9. 동작 검증

### Streamlit 앱
1. 앱(https://ligibiometrics.streamlit.app/) 접속
2. 오늘 데이터 입력 → 저장
3. Google Sheet에 들어가서 같은 날짜 row가 업데이트됐는지 확인

### GitHub Actions 일일 알림
1. 리포 → **Actions** 탭에서 "Daily Slack Reminder" workflow 확인
2. **Run workflow** 버튼으로 즉시 테스트 실행
3. Slack 채널에 메시지가 도착하는지 확인
4. 실제 자동 실행은 매일 8 AM KST에 발생

### 문제 시 디버깅
- Streamlit 앱 로그: Streamlit Cloud 대시보드 → Manage app → Logs
- GitHub Actions 로그: Actions 탭에서 실패한 run 클릭

---

## 정리

이제 데이터 흐름은:

```
[Streamlit UI] → [Google Sheets] ← [batch_reminder.py via GitHub Actions]
                                                    ↓
                                              [Slack DM/채널]
```

GitHub은 코드 저장소 역할만 하고, 데이터는 모두 Sheets에 있어요. 매번 commit 안 만들어지고 Streamlit Cloud auto-redeploy도 발생 안 합니다.

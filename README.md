# Ligi Biometrics

Streamlit app for daily biometric tracking with Google Sheets storage, Korean OpenAI analysis, and a Slack reminder via GitHub Actions.

Live: https://ligibiometrics.streamlit.app/

## Architecture

```
Streamlit UI ──▶ Google Sheets (canonical storage)
                       ▲
                       │ read at 08:00 KST
                       │
        GitHub Actions cron ──▶ Slack webhook (daily reminder)
```

- Streamlit Cloud hosts the app; data lives in a Google Sheet (no commit-per-update churn).
- A GitHub Actions cron job (`.github/workflows/daily_reminder.yml`) runs `batch_reminder.py --slack` daily at 08:00 KST.

## First-time setup

See [SETUP_SHEETS.md](SETUP_SHEETS.md) for the full step-by-step (Google Cloud service account, Sheet sharing, Slack webhook, Streamlit and GitHub secrets, data migration).

## Local development

```bash
cd ligi_biometrics
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in real values. For Streamlit-side dev, also copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.

Run the app:

```bash
streamlit run app.py
```

## Batch scripts

```bash
# Print today's reminder + save to data/today_reminder.txt
python batch_reminder.py

# Print + post to Slack
python batch_reminder.py --slack

# Run trend analysis (recent 14 rows → OpenAI → data/latest_analysis.md)
python batch_analysis.py
```

`batch_reminder.py` flags:
- `--no-save` — skip writing `data/today_reminder.txt`
- `--no-print` — suppress stdout (useful in CI)
- `--slack` — POST the reminder to `SLACK_WEBHOOK_URL`
- `--app-url URL` — override the "기록하러 가기" button URL

## One-time data migration

After credentials are set up, copy your local CSV into the sheet:

```bash
python migrate_csv_to_sheet.py
```

The script is idempotent — re-running it won't duplicate dates already present in the sheet.

## Behavior

- The app has three screens: previous-day causes, today's outcomes, then saved analysis and trend charts.
- Form fields are built dynamically from `data/metadata.json` (28 fields: 15 cause inputs and 13 result inputs).
- Each field shows the previous row's value and a Korean anchor description for calibration.
- Submission upserts today's row by date.
- The app uses Asia/Seoul as the canonical date, so Streamlit Cloud's server timezone does not overwrite the previous KST day.
- All persistence goes to Google Sheets via `gspread` (`sheets_storage.py`); a local CSV at `data/biometrics.csv` is kept as a cache.
- Today's row + yesterday's row + recent 14 rows are sent to the OpenAI API for Korean analysis (gpt-4.1-mini by default).
- Slack trend details are posted as thread replies when `SLACK_BOT_TOKEN` and `SLACK_CHANNEL_ID` are configured; otherwise they fall back to one combined webhook message.
- Streamlit renders trend charts (weight, bloating vs gas) and a recent-data expander.
- Scheduled work (daily reminder, optional batch analysis) runs in GitHub Actions, not in the Streamlit process.

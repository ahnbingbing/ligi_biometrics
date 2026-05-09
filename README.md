# Ligi Biometrics

Local Streamlit app for daily biometric tracking with CSV storage and Korean OpenAI analysis.

## Setup

```bash
cd ligi_biometrics
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add your API key to `.env`:

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

## Run

```bash
streamlit run app.py
```

The app stores data in `data/biometrics.csv` and reads form settings from `data/metadata.json`.

## Batch Scripts

Scheduling does not run inside Streamlit. Use n8n or cron to call these command-line scripts:

```bash
python batch_reminder.py
python batch_analysis.py
```

`batch_reminder.py` prints today's Korean check-in message to stdout and saves it to `data/today_reminder.txt`.
Use `python batch_reminder.py --no-save` to print without writing a file.

`batch_analysis.py` sends recent rows to the OpenAI API and saves Korean trend analysis to `data/latest_analysis.md`.

## Behavior

- Builds the form dynamically from `metadata.json`
- Pre-fills today's fields with today's saved row, or the latest previous row when today has no row
- Shows the latest previous value and Korean anchor guidance beside each field
- Upserts today's row by date
- Migrates rows from `data/biometrics_origin.csv` into `data/biometrics.csv` when present, keeping current CSV rows for duplicate dates
- Sends today's row, the latest previous row, and recent 14 rows to the OpenAI API
- Displays Korean analysis and local trend charts
- Does not run scheduled jobs; n8n or cron should handle scheduling

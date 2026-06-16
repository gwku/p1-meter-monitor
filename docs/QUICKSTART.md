# Quick start

A condensed setup guide. See the [README](../README.md) for full details.

## 1. Configure

```bash
cp .env.example .env
```

Set at least these values in `.env`:

- `P1_API_URL` — your P1 meter JSON endpoint
- `P1_EMAIL_TO` — report recipient(s), comma-separated
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`

## 2. Start

```bash
docker compose up -d
```

Collection starts immediately. A monthly report is sent on the 1st of each
month at 00:00 (disable with `ENABLE_MONTHLY_REPORT=false`).

## 3. Verify email

```bash
docker compose exec p1-meter-monitor python -m p1monitor.reporter --test-email
```

## Common commands

```bash
# Logs
docker compose logs -f p1-meter-monitor

# Status
docker compose ps

# Generate and email a report
docker compose exec p1-meter-monitor python -m p1monitor.reporter --period month

# Export a period to CSV (no email)
docker compose exec p1-meter-monitor python -m p1monitor.reporter \
  --period this-month --csv-only --output /output/report.csv

# All reporter options
docker compose exec p1-meter-monitor python -m p1monitor.reporter --help

# Restart after editing .env
docker compose restart p1-meter-monitor

# Stop
docker compose down
```

## QuestDB console

http://localhost:9000

```sql
SELECT * FROM p1_meter_data ORDER BY timestamp DESC LIMIT 1;
```

## Troubleshooting

Email not sending:

```bash
docker compose exec p1-meter-monitor python -m p1monitor.reporter --test-email
docker compose logs p1-meter-monitor | grep -i smtp
```

No data collected:

```bash
docker compose exec p1-meter-monitor curl "$P1_API_URL"
docker compose logs p1-meter-monitor
docker compose ps questdb
```

# P1 Meter Monitor

Collects readings from a P1 smart meter, stores them in a QuestDB time-series
database, and emails periodic consumption reports. Everything runs in Docker.

The P1 port is the standard data interface on Dutch and Belgian smart meters
(DSMR / eMUCS-P1). This project targets a JSON HTTP API in front of that port,
such as the one exposed by a HomeWizard P1 dongle (`/api/v1/data`).

## How it works

- A collector polls the P1 HTTP API at a fixed interval (default 60s) and writes
  each reading to QuestDB.
- A built-in scheduler (APScheduler) sends a monthly report on the 1st of each
  month and, optionally, a weekly CSV export.
- Reports are rendered as HTML email with an optional CSV attachment, and can
  also be generated on demand from the command line.

## Requirements

- Docker and Docker Compose
- A P1 meter reachable over HTTP that returns JSON (e.g. HomeWizard P1)
- An SMTP account for sending reports

## Quick start

```bash
cp .env.example .env
# edit .env: set P1_API_URL, SMTP_* and P1_EMAIL_TO
docker compose up -d
```

This starts two services: `questdb` (the database) and `p1-meter-monitor` (the
collector and scheduler). Data collection begins immediately.

Verify email delivery:

```bash
docker compose exec p1-meter-monitor python -m p1monitor.reporter --test-email
```

## Configuration

All configuration is read from environment variables, set in `.env`. See
[.env.example](.env.example) for the full list. The important ones:

| Variable | Description | Default |
|----------|-------------|---------|
| `P1_API_URL` | P1 meter JSON endpoint | `http://192.168.1.123/api/v1/data` |
| `COLLECTION_INTERVAL` | Seconds between readings | `60` |
| `P1_EMAIL_TO` | Report recipients (comma-separated) | – |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server and port | – / `587` |
| `SMTP_USER` / `SMTP_PASS` | SMTP credentials | – |
| `SMTP_FROM` / `SMTP_FROM_NAME` | From address and display name | – |
| `ENABLE_MONTHLY_REPORT` | Send report on the 1st of the month | `true` |
| `ENABLE_WEEKLY_EXPORT` | Export a weekly CSV on Mondays | `false` |

Port 465 is detected as implicit SSL; port 587 uses STARTTLS.

## Generating reports manually

Reports default to sending email. Run the reporter inside the container:

```bash
# Send a report for a preset period
docker compose exec p1-meter-monitor python -m p1monitor.reporter --period month
docker compose exec p1-meter-monitor python -m p1monitor.reporter --period this-month

# Custom date range
docker compose exec p1-meter-monitor python -m p1monitor.reporter \
  --start 2025-01-01 --end 2025-01-31

# Write CSV only, no email
docker compose exec p1-meter-monitor python -m p1monitor.reporter \
  --period month --csv-only --output /output/report.csv

# All options
docker compose exec p1-meter-monitor python -m p1monitor.reporter --help
```

Available periods: `today`, `yesterday`, `week`, `this-week`, `last-week`,
`month`, `this-month`, `year`, `this-year`.

## Querying the data

QuestDB's web console is at http://localhost:9000. Data lands in the
`p1_meter_data` table.

```sql
-- Latest reading
SELECT * FROM p1_meter_data ORDER BY timestamp DESC LIMIT 1;

-- Daily consumption over the last week
SELECT timestamp,
       last(total_power_import_kwh) - first(total_power_import_kwh) AS kwh
FROM p1_meter_data
WHERE timestamp > dateadd('d', -7, now())
SAMPLE BY 1d;
```

## Project layout

```
.
├── p1monitor/                  Python package
│   ├── __main__.py             entry point: scheduler + service loop
│   ├── collector.py            polls the P1 API, writes to QuestDB
│   ├── reporter.py             report generation and CLI
│   ├── email_sender.py         SMTP delivery
│   └── templates.py            HTML email templates
├── scripts/                    QuestDB backup and restore helpers
├── docs/                       quick start and backup guides
├── Dockerfile
├── docker-compose.yml          local / development
├── docker-compose.prod.yml     uses a pre-built image from GHCR
├── docker-compose.backup.yml   optional scheduled backup service
├── requirements.txt
└── .env.example
```

The container runs `python -m p1monitor`, which starts the scheduler. The same
package exposes `python -m p1monitor.reporter` for the CLI.

## Operations

```bash
docker compose logs -f p1-meter-monitor   # follow logs
docker compose restart p1-meter-monitor   # restart after a config change
docker compose up -d --build              # rebuild after code changes
docker compose down                       # stop everything
```

## Backups

QuestDB data lives in the `questdb_data` Docker volume. Backup and restore
scripts are in [scripts/](scripts/); see [docs/BACKUP.md](docs/BACKUP.md) for
details.

```bash
./scripts/backup_questdb.sh                       # create a backup
./scripts/restore_questdb.sh <backup_directory>   # restore one
```

## Production deployment

`docker-compose.prod.yml` pulls a pre-built image from the GitHub Container
Registry instead of building locally. The image is published by the workflow in
[.github/workflows/docker-build.yml](.github/workflows/docker-build.yml).

```bash
docker compose -f docker-compose.prod.yml up -d
```

## Notes

- The email templates are written in Dutch and assume a Dutch tariff structure
  (normaal-/daltarief). Adjust [p1monitor/templates.py](p1monitor/templates.py)
  for other languages or layouts.
- QuestDB uses its default `admin`/`quest` credentials and is only reachable on
  the internal Docker network. Change them and restrict exposed ports before
  putting this on an untrusted network.

## License

[MIT](LICENSE). Copyright (c) 2025 Gerwin Kuijntjes.

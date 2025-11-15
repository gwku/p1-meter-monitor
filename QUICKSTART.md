# P1 Monitor - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Configure Environment

```bash
cp .env.example .env
nano .env
```

Set these required values:
- `P1_API_URL` - Your P1 meter API endpoint
- `P1_EMAIL_TO` - Email recipient(s) for reports (comma-separated)
- `SMTP_*` - Your SMTP server details

### 2. Start the System

```bash
docker-compose up -d
```

### 3. Verify Email Works

```bash
docker-compose exec p1-meter-monitor python reporter.py --test-email
```

**That's it!** The system is now:
- ✅ Collecting data every 60 seconds
- ✅ Storing in QuestDB
- ✅ Ready to send monthly reports (1st of month at midnight)

---

## 📧 Email Features

### Test SMTP Configuration

```bash
docker-compose exec p1-meter-monitor python reporter.py --test-email
```

### Multiple Recipients

In `.env`:
```bash
P1_EMAIL_TO=admin@example.com, user@example.com, team@example.com
```

---

## 📊 Generate Reports Manually

### Period Presets

```bash
# Quick reports
docker-compose exec p1-meter-monitor python reporter.py --period today
docker-compose exec p1-meter-monitor python reporter.py --period yesterday
docker-compose exec p1-meter-monitor python reporter.py --period week
docker-compose exec p1-meter-monitor python reporter.py --period this-week
docker-compose exec p1-meter-monitor python reporter.py --period last-week

# Monthly reports
docker-compose exec p1-meter-monitor python reporter.py --period month          # Last complete month
docker-compose exec p1-meter-monitor python reporter.py --period this-month     # Current month so far

# Yearly reports
docker-compose exec p1-meter-monitor python reporter.py --period year           # Last complete year
docker-compose exec p1-meter-monitor python reporter.py --period this-year      # Current year so far
```

### Custom Date Range

```bash
docker-compose exec p1-meter-monitor python reporter.py --start 2025-01-01 --end 2025-01-31
docker-compose exec p1-meter-monitor python reporter.py --start 2025-11-01 --end 2025-11-15
```

### Export to CSV (no email)

```bash
docker-compose exec p1-meter-monitor python reporter.py --period month --csv-only --output /output/report.csv
docker-compose exec p1-meter-monitor python reporter.py --start 2025-01-01 --end 2025-12-31 --csv-only --output /output/year_2025.csv
```

---

## 🔍 Monitoring

### View Logs

```bash
# All logs
docker-compose logs -f

# P1 Monitor only
docker-compose logs -f p1-meter-monitor

# Last 50 lines
docker-compose logs --tail=50 p1-meter-monitor
```

### Check Status

```bash
docker-compose ps
```

### Access QuestDB Console

Open in browser: http://localhost:9000

Example queries:
```sql
-- Latest reading
SELECT * FROM p1_meter_data ORDER BY timestamp DESC LIMIT 1;

-- Today's consumption
SELECT 
    last(total_power_import_kwh) - first(total_power_import_kwh) as kwh_consumed
FROM p1_meter_data
WHERE timestamp > dateadd('d', -1, now());
```

---

## 🛠️ Management

### Restart Services

```bash
docker-compose restart
```

### Stop Services

```bash
docker-compose down
```

### Update Configuration

```bash
# 1. Edit .env
nano .env

# 2. Restart to apply changes
docker-compose restart p1-meter-monitor
```

### Rebuild After Code Changes

```bash
docker-compose up -d --build
```

---

## 🐳 Production Deployment

### Using Pre-built Images (Recommended)

1. Set up GitHub Container Registry:
```bash
export GITHUB_REPOSITORY=yourusername/p1-meter-monitor
export IMAGE_TAG=latest
```

2. Configure environment:
```bash
cp .env.example .env
nano .env
```

3. Use production compose file:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

The GitHub workflow automatically builds and pushes images on every commit to main/master.

### Available Image Tags

- `latest` - Latest stable build from main branch
- `v1.0.0` - Specific version tags
- `main-abc123` - Commit-specific builds

---

## 📋 Common Commands Cheat Sheet

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f p1-meter-monitor

# Test email
docker-compose exec p1-meter-monitor python reporter.py --test-email

# Generate report for last month
docker-compose exec p1-meter-monitor python reporter.py --period month

# Export current month to CSV
docker-compose exec p1-meter-monitor python reporter.py --period this-month --csv-only --output /output/report.csv

# Access QuestDB
http://localhost:9000

# View help
docker-compose exec p1-meter-monitor python reporter.py --help
```

---

## 🆘 Troubleshooting

### Email Not Sending

```bash
# 1. Test configuration
docker-compose exec p1-meter-monitor python reporter.py --test-email

# 2. Check logs
docker-compose logs p1-meter-monitor | grep -i smtp

# 3. Verify .env settings
cat .env | grep SMTP
```

### No Data Being Collected

```bash
# 1. Check P1 API is reachable
docker-compose exec p1-meter-monitor curl $P1_API_URL

# 2. View collector logs
docker-compose logs p1-meter-monitor | grep collector

# 3. Verify QuestDB is running
docker-compose ps questdb
```

### QuestDB Issues

```bash
# Check QuestDB logs
docker-compose logs questdb

# Access QuestDB console
http://localhost:9000

# Restart QuestDB
docker-compose restart questdb
```

---

## 📚 More Information

- Full documentation: See `README.md`
- GitHub workflow: `.github/workflows/docker-build.yml`
- Production deployment: `docker-compose.prod.yml`

---

**Need help?** Check the logs first:
```bash
docker-compose logs -f
```


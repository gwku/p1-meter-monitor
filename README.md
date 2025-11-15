# 🐍 P1 Monitor - Automated Python Solution

**Simple, automated P1 Smart Meter monitoring with QuestDB - everything runs in Docker!**

## ✨ Features

- ⏱️  **Automatic data collection** every 60 seconds
- 📧 **Automated monthly email reports** (HTML + CSV)
- 📊 **QuestDB time series database**
- 🐳 **Fully dockerized** - zero manual intervention
- 🐍 **Pure Python** - clean and maintainable
- 🔄 **Built-in scheduler** - no external cron needed
- 📱 **HTML emails** with live meter readings
- 💾 **Optional weekly CSV exports**

## 🚀 Quick Start

```bash
# 1. Configure
cp .env.example .env
nano .env  # Set your P1_API_URL and SMTP settings

# 2. Start (builds and runs everything)
docker-compose up -d

# 3. Done! 
```

✅ **That's it!** The system will:
- Collect data every minute
- Send monthly reports automatically (1st of month at 9 AM)
- Store everything in QuestDB

## 📁 Project Structure

```
p1-meter-monitor/
├── app.py                  # Main application with scheduler
├── collector.py            # Data collection from P1 API
├── reporter.py             # Report generation
├── email_sender.py         # SMTP email handling
├── email_templates.py      # HTML email templates
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container image
├── docker-compose.yml      # Service orchestration
├── .env.example            # Configuration template
└── README.md               # This file
```

## ⚙️ Configuration

Edit `.env` file:

```bash
# Required
P1_API_URL=http://192.168.178.43/api/v1/data  # Your P1 meter API

# Email Recipients (comma-separated for multiple)
P1_EMAIL_TO=your-email@example.com
# Or multiple: user1@example.com, user2@example.com, user3@example.com

# SMTP (for monthly emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=your-email@gmail.com

# Optional
COLLECTION_INTERVAL=60              # Seconds between collections
ENABLE_MONTHLY_REPORT=true          # Auto-send monthly reports
ENABLE_WEEKLY_EXPORT=false          # Auto-export weekly CSV
```

## 📧 Monthly Reports

**Automatically sent on the 1st of each month at 9:00 AM**

Includes:
- ✅ Period consumption statistics
- ✅ Live meter readings from P1 API
- ✅ HTML formatted email
- ✅ CSV attachment with all data
- ✅ Normaaltarief & Daltarief breakdown

### Multiple Recipients

Send reports to multiple email addresses by separating them with commas:

```bash
# Single recipient
P1_EMAIL_TO=user@example.com

# Multiple recipients
P1_EMAIL_TO=user1@example.com, user2@example.com, admin@example.com
```

All recipients will receive the same report with CSV attachment.

### Disable Auto-Reports

Set in `.env`:
```bash
ENABLE_MONTHLY_REPORT=false
```

## 🛠️ Management

```bash
# Start system
docker-compose up -d

# View logs
docker-compose logs -f p1-meter-monitor

# Stop system
docker-compose down

# Restart
docker-compose restart

# Rebuild after code changes
docker-compose up -d --build
```

## 📊 Access QuestDB

- **Web Console**: http://localhost:9000
- **PostgreSQL**: localhost:8812
- **InfluxDB**: localhost:9009

### Example Queries

```sql
-- Latest reading
SELECT * FROM p1_meter_data 
ORDER BY timestamp DESC LIMIT 1;

-- Last 24 hours
SELECT * FROM p1_meter_data 
WHERE timestamp > dateadd('h', -24, now());

-- Daily consumption
SELECT 
    timestamp,
    last(total_power_import_kwh) - first(total_power_import_kwh) as daily_kwh
FROM p1_meter_data
WHERE timestamp > dateadd('d', -7, now())
SAMPLE BY 1d;
```

## 🔧 Manual Operations

### Test Email Configuration

Test your SMTP settings before generating reports:

```bash
# Send a test email to verify SMTP configuration
docker-compose exec p1-meter-monitor python reporter.py --test-email
```

This will send a beautifully formatted test email showing:
- SMTP configuration details
- All configured recipients
- Timestamp and system information
- Confirmation that everything is working

### Generate Reports for Any Period

The reporter supports flexible period selection with presets and custom date ranges:

```bash
# Period presets
docker-compose exec p1-meter-monitor python reporter.py --period today
docker-compose exec p1-meter-monitor python reporter.py --period yesterday
docker-compose exec p1-meter-monitor python reporter.py --period week          # Last 7 days
docker-compose exec p1-meter-monitor python reporter.py --period this-week     # Current week (Mon-now)
docker-compose exec p1-meter-monitor python reporter.py --period last-week     # Previous week
docker-compose exec p1-meter-monitor python reporter.py --period month         # Last complete month
docker-compose exec p1-meter-monitor python reporter.py --period this-month    # Current month so far
docker-compose exec p1-meter-monitor python reporter.py --period year          # Last complete year
docker-compose exec p1-meter-monitor python reporter.py --period this-year     # Current year so far

# Custom date range
docker-compose exec p1-meter-monitor python reporter.py --start 2025-01-01 --end 2025-01-31
docker-compose exec p1-meter-monitor python reporter.py --start 2025-11-01 --end 2025-11-15

# Export to CSV only (no email)
docker-compose exec p1-meter-monitor python reporter.py --period month --csv-only --output /output/report.csv
docker-compose exec p1-meter-monitor python reporter.py --start 2025-01-01 --end 2025-01-31 --csv-only --output /output/jan2025.csv
```

### Show Available Options

```bash
docker-compose exec p1-meter-monitor python reporter.py --help
```

## 📅 Automation Schedule

Built into the container:

| Task | Schedule | Configurable |
|------|----------|--------------|
| Data Collection | Every 60s | `COLLECTION_INTERVAL` |
| Monthly Report | 1st at 9:00 AM | `ENABLE_MONTHLY_REPORT` |
| Weekly Export | Mondays at 8:00 AM | `ENABLE_WEEKLY_EXPORT` |

**No external cron needed!** All scheduling is handled by APScheduler inside the container.

## 🐳 Docker Services

- **questdb** - Time series database
  - Port 9000 (Web Console)
  - Port 8812 (PostgreSQL)
  - Persistent storage in Docker volume

- **p1-meter-monitor** - Python application
  - Auto-restarts on failure
  - Built-in scheduler
  - Automatic reporting

## 💾 Data Storage

- **Database**: Docker volume `questdb_data`
- **CSV Exports**: `./output/` directory
- **Logs**: `./logs/` directory

### Backup Data

```bash
# Backup QuestDB
docker run --rm -v p1-meter-monitor_questdb_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/questdb-backup-$(date +%Y%m%d).tar.gz /data

# Restore
docker run --rm -v p1-meter-monitor_questdb_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/questdb-backup-YYYYMMDD.tar.gz -C /
```

## 🔍 Troubleshooting

### Check Logs

```bash
docker-compose logs -f p1-meter-monitor
```

### System Not Collecting Data

1. Check P1 API is accessible:
```bash
docker-compose exec p1-meter-monitor curl -s $P1_API_URL
```

2. Check QuestDB connection:
```bash
docker-compose logs questdb
```

### Emails Not Sending

1. Verify SMTP settings in `.env`
2. Check application logs for errors
3. Test SMTP credentials

### Restart Services

```bash
docker-compose restart
```

## 📈 Storage Requirements

- **Per minute**: ~200 bytes
- **Per hour**: ~12 KB
- **Per day**: ~288 KB
- **Per month**: ~9 MB
- **Per year**: ~108 MB

## 🎯 Advantages Over Bash Version

✅ **Simpler** - Single Python app vs multiple bash scripts  
✅ **Automated** - Built-in scheduler, no external cron  
✅ **Maintainable** - Python is easier to extend  
✅ **Robust** - Better error handling  
✅ **Clean** - 7 files vs 25+ files  
✅ **Portable** - Pure Docker solution  

## 🔐 Security

- SMTP credentials in `.env` (never commit!)
- Services on isolated Docker network
- QuestDB not exposed to internet
- Read-only mounts where possible

## 📦 Dependencies

- Python 3.11
- requests - HTTP client
- psycopg2 - PostgreSQL/QuestDB driver
- apscheduler - Job scheduling
- jinja2 - HTML templates
- python-dotenv - Environment variables

## 🚢 Production Deployment

1. Clone to server
2. Configure `.env`
3. Run `docker-compose up -d`
4. Monitor with `docker-compose logs`

Done! Everything runs automatically.

## 🆘 Support

1. Check logs: `docker-compose logs`
2. Verify `.env` configuration
3. Test P1 API connectivity
4. Check QuestDB web console

---

**Simple, automated, and reliable P1 meter monitoring!** 🐍🐳📊


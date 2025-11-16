# QuestDB Backup Guide

This guide explains how to backup and restore your QuestDB database.

## Quick Start

### Manual Backup

```bash
# Run backup script
./backup_questdb.sh

# Backups are stored in ./backups/questdb_backup_YYYYMMDD_HHMMSS/
```

### Automated Daily Backups

#### Option 1: Using System Cron (Recommended)

Add to your crontab (`crontab -e`):

```bash
# Run QuestDB backup daily at 2:00 AM
0 2 * * * cd /path/to/p1-meter-monitor && ./backup_questdb.sh >> ./backups/backup.log 2>&1
```

#### Option 2: Using Docker Cron Container

```bash
# Start backup service
docker-compose -f docker-compose.yml -f docker-compose.backup.yml up -d questdb-backup
```

## Configuration

Set environment variables to customize backup behavior:

```bash
export BACKUP_DIR="./backups"           # Backup storage directory
export RETENTION_DAYS=30                # Keep backups for 30 days
export VOLUME_NAME="p1-meter-monitor_questdb_data"  # Docker volume name
export QUESTDB_CONTAINER="p1-questdb"  # QuestDB container name
```

## Restore from Backup

```bash
# List available backups
ls -la backups/

# Restore a specific backup
./restore_questdb.sh questdb_backup_20251116_020000
```

**⚠️ Warning:** Restore will replace all current data in QuestDB!

## How It Works

This backup solution follows the [official QuestDB backup procedure](https://questdb.com/docs/operations/backup/):

1. **Checkpoint Creation**: Issues `CHECKPOINT CREATE` SQL command via PostgreSQL protocol (port 8812) using the `p1-meter-monitor` container to ensure data consistency
2. **Volume Backup**: Copies the entire QuestDB root directory (including `db`, `snapshot`, and all other directories) to a compressed tar archive
3. **Checkpoint Release**: Issues `CHECKPOINT RELEASE` SQL command (critical: must release even if backup fails)
4. **Cleanup**: Automatically removes backups older than retention period

**Important Notes:**
- QuestDB remains available for reads and writes during checkpoint mode
- The checkpoint must be released even if the backup fails (script will exit with error if release fails)
- Backups include the entire root directory, not just data files
- Uses PostgreSQL protocol (recommended) with HTTP API fallback

## Backup Storage

- **Location**: `./backups/questdb_backup_YYYYMMDD_HHMMSS/`
- **Format**: Compressed tar.gz archive
- **Size**: Typically 10-50 MB per backup (depends on data volume)

## Backup Retention

By default, backups older than 30 days are automatically deleted. Adjust `RETENTION_DAYS` to change this.

## Troubleshooting

### Backup Fails

1. Check QuestDB container is running:
   ```bash
   docker ps | grep questdb
   ```

2. Check volume exists:
   ```bash
   docker volume ls | grep questdb
   ```

3. Check disk space:
   ```bash
   df -h
   ```

### Restore Fails

1. Ensure QuestDB container is stopped before restore
2. Verify backup file exists and is not corrupted
3. Check you have write permissions to the volume
4. Verify QuestDB version matches the backup version (same major version required)
5. Check QuestDB logs for recovery errors: `docker logs p1-questdb`
6. If `_restore` file still exists after startup, recovery failed - check logs for details

## Best Practices

1. **Test Restores**: Regularly test restoring from backups to ensure they work
2. **Offsite Backups**: Copy backups to external storage or cloud storage
3. **Monitor Disk Space**: Ensure backup directory has sufficient space
4. **Backup Before Updates**: Always backup before updating QuestDB or the application

## Example: Offsite Backup to S3

```bash
# After local backup, sync to S3
aws s3 sync ./backups s3://your-bucket/p1-meter-backups/
```

## Example: Backup to Remote Server

```bash
# Copy backup to remote server
scp -r backups/questdb_backup_* user@remote-server:/backups/p1-meter/
```


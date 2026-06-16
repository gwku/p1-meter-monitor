# QuestDB backup and restore

How to back up and restore the QuestDB database used by this project.

Run the scripts from the repository root so that relative paths such as
`./backups` resolve correctly.

## Manual backup

```bash
./scripts/backup_questdb.sh
```

Backups are written to `./backups/questdb_backup_YYYYMMDD_HHMMSS/`.

## Automated daily backups

### Option 1: system cron (recommended)

Add to your crontab (`crontab -e`):

```bash
# Daily at 02:00
0 2 * * * cd /path/to/p1-meter-monitor && ./scripts/backup_questdb.sh >> ./backups/backup.log 2>&1
```

### Option 2: Docker cron container

```bash
docker compose -f docker-compose.yml -f docker-compose.backup.yml up -d questdb-backup
```

## Configuration

The scripts read these environment variables:

```bash
export BACKUP_DIR="./backups"                       # backup storage directory
export RETENTION_DAYS=30                             # days to keep backups
export VOLUME_NAME="p1-meter-monitor_questdb_data"   # Docker volume name
export QUESTDB_CONTAINER="p1-questdb"                # QuestDB container name
```

## Restore

```bash
# List available backups
ls -la backups/

# Restore a specific backup
./scripts/restore_questdb.sh questdb_backup_20251116_020000
```

Warning: restore replaces all current data in QuestDB.

## How it works

This follows the [official QuestDB backup procedure](https://questdb.com/docs/operations/backup/):

1. **Checkpoint create** — issues `CHECKPOINT CREATE` over the PostgreSQL wire
   protocol (port 8812) so the on-disk state is consistent.
2. **Volume backup** — copies the entire QuestDB root directory into a
   compressed tar archive.
3. **Checkpoint release** — issues `CHECKPOINT RELEASE`. This must run even if
   the backup fails; the script errors out if it cannot release.
4. **Cleanup** — removes backups older than the retention period.

QuestDB stays available for reads and writes while a checkpoint is active.

## Troubleshooting

Backup fails:

```bash
docker ps | grep questdb         # container running?
docker volume ls | grep questdb  # volume exists?
df -h                            # disk space?
```

Restore fails:

- Ensure the QuestDB container is stopped before restoring.
- Verify the backup archive exists and is not corrupted.
- The QuestDB major version must match the one the backup was made with.
- Check recovery logs: `docker logs p1-questdb`.
- If a `_restore` file remains after startup, recovery did not complete — check
  the logs.

## Off-site copies

```bash
# Sync to S3
aws s3 sync ./backups s3://your-bucket/p1-meter-backups/

# Copy to a remote host
scp -r backups/questdb_backup_* user@remote-server:/backups/p1-meter/
```

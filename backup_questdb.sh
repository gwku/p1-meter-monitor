#!/bin/bash
# QuestDB Daily Backup Script
# Creates a checkpoint and backs up the QuestDB volume

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
VOLUME_NAME="${VOLUME_NAME:-p1-meter-monitor_questdb_data}"
QUESTDB_CONTAINER="${QUESTDB_CONTAINER:-p1-questdb}"
MONITOR_CONTAINER="${MONITOR_CONTAINER:-p1-meter-monitor}"

# Create backup directory with date
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/questdb_backup_${DATE}"

echo "=========================================="
echo "QuestDB Backup Started: $(date)"
echo "=========================================="

# Create backup directory
mkdir -p "${BACKUP_PATH}"

# Check if QuestDB container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${QUESTDB_CONTAINER}$"; then
    echo "ERROR: QuestDB container '${QUESTDB_CONTAINER}' is not running!"
    exit 1
fi

# Create checkpoint (ensures data consistency)
# Using PostgreSQL protocol via p1-meter-monitor container (has Python + psycopg2)
echo "Creating QuestDB checkpoint..."
if docker exec "${MONITOR_CONTAINER}" python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(host='questdb', port=8812, user='admin', password='quest', database='qdb', connect_timeout=5)
    with conn.cursor() as cur:
        cur.execute('CHECKPOINT CREATE;')
        conn.commit()
    conn.close()
    exit(0)
except Exception as e:
    exit(1)
" > /dev/null 2>&1; then
    echo "✓ Checkpoint created (via PostgreSQL protocol)"
    CHECKPOINT_CREATED=true
else
    echo "⚠ Warning: Could not create checkpoint via PostgreSQL protocol"
    echo "  Attempting HTTP API fallback..."
    if docker exec "${QUESTDB_CONTAINER}" curl -s -G "http://localhost:9000/exec" --data-urlencode "query=CHECKPOINT CREATE" > /dev/null 2>&1; then
        echo "✓ Checkpoint created (via HTTP API)"
        CHECKPOINT_CREATED=true
    else
        echo "⚠ ERROR: Could not create checkpoint!"
        echo "  Backup will continue but data consistency is not guaranteed."
        echo "  Make sure QuestDB container is running and accessible."
        CHECKPOINT_CREATED=false
    fi
fi

# Backup the volume (entire root directory including db, snapshot, etc.)
# According to QuestDB docs: "Make sure to back up the entire server root directory,
# including the db, snapshot, and all other directories."
echo "Backing up QuestDB root directory..."
docker run --rm \
    -v "${VOLUME_NAME}:/source:ro" \
    -v "$(pwd)/${BACKUP_PATH}:/backup" \
    alpine:latest \
    sh -c "cd /source && tar czf /backup/questdb_data.tar.gz ."

# Release checkpoint (CRITICAL: must release even if backup failed)
# According to QuestDB docs: "It is very important to exit the checkpoint mode 
# regardless of whether the copy operation succeeded or failed!"
if [ "$CHECKPOINT_CREATED" = true ]; then
    echo "Releasing checkpoint..."
    if docker exec "${MONITOR_CONTAINER}" python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(host='questdb', port=8812, user='admin', password='quest', database='qdb', connect_timeout=5)
    with conn.cursor() as cur:
        cur.execute('CHECKPOINT RELEASE;')
        conn.commit()
    conn.close()
    exit(0)
except Exception as e:
    exit(1)
" > /dev/null 2>&1; then
        echo "✓ Checkpoint released (via PostgreSQL protocol)"
    elif docker exec "${QUESTDB_CONTAINER}" curl -s -G "http://localhost:9000/exec" --data-urlencode "query=CHECKPOINT RELEASE" > /dev/null 2>&1; then
        echo "✓ Checkpoint released (via HTTP API)"
    else
        echo "⚠ ERROR: Could not release checkpoint!"
        echo "  QuestDB may remain in checkpoint mode. Manual intervention required."
        echo "  Try manually: docker exec ${MONITOR_CONTAINER} python3 -c \"import psycopg2; conn = psycopg2.connect(host='questdb', port=8812, user='admin', password='quest', database='qdb'); cur = conn.cursor(); cur.execute('CHECKPOINT RELEASE;'); conn.commit(); conn.close()\""
        exit 1
    fi
fi

# Get backup size
BACKUP_SIZE=$(du -h "${BACKUP_PATH}/questdb_data.tar.gz" | cut -f1)
echo "✓ Backup completed: ${BACKUP_PATH}/questdb_data.tar.gz (${BACKUP_SIZE})"

# Clean up old backups (keep last N days)
if [ -d "${BACKUP_DIR}" ]; then
    echo "Cleaning up backups older than ${RETENTION_DAYS} days..."
    find "${BACKUP_DIR}" -name "questdb_backup_*" -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} + 2>/dev/null || true
    echo "✓ Cleanup completed"
fi

echo "=========================================="
echo "Backup completed successfully: $(date)"
echo "=========================================="


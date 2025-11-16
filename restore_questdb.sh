#!/bin/bash
# QuestDB Restore Script
# Restores QuestDB from a backup

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
VOLUME_NAME="${VOLUME_NAME:-p1-meter-monitor_questdb_data}"
QUESTDB_CONTAINER="${QUESTDB_CONTAINER:-p1-questdb}"

# Check arguments
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_directory_name>"
    echo ""
    echo "Available backups:"
    ls -1d "${BACKUP_DIR}"/questdb_backup_* 2>/dev/null | sed 's|.*/||' || echo "  No backups found"
    exit 1
fi

BACKUP_NAME="$1"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

if [ ! -d "${BACKUP_PATH}" ]; then
    echo "ERROR: Backup directory '${BACKUP_PATH}' not found!"
    exit 1
fi

BACKUP_FILE="${BACKUP_PATH}/questdb_data.tar.gz"
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file '${BACKUP_FILE}' not found!"
    exit 1
fi

echo "=========================================="
echo "QuestDB Restore Started: $(date)"
echo "=========================================="
echo "WARNING: This will replace all data in QuestDB!"
echo "Backup: ${BACKUP_NAME}"
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Stop QuestDB container
echo "Stopping QuestDB container..."
docker stop "${QUESTDB_CONTAINER}" || true

# Restore the volume (entire root directory)
echo "Restoring QuestDB root directory..."
docker run --rm \
    -v "${VOLUME_NAME}:/target" \
    -v "$(pwd)/${BACKUP_PATH}:/backup:ro" \
    alpine:latest \
    sh -c "rm -rf /target/* && cd /target && tar xzf /backup/questdb_data.tar.gz"

echo "✓ Root directory restored"

# Create _restore trigger file (required by QuestDB for recovery)
# According to QuestDB docs: "Touch the _restore file in the root directory"
echo "Creating _restore trigger file..."
docker run --rm \
    -v "${VOLUME_NAME}:/target" \
    alpine:latest \
    touch /target/_restore

echo "✓ _restore trigger file created"

# Start QuestDB container
echo "Starting QuestDB container..."
docker start "${QUESTDB_CONTAINER}" || true

# Wait a moment for QuestDB to start recovery
echo "Waiting for QuestDB recovery process..."
sleep 5

# Check if recovery was successful (QuestDB removes _restore file on success)
if docker run --rm -v "${VOLUME_NAME}:/target" alpine:latest test -f /target/_restore; then
    echo "⚠ WARNING: _restore file still exists - recovery may have failed!"
    echo "  Check QuestDB logs: docker logs ${QUESTDB_CONTAINER}"
else
    echo "✓ Recovery completed successfully (_restore file removed)"
fi

echo "=========================================="
echo "Restore completed: $(date)"
echo "=========================================="
echo "Note: Check QuestDB logs to verify recovery was successful."
echo "  docker logs ${QUESTDB_CONTAINER}"


#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${ROOT}/backups"
STAMP="$(date +%Y%m%d-%H%M)"
DB_FILE="${ROOT}/db.sqlite3"
MEDIA_DIR="${ROOT}/media"

mkdir -p "${BACKUP_DIR}"

if [[ ! -f "${DB_FILE}" ]]; then
  echo "База не найдена: ${DB_FILE}" >&2
  exit 1
fi

cp "${DB_FILE}" "${BACKUP_DIR}/db-${STAMP}.sqlite3"

if [[ ! -d "${MEDIA_DIR}" ]]; then
  echo "Папка media не найдена: ${MEDIA_DIR}" >&2
  exit 1
fi

tar -czf "${BACKUP_DIR}/media-${STAMP}.tar.gz" -C "${ROOT}" media

find "${BACKUP_DIR}" -type f -mtime +7 -delete

echo "Готово: ${BACKUP_DIR}/db-${STAMP}.sqlite3"
echo "Готово: ${BACKUP_DIR}/media-${STAMP}.tar.gz"

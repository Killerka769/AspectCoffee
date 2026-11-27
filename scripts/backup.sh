#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${ROOT}/backups"
STAMP="$(date +%Y%m%d-%H%M)"
MEDIA_DIR="${ROOT}/media"

# Сайт в проде пишет в data/db.sqlite3 (том ./data). db.sqlite3 в корне — только локальный dev.
if [[ -f "${ROOT}/data/db.sqlite3" ]]; then
  DB_FILE="${ROOT}/data/db.sqlite3"
elif [[ -f "${ROOT}/db.sqlite3" ]]; then
  DB_FILE="${ROOT}/db.sqlite3"
else
  DB_FILE="${ROOT}/data/db.sqlite3"
fi

mkdir -p "${BACKUP_DIR}"

if [[ ! -f "${DB_FILE}" ]]; then
  echo "База не найдена: ${DB_FILE}" >&2
  exit 1
fi

DB_COPY="${BACKUP_DIR}/db-${STAMP}.sqlite3"
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "${DB_FILE}" ".backup '${DB_COPY}'"
else
  cp "${DB_FILE}" "${DB_COPY}"
fi

if [[ ! -d "${MEDIA_DIR}" ]]; then
  echo "Папка media не найдена: ${MEDIA_DIR}" >&2
  exit 1
fi

tar -czf "${BACKUP_DIR}/media-${STAMP}.tar.gz" -C "${ROOT}" media

find "${BACKUP_DIR}" -type f -mtime +7 -delete

echo "Готово: ${BACKUP_DIR}/db-${STAMP}.sqlite3"
echo "Готово: ${BACKUP_DIR}/media-${STAMP}.tar.gz"

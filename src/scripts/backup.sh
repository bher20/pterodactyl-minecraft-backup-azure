#!/usr/bin/bash

BACKUP_DIR=""
AZURE_STORAGE_CONTAINER="minecraft"
AZURE_STORAGE_BLOB_PREFIX="minecraft-01"

while getopts "b:c:p:" opt; do
  case ${opt} in
    b )
      BACKUP_DIR=${OPTARG}
      ;;
    c )
      AZURE_STORAGE_CONTAINER=${OPTARG}
      ;;
    p )
      AZURE_STORAGE_BLOB_PREFIX=${OPTARG}
      ;;
    \? )
      echo "Usage: cmd [-b] backup_dir [-c] azure_storage_container [-p] azure_storage_blob_prefix"
      exit 1
      ;;
  esac
done

if [ -z "${BACKUP_DIR}" ] || [ -z "${AZURE_STORAGE_CONTAINER}" ] || [ -z "${AZURE_STORAGE_BLOB_PREFIX}" ]; then
  echo "Usage: cmd [-b] backup_dir [-c] azure_storage_container [-p] azure_storage_blob_prefix"
  exit 1
fi

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

function azure {
  ARCHIVE="${1}"
  archive_base_name=$(basename ${ARCHIVE})

  source "${SCRIPT_DIR}/.azure-creds"

  az storage blob upload  --no-progress --file "${ARCHIVE}" -c $AZURE_STORAGE_CONTAINER -n "${AZURE_STORAGE_BLOB_PREFIX}/${archive_base_name}"
}

function get_latest_backup {
  BACKUP_DIR=${1}

  DIR="${BACKUP_DIR}/$(ls -Art ${BACKUP_DIR} | tail -n 1)"

  find "${BACKUP_DIR}" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" "
}



for filename in $BACKUP_DIR/*.tar.gz; do
    [ -e "$filename" ] || continue
    azure "${filename}"
done
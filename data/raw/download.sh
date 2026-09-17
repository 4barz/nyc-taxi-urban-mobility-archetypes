#!/usr/bin/env bash
# Downloads the six monthly NYC TLC Yellow Taxi Trip Record Parquet files
# (January-June 2023) plus the taxi zone lookup table, into data/raw/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRIPS_DIR="${SCRIPT_DIR}/nyc-taxi-trips"
mkdir -p "${TRIPS_DIR}"

for m in 01 02 03 04 05 06; do
  url="https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-${m}.parquet"
  out="${TRIPS_DIR}/yellow_tripdata_2023-${m}.parquet"
  echo "Downloading ${url}"
  curl -sS --retry 3 -o "${out}" "${url}"
done

curl -sS -o "${SCRIPT_DIR}/taxi_zone_lookup.csv" \
  "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"

echo "Done. Files saved under ${SCRIPT_DIR}"

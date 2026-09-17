"""Shared configuration and constants for the NYC taxi urban mobility pipeline."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "nyc-taxi-trips"
ZONE_LOOKUP_PATH = PROJECT_ROOT / "data" / "raw" / "taxi_zone_lookup.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"
RESULTS_JSON = PROCESSED_DIR / "results_summary.json"

MONTHS = ["01", "02", "03", "04", "05", "06"]
MONTH_FILES = [RAW_DIR / f"yellow_tripdata_2023-{m}.parquet" for m in MONTHS]

RANDOM_STATE = 42

# ---------------------------------------------------------------------------
# Layer 1 — quality filter thresholds (per proposal Section 4, Layer 1)
# ---------------------------------------------------------------------------
MIN_DURATION_MIN, MAX_DURATION_MIN = 1, 180
MIN_DISTANCE_MI, MAX_DISTANCE_MI = 0.1, 60
MIN_FARE, MAX_FARE = 2.50, 500.0
MAX_SPEED_MPH = 80.0
MIN_ZONE_ID, MAX_ZONE_ID = 1, 263

# columns actually needed from the raw TLC parquet files
RAW_COLUMNS = [
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "trip_distance",
    "PULocationID",
    "DOLocationID",
    "payment_type",
    "fare_amount",
    "tip_amount",
]

# target size of the trip-level random sample retained for Layer 5 (Isolation Forest)
ISOFOREST_SAMPLE_TARGET = 500_000

# night hours (inclusive) and rush hours used for zone behavioural features
NIGHT_HOURS = {22, 23, 0, 1, 2, 3, 4, 5}
RUSH_HOURS = {7, 8, 9, 16, 17, 18, 19}
CASH_PAYMENT_TYPE = 2

# ---------------------------------------------------------------------------
# Layer 2 — K-Means zone feature set
# ---------------------------------------------------------------------------
ZONE_FEATURES = [
    "log_trip_count",
    "mean_fare",
    "mean_distance",
    "mean_duration",
    "mean_speed",
    "mean_tip_pct",
    "pct_weekend",
    "pct_cash",
    "pct_night",
    "pct_rush",
]
KMEANS_K_RANGE = range(2, 9)

# ---------------------------------------------------------------------------
# Layer 3 — K-Shape rhythm clustering
# ---------------------------------------------------------------------------
MIN_TRIPS_PER_DAY_FOR_RHYTHM = 10  # zones below this average are excluded (sparsity)
N_DAYS_IN_STUDY = 181  # 2023-01-01 .. 2023-06-30
KSHAPE_K_RANGE = range(2, 7)

# ---------------------------------------------------------------------------
# Layer 4 — Non-negative Tucker decomposition
# ---------------------------------------------------------------------------
TUCKER_PRIMARY_RANK = (6, 4, 2)
TUCKER_CANDIDATE_RANKS = [(4, 3, 2), (5, 4, 2), (6, 4, 2), (8, 4, 2)]

# ---------------------------------------------------------------------------
# Layer 5 — Isolation Forest
# ---------------------------------------------------------------------------
ISOFOREST_FEATURES = [
    "trip_distance",
    "duration_min",
    "fare_amount",
    "speed_mph",
    "tip_pct",
    "hour",
    "is_weekend",
]
ISOFOREST_N_TREES = 200
ISOFOREST_CONTAMINATION = 0.02

# ---------------------------------------------------------------------------
# Layer 6 — UMAP
# ---------------------------------------------------------------------------
UMAP_N_NEIGHBORS = 10
UMAP_MIN_DIST = 0.25

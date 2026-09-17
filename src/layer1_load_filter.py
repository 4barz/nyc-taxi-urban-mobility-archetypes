"""Layer 1 — Data loading, quality filtering, and streaming feature aggregation.

Rather than materialising the full ~19.5M-trip dataset in memory at once, this
module streams through the six monthly Parquet files one at a time (columnar,
selective loads via PyArrow/Pandas), applies the domain-knowledge quality
filters, engineers trip-level features, and folds the results into three
compact artefacts that are all that later layers require:

    1. zone_profile   — per-zone aggregate statistics (263 rows)
    2. tensor_counts   — Zone x Hour x DayType trip-count tensor (263, 24, 2)
    3. sample_trips    — a ~500k-row random sample of individual trips, with
                          trip-level features, for Layer 5 (Isolation Forest)

This keeps peak memory bounded to a single month's frame (~3M rows) at a
time, which is the Big-Data-appropriate way to compute exact zone/tensor
aggregates and an unbiased trip-level sample without ever holding all 19.5M
rows simultaneously.
"""

import gc
import json
import time

import numpy as np
import pandas as pd

from . import config


def _load_month(path):
    df = pd.read_parquet(path, columns=config.RAW_COLUMNS)
    return df


def _engineer_and_filter(df):
    raw_count = len(df)

    duration_min = (
        df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]
    ).dt.total_seconds() / 60.0
    df = df.assign(duration_min=duration_min)

    with np.errstate(divide="ignore", invalid="ignore"):
        speed_mph = df["trip_distance"] / (df["duration_min"] / 60.0)
    df = df.assign(speed_mph=speed_mph.replace([np.inf, -np.inf], np.nan))

    mask = (
        df["duration_min"].between(config.MIN_DURATION_MIN, config.MAX_DURATION_MIN)
        & df["trip_distance"].between(config.MIN_DISTANCE_MI, config.MAX_DISTANCE_MI)
        & df["fare_amount"].between(config.MIN_FARE, config.MAX_FARE)
        & df["speed_mph"].le(config.MAX_SPEED_MPH)
        & df["PULocationID"].between(config.MIN_ZONE_ID, config.MAX_ZONE_ID)
        & df["DOLocationID"].between(config.MIN_ZONE_ID, config.MAX_ZONE_ID)
    )
    df = df.loc[mask].copy()

    df["tip_pct"] = (df["tip_amount"] / df["fare_amount"]).clip(lower=0, upper=2)
    df["hour"] = df["tpep_pickup_datetime"].dt.hour
    df["dow"] = df["tpep_pickup_datetime"].dt.dayofweek  # 0=Mon
    df["is_weekend"] = (df["dow"] >= 5).astype(np.int8)
    df["is_cash"] = (df["payment_type"] == config.CASH_PAYMENT_TYPE).astype(np.int8)
    df["is_night"] = df["hour"].isin(config.NIGHT_HOURS).astype(np.int8)
    df["is_rush"] = df["hour"].isin(config.RUSH_HOURS).astype(np.int8)

    return df, raw_count, len(df)


def _accumulate_zone_stats(df, zone_sums):
    g = df.groupby("PULocationID")
    agg = g.agg(
        count=("fare_amount", "size"),
        sum_fare=("fare_amount", "sum"),
        sum_distance=("trip_distance", "sum"),
        sum_duration=("duration_min", "sum"),
        sum_speed=("speed_mph", "sum"),
        sum_tip_pct=("tip_pct", "sum"),
        sum_weekend=("is_weekend", "sum"),
        sum_cash=("is_cash", "sum"),
        sum_night=("is_night", "sum"),
        sum_rush=("is_rush", "sum"),
    )
    for zone_id, row in agg.iterrows():
        z = zone_sums.setdefault(
            zone_id,
            dict(
                count=0,
                sum_fare=0.0,
                sum_distance=0.0,
                sum_duration=0.0,
                sum_speed=0.0,
                sum_tip_pct=0.0,
                sum_weekend=0,
                sum_cash=0,
                sum_night=0,
                sum_rush=0,
            ),
        )
        for k in z:
            z[k] += row[k]


def _accumulate_tensor(df, tensor_counts):
    g = df.groupby(["PULocationID", "hour", "is_weekend"]).size()
    for (zone_id, hour, is_weekend), cnt in g.items():
        tensor_counts[int(zone_id), int(hour), int(is_weekend)] += cnt


def run_layer1(verbose=True):
    """Stream through all six months and produce the Layer 1 artefacts."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    zone_sums = {}
    tensor_counts = np.zeros((config.MAX_ZONE_ID + 1, 24, 2), dtype=np.float64)
    samples = []

    raw_total = 0
    filtered_total = 0
    t0 = time.time()

    n_months = len(config.MONTH_FILES)
    for i, path in enumerate(config.MONTH_FILES, start=1):
        if verbose:
            print(f"[Layer 1] Loading {path.name} ({i}/{n_months}) ...")
        df = _load_month(path)
        df, raw_c, filt_c = _engineer_and_filter(df)
        raw_total += raw_c
        filtered_total += filt_c

        _accumulate_zone_stats(df, zone_sums)
        _accumulate_tensor(df, tensor_counts)

        # unbiased trip-level sample for Layer 5, proportional across months
        frac = min(1.0, config.ISOFOREST_SAMPLE_TARGET / (filt_c * n_months))
        s = df.sample(frac=frac, random_state=config.RANDOM_STATE)
        samples.append(
            s[
                [
                    "PULocationID",
                    "trip_distance",
                    "duration_min",
                    "fare_amount",
                    "speed_mph",
                    "tip_pct",
                    "hour",
                    "is_weekend",
                ]
            ].copy()
        )

        if verbose:
            print(
                f"    raw={raw_c:,}  kept={filt_c:,}  "
                f"retention={filt_c/raw_c:.1%}  sample_frac={frac:.4f}"
            )
        del df
        gc.collect()

    sample_trips = pd.concat(samples, ignore_index=True)
    del samples
    gc.collect()

    # ---- finalise zone profile ----
    rows = []
    for zone_id, z in zone_sums.items():
        n = z["count"]
        rows.append(
            dict(
                zone_id=zone_id,
                trip_count=n,
                log_trip_count=np.log1p(n),
                mean_fare=z["sum_fare"] / n,
                mean_distance=z["sum_distance"] / n,
                mean_duration=z["sum_duration"] / n,
                mean_speed=z["sum_speed"] / n,
                mean_tip_pct=z["sum_tip_pct"] / n,
                pct_weekend=z["sum_weekend"] / n,
                pct_cash=z["sum_cash"] / n,
                pct_night=z["sum_night"] / n,
                pct_rush=z["sum_rush"] / n,
            )
        )
    zone_profile = pd.DataFrame(rows).sort_values("zone_id").reset_index(drop=True)

    zone_lookup = pd.read_csv(config.ZONE_LOOKUP_PATH)
    zone_lookup = zone_lookup.rename(columns={"LocationID": "zone_id"})
    zone_profile = zone_profile.merge(
        zone_lookup[["zone_id", "Borough", "Zone", "service_zone"]],
        on="zone_id",
        how="left",
    )

    elapsed = time.time() - t0
    qc = dict(
        raw_trip_count=raw_total,
        filtered_trip_count=filtered_total,
        retention_rate=filtered_total / raw_total,
        n_zones_with_data=len(zone_profile),
        sample_trip_count=len(sample_trips),
        elapsed_seconds=round(elapsed, 1),
    )
    if verbose:
        print(f"[Layer 1] Done in {elapsed:.1f}s. QC: {qc}")

    zone_profile.to_parquet(config.PROCESSED_DIR / "zone_profile.parquet")
    np.save(config.PROCESSED_DIR / "tensor_counts.npy", tensor_counts)
    sample_trips.to_parquet(config.PROCESSED_DIR / "sample_trips.parquet")
    with open(config.PROCESSED_DIR / "layer1_qc.json", "w") as f:
        json.dump(qc, f, indent=2)

    return zone_profile, tensor_counts, sample_trips, qc


if __name__ == "__main__":
    run_layer1()

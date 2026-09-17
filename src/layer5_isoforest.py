"""Layer 5 — Isolation Forest trip-level anomaly detection (RQ4)."""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from scipy.stats import pearsonr

from . import config


def _fit_and_score(X, random_state=config.RANDOM_STATE):
    model = IsolationForest(
        n_estimators=config.ISOFOREST_N_TREES,
        contamination=config.ISOFOREST_CONTAMINATION,
        random_state=random_state,
        n_jobs=-1,
    )
    labels = model.fit_predict(X)  # -1 = anomaly, 1 = normal
    return model, labels


def run_layer5(sample_trips: pd.DataFrame):
    X = sample_trips[config.ISOFOREST_FEATURES].values
    model, labels = _fit_and_score(X)

    df = sample_trips.copy()
    df["is_anomaly"] = labels == -1

    anomalies = df[df.is_anomaly]
    normal = df[~df.is_anomaly]

    zone_rate = (
        df.groupby("PULocationID")["is_anomaly"]
        .agg(anomaly_rate="mean", n_sampled="size")
        .reset_index()
        .rename(columns={"PULocationID": "zone_id"})
    )

    # stability check: split sample in half, refit independently, compare
    # per-zone anomaly rates between the two halves (proposal Section 5/10)
    rng = np.random.RandomState(config.RANDOM_STATE)
    idx = rng.permutation(len(df))
    half_a, half_b = idx[: len(idx) // 2], idx[len(idx) // 2 :]

    def _half_rate(sub_idx):
        sub = df.iloc[sub_idx]
        _, lab = _fit_and_score(sub[config.ISOFOREST_FEATURES].values)
        sub = sub.assign(is_anomaly=lab == -1)
        return sub.groupby("PULocationID")["is_anomaly"].mean()

    rate_a = _half_rate(half_a)
    rate_b = _half_rate(half_b)
    common = rate_a.index.intersection(rate_b.index)
    stability_corr = float(pearsonr(rate_a.loc[common], rate_b.loc[common])[0])

    result = dict(
        n_sampled=len(df),
        n_anomalies=int(df.is_anomaly.sum()),
        anomaly_share=float(df.is_anomaly.mean()),
        median_fare_anomaly=float(anomalies.fare_amount.median()),
        median_fare_normal=float(normal.fare_amount.median()),
        median_speed_anomaly=float(anomalies.speed_mph.median()),
        median_speed_normal=float(normal.speed_mph.median()),
        median_distance_anomaly=float(anomalies.trip_distance.median()),
        median_distance_normal=float(normal.trip_distance.median()),
        top_anomaly_zones=zone_rate.sort_values("anomaly_rate", ascending=False)
        .head(10)
        .to_dict(orient="records"),
        stability_correlation_between_random_halves=stability_corr,
    )
    return df, zone_rate, result


if __name__ == "__main__":
    st = pd.read_parquet(config.PROCESSED_DIR / "sample_trips.parquet")
    df, zone_rate, result = run_layer5(st)
    zone_rate.to_parquet(config.PROCESSED_DIR / "layer5_zone_anomaly_rate.parquet")
    print(result)

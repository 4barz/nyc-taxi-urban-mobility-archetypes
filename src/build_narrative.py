"""Builds narrative_data.json — the consolidated, human-labelled digest of
pipeline results that reports/dissertation/build_dissertation.py reads to
populate the write-up with real numbers, tables, and zone names.

Kept as part of the reproducible pipeline (called from src/run_pipeline.py)
rather than as an ad-hoc analysis step, so that every number in the
dissertation can be regenerated from `python3 -m src.run_pipeline`.
"""

import json

import numpy as np
import pandas as pd

from . import config

ARCHETYPE_LABELS = {
    1: "High-volume Manhattan core",
    2: "Nightlife / entertainment",
    0: "Mixed-access (elevated cash share)",
    3: "Outer-borough residential",
    4: "Airport / transport hub",
}
RHYTHM_LABELS = {0: "Evening/business-dominant", 1: "Nightlife (midnight-peaking)", 2: "Morning-commuter"}
TUCKER_HOUR_LABELS = {
    0: "Evening rush (peak 18h)", 1: "Morning rush (peak 8h)",
    2: "Late-night (peak 23h)", 3: "Midday (peak 15h)",
}


def _kmeans_cluster_table(l2_df):
    rows = []
    for c in sorted(l2_df.kmeans_cluster.unique()):
        sub = l2_df[l2_df.kmeans_cluster == c]
        top_zones = sub.sort_values("trip_count", ascending=False).head(3)["Zone"].tolist()
        rows.append(dict(
            cluster=int(c),
            label=ARCHETYPE_LABELS.get(int(c), f"Cluster {c}"),
            n_zones=int(len(sub)),
            total_trips=int(sub.trip_count.sum()),
            mean_fare=round(float(sub.mean_fare.mean()), 2),
            mean_distance=round(float(sub.mean_distance.mean()), 2),
            pct_night=round(float(sub.pct_night.mean()), 3),
            pct_cash=round(float(sub.pct_cash.mean()), 3),
            pct_weekend=round(float(sub.pct_weekend.mean()), 3),
            top_zones=top_zones,
        ))
    return rows


def _rhythm_table(l3_df, centroids):
    rows = []
    for c in sorted(l3_df.rhythm_cluster.unique()):
        sub = l3_df[l3_df.rhythm_cluster == c]
        rows.append(dict(
            cluster=int(c),
            label=RHYTHM_LABELS.get(int(c), f"Rhythm {c}"),
            n_zones=int(len(sub)),
            mean_trip_count=round(float(sub.trip_count.mean()), 0),
            peak_hour=int(np.argmax(centroids[c].ravel())),
            trough_hour=int(np.argmin(centroids[c].ravel())),
            borough_mix=sub.Borough.value_counts().to_dict(),
        ))
    return rows


def _tucker_zone_top(zone_profile, zone_factors, top_n=5):
    zpid = zone_profile.set_index("zone_id")
    out = {}
    for i in range(zone_factors.shape[1]):
        order = np.argsort(-zone_factors[:, i])[:top_n]
        zids = (order + 1).tolist()
        out[i] = [zpid.loc[z, "Zone"] if z in zpid.index else "?" for z in zids]
    return out


def build_narrative(zone_profile, l2_df, l3_df, zone_rate, zone_factors, hour_factors,
                     daytype_factors, l3_centroids, summary):
    zr = zone_rate.merge(zone_profile[["zone_id", "Zone", "Borough", "trip_count"]], on="zone_id", how="left")
    top_robust = (
        zr[zr.n_sampled >= 30].sort_values("anomaly_rate", ascending=False).head(10)
        [["Zone", "Borough", "anomaly_rate", "n_sampled", "trip_count"]]
    )
    top_robust["anomaly_rate"] = top_robust["anomaly_rate"].round(4)
    sparsity_artefact_zones = int(((zr.n_sampled < 5) & (zr.anomaly_rate == 1.0)).sum())

    narrative = dict(
        qc=summary["layer1"],
        kmeans=dict(
            statistical_best_k=summary["layer2"]["best_k"],
            statistical_best_silhouette=round(summary["layer2"]["silhouettes"][str(summary["layer2"]["best_k"])], 3),
            k_used=summary["layer2"]["k_used"],
            silhouette_k5=round(summary["layer2"]["silhouette_k_used"], 3),
            silhouettes_full=summary["layer2"]["silhouettes"],
            cluster_table=_kmeans_cluster_table(l2_df),
        ),
        kshape=dict(
            n_active_zones=summary["layer3"]["n_active_zones"],
            best_k=summary["layer3"]["best_k"],
            best_silhouette=round(summary["layer3"]["silhouettes"][str(summary["layer3"]["best_k"])], 3),
            silhouettes_full=summary["layer3"]["silhouettes"],
            rhythm_table=_rhythm_table(l3_df, l3_centroids),
        ),
        tucker=dict(
            primary_rank=summary["layer4"]["primary_rank"],
            reconstruction_error=round(summary["layer4"]["reconstruction_error"], 4),
            explained_variance=round(summary["layer4"]["explained_variance"], 4),
            rank_sensitivity=summary["layer4"]["rank_sensitivity"],
            daytype_factors=daytype_factors.tolist(),
            hour_component_labels=TUCKER_HOUR_LABELS,
            zone_top=_tucker_zone_top(zone_profile, zone_factors),
        ),
        isoforest=dict(
            n_sampled=summary["layer5"]["n_sampled"],
            n_anomalies=summary["layer5"]["n_anomalies"],
            anomaly_share=round(summary["layer5"]["anomaly_share"], 4),
            median_fare_anomaly=summary["layer5"]["median_fare_anomaly"],
            median_fare_normal=summary["layer5"]["median_fare_normal"],
            median_speed_anomaly=round(summary["layer5"]["median_speed_anomaly"], 1),
            median_speed_normal=round(summary["layer5"]["median_speed_normal"], 1),
            median_distance_anomaly=summary["layer5"]["median_distance_anomaly"],
            median_distance_normal=summary["layer5"]["median_distance_normal"],
            stability_correlation=round(summary["layer5"]["stability_correlation_between_random_halves"], 3),
            sparsity_artefact_zones=sparsity_artefact_zones,
            top_anomaly_zones_robust=top_robust.to_dict(orient="records"),
        ),
        umap=dict(
            n_zones=summary["layer6"]["n_zones"],
            n_fingerprint_dims=summary["layer6"]["n_fingerprint_dims"],
            pca_variance_explained=round(sum(summary["layer6"]["pca_explained_variance_ratio"]), 3),
        ),
        total_elapsed_seconds=summary["total_elapsed_seconds"],
    )
    return narrative


def save_narrative(narrative, path=None):
    path = path or (config.PROCESSED_DIR / "narrative_data.json")
    with open(path, "w") as f:
        json.dump(narrative, f, indent=2, default=str)
    return path

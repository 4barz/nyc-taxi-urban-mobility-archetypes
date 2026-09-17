"""End-to-end pipeline orchestrator.

Runs Layers 1-6 in sequence, persists every intermediate artefact under
data/processed/, generates all figures under reports/figures/, and writes a
single results_summary.json that the dissertation write-up script reads to
populate real numbers, tables and figure references.
"""

import json
import time

import numpy as np
import pandas as pd

from . import config, viz
from .build_narrative import build_narrative, save_narrative
from .layer1_load_filter import run_layer1
from .layer2_kmeans import run_layer2
from .layer3_kshape import run_layer3
from .layer4_tucker import run_layer4
from .layer5_isoforest import run_layer5
from .layer6_umap import run_layer6


def main():
    t_start = time.time()
    summary = {}

    print("=" * 70)
    print("LAYER 1 — Data loading, quality filtering, feature engineering")
    print("=" * 70)
    zone_profile, tensor_counts, sample_trips, qc1 = run_layer1()
    summary["layer1"] = qc1

    print("=" * 70)
    print("LAYER 2 — K-Means spatial clustering")
    print("=" * 70)
    # forced_k=5: the interpretively-selected solution reported as the primary
    # zone taxonomy (Section 5.1 of the dissertation); result2 still records
    # the full k=2..8 silhouette/inertia sweep, including the statistically-
    # optimal k, for transparency.
    l2_df, l2_X, l2_km, result2 = run_layer2(zone_profile, forced_k=5)
    l2_df.to_parquet(config.PROCESSED_DIR / "layer2_kmeans_zones.parquet")
    viz.plot_kmeans_selection(result2["inertias"], result2["silhouettes"], result2["best_k"])
    viz.plot_kmeans_violins(l2_df)
    summary["layer2"] = result2
    print(json.dumps({k: v for k, v in result2.items() if k != "cluster_summary"}, indent=2))

    print("=" * 70)
    print("LAYER 3 — K-Shape temporal rhythm clustering")
    print("=" * 70)
    l3_df, l3_shares, l3_centroids, result3 = run_layer3(zone_profile, tensor_counts)
    l3_df.to_parquet(config.PROCESSED_DIR / "layer3_kshape_zones.parquet")
    np.save(config.PROCESSED_DIR / "layer3_centroids.npy", l3_centroids)
    viz.plot_kshape_selection(result3["silhouettes"], result3["best_k"])
    viz.plot_kshape_centroids(l3_centroids)
    summary["layer3"] = result3
    print(json.dumps(result3, indent=2))

    print("=" * 70)
    print("LAYER 4 — Non-negative Tucker decomposition")
    print("=" * 70)
    core, zone_factors, hour_factors, daytype_factors, result4 = run_layer4(tensor_counts)
    np.save(config.PROCESSED_DIR / "layer4_core.npy", core)
    np.save(config.PROCESSED_DIR / "layer4_zone_factors.npy", zone_factors)
    np.save(config.PROCESSED_DIR / "layer4_hour_factors.npy", hour_factors)
    np.save(config.PROCESSED_DIR / "layer4_daytype_factors.npy", daytype_factors)
    viz.plot_tucker_rank_sensitivity(result4["rank_sensitivity"], result4["primary_rank"])
    viz.plot_tucker_hour_factors(hour_factors)
    viz.plot_tucker_zone_scatter(zone_factors, zone_profile)
    summary["layer4"] = result4
    print(json.dumps(result4, indent=2))

    print("=" * 70)
    print("LAYER 5 — Isolation Forest anomaly detection")
    print("=" * 70)
    l5_df, zone_rate, result5 = run_layer5(sample_trips)
    zone_rate.to_parquet(config.PROCESSED_DIR / "layer5_zone_anomaly_rate.parquet")
    viz.plot_isoforest_scatter(l5_df)
    viz.plot_isoforest_zone_heatmap(zone_rate, zone_profile)
    summary["layer5"] = result5
    print(json.dumps({k: v for k, v in result5.items() if k != "top_anomaly_zones"}, indent=2))

    print("=" * 70)
    print("LAYER 6 — UMAP unified zone fingerprint")
    print("=" * 70)
    l6_df, result6 = run_layer6(zone_profile, zone_factors, zone_rate)
    l6_df = l6_df.merge(
        l2_df[["zone_id", "kmeans_cluster"]], on="zone_id", how="left"
    )
    l6_df.to_parquet(config.PROCESSED_DIR / "layer6_umap_zones.parquet")
    viz.plot_umap(l6_df)
    viz.plot_umap_vs_pca(l6_df)
    summary["layer6"] = result6
    print(json.dumps(result6, indent=2))

    summary["total_elapsed_seconds"] = round(time.time() - t_start, 1)
    with open(config.RESULTS_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("=" * 70)
    print("Building narrative_data.json (dissertation write-up digest)")
    print("=" * 70)
    narrative = build_narrative(
        zone_profile, l2_df, l3_df, zone_rate, zone_factors, hour_factors,
        daytype_factors, l3_centroids, summary,
    )
    narrative_path = save_narrative(narrative)

    print("=" * 70)
    print(f"PIPELINE COMPLETE in {summary['total_elapsed_seconds']}s")
    print(f"Results summary written to {config.RESULTS_JSON}")
    print(f"Narrative digest written to {narrative_path}")
    print("=" * 70)
    return summary


if __name__ == "__main__":
    main()

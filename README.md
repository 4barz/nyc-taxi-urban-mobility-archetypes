# Unsupervised Discovery of Urban Mobility Archetypes from High-Volume NYC Taxi Trip Records

MSc Big Data Analytics: Research Project
**Candidate:** Rubin Apore (Student ID: 22495624)

This repository implements the six-layer unsupervised learning pipeline described
in `nyc_taxi_urban_mobility_proposal.pdf`, applied to the full NYC TLC Yellow Taxi
Trip Records for January–June 2023 (~19.5M raw trips, ~305MB compressed Parquet).
Beyond the dissertation itself, the code is published here as a complete, working
reference for applying a range of unsupervised methods — clustering, tensor
decomposition, anomaly detection, and manifold embedding — end-to-end on a
real, high-volume dataset.

## Methods

| Layer | Technique | Purpose |
| --- | --- | --- |
| 2 | K-Means | Spatial demand archetypes |
| 3 | K-Shape | Temporal rhythm clustering |
| 4 | Non-negative Tucker decomposition | Zone × hour × day-type factorisation |
| 5 | Isolation Forest | Trip-level anomaly detection |
| 6 | UMAP | Unified zone fingerprint embedding |

**[Read the full dissertation (PDF)](reports/dissertation/NYC_Taxi_Urban_Mobility_Dissertation.pdf)**

## Project layout

```
bdat_project/
├── nyc_taxi_urban_mobility_proposal.pdf    # approved research proposal
├── requirements.txt
├── src/                                    # pipeline source code (Layers 1-6)
│   ├── config.py                           # paths, thresholds, hyperparameters
│   ├── layer1_load_filter.py               # loading, quality filtering, features
│   ├── layer2_kmeans.py                    # spatial demand archetypes (RQ1)
│   ├── layer3_kshape.py                    # temporal rhythm clustering (RQ2)
│   ├── layer4_tucker.py                    # non-negative Tucker decomposition (RQ3)
│   ├── layer5_isoforest.py                 # trip-level anomaly detection (RQ4)
│   ├── layer6_umap.py                      # unified zone fingerprint embedding (RQ5)
│   ├── viz.py                              # figure generation
│   └── run_pipeline.py                     # end-to-end orchestrator
├── notebooks/
│   └── 01_full_pipeline.ipynb              # executed, reproducible analysis notebook
├── data/
│   ├── raw/nyc-taxi-trips/                 # downloaded TLC Parquet files (not committed)
│   └── processed/                          # pipeline artefacts + results_summary.json
└── reports/
    ├── figures/                            # all generated figures (PNG)
    └── dissertation/                       # submission-ready write-up (.docx / .pdf)
```

## Reproducing the analysis

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 1. Download the six monthly Yellow Taxi Parquet files + zone lookup table
#    (see data/raw/nyc-taxi-trips/download.sh)
bash data/raw/download.sh

# 2. Run the full six-layer pipeline (takes a few minutes on a modern laptop)
python3 -m src.run_pipeline

# 3. Regenerate the executed notebook (optional: mirrors run_pipeline.py with
#    inline figures for narrative walk-through)
jupyter nbconvert --to notebook --execute notebooks/01_full_pipeline.ipynb --inplace

# 4. Rebuild the dissertation .docx/.pdf from the pipeline's output (optional;
#    iterates build_dissertation.py + LibreOffice a few times to compute a
#    real table of contents with correct page numbers, no manual "Update
#    Field" step required)
python3 reports/dissertation/build_toc.py
```

All intermediate artefacts (zone profiles, the Zone×Hour×DayType tensor, the
Isolation Forest sample, cluster assignments, and a `results_summary.json`
consolidating every quantitative result referenced in the dissertation
write-up) are written to `data/processed/`. All figures are written to
`reports/figures/`.

## Data source

NYC Taxi & Limousine Commission, Yellow Taxi Trip Records, January–June 2023,
retrieved from the public TLC Parquet distribution
(`https://d37ci6vzurychx.cloudfront.net/trip-data/`). Data is anonymised at
source (zone-level, not GPS-level, locations; no rider/driver identifiers).

## Reproducibility notes

- Random seed `42` is fixed throughout (`src/config.RANDOM_STATE`) for K-Means,
  K-Shape, Isolation Forest, Tucker initialisation, and UMAP.
- Layer 1 streams through the six monthly files one at a time rather than
  materialising all ~19.5M rows in memory simultaneously, computing exact
  zone-level and tensor aggregates incrementally and retaining an unbiased
  ~500,000-trip random sample for the trip-level anomaly layer.

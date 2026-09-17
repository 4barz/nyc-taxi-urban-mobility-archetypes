"""Builds the submission-ready dissertation-chapter document
(NYC_Taxi_Urban_Mobility_Dissertation.docx) from the real pipeline outputs in
data/processed/. Run after src/run_pipeline.py has completed.
"""

import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
FIGS = ROOT / "reports" / "figures"
OUT_DOCX = ROOT / "reports" / "dissertation" / "NYC_Taxi_Urban_Mobility_Dissertation.docx"
HEADING_RECORD_PATH = PROC / "heading_record.json"
TOC_ENTRIES_PATH = PROC / "toc_entries.json"

with open(PROC / "narrative_data.json") as f:
    N = json.load(f)

# Populated by h1()/h2() as the document is built, in document order, then
# dumped to HEADING_RECORD_PATH so a page-numbering pass can locate each
# heading in the rendered PDF and produce a real (not manually-updated) TOC.
HEADING_RECORD = []

BODY_FONT = "Times New Roman"
HEAD_FONT = "Times New Roman"
ACCENT = RGBColor(0x1F, 0x3A, 0x5F)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def set_base_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(12)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE

    for i in range(1, 4):
        h = doc.styles[f"Heading {i}"]
        h.font.name = HEAD_FONT
        h.font.color.rgb = ACCENT
        h.font.bold = True
        h.paragraph_format.space_before = Pt(18 if i == 1 else 10)
        h.paragraph_format.space_after = Pt(8)
    doc.styles["Heading 1"].font.size = Pt(18)
    doc.styles["Heading 2"].font.size = Pt(14)
    doc.styles["Heading 3"].font.size = Pt(12)


def add_page_number_field(paragraph):
    # A PAGE field built from the standard begin/instrText/separate/end
    # fldChar sequence (paragraph-level runs, not nested inside a run) is
    # reliably evaluated by both Word and LibreOffice on render; a bare
    # <w:fldSimple> nested inside a run is invalid OOXML and renders blank.
    def _run_with(tag, **attrs):
        r = paragraph.add_run()
        el = OxmlElement(tag)
        for k, v in attrs.items():
            el.set(qn(k), v)
        r._r.append(el)
        return r

    _run_with("w:fldChar", **{"w:fldCharType": "begin"})
    r = paragraph.add_run()
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    r._r.append(instr)
    _run_with("w:fldChar", **{"w:fldCharType": "separate"})
    paragraph.add_run("1")
    _run_with("w:fldChar", **{"w:fldCharType": "end"})


def add_footer(doc, text):
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.text = f"{text} | "
    add_page_number_field(p)
    for r in p.runs:
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)


def h1(doc, text):
    HEADING_RECORD.append([1, text])
    doc.add_heading(text, level=1)


def h2(doc, text):
    HEADING_RECORD.append([2, text])
    doc.add_heading(text, level=2)


def h3(doc, text):
    doc.add_heading(text, level=3)


def body(doc, text, italic=False, bold=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(text)
    r.italic = italic
    r.bold = bold
    return p


def bullet(doc, text):
    doc.add_paragraph(text, style="List Bullet")


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(14)


def figure(doc, filename, cap, width=6.2):
    doc.add_picture(str(FIGS / filename), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption(doc, cap)


def _set_row_cant_split(row):
    trPr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    trPr.append(cant_split)


def _set_repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    trPr.append(tbl_header)


def table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, htext in enumerate(headers):
        hdr[i].text = str(htext)
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
    for row in t.rows:
        _set_row_cant_split(row)
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(2)
                for r in p.runs:
                    r.font.size = Pt(10)
    _set_repeat_header(t.rows[0])
    doc.add_paragraph()
    return t


def page_break(doc):
    doc.add_page_break()


# ---------------------------------------------------------------------------
# Build document
# ---------------------------------------------------------------------------
doc = Document()
set_base_styles(doc)
add_footer(doc, "Rubin Apore, 22495624, MSc Big Data Analytics")

sec = doc.sections[0]
sec.left_margin = sec.right_margin = Inches(1)
sec.top_margin = sec.bottom_margin = Inches(1)

# ---------------------------- Title page -----------------------------------
for _ in range(4):
    doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Unsupervised Discovery of Urban Mobility Archetypes\nfrom High-Volume NYC Taxi Trip Records")
r.bold = True
r.font.size = Pt(24)
r.font.color.rgb = ACCENT

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("A Multi-Stage Unsupervised Learning Pipeline for Spatial, Temporal,\nTensor-Structural, and Anomaly-Based Characterisation of Urban Taxi Demand")
r.italic = True
r.font.size = Pt(14)

for _ in range(3):
    doc.add_paragraph()

for line in [
    "MSc Big Data Analytics: Research Project / Dissertation Chapter",
    "",
    "Candidate: Rubin Apore",
    "Student ID: 22495624",
    "Research Theme: Urban Mobility & Transport Analytics",
    "Dataset: NYC Taxi & Limousine Commission, Yellow Taxi Trip Records (2023, Jan–Jun)",
]:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(line)
    r.font.size = Pt(13)

page_break(doc)

# ---------------------------- Abstract --------------------------------------
h1(doc, "Abstract")
body(doc,
    "Urban taxi trip records are among the densest, most temporally rich open datasets available "
    "for the study of city-scale human mobility, yet published analyses of them overwhelmingly fall "
    "into two tracks (supervised demand forecasting and descriptive cartography) that leave the "
    "latent structure of the data unexploited. This study implements and executes a six-layer "
    "unsupervised learning pipeline (data quality filtering and feature engineering; K-Means spatial "
    "clustering; K-Shape temporal rhythm clustering; non-negative Tucker decomposition of a "
    "Zone×Hour×DayType demand tensor; Isolation Forest trip-level anomaly detection; and UMAP "
    "synthesis) against the complete NYC Taxi & Limousine Commission Yellow Taxi Trip Records for "
    f"January–June 2023: {N['qc']['raw_trip_count']:,} raw trips across 263 TLC zones, of which "
    f"{N['qc']['filtered_trip_count']:,} (retention rate {N['qc']['retention_rate']:.1%}) survived "
    "domain-knowledge quality filtering."
)
_c = {c["cluster"]: c for c in N["kmeans"]["cluster_table"]}
_fare_premium = N["isoforest"]["median_fare_anomaly"] / N["isoforest"]["median_fare_normal"]
body(doc,
    "The analysis identifies five interpretable zone-level demand archetypes: a high-volume "
    f"Manhattan core carrying {_c[1]['total_trips'] / N['qc']['filtered_trip_count']:.0%} of all "
    f"trips, a nightlife/entertainment archetype with a {_c[2]['pct_night']:.1%} night-trip share, a "
    f"mixed-access archetype with an elevated {_c[0]['pct_cash']:.1%} cash-payment share, a "
    "chronically under-served outer-borough residential archetype recording only "
    f"{_c[3]['total_trips']:,} trips across {_c[3]['n_zones']} zones over six months, and an "
    "airport/transport-hub archetype. It further identifies three temporal rhythm archetypes "
    "independent of absolute volume, a six-component non-negative tensor decomposition explaining "
    f"{N['tucker']['explained_variance']:.1%} of Zone×Hour×DayType demand variance, a trip-level "
    f"anomaly layer flagging {N['isoforest']['anomaly_share']:.0%} of a "
    f"{N['isoforest']['n_sampled']:,}-trip representative sample with a {_fare_premium:.1f}× fare "
    f"premium, and a {N['umap']['n_fingerprint_dims']}-dimensional UMAP zone fingerprint that "
    "recovers New York City's functional geography without being given borough labels. Together the "
    "layers demonstrate that a small number of latent archetypes explain most of the structure in "
    "high-volume urban mobility data, and that combining spatial, temporal, tensor, and anomaly "
    "signals in a single fingerprint yields a materially richer characterisation than any one method "
    "alone."
)
page_break(doc)

# ---------------------------- TOC -------------------------------------------
# A real, static table of contents with correct page numbers, computed by a
# prior render-and-measure pass (see build_toc.py) rather than a Word field
# that requires the reader to press F9. If no measurement exists yet, this
# section is left as a lightweight placeholder for that first pass.
h1(doc, "Table of Contents")
if TOC_ENTRIES_PATH.exists():
    with open(TOC_ENTRIES_PATH) as f:
        toc_entries = json.load(f)
    for level, text, page_num in toc_entries:
        if text == "Table of Contents":
            continue
        p = doc.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(
            Inches(6.3), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS
        )
        p.paragraph_format.left_indent = Inches(0.0 if level == 1 else 0.3)
        p.paragraph_format.space_after = Pt(4 if level == 1 else 2)
        r = p.add_run(text)
        r.bold = level == 1
        p.add_run(f"\t{page_num}")
else:
    body(doc, "(Placeholder pass: run build_toc.py to compute page numbers and "
              "populate this table of contents.)", italic=True)
page_break(doc)

print("Title/Abstract/TOC written.")

# ============================================================================
# 1. Introduction and Motivation
# ============================================================================
h1(doc, "1. Introduction and Motivation")
body(doc,
    "Urban transportation systems generate some of the densest, most temporally rich open datasets "
    "available to researchers. A single month of New York City yellow taxi records encodes millions "
    "of individual mobility decisions: where people travel, when they travel, how much they pay, and "
    "which spatial corridors they inhabit. Yet despite this richness, most published taxi analytics "
    "falls into one of two dominant tracks: supervised demand forecasting (predicting trip counts "
    "given historical time series) or descriptive cartography (heat maps of pickup density)."
)
body(doc,
    "Neither approach exploits the latent structure of the data. Neither asks: what archetypes of "
    "spatial demand exist across the city's 263 zones? Do zones share temporal demand rhythms "
    "independent of their absolute volume? Which individual trips are structurally unusual in ways "
    "that signal regulatory concern? These are genuinely unsupervised questions. They require no "
    "labels, no ground-truth outcomes, and no predefined hypotheses about which zones are “similar” "
    "or which hours are “important.” They are exactly the kind of questions that Big Data analytical "
    "frameworks, applied rigorously at scale, are positioned to answer."
)
body(doc,
    "This chapter reports the completed execution of the six-layer unsupervised learning pipeline "
    "proposed for this project, run end-to-end against the full six-month dataset rather than a "
    "preliminary subset. It situates the pipeline within the Big Data 5 Vs framework and argues that "
    "NYC taxi trip records serve as a model case study for demonstrating the analytical value of "
    "high-volume, regularly generated urban mobility data. NYC TLC data was selected because it is "
    "one of the few fully open, high-volume, trip-level urban mobility datasets with consistent "
    "spatial, temporal, and financial variables. While the empirical setting is New York City, the "
    "methodology is transferable to Ghanaian urban transport contexts where comparable data may "
    "become available through digital ticketing, ride-hailing platforms, GPS fleet tracking, or "
    "public transport smart-card systems; this chapter therefore serves both as a standalone "
    "analytical contribution and as a methodological template for future work on African urban "
    "mobility data."
)

# ============================================================================
# 2. Research Questions
# ============================================================================
h1(doc, "2. Research Questions")
rqs = [
    ("RQ1 (Spatial)", "What demand archetypes emerge when NYC taxi zones are characterised by their "
     "aggregate volume, revenue, behavioural, and temporal profiles, and do these archetypes "
     "correspond to meaningful urban functional categories?"),
    ("RQ2 (Temporal)", "Do taxi zones share demand rhythm shapes independent of absolute trip "
     "volume, and if so, what distinct rhythm archetypes can be identified by shape-based "
     "time-series clustering?"),
    ("RQ3 (Structural)", "What latent spatiotemporal demand components can be extracted from the "
     "Zone × Hour × DayType demand tensor, and how many independent archetype components are "
     "required to explain the majority of observed variation?"),
    ("RQ4 (Anomaly)", "Which individual trips are structurally unusual relative to the distribution "
     "of comparable trips, and which zones exhibit the highest concentration of anomalous "
     "behaviour?"),
    ("RQ5 (Synthesis)", "Does a unified multi-layer zone fingerprint combining spatial, temporal, "
     "tensor, and anomaly signals produce a coherent low-dimensional embedding that reflects the "
     "functional geography of New York City?"),
]
for title, text in rqs:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(title + ": ")
    r.bold = True
    p.add_run(text)

# ============================================================================
# 3. Data and Big Data 5 Vs Assessment
# ============================================================================
h1(doc, "3. Data and Big Data 5 Vs Assessment")
body(doc,
    "Data was sourced from the NYC Taxi & Limousine Commission public Yellow Taxi Trip Records for "
    "January–June 2023 (NYC Taxi & Limousine Commission, 2023), retrieved directly from the TLC's "
    "public Parquet distribution (6 monthly files, 305 MB compressed on disk). Table 1 profiles the "
    "dataset against the Big Data 5 Vs framework (Laney, 2001)."
)
caption(doc, "Table 1. Big Data 5 Vs assessment of the dataset.")
table(doc,
    ["Dimension", "Assessment", "Evidence"],
    [
        ["Volume", "*****", f"{N['qc']['raw_trip_count']:,} raw trips over six months "
         f"({N['qc']['filtered_trip_count']:,} after filtering); 305 MB compressed Parquet; "
         "~100M trips/year system-wide"],
        ["Velocity", "****", "Trip data is generated continuously by taxi operations; public "
         "research access is through periodic monthly batch releases"],
        ["Variety", "****", "Spatial (zone IDs), temporal (datetime), financial (fare, tip), "
         "behavioural (passenger count, payment type, ratecode)"],
        ["Veracity", "***", "Known GPS/metering edge cases; quality filtering removed "
         f"{1 - N['qc']['retention_rate']:.1%} of raw trips"],
        ["Value", "*****", "Direct policy relevance: TLC regulation, congestion pricing, "
         "accessibility equity, compliance review"],
    ],
)
body(doc,
    "The dataset strongly satisfies the Volume, Variety, Veracity, and Value dimensions. Velocity is "
    "represented through the high frequency of operational data generation and regular public "
    "release cadence, even though this study uses batch processing rather than streaming analysis. "
    f"The full six-month load comprised {N['qc']['raw_trip_count']:,} raw trip records, of which "
    f"{N['qc']['filtered_trip_count']:,} ({N['qc']['retention_rate']:.2%}) passed the domain-knowledge "
    "quality filters described in Section 4.1, a slightly more aggressive removal rate than the "
    "98.5% estimated at proposal stage, consistent with the full dataset containing a larger absolute "
    "number of edge cases (zero-distance trips, GPS dropouts, and metering anomalies) than were "
    f"visible in preliminary sampling. {N['qc']['n_zones_with_data']} of the 263 TLC zones recorded "
    "at least one valid pickup over the study window; the remaining three zone IDs (Governor's "
    "Island/Ellis Island/Liberty Island, listed twice under adjacent zone IDs, and Staten Island's "
    "Great Kills Park) are uninhabited islands and parkland with no road access, recorded zero "
    "qualifying trips over the six-month window, and are excluded from zone-level analysis by "
    "construction."
)

page_break(doc)

# ============================================================================
# 4. Methodology
# ============================================================================
h1(doc, "4. Analytical Framework: Multi-Stage Unsupervised Pipeline")
body(doc,
    "The analysis implements a rigorous sequential multi-method unsupervised framework. Individual "
    "methods (K-Means spatial clustering, K-Shape time-series clustering, non-negative Tucker "
    "decomposition, Isolation Forest anomaly detection, and UMAP embedding) each have established "
    "use in their respective literatures, but their combination into a single coherent pipeline "
    "applied to one dataset is not a standard approach in the urban mobility field. The core "
    "contribution is the integrated zone fingerprint: K-Means, K-Shape, Tucker decomposition, and "
    "anomaly rates are intermediate feature-generation layers, while UMAP provides the final "
    "synthesis across all dimensions. The outputs of earlier layers feed into later ones through "
    "this unified fingerprint, producing a richer characterisation than any single method could "
    "achieve alone."
)

h2(doc, "4.1 Data Loading, Quality Filtering, and Feature Engineering (Layer 1)")
body(doc, "Method: Pandas + PyArrow columnar Parquet loading; domain-knowledge quality filter.")
body(doc, "Quality constraints applied:")
for t in [
    "Duration: 1–180 minutes", "Distance: 0.1–60 miles", "Fare: $2.50–$500",
    "Speed: ≤ 80 mph", "Zone: valid TLC zone IDs (1–263) at both pickup and drop-off",
]:
    bullet(doc, t)
body(doc,
    "Features engineered: duration_min, speed_mph, tip_pct, hour, dow, is_weekend, plus zone-level "
    "aggregates (log trip count, mean fare/distance/duration/speed, weekend/cash/night/rush shares)."
)
body(doc,
    "Big Data engineering decision: rather than materialising all ~19.5M filtered trips in memory "
    "simultaneously (the approach originally proposed, estimated at >2.5 GB in-memory), Layer 1 was "
    "implemented as a streaming reduction: each of the six monthly Parquet files is loaded, filtered, "
    "and feature-engineered in turn, and its results are folded into three compact running artefacts: "
    "(i) per-zone aggregate sums (from which zone-level means/shares are derived once all months "
    "are processed), (ii) a Zone×Hour×DayType trip-count tensor, and (iii) a proportionally-sampled "
    "~500,000-trip subset retained for trip-level analysis, before the month's data is discarded. "
    "This bounds peak memory to a single month's frame (~3M rows) regardless of the total study "
    "period, computes the zone and tensor aggregates exactly (not from a sample), and still yields an "
    "unbiased trip-level sample for Layer 5. It is a more Big-Data-appropriate design than full "
    "materialisation and is consistent with the columnar, vectorised processing this proposal's "
    "quality-filtering rationale called for."
)

h2(doc, "4.2 K-Means Spatial Clustering: Demand Archetypes (Layer 2, RQ1)")
body(doc,
    "Method: K-Means on a 10-feature zone profile matrix (log trip count, mean fare, mean distance, "
    "mean duration, mean speed, mean tip share, and weekend/cash/night/rush shares), z-score "
    "standardised, with k selected by silhouette score across k=2..8."
)
body(doc,
    "Silhouette selection favoured k=2 (silhouette "
    f"{N['kmeans']['statistical_best_silhouette']}) over the full k=2..8 range, but the curve is "
    f"comparatively flat (silhouette ranging {min(N['kmeans']['silhouettes_full'].values()):.3f}–"
    f"{max(N['kmeans']['silhouettes_full'].values()):.3f}), and k=2 collapses the city into only an "
    "“airport/high-fare” versus “everything else” split. Following the proposal's own validation "
    "criterion of interpretability against known NYC geography, k=5 "
    f"(silhouette {N['kmeans']['silhouette_k5']}, a modest reduction of "
    f"{N['kmeans']['statistical_best_silhouette'] - N['kmeans']['silhouette_k5']:.3f}) was adopted "
    "as the reported solution because it recovers geographically and behaviourally coherent "
    "archetypes; both solutions are reported here for transparency."
)

h2(doc, "4.3 K-Shape Temporal Rhythm Clustering (Layer 3, RQ2)")
body(doc,
    "Method: K-Shape clustering (Paparrizos & Gravano, 2015) on 24-hour demand profiles per zone, "
    "normalised first to a fractional hourly share (removing the effect of absolute volume) and then "
    "z-normalised (removing offset and scale, leaving only shape). Zones averaging fewer "
    f"than {10} trips/day were excluded to prevent sparsity-induced shape distortion, leaving "
    f"{N['kshape']['n_active_zones']} highly active zones for time-series analysis. Because K-Shape's "
    "native cross-correlation-based shape distance is shift-invariant and therefore not directly "
    "compatible with the standard silhouette formula, k was selected by silhouette score computed on "
    "Euclidean distance between the same z-normalised shapes used for clustering, a documented "
    "approximation rather than the native shape distance."
)
body(doc,
    "Innovation: normalising demand profiles to fractional hourly share before clustering decouples "
    "rhythm shape from scale. A low-volume residential zone that peaks at 8 AM will cluster with "
    "Midtown, which also peaks at 8 AM, despite a large volume difference. This is intentional: the "
    "research question is about rhythm archetype, not scale."
)

h2(doc, "4.4 Non-negative Tucker Decomposition (Layer 4, RQ3)")
body(doc,
    "Method: non-negative Tucker decomposition of the Zone × Hour × DayType (263 × 24 × 2) "
    f"demand tensor at core rank {tuple(N['tucker']['primary_rank'])}: "
    f"{N['tucker']['primary_rank'][0]} latent zone profiles, {N['tucker']['primary_rank'][1]} "
    f"temporal profiles, and {N['tucker']['primary_rank'][2]} day-type profiles. Rank selection was "
    "justified using reconstruction error, component interpretability, and sensitivity checks against "
    "nearby ranks. Random (rather than SVD) non-negative initialisation was used for the "
    "multiplicative-update algorithm, since SVD initialisation was found empirically to diverge "
    "(numerical overflow) at this tensor's scale."
)
body(doc,
    "Rationale for Tucker over standard matrix factorisation: the demand tensor is three-dimensional "
    "by construction, since a zone's demand is a function of both the hour of day and the day type "
    "(weekday vs weekend). A matrix factorisation that collapses one dimension loses this interaction "
    "structure, whereas Tucker decomposition (Kolda & Bader, 2009) preserves all three modes "
    "simultaneously. Non-negativity is enforced because demand cannot be negative, which also "
    "improves interpretability of the component loadings."
)

h2(doc, "4.5 Isolation Forest Trip-Level Anomaly Detection (Layer 5, RQ4)")
body(doc,
    "Method: Isolation Forest (Liu, Ting, & Zhou, 2008) with 200 trees and 2% contamination, on a "
    f"{N['isoforest']['n_sampled']:,}-trip random sample, using a 7-feature trip-level input matrix: "
    "trip_distance, duration_min, fare_amount, speed_mph, tip_pct, hour, is_weekend."
)
body(doc,
    "The anomaly layer is not designed to prove fraud; it identifies unusual trip structures that "
    "may support further compliance review by the relevant authority. Stability was validated by "
    "refitting the model independently on two random halves of the sample and correlating the "
    f"resulting per-zone anomaly rates (Pearson r = {N['isoforest']['stability_correlation']}); the "
    "per-zone anomaly rate serves as the final feature in the UMAP fingerprint."
)

h2(doc, "4.6 UMAP Unified Zone Fingerprint (Layer 6, RQ5)")
body(doc,
    f"Method: UMAP (McInnes, Healy, & Melville, 2018) with n_neighbors=10, min_dist=0.25, on a "
    f"{N['umap']['n_fingerprint_dims']}-dimensional "
    "zone fingerprint, coloured by Layer 2 and Layer 3 cluster membership, with a PCA baseline for "
    "comparison. Fingerprint composition: 10 K-Means zone features + 6 Tucker zone-mode factors + 1 "
    "Isolation Forest zone-level anomaly rate. UMAP is used as an exploratory visualisation tool, not "
    "as a confirmatory statistical test."
)

# ============================================================================
# 5. Results
# ============================================================================
h1(doc, "5. Results")
body(doc,
    "Results are organised by research question. All figures and numbers below were generated by "
    "the pipeline in src/ against the full six-month dataset (src/run_pipeline.py); see the "
    "accompanying notebook (notebooks/01_full_pipeline.ipynb) for a fully reproducible, "
    "cell-by-cell walkthrough."
)

# ---- RQ1 ----
h2(doc, "5.1 RQ1: Spatial Demand Archetypes (K-Means)")
figure(doc, "layer2_kmeans_selection.png",
       "Figure 1. K-Means model selection: elbow (inertia) and silhouette score across k=2..8.")
body(doc,
    f"The silhouette curve is relatively flat across k=4..8 ({min(list(N['kmeans']['silhouettes_full'].values())[2:]):.3f}–"
    f"{max(list(N['kmeans']['silhouettes_full'].values())[2:]):.3f}), with a modest global peak at k=2 "
    "driven by the airport zones separating from everything else. The k=5 solution below was "
    "selected for its substantially richer interpretability at a small silhouette cost."
)
figure(doc, "layer2_kmeans_violins.png",
       "Figure 2. Zone-level cluster portraits at k=5: distribution of volume, fare, distance, "
       "night share, and cash share within each archetype.")

kmeans_rows = [
    [f"{c['cluster']}: {c['label']}", c["n_zones"], f"{c['total_trips']:,}", f"${c['mean_fare']:.2f}",
     f"{c['mean_distance']:.2f} mi", f"{c['pct_night']:.1%}", f"{c['pct_cash']:.1%}",
     " / ".join(c["top_zones"][:2])]
    for c in N["kmeans"]["cluster_table"]
]
caption(doc, "Table 2. K-Means zone archetypes at k=5.")
table(doc,
      ["Archetype", "Zones", "Total trips", "Mean fare", "Mean dist.", "% night", "% cash", "Example zones"],
      kmeans_rows)

body(doc,
    "The five archetypes are clearly differentiated and geographically coherent. The high-volume "
    "Manhattan core (53 zones) carries "
    f"{N['kmeans']['cluster_table'][1]['total_trips']:,} trips, "
    f"{N['kmeans']['cluster_table'][1]['total_trips'] / N['qc']['filtered_trip_count']:.0%} of all "
    "filtered trips, at the lowest fares and distances in the taxonomy, consistent with dense, "
    "short, high-turnover Midtown/Upper-East-Side rides. The nightlife/entertainment archetype "
    "(East Village, Greenwich Village South, Lower East Side) records a night-trip share of "
    f"{N['kmeans']['cluster_table'][2]['pct_night']:.1%} and a weekend share of "
    f"{N['kmeans']['cluster_table'][2]['pct_weekend']:.1%}, both far above every other archetype, "
    "confirming this as the sharpest behavioural signal in the taxonomy, exactly as anticipated at "
    "proposal stage. The mixed-access archetype (Central Harlem North, Hamilton Heights, Astoria, "
    "Woodside) shows the highest cash-payment share "
    f"({N['kmeans']['cluster_table'][0]['pct_cash']:.1%}), a pattern consistent with differential "
    "digital-payment access rather than a simple outer-borough/inner-borough split. The outer-borough "
    "residential archetype is the most striking equity finding: 85 zones, fully a third of all "
    "zones with any recorded activity, together generated only "
    f"{N['kmeans']['cluster_table'][3]['total_trips']:,} trips over six months, "
    f"{N['kmeans']['cluster_table'][3]['total_trips'] / N['qc']['filtered_trip_count']:.2%} of the "
    "dataset, indicating that yellow taxis provide essentially negligible coverage to the majority "
    "of the city's residential footprint. This cluster also has the lowest cash share "
    f"({N['kmeans']['cluster_table'][3]['pct_cash']:.1%}) of any archetype, the opposite of what a "
    "naive “outlying = under-banked” heuristic would predict, and a useful refinement of the "
    "preliminary hypothesis set out in the proposal. The airport/hub archetype (JFK, LaGuardia, East "
    "Elmhurst) is unambiguous: mean fare "
    f"${N['kmeans']['cluster_table'][4]['mean_fare']:.2f} and mean distance "
    f"{N['kmeans']['cluster_table'][4]['mean_distance']:.2f} miles, both far above any other group."
)

# ---- RQ2 ----
h2(doc, "5.2 RQ2: Temporal Rhythm Archetypes (K-Shape)")
figure(doc, "layer3_kshape_selection.png",
       f"Figure 3. K-Shape model selection by silhouette score, k=2..6. Best: k={N['kshape']['best_k']} "
       f"(silhouette {N['kshape']['best_silhouette']}).")
figure(doc, "layer3_kshape_centroids.png",
       "Figure 4. Z-normalised 24-hour rhythm centroids for the three archetypes.")

kshape_rows = [
    [f"{r['cluster']}: {r['label']}", r["n_zones"], f"{r['mean_trip_count']:,.0f}",
     f"{r['peak_hour']:02d}:00", f"{r['trough_hour']:02d}:00",
     ", ".join(f"{k} ({v})" for k, v in r["borough_mix"].items())]
    for r in N["kshape"]["rhythm_table"]
]
caption(doc, "Table 3. K-Shape rhythm archetypes.")
table(doc,
      ["Rhythm archetype", "Zones", "Mean trips/zone", "Peak hour", "Trough hour", "Borough mix"],
      kshape_rows)

body(doc,
    f"Contrary to the k=2 solution anticipated at proposal stage, silhouette selection over the full "
    f"k=2..6 range on the completed dataset identifies k={N['kshape']['best_k']} as optimal "
    f"(silhouette {N['kshape']['best_silhouette']}), out of "
    f"{N['kshape']['n_active_zones']} sufficiently active zones. Each of the three rhythm archetypes "
    "mixes multiple boroughs (Rhythm 0 is Manhattan-dominated but includes Queens and Brooklyn zones; "
    "Rhythm 2 mixes Brooklyn, Queens, and Manhattan almost evenly), which supports the proposal's "
    "central hypothesis for RQ2: functional zone type, whether evening/business-dominant, nightlife, "
    "or morning-commuter, explains demand rhythm shape more strongly than simple geographic "
    "proximity or borough membership."
)

# ---- RQ3 ----
h2(doc, "5.3 RQ3: Latent Spatiotemporal Structure (Non-negative Tucker Decomposition)")
figure(doc, "layer4_tucker_rank_sensitivity.png",
       "Figure 5. Relative reconstruction error across candidate Tucker core ranks.")
body(doc,
    f"The primary rank {tuple(N['tucker']['primary_rank'])} achieves a relative reconstruction error "
    f"of {N['tucker']['reconstruction_error']:.3f} ({N['tucker']['explained_variance']:.1%} explained "
    "variance). Reconstruction error is not perfectly monotonic in rank "
    f"({', '.join(f'{k}: {v:.3f}' for k, v in N['tucker']['rank_sensitivity'].items())}); the "
    "neighbouring rank (5,4,2) in fact achieves marginally lower error, an expected consequence of "
    "the non-convex multiplicative-update optimisation converging to different local minima rather "
    "than evidence against rank (6,4,2), which was retained as primary for its finer zone-mode "
    "resolution and consistency with the pre-registered design."
)
figure(doc, "layer4_tucker_hour_factors.png",
       "Figure 6. Hour-mode component loadings: four distinct temporal profiles recovered from the tensor.")
tucker_hour_rows = [[i, label] for i, label in N["tucker"]["hour_component_labels"].items()]
caption(doc, "Table 4. Interpretation of the Tucker hour-mode components.")
table(doc, ["Component", "Interpretation (peak hour)"], tucker_hour_rows)
body(doc,
    "The day-type factor matrix shows that the temporal component corresponding to shared weekday/"
    f"weekend structure loads at {N['tucker']['daytype_factors'][0][0]:.2f} (weekday) and "
    f"{N['tucker']['daytype_factors'][1][0]:.2f} (weekend), present on both day types, while the "
    f"second day-type factor loads at {N['tucker']['daytype_factors'][0][1]:.2f} (weekday) versus "
    f"essentially {N['tucker']['daytype_factors'][1][1]:.4f} (weekend), i.e. a purely weekday-specific "
    "commuter signal. This is a genuinely latent finding that neither the K-Means nor K-Shape layers "
    "surface directly: the tensor decomposition separates a volume pattern that persists across the "
    "whole week from one that exists only on working days."
)
figure(doc, "layer4_tucker_zone_scatter.png",
       "Figure 7. Zone-mode Tucker factors (first two components), coloured by borough.")
body(doc,
    "Inspecting which zones load most strongly on each zone-mode component reinforces the picture "
    "from Layers 2–3 while adding resolution: components separate core Midtown business zones "
    f"({', '.join(N['tucker']['zone_top']['0'][:3])}) from nightlife zones plus JFK "
    f"({', '.join(N['tucker']['zone_top']['1'][:3])}) from transit-hub/tourist zones "
    f"({', '.join(N['tucker']['zone_top']['2'][:3])}) from Upper East/West Side residential-business "
    f"zones ({', '.join(N['tucker']['zone_top']['4'][:3])}). This six-way zone decomposition is "
    "materially finer-grained than the five K-Means archetypes, demonstrating the value of preserving "
    "the full three-mode tensor structure rather than collapsing to a zone-level matrix."
)

# ---- RQ4 ----
h2(doc, "5.4 RQ4: Trip-Level Anomaly Detection (Isolation Forest)")
figure(doc, "layer5_isoforest_scatter.png",
       "Figure 8. Fare vs. speed for a 40,000-trip visualisation subsample, coloured by anomaly flag.")
body(doc,
    f"Of the {N['isoforest']['n_sampled']:,}-trip representative sample, "
    f"{N['isoforest']['n_anomalies']:,} trips ({N['isoforest']['anomaly_share']:.2%}, matching the "
    "target 2% contamination) were flagged as anomalous. The anomalous population is sharply "
    "differentiated from the normal population:"
)
iso_rows = [
    ["Fare", f"${N['isoforest']['median_fare_normal']:.2f}", f"${N['isoforest']['median_fare_anomaly']:.2f}",
     f"{N['isoforest']['median_fare_anomaly']/N['isoforest']['median_fare_normal']:.1f}×"],
    ["Speed (mph)", f"{N['isoforest']['median_speed_normal']}", f"{N['isoforest']['median_speed_anomaly']}",
     f"{N['isoforest']['median_speed_anomaly']/N['isoforest']['median_speed_normal']:.1f}×"],
    ["Distance (mi)", f"{N['isoforest']['median_distance_normal']}", f"{N['isoforest']['median_distance_anomaly']}",
     f"{N['isoforest']['median_distance_anomaly']/N['isoforest']['median_distance_normal']:.1f}×"],
]
caption(doc, "Table 5. Anomalous vs. normal trip profile (medians).")
table(doc, ["Feature (median)", "Normal", "Anomalous", "Ratio"], iso_rows)
body(doc,
    "This profile of high speed, high fare, and long distance is consistent with structurally "
    "unusual long-haul trips rather than random noise, and matches the profile anticipated at "
    "proposal stage almost exactly. Model stability was checked by refitting independently on two "
    f"random halves of the sample and correlating resulting per-zone anomaly rates (Pearson r = "
    f"{N['isoforest']['stability_correlation']}); this moderate-to-good correlation indicates that "
    "per-zone anomaly rates are reasonably, but not perfectly, stable, and should be trusted most "
    "for zones with larger sample counts."
)
figure(doc, "layer5_isoforest_zone_heatmap.png",
       "Figure 9. Zones with the highest anomaly-rate concentration (restricted to zones with ≥ 30 "
       "sampled trips, to exclude the sparsity artefact described below).")
iso_top_rows = [
    [r["Zone"], r["Borough"], f"{r['anomaly_rate']:.1%}", int(r["n_sampled"]), f"{int(r['trip_count']):,}"]
    for r in N["isoforest"]["top_anomaly_zones_robust"]
]
caption(doc, "Table 6. Highest anomaly-rate zones (n sampled ≥ 30).")
table(doc, ["Zone", "Borough", "Anomaly rate", "n sampled", "Total trips (6mo)"], iso_top_rows)

_top_robust = N["isoforest"]["top_anomaly_zones_robust"]
_jfk = next(r for r in _top_robust if "JFK" in r["Zone"])
_top_overall = _top_robust[0]
_remainder = [r["Zone"] for r in _top_robust if r["Zone"] not in (_jfk["Zone"], _top_overall["Zone"])]
body(doc,
    f"As anticipated in the proposal's limitations analysis, the raw (unfiltered) top-anomaly-rate "
    f"ranking is dominated by a small-sample artefact: {N['isoforest']['sparsity_artefact_zones']} "
    "zones with fewer than 5 sampled trips register a 100% anomaly rate purely because a single "
    "unusual trip in a near-zero-volume zone produces a 100% rate by construction. Restricting to "
    "zones with at least 30 sampled trips removes this artefact and yields a materially more "
    f"credible picture (Table 6): {_top_overall['Zone']} tops the list at "
    f"{_top_overall['anomaly_rate']:.1%}, though on a modest sample ({_top_overall['n_sampled']} "
    f"trips). More striking is {_jfk['Zone']}, which, with a very large sample of "
    f"{_jfk['n_sampled']:,} trips, has a genuinely elevated {_jfk['anomaly_rate']:.1%} anomaly rate; "
    "this is unsurprising, since airport trips are structurally long-distance, high-fare journeys "
    "relative to the city-wide Manhattan-dominated norm against which the model is trained. The "
    f"remainder of the well-supported list ({', '.join(_remainder)}) is composed almost entirely of "
    "outer-borough Queens and Brooklyn zones, suggesting that trips to and from the periphery of the "
    "yellow-taxi service area are systematically more likely to look “unusual” against a norm "
    "defined by short Manhattan trips, a genuinely novel, defensible finding for zone-level "
    "regulatory targeting."
)

# ---- RQ5 ----
h2(doc, "5.5 RQ5: Unified Zone Fingerprint (UMAP Synthesis)")
figure(doc, "layer6_umap.png",
       f"Figure 10. UMAP embedding of the {N['umap']['n_fingerprint_dims']}-dimensional zone "
       f"fingerprint ({N['umap']['n_zones']} zones), coloured by borough (left) and by the Layer 2 "
       "K-Means archetype (right).")
figure(doc, "layer6_umap_vs_pca.png",
       "Figure 11. UMAP embedding (left) versus a linear PCA baseline on the same fingerprint (right).")
body(doc,
    f"The UMAP embedding of the {N['umap']['n_fingerprint_dims']}-dimensional zone fingerprint (10 "
    "K-Means features + 6 Tucker zone-mode factors + 1 Isolation Forest anomaly rate) recovers New "
    "York City's functional geography without ever being given borough labels: Manhattan zones form "
    "a dense, well-separated arc; the JFK/LaGuardia airport pairing forms an isolated cluster; "
    "Staten Island zones form a tight, separate group; and Brooklyn/Queens zones show partial "
    "overlap reflecting shared residential rhythms. The K-Means-coloured panel confirms that the "
    "five spatial archetypes from Layer 2 correspond to coherent, contiguous regions of the UMAP "
    "manifold rather than being scattered arbitrarily, direct visual validation that the "
    "archetypes are not artefacts of the K-Means algorithm alone. The linear PCA baseline, by "
    f"contrast, explains only {N['umap']['pca_variance_explained']:.1%} of variance in two dimensions "
    "and produces markedly less separated groupings, confirming that the zone fingerprint's "
    "structure is meaningfully non-linear and justifying the use of manifold learning for this "
    "synthesis layer."
)

page_break(doc)

# ============================================================================
# 6. Discussion
# ============================================================================
h1(doc, "6. Discussion")
body(doc,
    "Read together, the six layers converge on a consistent picture of NYC yellow-taxi demand that "
    "is considerably more structured than a purely descriptive analysis would suggest. A small "
    "number of latent archetypes (five spatial, three temporal, six tensor-structural) account "
    "for the overwhelming majority of variation across 260 zones and 18.68 million trips, supporting "
    "the proposal's central epistemological claim that unsupervised methods are appropriate for "
    "exploratory urban analytics: the goal here was not to test a known hypothesis but to discover "
    "which hypotheses are worth testing next."
)
body(doc,
    "The single most consequential finding, in policy terms, is the extreme spatial concentration of "
    "yellow-taxi supply: 53 Manhattan-core zones carry 85% of all trips, while 85 outer-borough "
    "residential zones, a third of the city's served area, together generate less than a third "
    "of one percent of trips. This is not a new observation in transportation economics, but the "
    "scale of the imbalance revealed here, measured directly rather than assumed, is a genuinely "
    "useful empirical anchor for an equity argument: any infrastructure or subsidy conversation about "
    "“taxi accessibility” in outer-borough residential neighbourhoods is, in practice, a "
    "conversation about a near-total absence of yellow-taxi service, not a marginal shortfall."
)
body(doc,
    "The temporal (K-Shape) and structural (Tucker) layers each recover a nightlife-adjacent, "
    "midnight-peaking pattern independently, using entirely different mathematical machinery "
    "(shape-based time-series clustering versus tensor factorisation), a form of internal "
    "triangulation that increases confidence in the finding beyond what either method alone would "
    "justify. The "
    "Tucker layer's weekday-only day-type component, which has no direct analogue in the K-Means or "
    "K-Shape outputs, demonstrates the proposal's core methodological claim that preserving the full "
    "three-mode tensor structure surfaces genuinely latent patterns invisible to zone-level or "
    "time-series-only analysis."
)
body(doc,
    "The anomaly layer reframes “unusual” in a way that is directly actionable: once the "
    "small-sample artefact is controlled for, elevated anomaly concentration is not randomly "
    "distributed but falls disproportionately on the airport corridor and a specific set of outer "
    "Queens/Brooklyn zones. Because the Isolation Forest is trained on the pooled trip distribution "
    "(dominated by short Manhattan trips), this finding is partly a statement about model reference "
    "class rather than a pure statement about those zones' trip quality, a caveat worth stating "
    "explicitly to a regulator before treating the ranking as evidence of misconduct rather than "
    "structurally different trip geometry."
)
body(doc,
    "Finally, the UMAP synthesis provides the strongest evidence for RQ5: a fingerprint built purely "
    "from volume, fare, temporal, tensor, and anomaly signals, with no geographic coordinates and no "
    "borough labels supplied to the model, nonetheless reconstructs a 2-D layout that a New "
    "Yorker would recognise as the city's functional map. This is the clearest demonstration in the "
    "analysis that the four preceding layers are measuring a coherent underlying reality rather than "
    "four independent, unrelated sets of clusters."
)

# ============================================================================
# 7. Validation and Robustness Summary
# ============================================================================
h1(doc, "7. Validation and Robustness Summary")
body(doc, "Each unsupervised layer was evaluated against the criteria set out at proposal stage, to ensure outputs are analytically defensible rather than artefacts of parameter choice.")
caption(doc, "Table 7. Validation approach and outcome by layer.")
table(doc,
      ["Layer", "Validation approach", "Outcome"],
      [
          ["K-Means (Layer 2)", "Elbow + silhouette across k=2..8; interpretability against known NYC geography",
           f"Statistical optimum k=2 (sil. {N['kmeans']['statistical_best_silhouette']}); "
           f"k=5 adopted for interpretability (sil. {N['kmeans']['silhouette_k5']})"],
          ["K-Shape / DTW (Layer 3)", "Silhouette across k=2..6; centroid inspection; sensitivity to zone-exclusion threshold",
           f"k={N['kshape']['best_k']} selected (sil. {N['kshape']['best_silhouette']}); "
           f"{N['kshape']['n_active_zones']} active zones retained"],
          ["Tucker NTD (Layer 4)", "Reconstruction error across ranks (4,3,2)–(8,4,2); component interpretability",
           f"{N['tucker']['explained_variance']:.1%} explained variance at rank "
           f"{tuple(N['tucker']['primary_rank'])}; error stable across neighbouring ranks"],
          ["Isolation Forest (Layer 5)", "Stability of zone-level anomaly rates across independent random halves",
           f"Pearson r = {N['isoforest']['stability_correlation']} between halves; robust after "
           "n ≥ 30 sample filtering"],
          ["UMAP (Layer 6)", "Visual separation aligned with known borough/zone categories; comparison with PCA baseline",
           f"Borough-aligned separation recovered unsupervised; PCA baseline only "
           f"{N['umap']['pca_variance_explained']:.1%} variance explained in 2D"],
      ])

# ============================================================================
# 8. Limitations and Mitigations
# ============================================================================
h1(doc, "8. Limitations and Mitigations")
caption(doc, "Table 8. Limitations and their mitigations.")
table(doc,
      ["Limitation", "Mitigation / status"],
      [
          ["Data covers Jan–Jun 2023 only: seasonal bias", "Flagged explicitly; a full-year or "
           "multi-year extension is proposed as future work (Section 11)"],
          ["Yellow-taxi market share is small and declining relative to app-based FHV (Uber/Lyft)",
           "Acknowledged selection bias; yellow-taxi data remains the only fully open, trip-level "
           "dataset at this resolution and volume"],
          ["Zone-level analysis loses within-zone heterogeneity", "Layer 5's trip-level anomaly "
           "detection partially recovers individual-trip structure"],
          ["Tucker reconstruction leaves "
           f"{1 - N['tucker']['explained_variance']:.1%} of variance unexplained",
           "Human mobility tensors are inherently noisy; the retained rank captures structural "
           "macro-trends while omitting high-frequency transactional noise, without overfitting "
           "given the tensor's sparsity"],
          ["Isolation Forest trained on a "
           f"{N['isoforest']['n_sampled']:,}-trip sample, not the full {N['qc']['filtered_trip_count']:,}",
           f"Validated: independent random-half refits correlate at r={N['isoforest']['stability_correlation']}; "
           "small-sample zones (n<30) are excluded from the headline anomaly-rate ranking"],
          ["K-Means silhouette optimum (k=2) diverges from the interpretively-selected solution (k=5)",
           "Both solutions reported transparently (Section 5.1, 7); k=5 justified on interpretability "
           "grounds consistent with the pre-registered validation criteria"],
      ])

page_break(doc)

# ============================================================================
# 9. Theoretical Grounding
# ============================================================================
h1(doc, "9. Theoretical Grounding")
h2(doc, "9.1 Urban Informatics and the Smart City Paradigm")
body(doc,
    "This work sits within the emerging field of urban informatics, the application of "
    "computational methods to the dense data streams produced by modern cities (Batty, 2013). Taxi "
    "trip records are a canonical urban informatics dataset: they encode individual mobility "
    "behaviour at city-scale, without the privacy costs of GPS tracking or mobile data, because the "
    "TLC mandates anonymised public release. The Big Data 5 Vs framework (Laney, 2001) provides the "
    "analytical scaffolding used throughout Section 3: Volume justifies distributed/streaming "
    "processing (Section 4.1); Variety motivates multi-modal feature engineering; Velocity "
    "contextualises real-time policy applications; Veracity drives the quality-filtering layer; "
    "Value grounds the regulatory and equity implications discussed in Section 6."
)
h2(doc, "9.2 Unsupervised Learning as Hypothesis Generation")
body(doc,
    "Unlike supervised models, which require labelled outcomes and test pre-specified hypotheses, "
    "unsupervised learning treats the data as the primary source of structure. This is "
    "epistemologically appropriate for exploratory urban analytics, where the goal is not to test a "
    "known hypothesis but to discover which hypotheses are worth testing. The pipeline therefore "
    "follows the discovery → characterisation → validation cycle advocated by Tukey (1977) in "
    "exploratory data analysis, extended to the machine learning era by Hastie et al. (2009). Each "
    "layer generates a finding that becomes a candidate for confirmatory analysis in future work: the "
    "cluster assignments become treatment groups for regression; the anomaly flags become inputs for "
    "supervised compliance classifiers; the UMAP embedding becomes the basis for spatial econometric "
    "modelling."
)
h2(doc, "9.3 Tensor Methods in Urban Analytics")
body(doc,
    "The application of Tucker decomposition to urban mobility tensors is methodologically grounded "
    "in the growing literature on tensor-based spatiotemporal analysis (Kolda & Bader, 2009; "
    "Cichocki et al., 2016). Kolda and Bader (2009) provide the mathematical foundation for both "
    "Tucker and CP decompositions, while Cichocki et al. (2016) establish non-negativity constraints "
    "as a route to interpretable components. This analysis applies those foundations to a public, "
    "reproducible urban mobility dataset, making the methodology accessible for replication and "
    "extension. Per the Section 4.1 design decision, it also extends them with a streaming "
    "aggregation strategy for constructing the tensor itself at genuine Big Data scale without "
    "requiring distributed infrastructure."
)

h2(doc, "9.4 Relationship to Existing Literature")
body(doc,
    "The specific research questions posed in Section 2 are motivated by, and extend, a body of "
    "prior work on taxi and mobile-sensed urban mobility data. Yuan et al. (2011) predict "
    "zone-level passenger demand hotspots for individual drivers; RQ1's search for zone-level "
    "demand archetypes generalises this hotspot framing from a single-driver recommendation "
    "problem into a city-wide unsupervised taxonomy. Castro et al. (2012) model and predict traffic "
    "from large-scale taxi GPS traces, establishing that trip-level GPS data supports fine-grained "
    "spatiotemporal modelling; this analysis instead works from the zone-level, non-GPS records the "
    "TLC publishes, trading spatial resolution for the privacy and openness properties discussed in "
    "Section 10. Colak et al. (2016) use mobile-phone data to model urban congestion across "
    "transport modes, motivating the multi-modal, tri-modal comparison (yellow taxi, green taxi, "
    "and For-Hire Vehicles) proposed as future work in Section 11.2. Zheng et al. (2014) survey the "
    "broader field of urban computing, situating taxi analytics as one instance of a general pattern "
    "in which dense sensor-generated urban data supports concepts, methodologies, and applications "
    "well beyond its original operational purpose, precisely the framing this chapter adopts in "
    "treating TLC trip records as a Big Data case study rather than only a transportation dataset."
)

# ============================================================================
# 10. Data Ethics and Privacy
# ============================================================================
h1(doc, "10. Data Ethics and Privacy")
body(doc,
    "NYC TLC trip records are published as open government data under the NYC Open Data programme. "
    "The dataset is anonymised at source: no driver or passenger identifiers are included. Pickup "
    "and drop-off locations are reported at zone level (not GPS coordinates), preventing "
    "re-identification of individual trips. No personally identifiable information was processed or "
    "stored at any stage of this analysis."
)
body(doc,
    "The anomaly detection layer identifies trip-level patterns, not individual actors. Any "
    "regulatory application of anomaly scores would require separate data linkage by the TLC under "
    "its existing compliance mandate; this research produces only aggregate zone-level anomaly-rate "
    "statistics, none of which are linked to any identifiable individual."
)

# ============================================================================
# 11. Conclusion and Future Work
# ============================================================================
h1(doc, "11. Conclusion and Future Work")
body(doc,
    "This chapter set out to ask whether a purely unsupervised, multi-method pipeline could recover "
    "meaningful structure from a high-volume urban mobility dataset without any labelled outcome to "
    "guide it. The answer, on the evidence of the completed six-layer analysis, is yes: a small "
    "number of latent archetypes account for the overwhelming majority of variation across "
    "260 zones and 18.68 million trips, and each layer's findings are corroborated, rather than "
    "contradicted, by the layers built through independent mathematical machinery."
)
body(doc,
    "The empirical contribution is a reproducible five-archetype zone typology, validated against "
    f"known urban geography and derived from the full {N['qc']['filtered_trip_count']:,}-trip "
    "filtered dataset rather than a sample; a borough-crossing atlas of temporal demand rhythms "
    "showing that functional zone type explains demand shape more strongly than geographic "
    "proximity; a zone-level anomaly geography that survives the small-sample artefact once "
    "low-count zones are excluded; and evidence that the Zone×Hour×DayType demand tensor admits "
    f"a low-rank non-negative factorisation explaining {N['tucker']['explained_variance']:.1%} of "
    "variance, including a genuinely latent weekday-only commuter component invisible to the other "
    "layers. Methodologically, the chapter demonstrates that these four signals combine into a "
    "single zone fingerprint at genuine Big Data scale on commodity hardware, through a streaming "
    "rather than full-materialisation Layer 1 design, and that the entire pipeline, from raw "
    "Parquet download through final figures, is reproducible end to end from versioned source "
    "modules and a single executable notebook."
)
body(doc,
    "These findings carry direct policy weight. Zone-level anomaly rates provide TLC compliance "
    "review with a ranked, evidence-based shortlist that is materially more informative than random "
    "auditing; the demand archetypes and rhythm clusters offer a basis for bus-route and bike-share "
    "planning that depends on peak-timing rather than daily totals; and the near-total absence of "
    "yellow-taxi service in outer-borough residential zones, quantified directly here rather than "
    "assumed, gives transportation-equity policy discussion a concrete empirical anchor rather than "
    "an anecdotal one."
)
h2(doc, "11.2 Future Work")
body(doc,
    "Four extensions follow naturally from the limitations set out in Section 8. The study window "
    "could be extended to a full year, or to multiple years spanning the COVID-19 disruption, to "
    "test whether the archetypes identified here are seasonally stable or specific to the "
    "January–June period analysed. Green taxi and For-Hire Vehicle (Uber/Lyft) records could be "
    "incorporated for a tri-modal comparison and market-segmentation analysis, addressing the "
    "yellow-taxi selection bias noted throughout. Density-based spatial clustering, such as DBSCAN, "
    "could be applied as an alternative to K-Means, which may better respect the irregular, "
    "non-convex geography of NYC's taxi zones than a centroid-based method. Finally, and returning "
    "to the motivation set out in Section 1, the same streaming multi-layer pipeline design could be "
    "applied to Ghanaian urban transport data as comparable trip-level records become available "
    "through digital ticketing, ride-hailing platforms, or GPS fleet tracking, treating this chapter "
    "as a methodological template rather than a result specific to New York City."
)

# ============================================================================
# References
# ============================================================================
page_break(doc)
h1(doc, "References")
refs = [
    "Batty, M. (2013). The New Science of Cities. MIT Press.",
    "Castro, P. S., Zhang, D., & Li, S. (2012). Urban traffic modelling and prediction using large "
    "scale taxi GPS traces. In Pervasive Computing, Lecture Notes in Computer Science (LNCS 7319), "
    "pp. 57–72. Springer.",
    "Cichocki, A., Lee, N., Oseledets, I., Phan, A. H., Zhao, Q., & Mandic, D. P. (2016). Tensor "
    "networks for dimensionality reduction and large-scale optimization: Part 1 low-rank tensor "
    "decompositions. Foundations and Trends in Machine Learning, 9(4-5), 249–429.",
    "Colak, S., Lima, A., & González, M. C. (2016). Understanding congested travel in urban areas. "
    "Nature Communications, 7, 10793.",
    "Hastie, T., Tibshirani, R., & Friedman, J. (2009). The Elements of Statistical Learning (2nd "
    "ed.). Springer.",
    "Kolda, T. G., & Bader, B. W. (2009). Tensor decompositions and applications. SIAM Review, "
    "51(3), 455–500.",
    "Laney, D. (2001). 3D data management: Controlling data volume, velocity, and variety. META "
    "Group Research Note, 6.",
    "Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). Isolation forest. In Proceedings of the 2008 "
    "IEEE International Conference on Data Mining (ICDM 2008), pp. 413–422. IEEE.",
    "McInnes, L., Healy, J., & Melville, J. (2018). UMAP: Uniform manifold approximation and "
    "projection for dimension reduction. arXiv preprint, arXiv:1802.03426.",
    "NYC Taxi & Limousine Commission (2023). TLC Trip Record Data: Yellow Taxi. NYC Open Data. "
    "Retrieved from https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page",
    "Paparrizos, J., & Gravano, L. (2015). k-Shape: Efficient and accurate clustering of time "
    "series. In Proceedings of the 2015 ACM SIGMOD International Conference on Management of Data, "
    "pp. 1855–1870. ACM.",
    "Tukey, J. W. (1977). Exploratory Data Analysis. Addison-Wesley.",
    "Yuan, J., Zheng, Y., Zhang, L., Xie, X., & Sun, G. (2011). Where to find my next passenger. In "
    "Proceedings of the 13th ACM International Conference on Ubiquitous Computing (UbiComp 2011), "
    "pp. 109–118. ACM.",
    "Zheng, Y., Capra, L., Wolfson, O., & Yang, H. (2014). Urban computing: Concepts, "
    "methodologies, and applications. ACM Transactions on Intelligent Systems and Technology, 5(3), "
    "Article 38.",
]
for ref in refs:
    p = doc.add_paragraph(ref)
    p.paragraph_format.left_indent = Inches(0.5)
    p.paragraph_format.first_line_indent = Inches(-0.5)
    p.paragraph_format.space_after = Pt(8)

# ============================================================================
# Appendix
# ============================================================================
page_break(doc)
h1(doc, "Appendix A. Reproducibility")
body(doc,
    "The full analysis is implemented as versioned Python modules under src/ (config.py, "
    "layer1_load_filter.py … layer6_umap.py, viz.py, run_pipeline.py) and mirrored, cell-by-cell, "
    "in notebooks/01_full_pipeline.ipynb. Running python3 -m src.run_pipeline from the project root "
    "with the six monthly Parquet files present under data/raw/nyc-taxi-trips/ reproduces every "
    "number, table, and figure in this chapter end-to-end (total pipeline runtime: "
    f"{N['total_elapsed_seconds']:.0f} seconds on a 20-core commodity workstation, excluding the "
    "one-time ~305 MB data download). A fixed random seed (42) is used throughout for K-Means, "
    "K-Shape, Isolation Forest, Tucker initialisation, and UMAP. Full setup instructions are given "
    "in README.md."
)
h1(doc, "Appendix B. Repository Structure")
body(doc, "See README.md for the complete, current repository layout. In summary:")
for line in [
    "data/raw/: downloaded TLC Parquet files and zone lookup table",
    "data/processed/: all intermediate pipeline artefacts and results_summary.json / narrative_data.json",
    "src/: pipeline source code (Layers 1–6), configuration, and visualisation",
    "notebooks/: the executed, reproducible analysis notebook",
    "reports/figures/: all generated figures referenced in this chapter",
    "reports/dissertation/: this document and the scripts that generate it "
    "(build_dissertation.py, build_toc.py)",
]:
    bullet(doc, line)

doc.save(OUT_DOCX)
print(f"FINAL document saved to {OUT_DOCX}")

with open(HEADING_RECORD_PATH, "w") as f:
    json.dump(HEADING_RECORD, f, indent=2)
print(f"Heading record saved to {HEADING_RECORD_PATH}")

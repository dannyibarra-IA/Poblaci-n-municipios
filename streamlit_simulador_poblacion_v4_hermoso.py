import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="Urban Waste Circularity Simulator",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

PLOT_TEMPLATE = "plotly_white"

# =========================================================
# DEFAULT PARAMETERS
# =========================================================
FRACTION_COLUMNS = [
    "organics_pct",
    "plastics_pct",
    "paper_cardboard_pct",
    "glass_pct",
    "metals_pct",
    "textiles_pct",
    "others_pct",
]

RECOVERABLE_FRACTIONS = [
    "plastics_pct",
    "paper_cardboard_pct",
    "glass_pct",
    "metals_pct",
    "textiles_pct",
]

CITY_COORDS = {
    "Medellín": (6.2442, -75.5812),
    "Santiago de Cali": (3.4516, -76.5320),
    "Barranquilla": (10.9685, -74.7813),
    "Cartagena de Indias": (10.3910, -75.4794),
    "Soacha": (4.5833, -74.2167),
    "San José de Cúcuta": (7.8939, -72.5078),
    "Soledad": (10.9184, -74.7646),
    "Bucaramanga": (7.1254, -73.1198),
    "Bello": (6.3373, -75.5540),
    "Valledupar": (10.4631, -73.2532),
}

DEFAULT_INPUTS = pd.DataFrame(
    [
        ["Medellín", 2025, 2650000, 2050, 3000000, 0.78, 0.002, 12000000, 52, 13, 12, 4, 2, 5, 12],
        ["Santiago de Cali", 2025, 2280000, 2050, 2600000, 0.80, 0.002, 8500000, 50, 14, 11, 4, 2, 4, 15],
        ["Barranquilla", 2025, 1320000, 2050, 1550000, 0.85, 0.003, 7000000, 49, 15, 10, 4, 2, 5, 15],
        ["Cartagena de Indias", 2025, 1100000, 2050, 1320000, 0.82, 0.003, 5500000, 51, 14, 10, 4, 2, 4, 15],
        ["Soacha", 2025, 820000, 2050, 1050000, 0.74, 0.003, 4000000, 53, 13, 10, 3, 2, 5, 14],
        ["San José de Cúcuta", 2025, 800000, 2050, 960000, 0.77, 0.002, 4500000, 52, 13, 11, 4, 2, 4, 14],
        ["Soledad", 2025, 740000, 2050, 910000, 0.79, 0.003, 4200000, 50, 15, 10, 4, 2, 5, 14],
        ["Bucaramanga", 2025, 620000, 2050, 700000, 0.76, 0.001, 5200000, 51, 13, 12, 4, 2, 4, 14],
        ["Bello", 2025, 560000, 2050, 660000, 0.75, 0.002, 3600000, 52, 13, 11, 4, 2, 5, 13],
        ["Valledupar", 2025, 560000, 2050, 700000, 0.81, 0.003, 3300000, 51, 14, 10, 4, 2, 5, 14],
    ],
    columns=[
        "city",
        "base_year",
        "population_base",
        "validation_year",
        "population_validation",
        "gpc_base_kg_person_day",
        "gpc_annual_growth",
        "landfill_remaining_capacity_t",
        *FRACTION_COLUMNS,
    ],
)

SCENARIOS = {
    "BAU": {
        "source_reduction_target": 0.00,
        "collection_target": 0.85,
        "recycling_target": 0.18,
        "composting_target": 0.08,
        "education_bonus_target": 0.00,
        "formalization_bonus_target": 0.00,
        "label": "Business as usual",
    },
    "Moderate Circularity": {
        "source_reduction_target": 0.05,
        "collection_target": 0.90,
        "recycling_target": 0.28,
        "composting_target": 0.16,
        "education_bonus_target": 0.03,
        "formalization_bonus_target": 0.04,
        "label": "Moderate intervention",
    },
    "Accelerated Circularity": {
        "source_reduction_target": 0.12,
        "collection_target": 0.96,
        "recycling_target": 0.40,
        "composting_target": 0.28,
        "education_bonus_target": 0.06,
        "formalization_bonus_target": 0.08,
        "label": "High circularity push",
    },
}

# =========================================================
# HELPERS
# =========================================================
def human_format(value, decimals=0):
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return str(value)


def validate_inputs(df):
    required = {
        "city",
        "base_year",
        "population_base",
        "validation_year",
        "population_validation",
        "gpc_base_kg_person_day",
        "gpc_annual_growth",
        "landfill_remaining_capacity_t",
        *FRACTION_COLUMNS,
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    out = df.copy()
    out["city"] = out["city"].astype(str).str.strip()
    numeric_cols = [c for c in out.columns if c != "city"]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.dropna(subset=["city", "base_year", "population_base", "validation_year", "population_validation"])
    out["base_year"] = out["base_year"].astype(int)
    out["validation_year"] = out["validation_year"].astype(int)

    if (out["population_base"] <= 0).any() or (out["population_validation"] <= 0).any():
        raise ValueError("Population values must be greater than zero.")

    if (out["validation_year"] <= out["base_year"]).any():
        raise ValueError("validation_year must be greater than base_year for every city.")

    out["fraction_sum_pct"] = out[FRACTION_COLUMNS].sum(axis=1)
    if not np.allclose(out["fraction_sum_pct"], 100, atol=2.0):
        st.warning("Some composition percentages do not add up to 100%. They will be normalized internally.")

    return out


def input_template_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="city_inputs", index=False)
    return output.getvalue()


@st.cache_data(show_spinner=False)
def load_input_file(uploaded_file):
    df = pd.read_excel(uploaded_file, sheet_name="city_inputs")
    return validate_inputs(df)


def interpolate_policy(start_value, target_value, year, start_year, end_year):
    if end_year <= start_year:
        return float(target_value)
    alpha = np.clip((year - start_year) / (end_year - start_year), 0, 1)
    return float(start_value + alpha * (target_value - start_value))


def effective_policy_params(source_reduction, collection, recycling, composting, education_bonus, formalization_bonus):
    eff_recycling = min(0.95, recycling + education_bonus * 0.35 + formalization_bonus * 0.65)
    eff_composting = min(0.90, composting + education_bonus * 0.50)
    eff_collection = min(0.99, collection + education_bonus * 0.20)
    eff_source = min(0.35, source_reduction + education_bonus * 0.15)
    return eff_source, eff_collection, eff_recycling, eff_composting


def project_city(row, start_year, end_year, scenario_name, overrides=None):
    scenario = SCENARIOS[scenario_name].copy()
    if overrides:
        scenario.update(overrides)

    base_year = int(row["base_year"])
    validation_year = int(row["validation_year"])
    p0 = float(row["population_base"])
    p_validation = float(row["population_validation"])
    gpc0 = float(row["gpc_base_kg_person_day"])
    gpc_growth = float(row["gpc_annual_growth"])
    capacity = float(row["landfill_remaining_capacity_t"])

    rp = (p_validation / p0) ** (1 / (validation_year - base_year)) - 1

    fractions_raw = row[FRACTION_COLUMNS].astype(float) / 100
    fractions = fractions_raw / fractions_raw.sum() if fractions_raw.sum() > 0 else fractions_raw
    f_org = float(fractions["organics_pct"])
    f_rec = float(fractions[RECOVERABLE_FRACTIONS].sum())

    records = []
    cumulative_landfilled = 0.0

    for year in range(start_year, end_year + 1):
        dt = year - base_year
        population = p0 * ((1 + rp) ** dt)
        gpc_without_prevention = gpc0 * ((1 + gpc_growth) ** dt)

        source_reduction = interpolate_policy(0, scenario["source_reduction_target"], year, start_year, end_year)
        collection = interpolate_policy(0.85, scenario["collection_target"], year, start_year, end_year)
        recycling = interpolate_policy(0.18, scenario["recycling_target"], year, start_year, end_year)
        composting = interpolate_policy(0.08, scenario["composting_target"], year, start_year, end_year)
        education_bonus = interpolate_policy(0, scenario["education_bonus_target"], year, start_year, end_year)
        formalization_bonus = interpolate_policy(0, scenario["formalization_bonus_target"], year, start_year, end_year)

        eff_source, eff_collection, eff_recycling, eff_composting = effective_policy_params(
            source_reduction, collection, recycling, composting, education_bonus, formalization_bonus
        )

        gpc_effective = gpc_without_prevention * (1 - eff_source)
        generated_t = population * gpc_effective * 365 / 1000
        collected_t = generated_t * eff_collection
        uncollected_t = generated_t - collected_t

        recoverable_pool_t = generated_t * f_rec
        organics_pool_t = generated_t * f_org

        recycled_t = min(collected_t, recoverable_pool_t * eff_recycling)
        remaining_after_recycling_t = max(0, collected_t - recycled_t)
        composted_t = min(remaining_after_recycling_t, organics_pool_t * eff_composting)
        diverted_t = recycled_t + composted_t
        landfilled_t = max(0, collected_t - diverted_t)
        cumulative_landfilled += landfilled_t
        remaining_capacity_t = max(0, capacity - cumulative_landfilled)

        diversion_rate = diverted_t / generated_t if generated_t > 0 else 0
        collection_rate = collected_t / generated_t if generated_t > 0 else 0
        landfill_life_years = remaining_capacity_t / landfilled_t if landfilled_t > 0 else np.inf
        circularity_gap = max(0, 1 - diversion_rate)

        fraction_amounts = {col.replace("_pct", "_t"): generated_t * float(fractions[col]) for col in FRACTION_COLUMNS}

        records.append(
            {
                "city": row["city"],
                "year": year,
                "scenario": scenario_name,
                "population": population,
                "population_growth_rate": rp,
                "gpc_without_prevention_kg_person_day": gpc_without_prevention,
                "gpc_effective_kg_person_day": gpc_effective,
                "generated_t": generated_t,
                "collected_t": collected_t,
                "uncollected_t": uncollected_t,
                "recycled_t": recycled_t,
                "composted_t": composted_t,
                "diverted_t": diverted_t,
                "landfilled_t": landfilled_t,
                "cumulative_landfilled_t": cumulative_landfilled,
                "remaining_capacity_t": remaining_capacity_t,
                "diversion_rate": diversion_rate,
                "collection_rate": collection_rate,
                "landfill_life_years": landfill_life_years,
                "circularity_gap": circularity_gap,
                "effective_source_reduction": eff_source,
                "effective_collection": eff_collection,
                "effective_recycling": eff_recycling,
                "effective_composting": eff_composting,
                "organics_share": f_org,
                "recoverables_share": f_rec,
                **fraction_amounts,
            }
        )

    return pd.DataFrame(records)


def run_projection(inputs, start_year, end_year, scenario_name, overrides=None):
    frames = [project_city(row, start_year, end_year, scenario_name, overrides=overrides) for _, row in inputs.iterrows()]
    return pd.concat(frames, ignore_index=True)


def compute_bau_reference(inputs, start_year, end_year):
    return run_projection(inputs, start_year, end_year, "BAU")


def classify_risk(row):
    score = 0
    if row["landfill_life_years"] < 5:
        score += 3
    elif row["landfill_life_years"] < 10:
        score += 2
    elif row["landfill_life_years"] < 20:
        score += 1

    if row["diversion_rate"] < 0.20:
        score += 2
    elif row["diversion_rate"] < 0.35:
        score += 1

    if row["collection_rate"] < 0.85:
        score += 2
    elif row["collection_rate"] < 0.95:
        score += 1

    if row["gpc_effective_kg_person_day"] > 1.1:
        score += 1

    if score >= 5:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"


def circularity_light(row):
    if row["diversion_rate"] >= 0.45 and row["landfill_life_years"] >= 15 and row["collection_rate"] >= 0.95:
        return "Green"
    if row["diversion_rate"] >= 0.25 and row["landfill_life_years"] >= 8 and row["collection_rate"] >= 0.85:
        return "Yellow"
    return "Red"


def priority_index(df_year):
    d = df_year.copy()

    def min_max(s):
        s = pd.Series(s, dtype=float)
        if s.max() == s.min():
            return pd.Series(np.zeros(len(s)), index=s.index)
        return (s - s.min()) / (s.max() - s.min())

    landfill_pressure = d["landfilled_t"] / d["remaining_capacity_t"].replace(0, np.nan).fillna(1)
    d["n_per_capita"] = min_max(d["gpc_effective_kg_person_day"])
    d["n_landfill_pressure"] = min_max(landfill_pressure)
    d["n_collection_gap"] = min_max(1 - d["collection_rate"])
    d["n_circularity_gap"] = min_max(d["circularity_gap"])
    d["n_uncollected"] = min_max(d["uncollected_t"])

    d["priority_score"] = 100 * (
        0.25 * d["n_per_capita"]
        + 0.25 * d["n_landfill_pressure"]
        + 0.20 * d["n_circularity_gap"]
        + 0.15 * d["n_collection_gap"]
        + 0.15 * d["n_uncollected"]
    )
    d["priority_level"] = pd.cut(d["priority_score"], bins=[-0.01, 33, 66, 100], labels=["Low", "Medium", "High"])
    return d.sort_values("priority_score", ascending=False)


def build_alerts(row):
    alerts = []
    if row["landfill_life_years"] < 5:
        alerts.append(("High", "Estimated landfill life is below 5 years."))
    elif row["landfill_life_years"] < 10:
        alerts.append(("Medium", "Estimated landfill life is below 10 years."))

    if row["collection_rate"] < 0.85:
        alerts.append(("High", "Collection rate is below 85%."))
    elif row["collection_rate"] < 0.95:
        alerts.append(("Medium", "Collection rate is below 95%."))

    if row["diversion_rate"] < 0.20:
        alerts.append(("High", "Diversion rate is below 20%."))
    elif row["diversion_rate"] < 0.35:
        alerts.append(("Medium", "Diversion rate remains moderate."))

    if row["gpc_effective_kg_person_day"] > 1.1:
        alerts.append(("Medium", "Per-capita waste generation is above 1.1 kg/person/day."))

    if not alerts:
        alerts.append(("Low", "No immediate structural alert under the selected scenario."))
    return alerts


def to_excel_download(df_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in df_dict.items():
            safe_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)
    return output.getvalue()


def make_sankey(row):
    labels = ["Generated", "Collected", "Uncollected", "Recycled", "Composted", "Landfilled"]
    source = [0, 0, 1, 1, 1]
    target = [1, 2, 3, 4, 5]
    values = [row["collected_t"], row["uncollected_t"], row["recycled_t"], row["composted_t"], row["landfilled_t"]]
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(label=labels, pad=18, thickness=18),
                link=dict(source=source, target=target, value=values),
            )
        ]
    )
    fig.update_layout(title_text="Waste flow balance", template=PLOT_TEMPLATE, height=430)
    return fig


def sensitivity_analysis(inputs, selected_city, start_year, end_year, scenario_name, baseline_results, selected_year):
    baseline_row = baseline_results[(baseline_results["city"] == selected_city) & (baseline_results["year"] == selected_year)].iloc[0]
    baseline_landfilled = baseline_row["landfilled_t"]
    baseline_diversion = baseline_row["diversion_rate"]

    tests = [
        ("Source reduction +5 pp", {"source_reduction_target": min(0.35, SCENARIOS[scenario_name]["source_reduction_target"] + 0.05)}),
        ("Collection +5 pp", {"collection_target": min(0.99, SCENARIOS[scenario_name]["collection_target"] + 0.05)}),
        ("Recycling +5 pp", {"recycling_target": min(0.95, SCENARIOS[scenario_name]["recycling_target"] + 0.05)}),
        ("Composting +5 pp", {"composting_target": min(0.90, SCENARIOS[scenario_name]["composting_target"] + 0.05)}),
        ("Education +5 pp", {"education_bonus_target": min(0.15, SCENARIOS[scenario_name]["education_bonus_target"] + 0.05)}),
        ("Formalization +5 pp", {"formalization_bonus_target": min(0.15, SCENARIOS[scenario_name]["formalization_bonus_target"] + 0.05)}),
    ]

    rows = []
    for label, override in tests:
        alt = run_projection(inputs, start_year, end_year, scenario_name, overrides=override)
        alt_row = alt[(alt["city"] == selected_city) & (alt["year"] == selected_year)].iloc[0]
        rows.append(
            {
                "lever": label,
                "landfilled_reduction_t": baseline_landfilled - alt_row["landfilled_t"],
                "diversion_rate_change_pp": (alt_row["diversion_rate"] - baseline_diversion) * 100,
            }
        )
    return pd.DataFrame(rows).sort_values("landfilled_reduction_t", ascending=False)

# =========================================================
# UI HEADER
# =========================================================
st.markdown(
    """
    <style>
        .hero-box {
            background: linear-gradient(135deg, rgba(13,92,145,0.11), rgba(47,125,107,0.10), rgba(185,137,0,0.08));
            border: 1px solid rgba(20, 50, 74, 0.10);
            border-radius: 24px;
            padding: 1.5rem 1.6rem 1.25rem 1.6rem;
            margin-bottom: 1rem;
            box-shadow: 0 6px 24px rgba(20, 50, 74, 0.08);
        }
        .hero-kicker {
            display: inline-block;
            font-size: 0.78rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #0d5c91;
            background: rgba(255,255,255,0.78);
            border: 1px solid rgba(13,92,145,0.12);
            border-radius: 999px;
            padding: 0.35rem 0.7rem;
            margin-bottom: 0.75rem;
        }
        .hero-title {
            font-size: 2.15rem;
            line-height: 1.1;
            font-weight: 850;
            color: #14324a;
            margin-bottom: 0.5rem;
        }
        .hero-subtitle {
            color: #375268;
            font-size: 1.02rem;
            max-width: 1080px;
            line-height: 1.55;
            margin-bottom: 0.65rem;
        }
        .hero-meta {
            color: #5a6c7d;
            font-size: 0.92rem;
        }
    </style>

    <div class="hero-box">
        <div class="hero-kicker">Academic decision-support platform</div>
        <div class="hero-title">Urban Waste Simulation and Circularity Observatory</div>
        <div class="hero-subtitle">
            Prospective software for Colombian cities that projects population, municipal solid waste generation,
            waste composition and circularity trajectories from minimum input data. The platform integrates annual
            simulation, scenario comparison, landfill stress indicators, sensitivity analysis and decision-support metrics
            for urban environmental planning.
        </div>
        <div class="hero-meta">
            Developed by <b>Danny Ibarra Vega, Ph.D.</b> · Universidad de Antioquia · Waste systems, circular economy and dynamic simulation
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# SIDEBAR INPUTS
# =========================================================
st.sidebar.header("Simulation settings")
start_year = st.sidebar.number_input("Start year", min_value=2020, max_value=2050, value=2025, step=1)
end_year = st.sidebar.number_input("End year", min_value=int(start_year) + 1, max_value=2100, value=2050, step=1)
scenario_name = st.sidebar.selectbox("Scenario", list(SCENARIOS.keys()), index=0)
comparison_scenarios = st.sidebar.multiselect(
    "Scenarios to compare",
    list(SCENARIOS.keys()),
    default=list(SCENARIOS.keys()),
)
if not comparison_scenarios:
    comparison_scenarios = [scenario_name]

st.sidebar.download_button(
    "Download input template (.xlsx)",
    data=input_template_to_excel(DEFAULT_INPUTS),
    file_name="city_inputs_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

uploaded = st.sidebar.file_uploader("Upload city inputs (.xlsx)", type=["xlsx"])

if uploaded is not None:
    try:
        inputs = load_input_file(uploaded)
        st.sidebar.success("Input file loaded successfully.")
    except Exception as exc:
        st.sidebar.error(f"Input file error: {exc}")
        st.stop()
else:
    inputs = validate_inputs(DEFAULT_INPUTS)

with st.expander("Edit input data", expanded=False):
    st.write(
        "Each row represents one city. The model uses current population, a future validation population, per-capita waste generation and composition fractions."
    )
    edited_inputs = st.data_editor(inputs, num_rows="dynamic", use_container_width=True)
    try:
        inputs = validate_inputs(edited_inputs)
    except Exception as exc:
        st.error(f"Input validation error: {exc}")
        st.stop()

# =========================================================
# MODEL EXECUTION
# =========================================================
results = run_projection(inputs, int(start_year), int(end_year), scenario_name)
scenario_results = pd.concat(
    [run_projection(inputs, int(start_year), int(end_year), s) for s in comparison_scenarios],
    ignore_index=True,
)
bau = compute_bau_reference(inputs, int(start_year), int(end_year))

comparison = results.merge(
    bau[["city", "year", "landfilled_t", "diverted_t"]].rename(
        columns={"landfilled_t": "landfilled_bau_t", "diverted_t": "diverted_bau_t"}
    ),
    on=["city", "year"],
    how="left",
)
comparison["avoided_landfill_vs_bau_t"] = comparison["landfilled_bau_t"] - comparison["landfilled_t"]
comparison["additional_diversion_vs_bau_t"] = comparison["diverted_t"] - comparison["diverted_bau_t"]
comparison["cumulative_avoided_landfill_vs_bau_t"] = comparison.groupby("city")["avoided_landfill_vs_bau_t"].cumsum()
comparison["cumulative_additional_diversion_vs_bau_t"] = comparison.groupby("city")["additional_diversion_vs_bau_t"].cumsum()

cities = sorted(results["city"].unique())
selected_city = st.sidebar.selectbox("City focus", cities, index=0)
selected_year = st.sidebar.slider("Year focus", int(start_year), int(end_year), int(end_year))

city_df = results[results["city"] == selected_city].copy()
year_df = results[results["year"] == selected_year].copy()
year_df["risk_level"] = year_df.apply(classify_risk, axis=1)
year_df["circularity_light"] = year_df.apply(circularity_light, axis=1)
selected_row = results[(results["city"] == selected_city) & (results["year"] == selected_year)].iloc[0]
selected_light = circularity_light(selected_row)
comparison_city = comparison[comparison["city"] == selected_city].copy()
comparison_selected_row = comparison_city[comparison_city["year"] == selected_year].iloc[0]

# =========================================================
# KPI CARDS
# =========================================================
st.subheader(f"Scenario: {scenario_name} — {SCENARIOS[scenario_name]['label']}")

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("City", selected_city)
k2.metric("Population", human_format(selected_row["population"], 0))
k3.metric("Generated", f"{human_format(selected_row['generated_t'], 0)} t/y")
k4.metric("Diverted", f"{human_format(selected_row['diverted_t'], 0)} t/y")
k5.metric("Diversion rate", f"{human_format(selected_row['diversion_rate'] * 100, 1)}%")
collapse_years = selected_row["landfill_life_years"]
collapse_text = "∞" if np.isinf(collapse_years) else f"{human_format(collapse_years, 1)} years"
k6.metric("Years to landfill collapse", collapse_text)

m1, m2, m3 = st.columns(3)
m1.metric("Cumulative avoided landfill vs BAU", f"{human_format(comparison_selected_row['cumulative_avoided_landfill_vs_bau_t'], 0)} t")
m2.metric("Additional diversion vs BAU", f"{human_format(comparison_selected_row['additional_diversion_vs_bau_t'], 0)} t/y")
m3.metric("Circularity traffic light", selected_light)

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs(
    [
        "📈 Projections",
        "♻️ Composition",
        "🗺️ Geography",
        "🧭 Circularity indicators",
        "🔁 Scenario comparison",
        "🌊 Flow Sankey",
        "🧪 Sensitivity",
        "🚨 Alerts & priority",
        "📐 Methodology",
        "⬇️ Export",
    ]
)

with tab1:
    st.markdown("### Population and waste projections")
    c1, c2 = st.columns(2)
    with c1:
        fig_pop = px.line(
            city_df,
            x="year",
            y="population",
            markers=True,
            template=PLOT_TEMPLATE,
            title=f"Population projection — {selected_city}",
            labels={"year": "Year", "population": "Population"},
        )
        st.plotly_chart(fig_pop, use_container_width=True)
    with c2:
        fig_waste = px.line(
            city_df,
            x="year",
            y=["generated_t", "collected_t", "landfilled_t", "diverted_t"],
            markers=True,
            template=PLOT_TEMPLATE,
            title=f"Waste flow projection — {selected_city}",
            labels={"year": "Year", "value": "tons/year", "variable": "Flow"},
        )
        st.plotly_chart(fig_waste, use_container_width=True)

    fig_compare = px.line(
        results,
        x="year",
        y="generated_t",
        color="city",
        template=PLOT_TEMPLATE,
        title="Generated waste by city",
        labels={"year": "Year", "generated_t": "tons/year", "city": "City"},
    )
    st.plotly_chart(fig_compare, use_container_width=True)

with tab2:
    st.markdown("### Waste composition by projected fraction")
    fraction_cols_t = [c.replace("_pct", "_t") for c in FRACTION_COLUMNS]
    fraction_labels = {
        "organics_t": "Organics",
        "plastics_t": "Plastics",
        "paper_cardboard_t": "Paper and cardboard",
        "glass_t": "Glass",
        "metals_t": "Metals",
        "textiles_t": "Textiles",
        "others_t": "Others",
    }
    comp_row = selected_row[fraction_cols_t].rename(index=fraction_labels).reset_index()
    comp_row.columns = ["fraction", "tons_year"]

    c1, c2 = st.columns(2)
    with c1:
        fig_comp = px.pie(
            comp_row,
            names="fraction",
            values="tons_year",
            hole=0.45,
            template=PLOT_TEMPLATE,
            title=f"Composition — {selected_city}, {selected_year}",
        )
        st.plotly_chart(fig_comp, use_container_width=True)
    with c2:
        fig_comp_bar = px.bar(
            comp_row.sort_values("tons_year", ascending=False),
            x="fraction",
            y="tons_year",
            text_auto=".2s",
            template=PLOT_TEMPLATE,
            title="Composition in tons/year",
            labels={"fraction": "Fraction", "tons_year": "tons/year"},
        )
        st.plotly_chart(fig_comp_bar, use_container_width=True)

with tab3:
    st.markdown("### Geographic view: generation size and risk color")
    geo_df = year_df.copy()
    geo_df["lat"] = geo_df["city"].map(lambda c: CITY_COORDS.get(c, (np.nan, np.nan))[0])
    geo_df["lon"] = geo_df["city"].map(lambda c: CITY_COORDS.get(c, (np.nan, np.nan))[1])
    geo_df = geo_df.dropna(subset=["lat", "lon"])

    if geo_df.empty:
        st.info("No coordinates are available for the selected cities.")
    else:
        fig_map = px.scatter_mapbox(
            geo_df,
            lat="lat",
            lon="lon",
            size="generated_t",
            color="risk_level",
            color_discrete_map={"Low": "green", "Medium": "orange", "High": "red"},
            hover_name="city",
            hover_data={
                "generated_t": ":,.0f",
                "landfilled_t": ":,.0f",
                "diverted_t": ":,.0f",
                "diversion_rate": ":.1%",
                "landfill_life_years": ":.1f",
                "circularity_light": True,
                "gpc_effective_kg_person_day": ":.2f",
                "lat": False,
                "lon": False,
            },
            mapbox_style="open-street-map",
            zoom=4.8,
            center={"lat": 6.5, "lon": -74.5},
            template=PLOT_TEMPLATE,
            title=f"Generated waste size and operational risk — {selected_year}",
        )
        fig_map.update_layout(margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig_map, use_container_width=True)

with tab4:
    st.markdown("### Circularity indicators")
    c1, c2 = st.columns(2)
    with c1:
        fig_div = px.line(
            city_df,
            x="year",
            y="diversion_rate",
            markers=True,
            template=PLOT_TEMPLATE,
            title=f"Diversion rate — {selected_city}",
            labels={"year": "Year", "diversion_rate": "Diversion rate"},
        )
        fig_div.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig_div, use_container_width=True)
    with c2:
        fig_gap = px.line(
            city_df,
            x="year",
            y="circularity_gap",
            markers=True,
            template=PLOT_TEMPLATE,
            title=f"Circularity gap — {selected_city}",
            labels={"year": "Year", "circularity_gap": "Circularity gap"},
        )
        fig_gap.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig_gap, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        fig_avoid = px.bar(
            comparison[comparison["year"] == selected_year].sort_values("avoided_landfill_vs_bau_t", ascending=False),
            x="city",
            y="avoided_landfill_vs_bau_t",
            template=PLOT_TEMPLATE,
            title=f"Avoided landfill compared with BAU — {selected_year}",
            labels={"city": "City", "avoided_landfill_vs_bau_t": "tons/year"},
        )
        fig_avoid.update_layout(xaxis_tickangle=-25)
        st.plotly_chart(fig_avoid, use_container_width=True)
    with c4:
        fig_cum_avoid = px.line(
            comparison_city,
            x="year",
            y="cumulative_avoided_landfill_vs_bau_t",
            markers=True,
            template=PLOT_TEMPLATE,
            title=f"Cumulative avoided landfill vs BAU — {selected_city}",
            labels={"year": "Year", "cumulative_avoided_landfill_vs_bau_t": "tons"},
        )
        st.plotly_chart(fig_cum_avoid, use_container_width=True)

with tab5:
    st.markdown("### Side-by-side scenario comparison")
    st.write("This section compares the selected scenarios using the same input data, year and city focus.")

    scenario_city = scenario_results[
        (scenario_results["city"] == selected_city) & (scenario_results["year"] == selected_year)
    ].copy()

    if scenario_city.empty:
        st.info("No scenario data available for the current selection.")
    else:
        scenario_table = scenario_city[[
            "scenario",
            "population",
            "generated_t",
            "collected_t",
            "diverted_t",
            "landfilled_t",
            "diversion_rate",
            "circularity_gap",
            "remaining_capacity_t",
            "landfill_life_years",
        ]].copy()
        scenario_table["landfill_life_years"] = scenario_table["landfill_life_years"].replace(np.inf, np.nan)

        st.dataframe(
            scenario_table.style.format({
                "population": "{:,.0f}",
                "generated_t": "{:,.0f}",
                "collected_t": "{:,.0f}",
                "diverted_t": "{:,.0f}",
                "landfilled_t": "{:,.0f}",
                "diversion_rate": "{:,.1%}",
                "circularity_gap": "{:,.1%}",
                "remaining_capacity_t": "{:,.0f}",
                "landfill_life_years": "{:,.1f}",
            }),
            use_container_width=True,
        )

        c1, c2 = st.columns(2)
        with c1:
            fig_side_landfill = px.bar(
                scenario_city,
                x="scenario",
                y="landfilled_t",
                template=PLOT_TEMPLATE,
                title=f"Landfilled waste by scenario — {selected_city}, {selected_year}",
                labels={"scenario": "Scenario", "landfilled_t": "tons/year"},
                text_auto=".2s",
            )
            st.plotly_chart(fig_side_landfill, use_container_width=True)
        with c2:
            fig_side_diversion = px.bar(
                scenario_city,
                x="scenario",
                y="diversion_rate",
                template=PLOT_TEMPLATE,
                title=f"Diversion rate by scenario — {selected_city}, {selected_year}",
                labels={"scenario": "Scenario", "diversion_rate": "Diversion rate"},
                text_auto=".1%",
            )
            fig_side_diversion.update_yaxes(tickformat=".0%")
            st.plotly_chart(fig_side_diversion, use_container_width=True)

        scenario_city_trend = scenario_results[scenario_results["city"] == selected_city].copy()
        fig_trend_compare = px.line(
            scenario_city_trend,
            x="year",
            y="landfilled_t",
            color="scenario",
            markers=True,
            template=PLOT_TEMPLATE,
            title=f"Landfilled waste trajectory by scenario — {selected_city}",
            labels={"year": "Year", "landfilled_t": "tons/year", "scenario": "Scenario"},
        )
        st.plotly_chart(fig_trend_compare, use_container_width=True)

with tab6:
    st.markdown("### Sankey flow diagram")
    st.plotly_chart(make_sankey(selected_row), use_container_width=True)

with tab7:
    st.markdown("### Sensitivity analysis")
    st.write("Each test increases one policy lever by 5 percentage points and estimates the effect on landfilled waste and diversion rate.")
    sens = sensitivity_analysis(inputs, selected_city, int(start_year), int(end_year), scenario_name, results, selected_year)
    c1, c2 = st.columns(2)
    with c1:
        fig_sens_landfill = px.bar(
            sens,
            x="lever",
            y="landfilled_reduction_t",
            template=PLOT_TEMPLATE,
            title=f"Landfilled waste reduction sensitivity — {selected_city}, {selected_year}",
            labels={"lever": "Policy lever", "landfilled_reduction_t": "tons/year"},
            text_auto=".2s",
        )
        fig_sens_landfill.update_layout(xaxis_tickangle=-25)
        st.plotly_chart(fig_sens_landfill, use_container_width=True)
    with c2:
        fig_sens_div = px.bar(
            sens,
            x="lever",
            y="diversion_rate_change_pp",
            template=PLOT_TEMPLATE,
            title=f"Diversion rate sensitivity — {selected_city}, {selected_year}",
            labels={"lever": "Policy lever", "diversion_rate_change_pp": "percentage points"},
            text_auto=".2f",
        )
        fig_sens_div.update_layout(xaxis_tickangle=-25)
        st.plotly_chart(fig_sens_div, use_container_width=True)
    st.dataframe(sens.style.format({"landfilled_reduction_t": "{:,.0f}", "diversion_rate_change_pp": "{:,.2f}"}), use_container_width=True)

with tab8:
    st.markdown("### Alerts and priority ranking")
    st.markdown(f"#### Alerts for {selected_city} in {selected_year}")
    for severity, message in build_alerts(selected_row):
        if severity == "High":
            st.error(f"{severity} · {message}")
        elif severity == "Medium":
            st.warning(f"{severity} · {message}")
        else:
            st.success(f"{severity} · {message}")

    ranking = priority_index(year_df)
    ranking["risk_level"] = ranking.apply(classify_risk, axis=1)
    ranking["circularity_light"] = ranking.apply(circularity_light, axis=1)
    fig_priority = px.bar(
        ranking,
        x="city",
        y="priority_score",
        color="priority_level",
        template=PLOT_TEMPLATE,
        title=f"Priority index — {selected_year}",
        labels={"city": "City", "priority_score": "Priority score"},
    )
    fig_priority.update_layout(xaxis_tickangle=-25)
    st.plotly_chart(fig_priority, use_container_width=True)

    st.dataframe(
        ranking[[
            "city",
            "priority_score",
            "priority_level",
            "risk_level",
            "circularity_light",
            "gpc_effective_kg_person_day",
            "collection_rate",
            "diversion_rate",
            "landfilled_t",
            "remaining_capacity_t",
        ]].style.format({
            "priority_score": "{:,.1f}",
            "gpc_effective_kg_person_day": "{:,.2f}",
            "collection_rate": "{:,.1%}",
            "diversion_rate": "{:,.1%}",
            "landfilled_t": "{:,.0f}",
            "remaining_capacity_t": "{:,.0f}",
        }),
        use_container_width=True,
    )

with tab9:
    st.markdown("### Methodology and equations")
    st.write("The software implements a discrete dynamic model with annual time steps.")

    st.markdown("#### Population projection")
    st.latex("r_p = (P_T/P_0)^{1/(T-t_0)} - 1")
    st.latex("P_t = P_0(1+r_p)^{t-t_0}")

    st.markdown("#### Per-capita waste generation")
    st.latex("g_t = g_0(1+r_g)^{t-t_0}(1-S_{eff,t})")

    st.markdown("#### Annual municipal solid waste generation")
    st.latex("W_t = P_t g_t 365 / 1000")

    st.markdown("#### Collection and uncollected waste")
    st.latex("Q_t = W_t K_{eff,t}")
    st.latex("U_t = W_t - Q_t")

    st.markdown("#### Recycling and composting")
    st.latex("Rec_t = min(Q_t, W_t f_{rec} R_{eff,t})")
    st.latex("Comp_t = min(Q_t-Rec_t, W_t f_{org} C_{eff,t})")

    st.markdown("#### Diversion and final disposal")
    st.latex("Div_t = Rec_t + Comp_t")
    st.latex("D_t = max(0, Q_t - Div_t)")

    st.markdown("#### Landfill remaining capacity and years to collapse")
    st.latex("Cap_t = max(0, Cap_0 - sum(D_i))")
    st.latex("YTC_t = Cap_t / D_t")

    st.write("The main indicators are diversion rate, circularity gap, cumulative landfilled waste, remaining landfill capacity, sensitivity response, priority level and estimated years to landfill collapse.")

with tab10:
    st.markdown("### Export results")
    st.download_button(
        "Download simulation results (.xlsx)",
        data=to_excel_download({"inputs": inputs, "results": results, "bau_comparison": comparison, "scenario_comparison": scenario_results}),
        file_name=f"urban_waste_circularity_results_{scenario_name.replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.download_button(
        "Download simulation results (.csv)",
        data=results.to_csv(index=False).encode("utf-8"),
        file_name=f"urban_waste_circularity_results_{scenario_name.replace(' ', '_')}.csv",
        mime="text/csv",
    )

    with st.expander("Preview results"):
        st.dataframe(results, use_container_width=True)

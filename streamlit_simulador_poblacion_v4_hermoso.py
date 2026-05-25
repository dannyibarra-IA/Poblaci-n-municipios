import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(
    page_title='Urban Waste Circularity Observatory',
    page_icon='♻️',
    layout='wide',
    initial_sidebar_state='expanded',
)

PLOT_TEMPLATE = 'plotly_white'
FRACTION_COLUMNS = [
    'organics_pct', 'plastics_pct', 'paper_cardboard_pct',
    'glass_pct', 'metals_pct', 'textiles_pct', 'others_pct',
]
RECOVERABLE_FRACTIONS = [
    'plastics_pct', 'paper_cardboard_pct', 'glass_pct', 'metals_pct', 'textiles_pct',
]

CITY_COORDS = {
    'Medellín': (6.2442, -75.5812), 'Santiago de Cali': (3.4516, -76.5320),
    'Barranquilla': (10.9685, -74.7813), 'Cartagena de Indias': (10.3910, -75.4794),
    'Soacha': (4.5833, -74.2167), 'San José de Cúcuta': (7.8939, -72.5078),
    'Soledad': (10.9184, -74.7646), 'Bucaramanga': (7.1254, -73.1198),
    'Bello': (6.3373, -75.5540), 'Valledupar': (10.4631, -73.2532),
}

DEFAULT_INPUTS = pd.DataFrame([
    ['Medellín', 2025, 2650000, 2050, 3000000, 0.78, 0.002, 12000000, 52, 13, 12, 4, 2, 5, 12],
    ['Santiago de Cali', 2025, 2280000, 2050, 2600000, 0.80, 0.002, 8500000, 50, 14, 11, 4, 2, 4, 15],
    ['Barranquilla', 2025, 1320000, 2050, 1550000, 0.85, 0.003, 7000000, 49, 15, 10, 4, 2, 5, 15],
    ['Cartagena de Indias', 2025, 1100000, 2050, 1320000, 0.82, 0.003, 5500000, 51, 14, 10, 4, 2, 4, 15],
    ['Soacha', 2025, 820000, 2050, 1050000, 0.74, 0.003, 4000000, 53, 13, 10, 3, 2, 5, 14],
    ['San José de Cúcuta', 2025, 800000, 2050, 960000, 0.77, 0.002, 4500000, 52, 13, 11, 4, 2, 4, 14],
    ['Soledad', 2025, 740000, 2050, 910000, 0.79, 0.003, 4200000, 50, 15, 10, 4, 2, 5, 14],
    ['Bucaramanga', 2025, 620000, 2050, 700000, 0.76, 0.001, 5200000, 51, 13, 12, 4, 2, 4, 14],
    ['Bello', 2025, 560000, 2050, 660000, 0.75, 0.002, 3600000, 52, 13, 11, 4, 2, 5, 13],
    ['Valledupar', 2025, 560000, 2050, 700000, 0.81, 0.003, 3300000, 51, 14, 10, 4, 2, 5, 14],
], columns=[
    'city', 'base_year', 'population_base', 'validation_year', 'population_validation',
    'gpc_base_kg_person_day', 'gpc_annual_growth', 'landfill_remaining_capacity_t',
    *FRACTION_COLUMNS,
])

# FIX 5 — each scenario declares its own interpolation start values so that
# Critical Stress (collection_target=0.78) doesn't wrongly ramp DOWN from 0.85.
SCENARIOS = {
    'Critical Stress': dict(
        source_reduction_target=0.00, collection_target=0.78,
        recycling_target=0.10, composting_target=0.04,
        education_bonus_target=0.00, formalization_bonus_target=0.00,
        collection_start=0.78, recycling_start=0.10, composting_start=0.04,
        label='Critical stress scenario',
    ),
    'BAU': dict(
        source_reduction_target=0.00, collection_target=0.85,
        recycling_target=0.18, composting_target=0.08,
        education_bonus_target=0.00, formalization_bonus_target=0.00,
        collection_start=0.85, recycling_start=0.18, composting_start=0.08,
        label='Business as usual',
    ),
    'Moderate Circularity': dict(
        source_reduction_target=0.05, collection_target=0.90,
        recycling_target=0.28, composting_target=0.16,
        education_bonus_target=0.03, formalization_bonus_target=0.04,
        collection_start=0.85, recycling_start=0.18, composting_start=0.08,
        label='Moderate intervention',
    ),
    'Accelerated Circularity': dict(
        source_reduction_target=0.12, collection_target=0.96,
        recycling_target=0.40, composting_target=0.28,
        education_bonus_target=0.06, formalization_bonus_target=0.08,
        collection_start=0.85, recycling_start=0.18, composting_start=0.08,
        label='High circularity push',
    ),
    'Optimistic Transition': dict(
        source_reduction_target=0.18, collection_target=0.98,
        recycling_target=0.55, composting_target=0.40,
        education_bonus_target=0.10, formalization_bonus_target=0.12,
        collection_start=0.85, recycling_start=0.18, composting_start=0.08,
        label='Optimistic circular transition',
    ),
}

SCENARIO_COLORS = {
    'Critical Stress': '#bd3b3b', 'BAU': '#0d5c91',
    'Moderate Circularity': '#b98900', 'Accelerated Circularity': '#2f7d6b',
    'Optimistic Transition': '#1f9d55',
}
RISK_COLORS = {'Low': '#2f7d6b', 'Medium': '#b98900', 'High': '#bd3b3b'}

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown('''
<style>
[data-testid="stAppViewContainer"]{background:radial-gradient(circle at top left,rgba(13,92,145,.09),transparent 31%),linear-gradient(180deg,#f8fbfd 0%,#eef4f8 45%,#f8fafc 100%);}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#edf4f8 0%,#e8eef4 100%);border-right:1px solid rgba(16,42,67,.1);}
.block-container{padding-top:1.4rem;max-width:1520px;}
h1,h2,h3{color:#102a43;letter-spacing:-.02em;}
div[data-testid="stMetric"]{background:#fff;border:1px solid rgba(16,42,67,.10);border-radius:18px;padding:1rem 1.1rem;box-shadow:0 4px 14px rgba(16,42,67,.06);}
div[data-testid="stMetric"] label{color:#5f6f7f!important;font-weight:800;text-transform:uppercase;letter-spacing:.04em;font-size:.76rem;}
div[data-testid="stMetric"] [data-testid="stMetricValue"]{color:#102a43;font-weight:900;font-size:1.55rem;}
.hero-box{background:#fff;border:1px solid rgba(16,42,67,.10);border-radius:28px;padding:1.75rem 1.9rem 1.35rem;margin-bottom:1rem;box-shadow:0 8px 24px rgba(16,42,67,.08);}
.hero-kicker{display:inline-block;font-size:.76rem;font-weight:900;text-transform:uppercase;letter-spacing:.13em;color:#0d5c91;background:rgba(13,92,145,.07);border:1px solid rgba(13,92,145,.14);border-radius:999px;padding:.38rem .78rem;margin-bottom:.78rem;}
.hero-title{font-size:2.2rem;line-height:1.08;font-weight:950;color:#102a43;margin-bottom:.55rem;}
.hero-subtitle{color:#334e68;font-size:1.02rem;max-width:1080px;line-height:1.58;margin-bottom:.85rem;}
.hero-meta{color:#5f6f7f;font-size:.92rem;margin-bottom:.75rem;}
.badge-row{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.2rem;}
.badge{background:rgba(13,92,145,.07);border:1px solid rgba(16,42,67,.10);border-radius:999px;padding:.35rem .72rem;color:#0d5c91;font-size:.82rem;font-weight:750;}
.scenario-card{border-radius:18px;padding:1rem 1.1rem;border:1px solid rgba(16,42,67,.10);box-shadow:0 4px 14px rgba(16,42,67,.06);margin:.6rem 0 1rem;}
.scenario-title{font-size:1.2rem;font-weight:900;margin-bottom:.25rem;color:#102a43;}
.scenario-text{font-size:.94rem;color:#486581;line-height:1.45;}
.insight-box{background:#fff;border:1px solid rgba(16,42,67,.10);border-left:5px solid #0d5c91;border-radius:0 14px 14px 0;padding:1rem 1.1rem;margin:.6rem 0 1rem;color:#334e68;line-height:1.5;}
.section-help{background:rgba(13,92,145,.07);border:1px solid rgba(13,92,145,.13);border-radius:12px;padding:.85rem 1rem;color:#23435c;line-height:1.5;margin:.5rem 0 1rem;}
.landing-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1rem;margin:1rem 0;}
@media(max-width:1000px){.landing-grid{grid-template-columns:repeat(2,minmax(0,1fr));}.steps{grid-template-columns:1fr!important;}}
.feature-card{background:#fff;border:1px solid rgba(16,42,67,.10);border-radius:18px;padding:1.05rem 1.1rem;box-shadow:0 4px 14px rgba(16,42,67,.06);min-height:140px;}
.feature-icon{font-size:1.4rem;margin-bottom:.45rem;}
.feature-title{font-weight:900;color:#102a43;font-size:1rem;margin-bottom:.32rem;}
.feature-text{color:#486581;font-size:.9rem;line-height:1.45;}
.workflow{background:#fff;border:1px solid rgba(16,42,67,.10);border-radius:20px;padding:1.1rem 1.25rem;margin:0 0 1rem;box-shadow:0 4px 14px rgba(16,42,67,.05);}
.workflow-title{font-weight:950;font-size:1.2rem;color:#102a43;margin-bottom:.75rem;}
.steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.85rem;}
.step{display:flex;gap:.75rem;align-items:flex-start;background:#f8fbfd;border:1px solid rgba(16,42,67,.08);border-radius:14px;padding:.9rem;}
.step-num{min-width:2rem;height:2rem;border-radius:999px;background:#0d5c91;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900;}
.step-title{font-weight:900;color:#102a43;margin-bottom:.18rem;}
.step-text{color:#486581;font-size:.9rem;line-height:1.4;}
.home-panel{background:#102a43;border-radius:22px;padding:1.2rem 1.25rem;margin:1rem 0;color:white;}
.home-panel h3{color:white;margin:.1rem 0 .4rem;}
.home-panel p{color:rgba(255,255,255,.82);line-height:1.5;margin-bottom:.3rem;}
.micro-label{font-size:.76rem;text-transform:uppercase;letter-spacing:.10em;font-weight:900;color:rgba(255,255,255,.6);margin-bottom:.4rem;}
.footer{text-align:center;color:#5f6f7f;font-size:.86rem;padding:1.2rem 0 .4rem;}
div.stButton>button,div.stDownloadButton>button{border-radius:999px!important;padding:.72rem 1.05rem!important;font-weight:850!important;border:1px solid rgba(16,42,67,.12)!important;box-shadow:0 4px 14px rgba(16,42,67,.07)!important;}
div.stButton>button[kind="primary"]{background:#0d5c91!important;color:#fff!important;}
div.stDownloadButton>button{background:rgba(255,255,255,.88)!important;color:#102a43!important;}
</style>
''', unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────
def human_format(value, decimals=0):
    try:
        if pd.isna(value):
            return 'N/A'
        return f'{float(value):,.{decimals}f}'
    except Exception:
        return str(value)


def validate_inputs(df):
    required = {
        'city', 'base_year', 'population_base', 'validation_year',
        'population_validation', 'gpc_base_kg_person_day', 'gpc_annual_growth',
        'landfill_remaining_capacity_t', *FRACTION_COLUMNS,
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'Missing required columns: {", ".join(sorted(missing))}')
    out = df.copy()
    out['city'] = out['city'].astype(str).str.strip()
    for col in [c for c in out.columns if c != 'city']:
        out[col] = pd.to_numeric(out[col], errors='coerce')
    out = out.dropna(subset=[
        'city', 'base_year', 'population_base', 'validation_year', 'population_validation',
    ])
    out['base_year'] = out['base_year'].astype(int)
    out['validation_year'] = out['validation_year'].astype(int)
    if (out['population_base'] <= 0).any() or (out['population_validation'] <= 0).any():
        raise ValueError('Population values must be greater than zero.')
    if (out['validation_year'] <= out['base_year']).any():
        raise ValueError('validation_year must be greater than base_year.')
    out['fraction_sum_pct'] = out[FRACTION_COLUMNS].sum(axis=1)
    if not np.allclose(out['fraction_sum_pct'], 100, atol=2.0):
        st.warning('Some composition percentages do not add up to 100%. They will be normalized internally.')
    return out


def input_template_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='city_inputs', index=False)
    return output.getvalue()


@st.cache_data(show_spinner=False)
def load_input_file(uploaded_file):
    return validate_inputs(pd.read_excel(uploaded_file, sheet_name='city_inputs'))


def interpolate_policy(start_value, target_value, year, start_year, end_year):
    if end_year <= start_year:
        return float(target_value)
    alpha = np.clip((year - start_year) / (end_year - start_year), 0, 1)
    return float(start_value + alpha * (target_value - start_value))


def effective_policy_params(source_reduction, collection, recycling, composting, education_bonus, formalization_bonus):
    return (
        min(0.35, source_reduction + education_bonus * 0.15),
        min(0.99, collection + education_bonus * 0.20),
        min(0.95, recycling + education_bonus * 0.35 + formalization_bonus * 0.65),
        min(0.90, composting + education_bonus * 0.50),
    )


def project_city(row, start_year, end_year, scenario_name, overrides=None):
    scenario = SCENARIOS[scenario_name].copy()
    if overrides:
        scenario.update(overrides)

    base_year = int(row['base_year'])
    validation_year = int(row['validation_year'])
    p0 = float(row['population_base'])
    pT = float(row['population_validation'])
    gpc0 = float(row['gpc_base_kg_person_day'])
    gpc_growth = float(row['gpc_annual_growth'])
    capacity = float(row['landfill_remaining_capacity_t'])
    rp = (pT / p0) ** (1 / (validation_year - base_year)) - 1

    # Pre-compute fractions once — time-invariant
    fractions_raw = row[FRACTION_COLUMNS].astype(float) / 100
    fractions = fractions_raw / fractions_raw.sum() if fractions_raw.sum() > 0 else fractions_raw
    f_org = float(fractions['organics_pct'])
    f_rec = float(fractions[RECOVERABLE_FRACTIONS].sum())

    # FIX 5 — use scenario-specific start values so Critical Stress never
    # ramps down from a higher BAU baseline.
    col_start = scenario.get('collection_start', 0.85)
    rec_start = scenario.get('recycling_start', 0.18)
    com_start = scenario.get('composting_start', 0.08)

    cumulative_landfilled = 0.0
    records = []

    for year in range(start_year, end_year + 1):
        dt = year - base_year
        population = p0 * ((1 + rp) ** dt)
        gpc_no_prev = gpc0 * ((1 + gpc_growth) ** dt)

        source     = interpolate_policy(0,         scenario['source_reduction_target'], year, start_year, end_year)
        collection = interpolate_policy(col_start,  scenario['collection_target'],       year, start_year, end_year)
        recycling  = interpolate_policy(rec_start,  scenario['recycling_target'],         year, start_year, end_year)
        composting = interpolate_policy(com_start,  scenario['composting_target'],        year, start_year, end_year)
        edu        = interpolate_policy(0,          scenario['education_bonus_target'],   year, start_year, end_year)
        formal     = interpolate_policy(0,          scenario['formalization_bonus_target'], year, start_year, end_year)

        eff_source, eff_collection, eff_recycling, eff_composting = effective_policy_params(
            source, collection, recycling, composting, edu, formal
        )

        gpc       = gpc_no_prev * (1 - eff_source)
        generated = population * gpc * 365 / 1000
        collected = generated * eff_collection
        uncollected = generated - collected

        # FIX 1 — pools capped to what was actually collected, avoiding
        # double-counting between recycling and composting streams.
        rec_pool = collected * f_rec
        org_pool = collected * f_org

        recycled  = rec_pool * eff_recycling
        remaining_after_rec = max(0.0, collected - recycled)
        org_remaining = min(org_pool, remaining_after_rec)
        composted = org_remaining * eff_composting

        diverted  = recycled + composted
        landfilled = max(0.0, collected - diverted)

        cumulative_landfilled += landfilled
        remaining_capacity = max(0.0, capacity - cumulative_landfilled)

        diversion_rate  = diverted  / generated if generated > 0 else 0.0
        collection_rate = collected / generated if generated > 0 else 0.0

        # FIX 6 — use sentinel 9999 instead of inf for Excel safety and
        # downstream arithmetic stability.
        landfill_life = remaining_capacity / landfilled if landfilled > 0 else 9999.0

        fraction_amounts = {
            col.replace('_pct', '_t'): generated * float(fractions[col])
            for col in FRACTION_COLUMNS
        }

        records.append(dict(
            city=row['city'], year=year, scenario=scenario_name,
            population=population, population_growth_rate=rp,
            gpc_without_prevention_kg_person_day=gpc_no_prev,
            gpc_effective_kg_person_day=gpc,
            generated_t=generated, collected_t=collected, uncollected_t=uncollected,
            recycled_t=recycled, composted_t=composted, diverted_t=diverted,
            landfilled_t=landfilled, cumulative_landfilled_t=cumulative_landfilled,
            remaining_capacity_t=remaining_capacity,
            diversion_rate=diversion_rate, collection_rate=collection_rate,
            landfill_life_years=landfill_life,
            circularity_gap=max(0.0, 1.0 - diversion_rate),
            effective_source_reduction=eff_source, effective_collection=eff_collection,
            effective_recycling=eff_recycling, effective_composting=eff_composting,
            organics_share=f_org, recoverables_share=f_rec,
            **fraction_amounts,
        ))

    return pd.DataFrame(records)


# FIX 3 — cache all projections so reruns on sidebar interactions are free.
@st.cache_data(show_spinner='Running simulation…')
def run_projection(inputs_json, start_year, end_year, scenario_name, overrides_json=None):
    inputs = pd.read_json(inputs_json, orient='split')
    overrides = None if overrides_json is None else pd.read_json(overrides_json, orient='index').iloc[0].to_dict()
    frames = [
        project_city(row, start_year, end_year, scenario_name, overrides)
        for _, row in inputs.iterrows()
    ]
    return pd.concat(frames, ignore_index=True)


def classify_risk(row):
    score = 0
    ytc = row['landfill_life_years']
    # FIX 6 — sentinel 9999 means "no imminent collapse"
    if ytc < 5:   score += 3
    elif ytc < 10: score += 2
    elif ytc < 20: score += 1
    if row['diversion_rate']  < 0.20: score += 2
    elif row['diversion_rate'] < 0.35: score += 1
    if row['collection_rate'] < 0.85: score += 2
    elif row['collection_rate'] < 0.95: score += 1
    if row['gpc_effective_kg_person_day'] > 1.1: score += 1
    return 'High' if score >= 5 else 'Medium' if score >= 3 else 'Low'


def circularity_light(row):
    llf = row['landfill_life_years']
    if row['diversion_rate'] >= 0.45 and llf >= 15 and row['collection_rate'] >= 0.95:
        return 'Green'
    if row['diversion_rate'] >= 0.25 and llf >= 8 and row['collection_rate'] >= 0.85:
        return 'Yellow'
    return 'Red'


def priority_index(df_year):
    d = df_year.copy()

    def min_max(s):
        s = pd.Series(s, dtype=float)
        rng = s.max() - s.min()
        return pd.Series(np.zeros(len(s)), index=s.index) if rng == 0 else (s - s.min()) / rng

    d['n_per_capita']       = min_max(d['gpc_effective_kg_person_day'])
    # FIX 6 — replace sentinel with NaN before pressure ratio so division is safe
    safe_capacity = d['remaining_capacity_t'].replace(0, np.nan).fillna(1)
    d['n_landfill_pressure'] = min_max(d['landfilled_t'] / safe_capacity)
    d['n_collection_gap']   = min_max(1 - d['collection_rate'])
    d['n_circularity_gap']  = min_max(d['circularity_gap'])
    d['n_uncollected']      = min_max(d['uncollected_t'])

    d['priority_score'] = 100 * (
        0.25 * d['n_per_capita'] + 0.25 * d['n_landfill_pressure'] +
        0.20 * d['n_circularity_gap'] + 0.15 * d['n_collection_gap'] +
        0.15 * d['n_uncollected']
    )
    d['priority_level'] = pd.cut(
        d['priority_score'], bins=[-0.01, 33, 66, 100], labels=['Low', 'Medium', 'High'],
    )
    return d.sort_values('priority_score', ascending=False)


def build_alerts(row):
    alerts = []
    llf = row['landfill_life_years']
    if llf < 5:    alerts.append(('High',   f'Landfill life below 5 years ({llf:.1f} yr).'))
    elif llf < 10: alerts.append(('Medium', f'Landfill life below 10 years ({llf:.1f} yr).'))
    if row['collection_rate'] < 0.85:   alerts.append(('High',   f"Collection rate {row['collection_rate']:.1%} is below 85%."))
    elif row['collection_rate'] < 0.95: alerts.append(('Medium', f"Collection rate {row['collection_rate']:.1%} is below 95%."))
    if row['diversion_rate'] < 0.20:   alerts.append(('High',   f"Diversion rate {row['diversion_rate']:.1%} is below 20%."))
    elif row['diversion_rate'] < 0.35: alerts.append(('Medium', f"Diversion rate {row['diversion_rate']:.1%} is moderate."))
    if row['gpc_effective_kg_person_day'] > 1.1:
        alerts.append(('Medium', f"Per-capita generation {row['gpc_effective_kg_person_day']:.2f} kg/p/d is above 1.1."))
    return alerts or [('Low', 'No immediate structural alert under the selected scenario.')]


def quick_insight(row, scenario_name):
    risk  = classify_risk(row)
    light = circularity_light(row)
    llf   = row['landfill_life_years']
    llf_text = 'an indefinite horizon' if llf >= 9999 else f'{human_format(llf, 1)} years'
    return (
        f"Under **{scenario_name}**, **{row['city']}** shows **{risk.lower()} operational risk**, "
        f"a **{light.lower()} circularity status**, a diversion rate of "
        f"**{human_format(row['diversion_rate'] * 100, 1)}%**, and approximately "
        f"**{llf_text}** before landfill exhaustion."
    )


def make_sankey(row):
    labels = ['Generated', 'Collected', 'Uncollected', 'Recycled', 'Composted', 'Landfilled']
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            label=labels, pad=20, thickness=18,
            color=['#0d5c91', '#486581', '#b98900', '#2f7d6b', '#1f9d55', '#bd3b3b'],
        ),
        link=dict(
            source=[0, 0, 1, 1, 1],
            target=[1, 2, 3, 4, 5],
            value=[
                row['collected_t'], row['uncollected_t'],
                row['recycled_t'], row['composted_t'], row['landfilled_t'],
            ],
        ),
    )])
    fig.update_layout(
        title_text='Waste flow balance', template=PLOT_TEMPLATE,
        height=430, margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


# FIX 3 & 8 — sensitivity analysis is now cached and uses absolute override
# targets (not additive) relative to BAU baseline, ensuring results are always
# interpretable even when the active scenario already has high targets.
@st.cache_data(show_spinner=False)
def sensitivity_analysis(inputs_json, selected_city, start_year, end_year, scenario_name, selected_year):
    inputs = pd.read_json(inputs_json, orient='split')
    baseline = run_projection(inputs_json, start_year, end_year, scenario_name)
    base_row = baseline[(baseline['city'] == selected_city) & (baseline['year'] == selected_year)].iloc[0]

    sc = SCENARIOS[scenario_name]
    tests = [
        ('Source reduction +5 pp',  {'source_reduction_target':   min(0.35, sc['source_reduction_target']   + 0.05)}),
        ('Collection +5 pp',        {'collection_target':          min(0.99, sc['collection_target']          + 0.05)}),
        ('Recycling +5 pp',         {'recycling_target':           min(0.95, sc['recycling_target']           + 0.05)}),
        ('Composting +5 pp',        {'composting_target':          min(0.90, sc['composting_target']          + 0.05)}),
        ('Education bonus +5 pp',   {'education_bonus_target':     min(0.15, sc['education_bonus_target']     + 0.05)}),
        ('Formalization +5 pp',     {'formalization_bonus_target': min(0.15, sc['formalization_bonus_target'] + 0.05)}),
    ]

    rows = []
    for label, override in tests:
        import json
        override_json = pd.Series(override).to_json(orient='index')
        alt = run_projection(inputs_json, start_year, end_year, scenario_name, overrides_json=override_json)
        alt_row = alt[(alt['city'] == selected_city) & (alt['year'] == selected_year)].iloc[0]
        rows.append({
            'lever': label,
            'landfilled_reduction_t': base_row['landfilled_t'] - alt_row['landfilled_t'],
            'diversion_rate_change_pp': (alt_row['diversion_rate'] - base_row['diversion_rate']) * 100,
        })

    return pd.DataFrame(rows).sort_values('landfilled_reduction_t', ascending=False)


# FIX 2 — safe Excel export: replace inf/nan in all numeric columns.
def to_excel_download(df_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet, df in df_dict.items():
            safe = df.copy()
            num_cols = safe.select_dtypes(include=[np.number]).columns
            safe[num_cols] = safe[num_cols].replace([np.inf, -np.inf], 9999).fillna(0)
            safe.to_excel(writer, sheet_name=sheet[:31], index=False)
    return output.getvalue()


def fmt_landfill_life(v):
    return '∞' if v >= 9999 else f'{v:.1f}'


# ── session state ─────────────────────────────────────────────────────────────
if 'active_scenario' not in st.session_state:
    st.session_state['active_scenario'] = 'BAU'
if 'landing_action' not in st.session_state:
    st.session_state['landing_action'] = ''

# ── hero ──────────────────────────────────────────────────────────────────────
st.markdown('''
<div class="hero-box">
  <div class="hero-kicker">Circular waste futures lab</div>
  <div class="hero-title">Simulate circular waste futures for Latin American cities</div>
  <div class="hero-subtitle">
    An open-source decision-support simulator for exploring municipal solid waste generation,
    circularity pathways, landfill pressure and territorial risk. Build scenarios, compare futures
    and translate waste data into better urban decisions.
  </div>
  <div class="hero-meta">Developed by <b>Danny Ibarra Vega, Ph.D.</b> · Universidad de Antioquia · Waste systems, circular economy and dynamic simulation</div>
  <div class="badge-row">
    <span class="badge">Open-source</span>
    <span class="badge">Scenario-based</span>
    <span class="badge">Landfill stress</span>
    <span class="badge">Circularity analytics</span>
    <span class="badge">Replicable in Latin America</span>
  </div>
</div>
''', unsafe_allow_html=True)

cta1, cta2, cta3 = st.columns(3)
with cta1:
    if st.button('▶ Start simulation', type='primary', use_container_width=True):
        st.session_state['active_scenario'] = 'BAU'
        st.session_state['landing_action'] = 'BAU baseline loaded. Explore projections below.'
with cta2:
    if st.button('🔁 Compare scenarios', use_container_width=True):
        st.session_state['active_scenario'] = 'Optimistic Transition'
        st.session_state['landing_action'] = 'Scenario comparison ready. Open the Scenario comparison tab.'
with cta3:
    st.download_button(
        '⬇ Download template', data=input_template_to_excel(DEFAULT_INPUTS),
        file_name='city_inputs_template.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        use_container_width=True,
    )

if st.session_state.get('landing_action'):
    st.success(st.session_state['landing_action'])

st.markdown('''
<div class="landing-grid">
  <div class="feature-card"><div class="feature-icon">⚡</div><div class="feature-title">Easy to start</div><div class="feature-text">Use minimum city-level inputs: population, per-capita waste, composition and landfill capacity.</div></div>
  <div class="feature-card"><div class="feature-icon">🔁</div><div class="feature-title">Scenario simulator</div><div class="feature-text">Explore BAU, critical stress, moderate, accelerated and optimistic circularity pathways.</div></div>
  <div class="feature-card"><div class="feature-icon">📊</div><div class="feature-title">Decision analytics</div><div class="feature-text">Track avoided landfill, diversion, remaining capacity, operational risk and priority ranking.</div></div>
  <div class="feature-card"><div class="feature-icon">🌎</div><div class="feature-title">Latin America ready</div><div class="feature-text">Designed to be replicated in any city with basic waste and population information.</div></div>
</div>
<div class="workflow">
  <div class="workflow-title">How it works</div>
  <div class="steps">
    <div class="step"><div class="step-num">1</div><div><div class="step-title">Enter city data</div><div class="step-text">Load or edit population, waste generation, composition and landfill capacity.</div></div></div>
    <div class="step"><div class="step-num">2</div><div><div class="step-title">Run scenarios</div><div class="step-text">Switch between baseline, stress and circularity transition pathways.</div></div></div>
    <div class="step"><div class="step-num">3</div><div><div class="step-title">Interpret decisions</div><div class="step-text">Compare risk, avoided disposal, circularity gains and intervention priorities.</div></div></div>
  </div>
</div>
''', unsafe_allow_html=True)

# ── sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown('## Control room')
st.sidebar.markdown('### 1. Simulation horizon')
start_year = st.sidebar.number_input('Start year', min_value=2020, max_value=2050, value=2025, step=1)
end_year   = st.sidebar.number_input('End year',   min_value=int(start_year) + 1, max_value=2100, value=2050, step=1)

st.sidebar.markdown('### 2. Scenario selection')
if st.sidebar.button('Baseline · BAU',        use_container_width=True): st.session_state['active_scenario'] = 'BAU'
if st.sidebar.button('Stress test · Critical', use_container_width=True): st.session_state['active_scenario'] = 'Critical Stress'
if st.sidebar.button('Ambitious · Optimistic', use_container_width=True): st.session_state['active_scenario'] = 'Optimistic Transition'

scenario_keys = list(SCENARIOS.keys())
scenario_name = st.sidebar.selectbox(
    'Full scenario menu', scenario_keys,
    index=scenario_keys.index(st.session_state['active_scenario']),
)
st.session_state['active_scenario'] = scenario_name

comparison_scenarios = st.sidebar.multiselect(
    'Scenarios to compare', scenario_keys, default=scenario_keys,
)
if not comparison_scenarios:
    comparison_scenarios = [scenario_name]

st.sidebar.markdown('### 3. Data input')
st.sidebar.download_button(
    'Download input template (.xlsx)', data=input_template_to_excel(DEFAULT_INPUTS),
    file_name='city_inputs_template.xlsx',
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
)
uploaded = st.sidebar.file_uploader('Upload city inputs (.xlsx)', type=['xlsx'])
if uploaded is not None:
    try:
        inputs = load_input_file(uploaded)
        st.sidebar.success('Input file loaded successfully.')
    except Exception as exc:
        st.sidebar.error(f'Input file error: {exc}')
        st.stop()
else:
    inputs = validate_inputs(DEFAULT_INPUTS)

with st.expander('Edit input data', expanded=False):
    st.write(
        'Each row represents one city. The model uses current population, future validation '
        'population, per-capita waste generation, remaining landfill capacity and waste composition.'
    )
    edited_inputs = st.data_editor(inputs, num_rows='dynamic', use_container_width=True)
    try:
        inputs = validate_inputs(edited_inputs)
    except Exception as exc:
        st.error(f'Input validation error: {exc}')
        st.stop()

# ── model execution (all calls cached) ───────────────────────────────────────
inputs_json = inputs.to_json(orient='split')

# FIX 4 — only compute comparison scenarios that are actually selected,
# and let @st.cache_data avoid redundant recalculations.
results = run_projection(inputs_json, int(start_year), int(end_year), scenario_name)

# FIX 7 — sort before cumsum to guarantee correct accumulation order.
bau = run_projection(inputs_json, int(start_year), int(end_year), 'BAU')

comparison = results.merge(
    bau[['city', 'year', 'landfilled_t', 'diverted_t']].rename(
        columns={'landfilled_t': 'landfilled_bau_t', 'diverted_t': 'diverted_bau_t'}
    ),
    on=['city', 'year'], how='left',
)
comparison['avoided_landfill_vs_bau_t']      = comparison['landfilled_bau_t'] - comparison['landfilled_t']
comparison['additional_diversion_vs_bau_t']  = comparison['diverted_t']      - comparison['diverted_bau_t']
# FIX 7 — sort by city then year before cumsum
comparison = comparison.sort_values(['city', 'year'])
comparison['cumulative_avoided_landfill_vs_bau_t']     = comparison.groupby('city')['avoided_landfill_vs_bau_t'].cumsum()
comparison['cumulative_additional_diversion_vs_bau_t'] = comparison.groupby('city')['additional_diversion_vs_bau_t'].cumsum()

cities = sorted(results['city'].unique())
st.sidebar.markdown('### 4. Analysis focus')
selected_city = st.sidebar.selectbox(
    'City focus', cities,
    index=cities.index('Barranquilla') if 'Barranquilla' in cities else 0,
)
selected_year = st.sidebar.slider('Year focus', int(start_year), int(end_year), int(end_year))

city_df  = results[results['city'] == selected_city].copy()
year_df  = results[results['year'] == selected_year].copy()
year_df['risk_level']       = year_df.apply(classify_risk,      axis=1)
year_df['circularity_light'] = year_df.apply(circularity_light, axis=1)

selected_row         = results[(results['city'] == selected_city) & (results['year'] == selected_year)].iloc[0]
comparison_city      = comparison[comparison['city'] == selected_city].copy()
comparison_sel_row   = comparison_city[comparison_city['year'] == selected_year].iloc[0]
selected_light       = circularity_light(selected_row)

# Scenario card
msg = {
    'Critical Stress':        'A conservative trajectory with lower collection, recycling and composting. Useful for stress-testing landfill pressure and operational risk.',
    'Optimistic Transition':  'An ambitious circularity pathway with stronger source reduction, recycling, composting, education and recycler formalization.',
    'BAU':                    'The reference trajectory used to estimate avoided landfill disposal and additional diversion under alternative scenarios.',
}.get(scenario_name, f'{scenario_name} explores a circularity pathway with specific assumptions on collection, recycling, composting and prevention.')

color = SCENARIO_COLORS.get(scenario_name, '#0d5c91')
st.markdown(f'''
<div class="scenario-card" style="background:{color}12;">
  <div class="scenario-title">Scenario: {scenario_name} — {SCENARIOS[scenario_name]["label"]}</div>
  <div class="scenario-text">{msg}</div>
</div>
''', unsafe_allow_html=True)

# KPIs
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric('City', selected_city)
k2.metric('Population', human_format(selected_row['population'], 0))
k3.metric('Generated', f"{human_format(selected_row['generated_t'], 0)} t/y")
k4.metric('Diverted', f"{human_format(selected_row['diverted_t'], 0)} t/y")
k5.metric('Diversion rate', f"{human_format(selected_row['diversion_rate'] * 100, 1)}%")
k6.metric('Years to landfill collapse', fmt_landfill_life(selected_row['landfill_life_years']))

m1, m2, m3 = st.columns(3)
m1.metric('Cumulative avoided landfill vs BAU', f"{human_format(comparison_sel_row['cumulative_avoided_landfill_vs_bau_t'], 0)} t")
m2.metric('Additional diversion vs BAU', f"{human_format(comparison_sel_row['additional_diversion_vs_bau_t'], 0)} t/y")
m3.metric('Circularity status', selected_light)

st.markdown(f'<div class="insight-box"><b>Quick insight.</b> {quick_insight(selected_row, scenario_name)}</div>', unsafe_allow_html=True)
st.markdown(f'''
<div class="home-panel">
  <div class="micro-label">Live simulation cockpit</div>
  <h3>{selected_city} · {selected_year} · {scenario_name}</h3>
  <p>Use the tabs below to move from projections to composition, geography, scenario comparison, Sankey flows, sensitivity and alerts.</p>
</div>
''', unsafe_allow_html=True)

# ── tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    '📈 Projections', '♻️ Composition', '🗺️ Geography', '🧭 Circularity indicators',
    '🔁 Scenario comparison', '🌊 Flow Sankey', '🧪 Sensitivity',
    '🚨 Alerts & priority', '📐 Methodology', '⬇️ Export',
])

with tab1:
    st.markdown('## Population and waste projections')
    st.markdown('<div class="section-help">Projected demographic and waste trajectories generated from minimum city-level inputs.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(city_df, x='year', y='population', markers=True, template=PLOT_TEMPLATE,
                      title=f'Population projection — {selected_city}',
                      labels={'year': 'Year', 'population': 'Population'})
        fig.update_traces(line=dict(width=3, color='#0d5c91'))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.line(city_df, x='year', y=['generated_t', 'collected_t', 'landfilled_t', 'diverted_t'],
                      markers=True, template=PLOT_TEMPLATE,
                      title=f'Waste flow projection — {selected_city}',
                      labels={'year': 'Year', 'value': 'tons/year', 'variable': 'Flow'})
        fig.update_layout(legend_title_text='')
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('### Animated simulation')
    st.markdown('<div class="section-help">Use the Play button to observe how population, generation and landfill pressure evolve year by year.</div>', unsafe_allow_html=True)
    anim = results.copy()
    anim['landfilled_size'] = anim['landfilled_t'].clip(lower=1)
    fig = px.scatter(anim, x='population', y='generated_t', animation_frame='year',
                     animation_group='city', size='landfilled_size', color='city',
                     hover_name='city', template=PLOT_TEMPLATE,
                     title='Animated population-waste-landfill trajectory by city',
                     labels={'population': 'Population', 'generated_t': 'Generated waste (tons/year)'},
                     size_max=45)
    fig.update_layout(transition={'duration': 400}, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown('## Waste composition')
    st.markdown('<div class="section-help">Organic fractions indicate composting potential; recoverable materials indicate recycling potential.</div>', unsafe_allow_html=True)
    fraction_cols_t = [c.replace('_pct', '_t') for c in FRACTION_COLUMNS]
    labels_map = {
        'organics_t': 'Organics', 'plastics_t': 'Plastics',
        'paper_cardboard_t': 'Paper and cardboard', 'glass_t': 'Glass',
        'metals_t': 'Metals', 'textiles_t': 'Textiles', 'others_t': 'Others',
    }
    comp = selected_row[fraction_cols_t].rename(index=labels_map).reset_index()
    comp.columns = ['fraction', 'tons_year']
    c1, c2 = st.columns(2)
    with c1:
        fig = px.pie(comp, names='fraction', values='tons_year', hole=0.55, template=PLOT_TEMPLATE,
                     title=f'Projected composition — {selected_city}, {selected_year}')
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(comp.sort_values('tons_year', ascending=False),
                     x='fraction', y='tons_year', text_auto='.2s', template=PLOT_TEMPLATE,
                     title='Composition in tons/year',
                     labels={'fraction': 'Fraction', 'tons_year': 'tons/year'})
        fig.update_layout(xaxis_tickangle=-20)
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown('## Geographic view')
    st.markdown('<div class="section-help">Bubble size = waste generation. Color = operational risk (landfill life, diversion, collection, per-capita generation).</div>', unsafe_allow_html=True)
    geo = year_df.copy()
    geo['lat'] = geo['city'].map(lambda c: CITY_COORDS.get(c, (np.nan, np.nan))[0])
    geo['lon'] = geo['city'].map(lambda c: CITY_COORDS.get(c, (np.nan, np.nan))[1])
    geo = geo.dropna(subset=['lat', 'lon'])
    if geo.empty:
        st.info('No coordinates available for the selected cities.')
    else:
        fig = px.scatter_mapbox(
            geo, lat='lat', lon='lon', size='generated_t', color='risk_level',
            color_discrete_map=RISK_COLORS, hover_name='city',
            hover_data={
                'generated_t': ':,.0f', 'landfilled_t': ':,.0f', 'diverted_t': ':,.0f',
                'diversion_rate': ':.1%', 'landfill_life_years': ':.1f',
                'circularity_light': True, 'gpc_effective_kg_person_day': ':.2f',
                'lat': False, 'lon': False,
            },
            mapbox_style='open-street-map', zoom=4.8, center={'lat': 6.5, 'lon': -74.5},
            template=PLOT_TEMPLATE, title=f'Generated waste size and operational risk — {selected_year}',
        )
        fig.update_layout(margin=dict(l=0, r=0, t=50, b=0), legend_title_text='Risk level')
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.markdown('## Circularity indicators')
    st.markdown('<div class="section-help">Final disposal pressure, diverted waste, remaining capacity and years to landfill collapse. Avoided landfill shown only for non-BAU scenarios.</div>', unsafe_allow_html=True)
    latest = city_df[city_df['year'] == selected_year].iloc[0]
    i1, i2, i3, i4 = st.columns(4)
    i1.metric('Landfilled waste',   f"{human_format(latest['landfilled_t'], 0)} t/y")
    i2.metric('Diverted waste',     f"{human_format(latest['diverted_t'], 0)} t/y")
    i3.metric('Remaining capacity', f"{human_format(latest['remaining_capacity_t'], 0)} t")
    i4.metric('Years to collapse',  fmt_landfill_life(latest['landfill_life_years']))

    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(city_df, x='year', y='landfilled_t', markers=True, template=PLOT_TEMPLATE,
                      title=f'Final disposal trajectory — {selected_city}',
                      labels={'landfilled_t': 'Landfilled waste (tons/year)'})
        fig.update_traces(line=dict(width=3, color='#bd3b3b'))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.line(city_df, x='year', y='diverted_t', markers=True, template=PLOT_TEMPLATE,
                      title=f'Diverted waste trajectory — {selected_city}',
                      labels={'diverted_t': 'Diverted waste (tons/year)'})
        fig.update_traces(line=dict(width=3, color='#2f7d6b'))
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        fig = px.line(city_df, x='year', y='remaining_capacity_t', markers=True,
                      template=PLOT_TEMPLATE, title=f'Remaining landfill capacity — {selected_city}',
                      labels={'remaining_capacity_t': 'Remaining capacity (tons)'})
        fig.update_traces(line=dict(width=3, color='#0d5c91'))
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        ytc = city_df.copy()
        ytc['landfill_life_plot'] = ytc['landfill_life_years'].replace(9999, np.nan)
        fig = px.line(ytc, x='year', y='landfill_life_plot', markers=True, template=PLOT_TEMPLATE,
                      title=f'Estimated years to landfill collapse — {selected_city}',
                      labels={'landfill_life_plot': 'Years'})
        fig.add_hline(y=10, line_dash='dash', line_color='orange', annotation_text='10-year threshold')
        fig.add_hline(y=5,  line_dash='dash', line_color='red',    annotation_text='5-year critical')
        fig.update_traces(line=dict(width=3, color='#b98900'))
        st.plotly_chart(fig, use_container_width=True)

    r1, r2, r3 = st.columns(3)
    r1.metric('Diversion rate',  f"{human_format(latest['diversion_rate']   * 100, 1)}%")
    r2.metric('Collection rate', f"{human_format(latest['collection_rate']  * 100, 1)}%")
    r3.metric('Circularity gap', f"{human_format(latest['circularity_gap']  * 100, 1)}%")

    fig = px.line(city_df, x='year', y='diversion_rate', markers=True, template=PLOT_TEMPLATE,
                  title=f'Diversion rate trajectory — {selected_city}',
                  labels={'diversion_rate': 'Diversion rate'})
    fig.update_yaxes(tickformat='.0%')
    fig.update_traces(line=dict(width=3, color='#2f7d6b'))
    st.plotly_chart(fig, use_container_width=True)

    if scenario_name == 'BAU':
        st.warning('Avoided landfill vs BAU is not shown because BAU is the reference scenario.')
    else:
        c5, c6 = st.columns(2)
        with c5:
            fig = px.bar(
                comparison[comparison['year'] == selected_year].sort_values('avoided_landfill_vs_bau_t', ascending=False),
                x='city', y='avoided_landfill_vs_bau_t', template=PLOT_TEMPLATE,
                title=f'Avoided landfill vs BAU — {selected_year}',
                labels={'avoided_landfill_vs_bau_t': 'tons/year'},
            )
            fig.update_layout(xaxis_tickangle=-25)
            st.plotly_chart(fig, use_container_width=True)
        with c6:
            fig = px.line(comparison_city, x='year', y='cumulative_avoided_landfill_vs_bau_t',
                          markers=True, template=PLOT_TEMPLATE,
                          title=f'Cumulative avoided landfill vs BAU — {selected_city}',
                          labels={'cumulative_avoided_landfill_vs_bau_t': 'tons'})
            fig.update_traces(line=dict(width=3, color='#2f7d6b'))
            st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.markdown('## Side-by-side scenario comparison')
    st.markdown('<div class="section-help">Same city, year and input assumptions across all selected scenarios.</div>', unsafe_allow_html=True)
    # FIX 4 — compute only selected scenarios, all cached
    scenario_frames = [run_projection(inputs_json, int(start_year), int(end_year), s) for s in comparison_scenarios]
    scenario_results = pd.concat(scenario_frames, ignore_index=True)

    scen_city = scenario_results[
        (scenario_results['city'] == selected_city) & (scenario_results['year'] == selected_year)
    ].copy()
    scen_city['landfill_life_display'] = scen_city['landfill_life_years'].apply(fmt_landfill_life)

    cols = ['scenario', 'population', 'generated_t', 'collected_t', 'diverted_t',
            'landfilled_t', 'diversion_rate', 'circularity_gap', 'remaining_capacity_t', 'landfill_life_display']
    st.dataframe(
        scen_city[cols].style.format({
            'population': '{:,.0f}', 'generated_t': '{:,.0f}', 'collected_t': '{:,.0f}',
            'diverted_t': '{:,.0f}', 'landfilled_t': '{:,.0f}',
            'diversion_rate': '{:,.1%}', 'circularity_gap': '{:,.1%}',
            'remaining_capacity_t': '{:,.0f}',
        }),
        use_container_width=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(scen_city, x='scenario', y='landfilled_t', color='scenario',
                     color_discrete_map=SCENARIO_COLORS, template=PLOT_TEMPLATE,
                     title=f'Landfilled waste by scenario — {selected_city}, {selected_year}', text_auto='.2s')
        fig.update_layout(xaxis_tickangle=-20, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(scen_city, x='scenario', y='diversion_rate', color='scenario',
                     color_discrete_map=SCENARIO_COLORS, template=PLOT_TEMPLATE,
                     title=f'Diversion rate by scenario — {selected_city}, {selected_year}', text_auto='.1%')
        fig.update_yaxes(tickformat='.0%')
        fig.update_layout(xaxis_tickangle=-20, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    trend = scenario_results[scenario_results['city'] == selected_city]
    fig = px.line(trend, x='year', y='landfilled_t', color='scenario',
                  color_discrete_map=SCENARIO_COLORS, markers=True, template=PLOT_TEMPLATE,
                  title=f'Landfilled waste trajectory by scenario — {selected_city}')
    fig.update_traces(line=dict(width=3))
    st.plotly_chart(fig, use_container_width=True)

with tab6:
    st.markdown('## Sankey flow diagram')
    st.markdown('<div class="section-help">Balance from generated waste through collection, recycling, composting, uncollected and final disposal.</div>', unsafe_allow_html=True)
    st.plotly_chart(make_sankey(selected_row), use_container_width=True)

with tab7:
    st.markdown('## Sensitivity analysis')
    st.markdown('<div class="section-help">Each test increases one policy lever by 5 pp and estimates the marginal effect on landfilled waste and diversion rate.</div>', unsafe_allow_html=True)
    sens = sensitivity_analysis(
        inputs_json, selected_city, int(start_year), int(end_year), scenario_name, selected_year,
    )
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(sens, x='lever', y='landfilled_reduction_t', template=PLOT_TEMPLATE,
                     title=f'Landfill reduction sensitivity — {selected_city}, {selected_year}', text_auto='.2s')
        fig.update_layout(xaxis_tickangle=-25)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(sens, x='lever', y='diversion_rate_change_pp', template=PLOT_TEMPLATE,
                     title=f'Diversion rate sensitivity — {selected_city}, {selected_year}', text_auto='.2f')
        fig.update_layout(xaxis_tickangle=-25)
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        sens.style.format({'landfilled_reduction_t': '{:,.0f}', 'diversion_rate_change_pp': '{:,.2f}'}),
        use_container_width=True,
    )

with tab8:
    st.markdown('## Alerts and priority ranking')
    st.markdown('<div class="section-help">Alerts flag operational stress. Priority index ranks cities by per-capita waste, landfill pressure, circularity gap, collection gap and uncollected waste.</div>', unsafe_allow_html=True)
    st.markdown(f'### Alerts for {selected_city} in {selected_year}')
    for severity, message in build_alerts(selected_row):
        {'High': st.error, 'Medium': st.warning}.get(severity, st.success)(f'{severity} · {message}')

    ranking = priority_index(year_df)
    ranking['risk_level']        = ranking.apply(classify_risk,      axis=1)
    ranking['circularity_light'] = ranking.apply(circularity_light,  axis=1)
    ranking['landfill_life_display'] = ranking['landfill_life_years'].apply(fmt_landfill_life)

    fig = px.bar(ranking, x='city', y='priority_score', color='priority_level',
                 color_discrete_map=RISK_COLORS, template=PLOT_TEMPLATE,
                 title=f'Priority index — {selected_year}')
    fig.update_layout(xaxis_tickangle=-25)
    st.plotly_chart(fig, use_container_width=True)

    display_cols = [
        'city', 'priority_score', 'priority_level', 'risk_level', 'circularity_light',
        'gpc_effective_kg_person_day', 'collection_rate', 'diversion_rate',
        'landfilled_t', 'remaining_capacity_t', 'landfill_life_display',
    ]
    st.dataframe(
        ranking[display_cols].style.format({
            'priority_score': '{:,.1f}', 'gpc_effective_kg_person_day': '{:,.2f}',
            'collection_rate': '{:,.1%}', 'diversion_rate': '{:,.1%}',
            'landfilled_t': '{:,.0f}', 'remaining_capacity_t': '{:,.0f}',
        }),
        use_container_width=True,
    )

with tab9:
    st.markdown('## Methodology and equations')
    st.markdown('<div class="section-help">Discrete dynamic model with annual time steps. All parameters interpolate linearly from scenario-specific start values to scenario targets.</div>', unsafe_allow_html=True)
    st.markdown('### Population projection')
    st.latex(r'r_p = \left(\frac{P_T}{P_0}\right)^{\frac{1}{T-t_0}} - 1')
    st.latex(r'P_t = P_0\,(1+r_p)^{t-t_0}')
    st.markdown('### Per-capita waste generation')
    st.latex(r'g_t = g_0\,(1+r_g)^{t-t_0}\,(1-S_{\mathrm{eff},t})')
    st.markdown('### Annual waste generation')
    st.latex(r'W_t = \dfrac{P_t\,g_t\,365}{1000}')
    st.markdown('### Collection and uncollected waste')
    st.latex(r'Q_t = W_t\,K_{\mathrm{eff},t}')
    st.latex(r'U_t = W_t - Q_t')
    st.markdown('### Recycling and composting (corrected, no double-counting)')
    st.latex(r'\mathrm{Rec}_t = Q_t\,f_{\mathrm{rec}}\,R_{\mathrm{eff},t}')
    st.latex(r'\mathrm{Comp}_t = \min\!\left(Q_t - \mathrm{Rec}_t,\; Q_t\,f_{\mathrm{org}}\right)\,C_{\mathrm{eff},t}')
    st.markdown('### Diversion and final disposal')
    st.latex(r'\mathrm{Div}_t = \mathrm{Rec}_t + \mathrm{Comp}_t')
    st.latex(r'D_t = \max\!\left(0,\; Q_t - \mathrm{Div}_t\right)')
    st.markdown('### Landfill remaining capacity and years to collapse')
    st.latex(r'\mathrm{Cap}_t = \max\!\left(0,\; \mathrm{Cap}_0 - \sum_{\tau \le t} D_\tau\right)')
    st.latex(r'\mathrm{YTC}_t = \dfrac{\mathrm{Cap}_t}{D_t}')

with tab10:
    st.markdown('## Export results')
    export_dict = {
        'inputs': inputs, 'results': results, 'bau_comparison': comparison,
    }
    # Append each selected scenario as its own sheet
    for s in comparison_scenarios:
        sheet_key = s.replace(' ', '_')[:28]
        export_dict[sheet_key] = run_projection(inputs_json, int(start_year), int(end_year), s)

    st.download_button(
        'Download simulation results (.xlsx)',
        data=to_excel_download(export_dict),
        file_name=f"urban_waste_circularity_{scenario_name.replace(' ', '_')}.xlsx",
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    st.download_button(
        'Download simulation results (.csv)',
        data=results.to_csv(index=False).encode('utf-8'),
        file_name=f"urban_waste_circularity_{scenario_name.replace(' ', '_')}.csv",
        mime='text/csv',
    )
    with st.expander('Preview results'):
        st.dataframe(results, use_container_width=True)

st.markdown(
    '<div class="footer">Urban Waste Simulation and Circularity Observatory · '
    'Open-source decision-support software for circular waste planning.</div>',
    unsafe_allow_html=True,
)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- Load Data ---
@st.cache_data
def load_data():
    return pd.read_csv("time_series_dashboard_data.csv", parse_dates=['week_start_date'])

df = load_data()

# --- Unique district/subdistrict options ---
districts = ["All"] + sorted([d for d in df['dtname'].dropna().unique() if d != "All"])

# --- Create 2 columns for side-by-side plots ---
col1, col2 = st.columns(2)

def district_selector(col, label_suffix):
    with col:
        dt = st.selectbox(f"Select District {label_suffix}", districts, key=f"dt_{label_suffix}")
        if dt == "All":
            sdt = st.selectbox(f"Sub-District {label_suffix}", ["All"], disabled=True, key=f"sdt_{label_suffix}")
        else:
            subdistricts = ["All"] + sorted([s for s in df[df['dtname'] == dt]['sdtname'].dropna().unique() if s != "All"])
            sdt = st.selectbox(f"Sub-District {label_suffix}", subdistricts, key=f"sdt_{label_suffix}")
    return dt, sdt

# --- Filters for both plots ---
dt1, sdt1 = district_selector(col1, "A")
dt2, sdt2 = district_selector(col2, "B")

def filter_data(df, dt, sdt):
    if dt == "All" and sdt == "All":
        return df.copy()
    elif dt != "All" and sdt == "All":
        return df[df['dtname'] == dt]
    else:
        return df[(df['dtname'] == dt) & (df['sdtname'] == sdt)]

df1 = filter_data(df, dt1, sdt1).sort_values("week_start_date")
df2 = filter_data(df, dt2, sdt2).sort_values("week_start_date")

def plot_ts(data, title):
    fig = go.Figure()

    # Dengue cases on secondary axis
    fig.add_trace(go.Scatter(
        x=data['week_start_date'], y=data['dengue_cases'],
        name='Dengue Cases', yaxis='y2',
        mode='lines+markers', line=dict(color='crimson')
    ))

    # Climate variables
    fig.add_trace(go.Scatter(x=data['week_start_date'], y=data['temperature_2m_max'], name='Max Temp', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=data['week_start_date'], y=data['temperature_2m_min'], name='Min Temp', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=data['week_start_date'], y=data['relative_humidity_2m_mean'], name='Humidity', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=data['week_start_date'], y=data['rain_sum'], name='Rainfall', line=dict(color='purple')))

    # Threshold lines
    fig.add_hline(y=35, line_dash="dot", line_color="orange", annotation_text="Max Temp ≤ 35")
    fig.add_hline(y=18, line_dash="dot", line_color="blue", annotation_text="Min Temp ≥ 18")
    fig.add_hline(y=60, line_dash="dot", line_color="green", annotation_text="Humidity ≥ 60%")

    # Threshold week highlights (optional)
    for _, row in data[data['meets_threshold']].iterrows():
        fig.add_vline(x=row['week_start_date'], line_width=0.5, line_color='lightgreen', opacity=0.3)

    # Layout
    fig.update_layout(
        title=title,
        xaxis_title="Week Start Date",
        yaxis=dict(title="Climate Variables"),
        yaxis2=dict(title="Dengue Cases", overlaying='y', side='right', showgrid=False),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center'),
        height=600
    )
    return fig

# --- Show plots ---
with col1:
    st.plotly_chart(plot_ts(df1, f"{dt1} / {sdt1}"), use_container_width=True)

with col2:
    st.plotly_chart(plot_ts(df2, f"{dt2} / {sdt2}"), use_container_width=True)

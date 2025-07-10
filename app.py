import streamlit as st
import pandas as pd
import json
import os
import tempfile
from datetime import timedelta
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Dengue Climate Dashboard", layout="wide")

# --- Load Google Drive credentials and file ---
@st.cache_resource
def load_drive():
    creds_json = st.secrets["gdrive_creds"]
    creds_dict = json.loads(creds_json)

    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        json.dump(creds_dict, tmp)
        tmp.flush()
        gauth = GoogleAuth()
        gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
            tmp.name,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive = GoogleDrive(gauth)

    return drive

# --- Download file if not exists ---
csv_path = "time_series_dashboard.csv"
if not os.path.exists(csv_path):
    drive = load_drive()
    file_id = "1ad-PcGSpk6YoO-ZolodMWfvFq64kO-Z_"  # Replace with your actual file ID
    downloaded = drive.CreateFile({'id': file_id})
    downloaded.GetContentFile(csv_path)

# --- Load CSV ---
@st.cache_data
def load_data():
    df = pd.read_csv(csv_path, parse_dates=["week_start_date"])
    df['dtname'] = df['dtname'].astype(str).str.strip()
    df['sdtname'] = df['sdtname'].astype(str).str.strip()
    if "meets_threshold" in df.columns:
        df["meets_threshold"] = df["meets_threshold"].astype(str).str.lower() == "true"
    return df

df = load_data()

# --- Sidebar filters ---
districts = ["All"] + sorted([d for d in df['dtname'].unique() if d != "All"])
selected_dt = st.sidebar.selectbox("Select District", districts)

subdistricts = ["All"] + sorted([s for s in df[df['dtname'] == selected_dt]['sdtname'].unique() if s != "All"])
selected_sdt = st.sidebar.selectbox("Select Block", subdistricts)

# --- Filter based on selection ---
filtered = df[(df['dtname'] == selected_dt) & (df['sdtname'] == selected_sdt)]

if filtered.empty:
    st.warning("No data available for this selection.")
    st.stop()

# --- Sort by date and prepare x-axis labels ---
filtered = filtered.sort_values("week_start_date")
week_dates = filtered["week_start_date"]
valid_dates = filtered[filtered["dengue_cases"].notna()]["week_start_date"]
x_start = valid_dates.min()
x_end = valid_dates.max()

# --- Create Plotly Subplots ---
fig = make_subplots(
    rows=5, cols=1, shared_xaxes=False,
    vertical_spacing=0.05,
    subplot_titles=[
        "Dengue Cases",
        "Max Temperature (°C)",
        "Min Temperature (°C)",
        "Mean Relative Humidity (%)",
        "Rainfall (mm)"
    ]
)

# --- Add Traces ---
def add_trace(row, col, y, name, color, is_integer=False):
    fig.add_trace(go.Scatter(
        x=week_dates,
        y=filtered[y],
        name=name,
        mode="lines+markers",
        marker=dict(size=4),
        line=dict(color=color)
    ), row=row, col=col)

    axis_name = f'yaxis{"" if row == 1 else row}'
    axis_config = dict(
        title=name,
        showgrid=True,
        zeroline=True,
        gridcolor='lightgray',
        tickfont=dict(color='black'),
    )
    if is_integer:
        axis_config["tickformat"] = ",d"

    fig.update_layout({axis_name: axis_config})

# Add each subplot
add_trace(1, 1, "dengue_cases", "Dengue Cases (Weekly Sum)", "crimson", is_integer=True)
add_trace(2, 1, "temperature_2m_max", "Max Temperature (°C) (Weekly Max)", "orange")
add_trace(3, 1, "temperature_2m_min", "Min Temperature (°C) (Weekly Min)", "blue")

# Humidity with fixed range
fig.add_trace(go.Scatter(
    x=week_dates,
    y=filtered["relative_humidity_2m_mean"],
    name="Mean Relative Humidity (%) (Weekly Mean)",
    mode="lines+markers",
    marker=dict(size=4),
    line=dict(color="green")
), row=4, col=1)

fig.update_layout({
    f'yaxis4': dict(
        title="Mean Relative Humidity (%) (Weekly Mean)",
        showgrid=True,
        zeroline=True,
        gridcolor='lightgray',
        tickfont=dict(color='black'),
        range=[0, 100]
    )
})

add_trace(5, 1, "rain_sum", "Rainfall (mm) (Weekly Sum)", "purple")

# --- Highlight meets_threshold weeks ---
highlight_weeks = filtered[filtered["meets_threshold"] == True]
for dt in highlight_weeks["week_start_date"].drop_duplicates():
    fig.add_vrect(
        x0=dt,
        x1=dt + timedelta(days=6),
        fillcolor="red",
        opacity=0.15,
        line_width=0,
        layer="below"
    )

# --- Update Layout ---
fig.update_layout(
    height=1800,
    width=3000,
    title_text=f"Weekly Dengue and Climate Trends — {selected_dt} district(s) / {selected_sdt} block(s)",
    showlegend=False,
    margin=dict(t=80, b=60),
    template=None,
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(color='black'),
    xaxis=dict(range=[x_start, x_end])
)

# --- Configure X-axis per subplot ---
for i in range(1, 6):
    fig.update_xaxes(
        row=i, col=1,
        tickangle=-45,
        tickformat="%d-%b-%y",
        tickfont=dict(size=11, color='black'),
        ticks="outside",
        showgrid=True,
        gridcolor='lightgray',
        dtick=604800000,
        showticklabels=True
    )

# --- Display Plot ---
st.plotly_chart(fig, use_container_width=True)

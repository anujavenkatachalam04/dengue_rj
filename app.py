import streamlit as st
import pandas as pd
import json
import os
import tempfile
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
    file_id = "1ad-PcGSpk6YoO-ZolodMWfvFq64kO-Z_"
    downloaded = drive.CreateFile({'id': file_id})
    downloaded.GetContentFile(csv_path)

# --- Load CSV ---
def load_data():
    df = pd.read_csv(csv_path, parse_dates=["week_start_date"])
    df['dtname'] = df['dtname'].astype(str).str.strip()
    df['sdtname'] = df['sdtname'].astype(str).str.strip()
    return df

df = load_data()


# --- Sidebar filters ---
districts = ["All"] + sorted([d for d in df['dtname'].unique() if d != "All"])
selected_dt = st.sidebar.selectbox("Select District", districts)

subdistricts = ["All"] + sorted([s for s in df[df['dtname'] == selected_dt]['sdtname'].unique() if s != "All"])
selected_sdt = st.sidebar.selectbox("Select Subdistrict", subdistricts)

# --- Filter based on selection ---
filtered = df[(df['dtname'] == selected_dt) & (df['sdtname'] == selected_sdt)]

if filtered.empty:
    st.warning("No data available for this selection.")
    st.stop()

# --- Prepare labels and sort ---
filtered = filtered.sort_values("week_start_date")
week_labels = filtered['week_start_date'].dt.strftime('%y-W%U')

# --- Create Plotly Subplots ---
fig = make_subplots(
    rows=5, cols=1, shared_xaxes=True,
    vertical_spacing=0.03,
    subplot_titles=[
        "Dengue Cases",
        "Max Temperature (°C)",
        "Min Temperature (°C)",
        "Relative Humidity (%)",
        "Rainfall (mm)"
    ]
)

# --- Add Traces ---
def add_trace(row, col, y, name, color, thresholds=None):
    fig.add_trace(go.Scatter(
        x=week_labels,
        y=filtered[y],
        name=name,
        mode="lines+markers",
        marker=dict(size=4),
        line=dict(color=color)
    ), row=row, col=col)

    if thresholds:
        for tmin, tmax in thresholds:
            fig.add_shape(
                type="rect",
                x0=week_labels.iloc[0], x1=week_labels.iloc[-1],
                y0=tmin if tmin is not None else -9999,
                y1=tmax if tmax is not None else 9999,
                fillcolor="lightgreen",
                opacity=0.3,
                line_width=0,
                row=row, col=col,
                layer="below"
            )

# Add each subplot
add_trace(1, 1, "dengue_cases", "Dengue Cases", "crimson")
add_trace(2, 1, "temperature_2m_max", "Max Temp", "orange", thresholds=[(None, 35)])
add_trace(3, 1, "temperature_2m_min", "Min Temp", "blue", thresholds=[(18, None)])
add_trace(4, 1, "relative_humidity_2m_mean", "Humidity", "green", thresholds=[(60, None)])
add_trace(5, 1, "rain_sum", "Rainfall", "purple")

# --- Update Layout ---
fig.update_layout(
    height=1200,
    title_text=f"Weekly Dengue and Climate Trends — {selected_dt} / {selected_sdt}",
    template="plotly_white",
    showlegend=False,
    margin=dict(t=80, b=40),
)

# --- Configure x-axis ---
fig.update_xaxes(
    tickangle=90,
    tickfont=dict(size=10),
    showgrid=True
)

# --- Display Plot ---
st.plotly_chart(fig, use_container_width=True)

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
    file_id = "1ad-PcGSpk6YoO-ZolodMWfvFq64kO-Z_"  # Replace with your actual file ID
    downloaded = drive.CreateFile({'id': file_id})
    downloaded.GetContentFile(csv_path)

# --- Load CSV ---
@st.cache_data
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

# --- Sort by date and prepare x-axis labels ---
filtered = filtered.sort_values("week_start_date")
week_dates = filtered["week_start_date"]

# --- Create Plotly Subplots ---
fig = make_subplots(
    rows=5, cols=1, shared_xaxes=False,  # <<== CHANGED THIS
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
    )
    if is_integer:
        axis_config["tickformat"] = ",d"

    fig.update_layout({axis_name: axis_config})

# Add each subplot
add_trace(1, 1, "dengue_cases", "Dengue Cases", "crimson", is_integer=True)
add_trace(2, 1, "temperature_2m_max", "Max Temp", "orange")
add_trace(3, 1, "temperature_2m_min", "Min Temp", "blue")
add_trace(4, 1, "relative_humidity_2m_mean", "Humidity", "green")
add_trace(5, 1, "rain_sum", "Rainfall", "purple")

# --- Update Layout ---
fig.update_layout(
    height=1800,
    title_text=f"Weekly Dengue and Climate Trends — {selected_dt} / {selected_sdt}",
    showlegend=False,
    margin=dict(t=80, b=60),
    template=None,  # Avoids grey text from some themes
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(color='black')  # All labels black
)

# --- Configure X-axis globally ---
for i in range(1, 6):  # 5 subplots
    fig.update_xaxes(
        row=i, col=1,
        tickangle=0,
        tickformat="%d-%b",  # Like 01-Jan
        tickfont=dict(size=11, color='black'),
        showgrid=True,
        gridcolor='lightgray',
        title_text="Week Start Date",
        dtick=604800000  # One week in ms
    )


# --- Display Plot ---
st.plotly_chart(fig, use_container_width=True)

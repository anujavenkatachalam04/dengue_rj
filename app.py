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

# Fix x_start and x_end to full date range, not just dengue cases
x_start = filtered["week_start_date"].min()
x_end = filtered["week_start_date"].max()

# --- Create Subplots ---
fig = make_subplots(
    rows=5, cols=1, shared_xaxes=True,  # shared_xaxes ensures all use same x range
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
def add_trace(row, col, y, name, color, is_integer=False, y_range=None):
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
        tickfont=dict(color='black', size=12)
    )
    if is_integer:
        axis_config["tickformat"] = ",d"
    if y_range:
        axis_config["range"] = y_range

    fig.update_layout({axis_name: axis_config})

# --- Add Each Plot with Custom Y-axis Start at 0 ---
add_trace(1, 1, "dengue_cases", "Dengue Cases (Weekly Sum)", "crimson", is_integer=True, y_range=[0, None])
add_trace(2, 1, "temperature_2m_max", "Max Temperature (°C) (Weekly Max)", "orange", y_range=[0, None])
add_trace(3, 1, "temperature_2m_min", "Min Temperature (°C) (Weekly Min)", "blue", y_range=[0, None])
add_trace(4, 1, "relative_humidity_2m_mean", "Mean Relative Humidity (%) (Weekly Mean)", "green", y_range=[0, 100])
add_trace(5, 1, "rain_sum", "Rainfall (mm) (Weekly Sum)", "purple", y_range=[0, None])

# --- Add X-axis label to last subplot only ---
fig.update_xaxes(
    row=5, col=1,
    title_text="Week Start Date",
    title_font=dict(size=12),
    title_standoff=30
)

# --- Apply X-axis settings to all subplots ---
for i in range(1, 6):
    fig.update_xaxes(
        row=i, col=1,
        tickangle=-45,
        tickformat="%d-%b-%y",
        tickfont=dict(size=10),
        ticks="outside",
        showgrid=True,
        gridcolor='lightgray',
        range=[x_start, x_end],  # Force all plots to have same x range
        dtick=604800000  # one week in ms
    )

# --- Final Layout ---
fig.update_layout(
    height=2100,
    width=3000,
    title_text=f"Weekly Dengue and Climate Trends — Block: {selected_sdt}, District: {selected_dt}",
    showlegend=False,
    margin=dict(t=80, b=100),
    template=None,
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(color='black')
)

# --- Configure X-axis for all subplots ---
for i in range(1, 6):
    fig.update_xaxes(
        row=i, col=1,
        tickangle=-45,
        tickformat="%d-%b-%y",
        tickfont=dict(size=10, color='black'),
        ticks="outside",
        showgrid=True,
        gridcolor='lightgray',
        dtick=604800000
    )

# --- Display Chart ---
st.plotly_chart(fig, use_container_width=True)

# --- Threshold Notes ---
st.markdown("""
**Note on Thresholds**:  
- **Dengue Cases**: Weeks shaded **red** indicate that Max Temperature (°C) ≤ 35°C AND Min Temperature (°C) ≥ 18°C OR Mean Relative Humidity (%) ≥ 60%.
- **Max Temperature (°C)**: Weeks shaded **orange** indicate values ≤ 35°C.  
- **Min Temperature (°C)**: Weeks shaded **blue** indicate values ≥ 18°C.  
- **Mean Relative Humidity (%)**: Weeks shaded **green** indicate values ≥ 60%.
""")

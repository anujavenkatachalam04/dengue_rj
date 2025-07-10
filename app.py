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
from plotly.subplots import make_subplots  # Important fix

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

def add_trace(row, col, y, name, color, is_integer=False, tickformat=None):
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
        titlefont=dict(size=12, color='black'),   # Title font size
        showgrid=True,
        zeroline=True,
        gridcolor='lightgray',
        tickfont=dict(size=12, color='black')     # Tick font size
    )
    if is_integer:
        axis_config["tickformat"] = ",d"
    elif tickformat:
        axis_config["tickformat"] = tickformat

    fig.update_layout({axis_name: axis_config})


# --- Subplot 1: Dengue Cases ---
add_trace(1, 1, "dengue_cases", "Dengue Cases (Weekly Sum)", "crimson", is_integer=True)

highlight_weeks = filtered[filtered["meets_threshold"] == True]
for dt in highlight_weeks["week_start_date"].drop_duplicates():
    fig.add_vrect(
        x0=dt,
        x1=dt + timedelta(days=6),
        fillcolor="red",
        opacity=0.15,
        line_width=0,
        layer="below",
        row=1, col=1
    )

# --- Subplot 2: Max Temperature ---
add_trace(2, 1, "temperature_2m_max", "Max Temperature (°C) (Weekly Max)", "orange")
highlight_max = filtered[filtered["temperature_2m_max"] <= 35]
for dt in highlight_max["week_start_date"].drop_duplicates():
    fig.add_vrect(
        x0=dt, x1=dt + timedelta(days=6),
        fillcolor="orange", opacity=0.1, line_width=0,
        layer="below", row=2, col=1
    )

# --- Subplot 3: Min Temperature ---
add_trace(3, 1, "temperature_2m_min", "Min Temperature (°C) (Weekly Min)", "blue")
highlight_min = filtered[filtered["temperature_2m_min"] >= 18]
for dt in highlight_min["week_start_date"].drop_duplicates():
    fig.add_vrect(
        x0=dt, x1=dt + timedelta(days=6),
        fillcolor="blue", opacity=0.1, line_width=0,
        layer="below", row=3, col=1
    )

# --- Subplot 4: Humidity ---
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
        titlefont=dict(size=12, color='black'),
        showgrid=True,
        zeroline=True,
        gridcolor='lightgray',
        tickfont=dict(size=12, color='black'),
        range=[0, 100]
    )
})

highlight_humidity = filtered[filtered["relative_humidity_2m_mean"] >= 60]
for dt in highlight_humidity["week_start_date"].drop_duplicates():
    fig.add_vrect(
        x0=dt, x1=dt + timedelta(days=6),
        fillcolor="green", opacity=0.1, line_width=0,
        layer="below", row=4, col=1
    )

# --- Subplot 5: Rainfall (Fix tickformat) ---
add_trace(5, 1, "rain_sum", "Rainfall (mm) (Weekly Sum)", "purple")

# --- Add X-axis label for last chart ---
fig.update_xaxes(
    row=5, col=1,
    title_text="Week Start Date",
    title_font=dict(size=12),
    title_standoff=30  # Avoid overlap
)

# --- Layout ---
fig.update_layout(
    height=2100,
    width=3000,
    title_text=f"Weekly Dengue and Climate Trends — Block: {selected_sdt}, District: {selected_dt}",
    showlegend=False,
    margin=dict(t=80, b=100),
    template=None,
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(color='black'),
    xaxis=dict(range=[x_start, x_end])
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

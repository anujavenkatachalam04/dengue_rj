import streamlit as st
import pandas as pd
import json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import plotly.graph_objects as go

st.set_page_config(page_title="Dengue Climate Dashboard", layout="wide")

@st.cache_resource
def load_drive():
    creds_str = st.secrets["gdrive_creds"]
    creds_dict = json.loads(creds_str)

    gauth = GoogleAuth()
    gauth.settings['client_config'] = creds_dict  # ✅ load directly from memory
    gauth.ServiceAuth()  # ✅ authenticate with service account

    return GoogleDrive(gauth)


# --- SETUP: Load CSV from Google Drive using file ID ---
@st.cache_data
def load_data(file_id):
    drive = load_drive()
    downloaded = drive.CreateFile({'id': file_id})
    downloaded.GetContentFile("time_series_dashboard.csv")
    df = pd.read_csv("time_series_dashboard.csv", parse_dates=["week_start_date"])
    return df

# --- CONFIG ---
st.title("Dengue & Climate Time Series, Rajasthan (2024-2025")

# --- Your Google Drive FILE ID here ---
FILE_ID = "1ABCxYZ_myp5aZJmKJxY9g1d0JgEe1234" 
df = load_data(FILE_ID)

# --- Sidebar Filters ---
districts = ["All"] + sorted([d for d in df['dtname'].dropna().unique() if d != "All"])
dt_filter = st.sidebar.selectbox("Select District (dtname):", districts)

if dt_filter == "All":
    sdt_filter = st.sidebar.selectbox("Select Sub-District (sdtname):", ["All"], disabled=True)
else:
    subdistricts = ["All"] + sorted([s for s in df[df['dtname'] == dt_filter]['sdtname'].dropna().unique() if s != "All"])
    sdt_filter = st.sidebar.selectbox("Select Sub-District (sdtname):", subdistricts)

# --- Filter Data ---
if dt_filter == "All" and sdt_filter == "All":
    filtered_df = df.copy()
elif sdt_filter == "All":
    filtered_df = df[df['dtname'] == dt_filter]
else:
    filtered_df = df[(df['dtname'] == dt_filter) & (df['sdtname'] == sdt_filter)]

filtered_df = filtered_df.sort_values("week_start_date")

# --- Plotting ---
fig = go.Figure()

# Dengue Cases
fig.add_trace(go.Scatter(
    x=filtered_df['week_start_date'],
    y=filtered_df['dengue_cases'],
    name="Dengue Cases",
    mode="lines+markers",
    yaxis="y2",
    line=dict(color='crimson')
))

# Climate Variables
fig.add_trace(go.Scatter(x=filtered_df['week_start_date'], y=filtered_df['temperature_2m_max'], name="Max Temp", line=dict(color='orange')))
fig.add_trace(go.Scatter(x=filtered_df['week_start_date'], y=filtered_df['temperature_2m_min'], name="Min Temp", line=dict(color='blue')))
fig.add_trace(go.Scatter(x=filtered_df['week_start_date'], y=filtered_df['relative_humidity_2m_mean'], name="Humidity", line=dict(color='green')))
fig.add_trace(go.Scatter(x=filtered_df['week_start_date'], y=filtered_df['rain_sum'], name="Rainfall", line=dict(color='purple')))

# Threshold Highlights
fig.add_hline(y=35, line_dash="dot", line_color="orange", annotation_text="Max Temp ≤ 35")
fig.add_hline(y=18, line_dash="dot", line_color="blue", annotation_text="Min Temp ≥ 18")
fig.add_hline(y=60, line_dash="dot", line_color="green", annotation_text="Humidity ≥ 60")

# Highlight threshold weeks
for _, row in filtered_df[filtered_df['meets_threshold']].iterrows():
    fig.add_vline(x=row['week_start_date'], line_color='lightgreen', opacity=0.3, line_width=0.5)

# Layout
fig.update_layout(
    title=f"📈 Weekly Trends for {dt_filter} / {sdt_filter}",
    xaxis_title="Week Start Date",
    yaxis=dict(title="Climate Variables"),
    yaxis2=dict(title="Dengue Cases", overlaying='y', side='right'),
    height=650,
    legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center')
)

# Display
st.plotly_chart(fig, use_container_width=True)

import streamlit as st
import pandas as pd
import json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials
import tempfile
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend

st.set_page_config(page_title="Dengue Climate Dashboard", layout="wide")

@st.cache_resource
def load_drive():
    # Load credentials from secrets
    creds_json = st.secrets["gdrive_creds"]
    creds_dict = json.loads(creds_json)

    # Save service account JSON to a temp file
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        json.dump(creds_dict, tmp)
        tmp.flush()

        # Create GoogleAuth instance and authorize with service account
        gauth = GoogleAuth()
        gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
            tmp.name,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        drive = GoogleDrive(gauth)

    return drive



# --- SETUP: Load CSV from Google Drive using file ID ---
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv("time_series_dashboard.csv", parse_dates=['week_start_date'])
    df['dtname'] = df['dtname'].astype(str).str.strip()
    df['sdtname'] = df['sdtname'].astype(str).str.strip()
    return df

df = load_data()

# Sidebar filters
districts = ["All"] + sorted(df['dtname'].unique())
selected_dt = st.sidebar.selectbox("Select District", districts)

if selected_dt == "All":
    selected_sdt = st.sidebar.selectbox("Select Subdistrict", ["All"], disabled=True)
    filtered = df.copy()
else:
    subdistricts = ["All"] + sorted(df[df['dtname'] == selected_dt]['sdtname'].unique())
    selected_sdt = st.sidebar.selectbox("Select Subdistrict", subdistricts)

    if selected_sdt == "All":
        df_all = df[(df['dtname'] == selected_dt) & (df['sdtname'] != "All")]
        if df_all.empty:
            st.warning("No subdistrict-level data available.")
            st.stop()
        filtered = df_all.groupby(['iso_year_week', 'week_start_date']).agg({
            'dengue_cases': 'sum',
            'temperature_2m_max': 'mean',
            'temperature_2m_min': 'mean',
            'relative_humidity_2m_mean': 'mean',
            'rain_sum': 'sum'
        }).reset_index()
    else:
        filtered = df[(df['dtname'] == selected_dt) & (df['sdtname'] == selected_sdt)]

if filtered.empty:
    st.warning("No data available for this selection.")
    st.stop()

# Prepare week label
filtered['Week_Label'] = filtered['week_start_date'].dt.strftime('%y-W%U')
plot_vars = ['dengue_cases', 'temperature_2m_max', 'temperature_2m_min', 'relative_humidity_2m_mean', 'rain_sum']
threshold_shades = {
    'temperature_2m_min': [(18, 100)],
    'temperature_2m_max': [(0, 35)],
    'relative_humidity_2m_mean': [(60, 100)]
}

# Set seaborn style
sns.set_theme(style="whitegrid")

# --- Generate One Plot Per Variable ---
for var in plot_vars:
    fig, ax = plt.subplots(figsize=(18, 3))
    data = filtered.copy()

    ax.plot(data['Week_Label'], data[var], marker='o', linestyle='-', color='steelblue', linewidth=1.5)

    if var in threshold_shades:
        for ymin, ymax in threshold_shades[var]:
            ax.axhspan(ymin, ymax, color='lightgreen', alpha=0.3)

    ax.set_xticks(range(len(data['Week_Label'])))
    ax.set_xticklabels(data['Week_Label'], rotation=90, fontsize=9)
    ax.grid(True, linestyle='--', linewidth=0.5, color='gray')
    ax.set_title(var.replace("_", " ").title(), fontsize=14, weight='bold')
    ax.set_ylabel("Value", fontsize=11)
    ax.set_xlabel("Week", fontsize=11)

    st.pyplot(fig)


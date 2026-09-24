import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import time

# Set Matplotlib dark theme to match Streamlit's dark aesthetic
plt.style.use("dark_background")

# --- Page Setup ---
st.set_page_config(
    page_title="Power Plant Remote Monitor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Firebase Endpoints ---
LIVE_URL = "https://power-monitor-660f6-default-rtdb.asia-southeast1.firebasedatabase.app/live.json"
HIST_URL = "https://power-monitor-660f6-default-rtdb.asia-southeast1.firebasedatabase.app/history.json"

# --- Sidebar Controls: Advanced Customization ---
st.sidebar.title("⚙️ Dashboard Controls")

# 1. Alarm Thresholds
st.sidebar.subheader("🚨 Alarm Thresholds")
mw_warning = st.sidebar.number_input("Max Gross MW Warning", min_value=50.0, max_value=500.0, value=250.0, step=10.0)
pf_min_limit = st.sidebar.number_input("Min Power Factor Warning", min_value=0.50, max_value=1.00, value=0.85, step=0.01)

# 2. Chart Display Options
st.sidebar.subheader("📊 Chart Settings")
time_horizon = st.sidebar.selectbox("Time Window", ["Last 1 Hour", "Last 6 Hours", "Last 12 Hours", "Last 24 Hours", "All Data"], index=3)
max_y_axis = st.sidebar.number_input("Y-Axis Max Range (MW)", min_value=100, max_value=600, value=300, step=20)
chart_color = st.sidebar.color_picker("Trend Line Color", "#00FFC8")
show_threshold_line = st.sidebar.checkbox("Show Overload Threshold Line", value=True)

# 3. Refresh Rate Settings
st.sidebar.subheader("🔄 Live Refresh")
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh Rate (seconds)", min_value=1, max_value=10, value=3)

# --- Data Fetching Functions ---
def fetch_live_data():
    try:
        res = requests.get(LIVE_URL, timeout=3)
        return res.json() if res.status_code == 200 and res.json() else {}
    except Exception:
        return {}

def fetch_history_data():
    try:
        res = requests.get(HIST_URL, timeout=5)
        if res.status_code == 200 and res.json():
            data = res.json()
            records = []
            for idx, (key, val) in enumerate(data.items(), start=1):
                hour = idx / 6.0  # 10-minute sampling mapping
                gross_mw = val.get("gross_mw", 0.0)
                gross_mvar = val.get("gross_mvar", 0.0)
                records.append({"Index": idx, "Hour": hour, "Gross MW": gross_mw, "Gross MVAR": gross_mvar})
            return pd.DataFrame(records)
    except Exception:
        pass
    return pd.DataFrame(columns=["Index", "Hour", "Gross MW", "Gross MVAR"])

# --- Main Dashboard Layout ---
st.title("⚡ Power Generation Remote Dashboard")

live_data = fetch_live_data()
gross_mw = live_data.get("gross_mw", 0.0)
gross_mvar = live_data.get("gross_mvar", 0.0)
gt_pf = live_data.get("gt_pf", 0.0)
st_pf = live_data.get("st_pf", 0.0)

# --- Real-Time Alarm Notifications ---
alarms = []
if gross_mw > mw_warning:
    alarms.append(f"<b>HIGH LOAD WARNING:</b> Gross Generation ({gross_mw:.2f} MW) has exceeded limit threshold ({mw_warning:.1f} MW)!")
if gt_pf < pf_min_limit and gt_pf > 0:
    alarms.append(f"<b>LOW POWER FACTOR WARNING:</b> GT PF ({gt_pf:.3f}) is below target limit ({pf_min_limit:.2f})!")
if st_pf < pf_min_limit and st_pf > 0:
    alarms.append(f"<b>LOW POWER FACTOR WARNING:</b> ST PF ({st_pf:.3f}) is below target limit ({pf_min_limit:.2f})!")

for alarm in alarms:
    st.error(alarm, icon="⚠️")

# --- Digital Readout Gauges / Metrics ---
c1, c2, c3, c4 = st.columns(4)
c1.metric(label="Gross MW", value=f"{gross_mw:.2f} MW", delta=f"{gross_mw - mw_warning:.1f} MW limit diff" if gross_mw > mw_warning else None)
c2.metric(label="Gross MVAR", value=f"{gross_mvar:.2f} MVAR")
c3.metric(label="GT Power Factor", value=f"{gt_pf:.3f}")
c4.metric(label="ST Power Factor", value=f"{st_pf:.3f}")

st.markdown("---")

# --- Interactive Historical Trend (Matplotlib) ---
st.subheader("📈 Historical Trend Analytics")

df_hist = fetch_history_data()

# Filter dataset by time horizon
if not df_hist.empty:
    if time_horizon == "Last 1 Hour":
        df_hist = df_hist.tail(6)
    elif time_horizon == "Last 6 Hours":
        df_hist = df_hist.tail(36)
    elif time_horizon == "Last 12 Hours":
        df_hist = df_hist.tail(72)
    elif time_horizon == "Last 24 Hours":
        df_hist = df_hist.tail(144)

# Create Matplotlib Figure
fig, ax = plt.subplots(figsize=(10, 4.5))

# Set transparent background to blend with Streamlit dark mode
fig.patch.set_facecolor('#0e1117')
ax.set_facecolor('#0e1117')

if not df_hist.empty:
    ax.plot(
        df_hist["Hour"],
        df_hist["Gross MW"],
        color=chart_color,
        marker='o',
        linewidth=2,
        label="Gross MW"
    )

# Threshold Reference Line
if show_threshold_line:
    ax.axhline(
        y=mw_warning,
        color='#FF4B4B',
        linestyle='--',
        linewidth=1.5,
        label=f"Warning Threshold ({mw_warning} MW)"
    )

# Axis & Grid Customization
ax.set_xlabel("Operational Time (Hours)", color='white', fontsize=10)
ax.set_ylabel("Power (MW)", color='white', fontsize=10)
ax.set_ylim(0, max_y_axis)

if time_horizon in ["Last 24 Hours", "All Data"]:
    ax.set_xlim(0, 24)

ax.grid(True, color='#262730', linestyle=':', linewidth=0.8)
ax.tick_params(colors='white')
ax.legend(facecolor='#1e1e1e', edgecolor='#333333', labelcolor='white')

# Render Matplotlib chart inside Streamlit
st.pyplot(fig)

# --- Data Table & CSV Export ---
with st.expander("📥 View & Export Historical CSV Data"):
    st.dataframe(df_hist, use_container_width=True)
    if not df_hist.empty:
        csv_data = df_hist.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Log History as CSV",
            data=csv_data,
            file_name="power_generation_history.csv",
            mime="text/csv"
        )

# Auto-refresh loop
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
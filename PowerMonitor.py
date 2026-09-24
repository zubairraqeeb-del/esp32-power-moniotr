import streamlit as st
import pandas as pd
import urllib.request
import json
import time

# --- Page Setup ---
st.set_page_config(
    page_title="EGB PLC Power Plants",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Firebase Endpoints ---
LIVE_URL = "https://power-monitor-660f6-default-rtdb.asia-southeast1.firebasedatabase.app/live.json"
HIST_URL = "https://power-monitor-660f6-default-rtdb.asia-southeast1.firebasedatabase.app/history.json"

# --- Sidebar Controls ---
st.sidebar.title("⚙️ Dashboard Controls")

# 1. Alarm Thresholds
st.sidebar.subheader("🚨 Alarm Thresholds")
mw_warning = st.sidebar.number_input("Max Gross MW Warning", min_value=50.0, max_value=500.0, value=250.0, step=10.0)
pf_min_limit = st.sidebar.number_input("Min Power Factor Warning", min_value=0.50, max_value=1.00, value=0.85, step=0.01)

# 2. Chart Display Options
st.sidebar.subheader("📊 Chart Settings")
time_horizon = st.sidebar.selectbox("Time Window", ["Last 1 Hour", "Last 6 Hours", "Last 12 Hours", "Last 24 Hours", "All Data"], index=3)

# 3. Refresh Rate Settings
st.sidebar.subheader("🔄 Live Refresh")
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh Rate (seconds)", min_value=1, max_value=10, value=3)

# --- Built-in Data Fetchers ---
def fetch_live_data():
    try:
        req = urllib.request.Request(LIVE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
    except Exception:
        pass
    return {}

def fetch_history_data():
    try:
        req = urllib.request.Request(HIST_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                records = []
                for idx, (key, val) in enumerate(data.items(), start=1):
                    # 👈 MODIFIED: Extracts timestamp field from Firebase or falls back to key
                    live_timestamp = val.get("ts") or val.get("time") or val.get("timestamp") or str(key)
                    gross_mw = val.get("gross_mw", 0.0)
                    records.append({"Live Time": str(live_timestamp), "Gross MW": gross_mw})
                return pd.DataFrame(records)
    except Exception:
        pass
    return pd.DataFrame(columns=["Live Time", "Gross MW"])  # 👈 MODIFIED: Updated fallback columns

# --- Dashboard Header ---
st.title("⚡ Siddhirganj 335MW")

live_data = fetch_live_data()
gross_mw = live_data.get("gross_mw", 0.0)
gross_mvar = live_data.get("gross_mvar", 0.0)
gt_pf = live_data.get("gt_pf", 0.0)
st_pf = live_data.get("st_pf", 0.0)

# --- Real-Time Alarm Notifications ---
if gross_mw > mw_warning:
    st.error(f"🚨 **HIGH LOAD WARNING:** Gross Generation ({gross_mw:.2f} MW) has exceeded limit threshold ({mw_warning:.1f} MW)!")
if 0 < gt_pf < pf_min_limit:
    st.error(f"🚨 **LOW POWER FACTOR WARNING:** GT PF ({gt_pf:.3f}) is below target limit ({pf_min_limit:.2f})!")
if 0 < st_pf < pf_min_limit:
    st.error(f"🚨 **LOW POWER FACTOR WARNING:** ST PF ({st_pf:.3f}) is below target limit ({pf_min_limit:.2f})!")

# --- Digital Metrics ---
c1, c2, c3, c4 = st.columns(4)
c1.metric(label="Gross MW", value=f"{gross_mw:.2f} MW")
c2.metric(label="Gross MVAR", value=f"{gross_mvar:.2f} MVAR")
c3.metric(label="GT Power Factor", value=f"{gt_pf:.3f}")
c4.metric(label="ST Power Factor", value=f"{st_pf:.3f}")

st.markdown("---")

# --- Native Historical Trend Chart ---
st.subheader("📈 Historical Trend Analytics")

df_hist = fetch_history_data()

if not df_hist.empty:
    if time_horizon == "Last 1 Hour":
        df_hist = df_hist.tail(6)
    elif time_horizon == "Last 6 Hours":
        df_hist = df_hist.tail(36)
    elif time_horizon == "Last 12 Hours":
        df_hist = df_hist.tail(72)
    elif time_horizon == "Last 24 Hours":
        df_hist = df_hist.tail(144)

    # 👈 MODIFIED: Render chart with 'Live Time' on X-axis and 'Gross MW' on Y-axis
    st.line_chart(
        data=df_hist,
        x="Live Time",
        y="Gross MW"
    )
else:
    st.info("No historical data available in Firebase yet.")

# --- Data Table & CSV Download ---
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

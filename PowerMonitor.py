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
# Main Siddhirganj / General Endpoints
LIVE_URL = "https://power-monitor-660f6-default-rtdb.asia-southeast1.firebasedatabase.app/live.json"
HIST_URL = "https://power-monitor-660f6-default-rtdb.asia-southeast1.firebasedatabase.app/history.json"

# 👈 ADDED: New Live Generation Endpoints
S120_LIVE_URL = "https://h412-egb-web-dashboard-default-rtdb.asia-southeast1.firebasedatabase.app/s120_live_generation.json"
H412_LIVE_URL = "https://h412-egb-web-dashboard-default-rtdb.asia-southeast1.firebasedatabase.app/h412_live_generation.json"

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
def fetch_url_json(url, timeout=3):
    """Generic JSON fetcher using urllib to prevent dependency issues."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return data if isinstance(data, dict) else {}
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
                    raw_ts = val.get("ts") or val.get("time") or val.get("timestamp") or key
                    
                    try:
                        if str(raw_ts).replace('.', '', 1).isdigit():
                            ts_num = float(raw_ts)
                            dt = pd.to_datetime(ts_num, unit='ms' if ts_num > 1e11 else 's')
                        else:
                            dt = pd.to_datetime(raw_ts)
                        
                        live_timestamp = dt.strftime('%d%b, %H:%M').lower()
                    except Exception:
                        live_timestamp = str(raw_ts)

                    gross_mw = val.get("gross_mw", 0.0)
                    records.append({"Live Time": live_timestamp, "Gross MW": gross_mw})
                return pd.DataFrame(records)
    except Exception:
        pass
    return pd.DataFrame(columns=["Live Time", "Gross MW"])

# --- Dashboard Header ---
st.title("⚡ EGB PLC Power Plants - Live Generation Dashboard")

# Fetch data from all active endpoints
live_data_main = fetch_url_json(LIVE_URL)
s120_data = fetch_url_json(S120_LIVE_URL)
h412_data = fetch_url_json(H412_LIVE_URL)

# Helper function to extract common metric names safely
def get_metrics(data_dict):
    gross_mw = float(data_dict.get("gross_mw", data_dict.get("mw", data_dict.get("MW", 0.0))))
    gross_mvar = float(data_dict.get("gross_mvar", data_dict.get("mvar", data_dict.get("MVAR", 0.0))))
    gt_pf = float(data_dict.get("gt_pf", data_dict.get("pf", data_dict.get("PF", 0.0))))
    st_pf = float(data_dict.get("st_pf", 0.0))
    return gross_mw, gross_mvar, gt_pf, st_pf

# --- Plant Sections Layout (Tabs) ---
tab1, tab2, tab3 = st.tabs(["🏭 Siddhirganj 335MW", "🏭 S120 Generation Unit", "🏭 H412 Generation Unit"])

with tab1:
    st.subheader("Siddhirganj 335MW Live Generation")
    mw, mvar, gt_pf, st_pf = get_metrics(live_data_main)
    
    if mw > mw_warning:
        st.error(f"🚨 **HIGH LOAD WARNING:** Gross Generation ({mw:.2f} MW) exceeded threshold ({mw_warning:.1f} MW)!")
    if 0 < gt_pf < pf_min_limit:
        st.error(f"🚨 **LOW POWER FACTOR WARNING:** GT PF ({gt_pf:.3f}) is below limit ({pf_min_limit:.2f})!")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gross MW", f"{mw:.2f} MW")
    c2.metric("Gross MVAR", f"{mvar:.2f} MVAR")
    c3.metric("GT Power Factor", f"{gt_pf:.3f}")
    c4.metric("ST Power Factor", f"{st_pf:.3f}")

with tab2:
    st.subheader("S120 Live Generation Unit")
    s120_mw, s120_mvar, s120_gt_pf, s120_st_pf = get_metrics(s120_data)

    if s120_mw > mw_warning:
        st.error(f"🚨 **HIGH LOAD WARNING (S120):** Generation ({s120_mw:.2f} MW) exceeded threshold ({mw_warning:.1f} MW)!")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gross MW", f"{s120_mw:.2f} MW")
    c2.metric("Gross MVAR", f"{s120_mvar:.2f} MVAR")
    c3.metric("GT Power Factor", f"{s120_gt_pf:.3f}")
    c4.metric("ST Power Factor", f"{s120_st_pf:.3f}")

with tab3:
    st.subheader("H412 Live Generation Unit")
    h412_mw, h412_mvar, h412_gt_pf, h412_st_pf = get_metrics(h412_data)

    if h412_mw > mw_warning:
        st.error(f"🚨 **HIGH LOAD WARNING (H412):** Generation ({h412_mw:.2f} MW) exceeded threshold ({mw_warning:.1f} MW)!")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gross MW", f"{h412_mw:.2f} MW")
    c2.metric("Gross MVAR", f"{h412_mvar:.2f} MVAR")
    c3.metric("GT Power Factor", f"{h412_gt_pf:.3f}")
    c4.metric("ST Power Factor", f"{h412_st_pf:.3f}")

st.markdown("---")

# --- Historical Trend Analytics ---
st.subheader("📈 Historical Trend Analytics (Siddhirganj)")

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

    st.line_chart(
        data=df_hist,
        x="Live Time",
        y="Gross MW"
    )
else:
    st.info("No historical data available in Firebase yet.")

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

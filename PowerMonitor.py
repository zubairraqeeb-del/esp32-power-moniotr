import streamlit as st
import pandas as pd
import urllib.request
import json
import time
import math

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

S120_LIVE_URL = "https://h412-egb-web-dashboard-default-rtdb.asia-southeast1.firebasedatabase.app/s120_live_generation.json"
H412_LIVE_URL = "https://h412-egb-web-dashboard-default-rtdb.asia-southeast1.firebasedatabase.app/h412_live_generation.json"

# --- Power Factor Helper Function ---
def calc_pf(mw, mvar):
    """Calculates Power Factor: PF = |MW| / sqrt(MW^2 + MVAR^2)"""
    apparent_power = math.sqrt(mw**2 + mvar**2)
    if apparent_power > 0:
        return abs(mw) / apparent_power
    return 0.0

# --- Data Fetchers ---
def fetch_url_json(url, timeout=3):
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
                for key, val in data.items():
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

# --- Sidebar Controls ---
st.sidebar.title("⚙️ Dashboard Controls")

st.sidebar.subheader("🚨 Alarm Thresholds")
mw_warning = st.sidebar.number_input("Max Gross MW Warning", min_value=50.0, max_value=500.0, value=250.0, step=10.0)
pf_min_limit = st.sidebar.number_input("Min Power Factor Warning", min_value=0.50, max_value=1.00, value=0.85, step=0.01)

st.sidebar.subheader("📊 Chart Settings")
time_horizon = st.sidebar.selectbox("Time Window", ["Last 1 Hour", "Last 6 Hours", "Last 12 Hours", "Last 24 Hours", "All Data"], index=3)

st.sidebar.subheader("🔄 Live Refresh")
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh Rate (seconds)", min_value=1, max_value=10, value=3)

# --- Main Dashboard ---
st.title("⚡ EGB PLC Power Plants")

# Fetch Live Endpoints
live_data_335 = fetch_url_json(LIVE_URL)
live_data_412 = fetch_url_json(H412_LIVE_URL)
live_data_120 = fetch_url_json(S120_LIVE_URL)

# Tabbed Layout
tab1, tab2, tab3 = st.tabs(["🏭 Siddhirganj 335MW", "🏭 H412 Plant", "🏭 S120 Plant"])

# ------------------ TAB 1: Siddhirganj 335MW ------------------
with tab1:
    st.subheader("Siddhirganj 335MW Overview")

    gt_mw_335 = float(live_data_335.get("gt_mw", 0.0))
    st_mw_335 = float(live_data_335.get("st_mw", 0.0))
    gt_mvar_335 = float(live_data_335.get("gt_mvar", 0.0))
    st_mvar_335 = float(live_data_335.get("st_mvar", 0.0))

    # Fallback to direct gross values if component values aren't individual in payload
    gross_mw_335 = (gt_mw_335 + st_mw_335) if (gt_mw_335 or st_mw_335) else float(live_data_335.get("gross_mw", 0.0))
    gross_mvar_335 = (gt_mvar_335 + st_mvar_335) if (gt_mvar_335 or st_mvar_335) else float(live_data_335.get("gross_mvar", 0.0))
    gt_pf_335 = calc_pf(gt_mw_335, gt_mvar_335) if (gt_mw_335 or gt_mvar_335) else float(live_data_335.get("gt_pf", 0.0))
    st_pf_335 = calc_pf(st_mw_335, st_mvar_335) if (st_mw_335 or st_mvar_335) else float(live_data_335.get("st_pf", 0.0))

    # Alarms
    if gross_mw_335 > mw_warning:
        st.error(f"🚨 **HIGH LOAD WARNING:** Gross Generation ({gross_mw_335:.2f} MW) has exceeded threshold ({mw_warning:.1f} MW)!")
    if 0 < gt_pf_335 < pf_min_limit:
        st.error(f"🚨 **LOW POWER FACTOR WARNING:** GT PF ({gt_pf_335:.3f}) is below limit ({pf_min_limit:.2f})!")
    if 0 < st_pf_335 < pf_min_limit:
        st.error(f"🚨 **LOW POWER FACTOR WARNING:** ST PF ({st_pf_335:.3f}) is below limit ({pf_min_limit:.2f})!")

    # Summary Row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(label="Gross MW", value=f"{gross_mw_335:.2f} MW")
    c2.metric(label="Gross MVAR", value=f"{gross_mvar_335:.2f} MVAR")
    c3.metric(label="GT Power Factor", value=f"{gt_pf_335:.3f}")
    c4.metric(label="ST Power Factor", value=f"{st_pf_335:.3f}")

    st.markdown("##### 🔌 Individual Component Breakdown")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(label="GT MW", value=f"{gt_mw_335:.2f} MW")
    m2.metric(label="GT MVAR", value=f"{gt_mvar_335:.2f} MVAR")
    m3.metric(label="ST MW", value=f"{st_mw_335:.2f} MW")
    m4.metric(label="ST MVAR", value=f"{st_mvar_335:.2f} MVAR")


# ------------------ TAB 2: H412 Plant ------------------
with tab2:
    st.subheader("H412 Generation Unit Overview")

    gt_mw_412 = float(live_data_412.get("gt_mw", 0.0))
    st_mw_412 = float(live_data_412.get("st_mw", 0.0))
    gt_mvar_412 = float(live_data_412.get("gt_mvar", 0.0))
    st_mvar_412 = float(live_data_412.get("st_mvar", 0.0))

    # Calculations
    gross_mw_412 = gt_mw_412 + st_mw_412
    gross_mvar_412 = gt_mvar_412 + st_mvar_412
    gt_pf_412 = calc_pf(gt_mw_412, gt_mvar_412)
    st_pf_412 = calc_pf(st_mw_412, st_mvar_412)

    # Alarms
    if gross_mw_412 > mw_warning:
        st.error(f"🚨 **HIGH LOAD WARNING:** Gross Generation ({gross_mw_412:.2f} MW) has exceeded threshold ({mw_warning:.1f} MW)!")
    if 0 < gt_pf_412 < pf_min_limit:
        st.error(f"🚨 **LOW POWER FACTOR WARNING:** GT PF ({gt_pf_412:.3f}) is below limit ({pf_min_limit:.2f})!")
    if 0 < st_pf_412 < pf_min_limit:
        st.error(f"🚨 **LOW POWER FACTOR WARNING:** ST PF ({st_pf_412:.3f}) is below limit ({pf_min_limit:.2f})!")

    # Summary Row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(label="Gross MW", value=f"{gross_mw_412:.2f} MW")
    c2.metric(label="Gross MVAR", value=f"{gross_mvar_412:.2f} MVAR")
    c3.metric(label="GT Power Factor", value=f"{gt_pf_412:.3f}")
    c4.metric(label="ST Power Factor", value=f"{st_pf_412:.3f}")

    st.markdown("##### 🔌 Individual Component Breakdown")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(label="GT MW", value=f"{gt_mw_412:.2f} MW")
    m2.metric(label="GT MVAR", value=f"{gt_mvar_412:.2f} MVAR")
    m3.metric(label="ST MW", value=f"{st_mw_412:.2f} MW")
    m4.metric(label="ST MVAR", value=f"{st_mvar_412:.2f} MVAR")


# ------------------ TAB 3: S120 Plant ------------------
with tab3:
    st.subheader("S120 Generation Unit Overview")

    gt1_mw_120 = float(live_data_120.get("gt1_mw", 0.0))
    gt2_mw_120 = float(live_data_120.get("gt2_mw", 0.0))
    gt1_mvar_120 = float(live_data_120.get("gt1_mvar", 0.0))
    gt2_mvar_120 = float(live_data_120.get("gt2_mvar", 0.0))

    # Calculations
    gross_mw_120 = gt1_mw_120 + gt2_mw_120
    gross_mvar_120 = gt1_mvar_120 + gt2_mvar_120
    gt1_pf_120 = calc_pf(gt1_mw_120, gt1_mvar_120)
    gt2_pf_120 = calc_pf(gt2_mw_120, gt2_mvar_120)

    # Alarms
    if gross_mw_120 > mw_warning:
        st.error(f"🚨 **HIGH LOAD WARNING:** Gross Generation ({gross_mw_120:.2f} MW) has exceeded threshold ({mw_warning:.1f} MW)!")
    if 0 < gt1_pf_120 < pf_min_limit:
        st.error(f"🚨 **LOW POWER FACTOR WARNING:** GT1 PF ({gt1_pf_120:.3f}) is below limit ({pf_min_limit:.2f})!")
    if 0 < gt2_pf_120 < pf_min_limit:
        st.error(f"🚨 **LOW POWER FACTOR WARNING:** GT2 PF ({gt2_pf_120:.3f}) is below limit ({pf_min_limit:.2f})!")

    # Summary Row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(label="Gross MW", value=f"{gross_mw_120:.2f} MW")
    c2.metric(label="Gross MVAR", value=f"{gross_mvar_120:.2f} MVAR")
    c3.metric(label="GT1 Power Factor", value=f"{gt1_pf_120:.3f}")
    c4.metric(label="GT2 Power Factor", value=f"{gt2_pf_120:.3f}")

    st.markdown("##### 🔌 Individual Component Breakdown")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(label="GT1 MW", value=f"{gt1_mw_120:.2f} MW")
    m2.metric(label="GT1 MVAR", value=f"{gt1_mvar_120:.2f} MVAR")
    m3.metric(label="GT2 MW", value=f"{gt2_mw_120:.2f} MW")
    m4.metric(label="GT2 MVAR", value=f"{gt2_mvar_120:.2f} MVAR")

st.markdown("---")

# --- Historical Trend Chart ---
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

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

# --- Prevent Graying-Out / Dimming on Auto-Refresh ---
st.markdown(
    """
    <style>
    /* Lock element opacity to prevent dimming/graying out during st.rerun() */
    [data-testid="stAppViewContainer"],
    [data-testid="stVerticalBlock"],
    .element-container,
    .stPlotlyChart,
    .stMetric {
        opacity: 1 !important;
        transition: none !important;
    }

    /* Optional: Hide top-right 'Running...' spinner icon */
    [data-testid="stStatusWidget"] {
        visibility: hidden !important;
    }
    </style>
    """,
    unsafe_allow_html=True
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
    """Fetches historical data containing gross_mw, gross_mw_412, and gross_mw_120."""
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

                    mw_335 = float(val.get("gross_mw", 0.0) or 0.0)
                    mw_412 = float(val.get("gross_mw_412", 0.0) or 0.0)
                    mw_120 = float(val.get("gross_mw_120", 0.0) or 0.0)

                    records.append({
                        "Live Time": live_timestamp,
                        "Siddhirganj 335MW": mw_335,
                        "Haripur 412MW": mw_412,
                        "Siddhirganj 2x120MW": mw_120
                    })
                return pd.DataFrame(records)
    except Exception:
        pass
    return pd.DataFrame(columns=["Live Time", "Siddhirganj 335MW", "Haripur 412MW", "Siddhirganj 2x120MW"])

def apply_time_filter(df, horizon_setting):
    """Filters history based on user selection in sidebar."""
    if df.empty:
        return df
    if horizon_setting == "Last 1 Hour":
        return df.tail(12)
    elif horizon_setting == "Last 6 Hours":
        return df.tail(72)
    elif horizon_setting == "Last 12 Hours":
        return df.tail(144)
    elif horizon_setting == "Last 24 Hours":
        return df.tail(288)
    return df

# --- Sidebar Controls ---
st.sidebar.title("⚙️ Dashboard Controls")

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

# Fetch History dataset
df_hist_all = fetch_history_data()
df_hist_filtered = apply_time_filter(df_hist_all, time_horizon)

# Tabbed Layout
tab1, tab2, tab3, tab4 = st.tabs([
    "🏭 Siddhirganj 335MW", 
    "🏭 Haripur 412MW", 
    "🏭 Siddhirganj 2x120MW", 
    "📊 Comparative Analytics"
])

# ------------------ TAB 1: Siddhirganj 335MW ------------------
with tab1:
    st.subheader("Siddhirganj 335MW Overview")

    gt_mw_335 = float(live_data_335.get("gt_mw", 0.0))
    st_mw_335 = float(live_data_335.get("st_mw", 0.0))
    gt_mvar_335 = float(live_data_335.get("gt_mvar", 0.0))
    st_mvar_335 = float(live_data_335.get("st_mvar", 0.0))

    gross_mw_335 = (gt_mw_335 + st_mw_335) if (gt_mw_335 or st_mw_335) else float(live_data_335.get("gross_mw", 0.0))
    gross_mvar_335 = (gt_mvar_335 + st_mvar_335) if (gt_mvar_335 or st_mvar_335) else float(live_data_335.get("gross_mvar", 0.0))
    gt_pf_335 = calc_pf(gt_mw_335, gt_mvar_335) if (gt_mw_335 or gt_mvar_335) else float(live_data_335.get("gt_pf", 0.0))
    st_pf_335 = calc_pf(st_mw_335, st_mvar_335) if (st_mw_335 or st_mvar_335) else float(live_data_335.get("st_pf", 0.0))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(label="GT MW", value=f"{gt_mw_335:.2f} MW")
    m2.metric(label="GT MVAR", value=f"{gt_mvar_335:.2f} MVAR")
    m3.metric(label="ST MW", value=f"{st_mw_335:.2f} MW")
    m4.metric(label="ST MVAR", value=f"{st_mvar_335:.2f} MVAR")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(label="Gross MW", value=f"{gross_mw_335:.2f} MW")
    c2.metric(label="Gross MVAR", value=f"{gross_mvar_335:.2f} MVAR")
    c3.metric(label="GT Power Factor", value=f"{gt_pf_335:.3f}")
    c4.metric(label="ST Power Factor", value=f"{st_pf_335:.3f}")

    st.markdown("---")

    st.subheader("📈 Historical Trend Analytics (Siddhirganj 335MW)")
    if not df_hist_filtered.empty:
        st.line_chart(data=df_hist_filtered, x="Live Time", y="Siddhirganj 335MW")
    else:
        st.info("No historical data available in Firebase yet.")

    with st.expander("📥 View & Export 335MW Historical CSV Data"):
        if not df_hist_filtered.empty:
            df_335_csv = df_hist_filtered[["Live Time", "Siddhirganj 335MW"]]
            st.dataframe(df_335_csv, use_container_width=True)
            st.download_button(
                label="Download 335MW History as CSV",
                data=df_335_csv.to_csv(index=False).encode('utf-8'),
                file_name="335mw_generation_history.csv",
                mime="text/csv"
            )


# ------------------ TAB 2: Haripur 412MW ------------------
with tab2:
    st.subheader("Haripur 412MW Overview")

    gt_mw_412 = float(live_data_412.get("gt_mw", 0.0))
    st_mw_412 = float(live_data_412.get("st_mw", 0.0))
    gt_mvar_412 = float(live_data_412.get("gt_mvar", 0.0))
    st_mvar_412 = float(live_data_412.get("st_mvar", 0.0))

    gross_mw_412 = gt_mw_412 + st_mw_412
    gross_mvar_412 = gt_mvar_412 + st_mvar_412
    gt_pf_412 = calc_pf(gt_mw_412, gt_mvar_412)
    st_pf_412 = calc_pf(st_mw_412, st_mvar_412)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(label="GT MW", value=f"{gt_mw_412:.2f} MW")
    m2.metric(label="GT MVAR", value=f"{gt_mvar_412:.2f} MVAR")
    m3.metric(label="ST MW", value=f"{st_mw_412:.2f} MW")
    m4.metric(label="ST MVAR", value=f"{st_mvar_412:.2f} MVAR")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(label="Gross MW", value=f"{gross_mw_412:.2f} MW")
    c2.metric(label="Gross MVAR", value=f"{gross_mvar_412:.2f} MVAR")
    c3.metric(label="GT Power Factor", value=f"{gt_pf_412:.3f}")
    c4.metric(label="ST Power Factor", value=f"{st_pf_412:.3f}")

    st.markdown("---")

    st.subheader("📈 Historical Trend Analytics (Haripur 412MW)")
    if not df_hist_filtered.empty:
        st.line_chart(data=df_hist_filtered, x="Live Time", y="Haripur 412MW")
    else:
        st.info("No historical data available in Firebase yet.")

    with st.expander("📥 View & Export Haripur 412MW Historical CSV Data"):
        if not df_hist_filtered.empty:
            df_412_csv = df_hist_filtered[["Live Time", "Haripur 412MW"]]
            st.dataframe(df_412_csv, use_container_width=True)
            st.download_button(
                label="Download Haripur 412MW History as CSV",
                data=df_412_csv.to_csv(index=False).encode('utf-8'),
                file_name="haripur_412mw_generation_history.csv",
                mime="text/csv"
            )


# ------------------ TAB 3: Siddhirganj 2x120MW ------------------
with tab3:
    st.subheader("Siddhirganj 2x120MW Overview")

    gt1_mw_120 = float(live_data_120.get("gt1_mw", 0.0))
    gt2_mw_120 = float(live_data_120.get("gt2_mw", 0.0))
    gt1_mvar_120 = float(live_data_120.get("gt1_mvar", 0.0))
    gt2_mvar_120 = float(live_data_120.get("gt2_mvar", 0.0))

    gross_mw_120 = gt1_mw_120 + gt2_mw_120
    gross_mvar_120 = gt1_mvar_120 + gt2_mvar_120
    gt1_pf_120 = calc_pf(gt1_mw_120, gt1_mvar_120)
    gt2_pf_120 = calc_pf(gt2_mw_120, gt2_mvar_120)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(label="GT1 MW", value=f"{gt1_mw_120:.2f} MW")
    m2.metric(label="GT1 MVAR", value=f"{gt1_mvar_120:.2f} MVAR")
    m3.metric(label="GT2 MW", value=f"{gt2_mw_120:.2f} MW")
    m4.metric(label="GT2 MVAR", value=f"{gt2_mvar_120:.2f} MVAR")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(label="Gross MW", value=f"{gross_mw_120:.2f} MW")
    c2.metric(label="Gross MVAR", value=f"{gross_mvar_120:.2f} MVAR")
    c3.metric(label="GT1 Power Factor", value=f"{gt1_pf_120:.3f}")
    c4.metric(label="GT2 Power Factor", value=f"{gt2_pf_120:.3f}")

    st.markdown("---")

    st.subheader("📈 Historical Trend Analytics (Siddhirganj 2x120MW)")
    if not df_hist_filtered.empty:
        st.line_chart(data=df_hist_filtered, x="Live Time", y="Siddhirganj 2x120MW")
    else:
        st.info("No historical data available in Firebase yet.")

    with st.expander("📥 View & Export Siddhirganj 2x120MW Historical CSV Data"):
        if not df_hist_filtered.empty:
            df_120_csv = df_hist_filtered[["Live Time", "Siddhirganj 2x120MW"]]
            st.dataframe(df_120_csv, use_container_width=True)
            st.download_button(
                label="Download Siddhirganj 2x120MW History as CSV",
                data=df_120_csv.to_csv(index=False).encode('utf-8'),
                file_name="siddhirganj_2x120mw_generation_history.csv",
                mime="text/csv"
            )


# ------------------ TAB 4: Comparative Analytics ------------------
with tab4:
    st.subheader("📊 Cross-Plant Comparative Trend Analysis")

    total_live_mw = gross_mw_335 + gross_mw_412 + gross_mw_120
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(label="Total Fleet Live Generation", value=f"{total_live_mw:.2f} MW")
    k2.metric(label="Siddhirganj 335MW Share", value=f"{gross_mw_335:.1f} MW")
    k3.metric(label="Haripur 412MW Share", value=f"{gross_mw_412:.1f} MW")
    k4.metric(label="Siddhirganj 2x120MW Share", value=f"{gross_mw_120:.1f} MW")

    st.markdown("---")

    selected_plants = st.multiselect(
        "Select Plants to Include in Trend Comparison:",
        options=["Siddhirganj 335MW", "Haripur 412MW", "Siddhirganj 2x120MW"],
        default=["Siddhirganj 335MW", "Haripur 412MW", "Siddhirganj 2x120MW"]
    )

    if not df_hist_filtered.empty:
        if selected_plants:
            st.line_chart(
                data=df_hist_filtered,
                x="Live Time",
                y=selected_plants
            )
        else:
            st.warning("Please select at least one plant above to render the chart.")
    else:
        st.info("No historical data available in Firebase yet.")

    with st.expander("📥 View & Export All Power Plants Combined CSV Data"):
        if not df_hist_filtered.empty:
            st.dataframe(df_hist_filtered, use_container_width=True)
            st.download_button(
                label="Download All Plants History as CSV",
                data=df_hist_filtered.to_csv(index=False).encode('utf-8'),
                file_name="all_plants_generation_history.csv",
                mime="text/csv"
            )

# Auto-refresh loop
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()

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

S120_LIVE_URL = "https://h412-egb-web-dashboard-default-rtdb.asia-southeast1.firebasedatabase.app/s120_live_generation.json"
H412_LIVE_URL = "https://h412-egb-web-dashboard-default-rtdb.asia-southeast1.firebasedatabase.app/h412_live_generation.json"

# --- Sidebar Controls ---
st.sidebar.title("⚙️ Dashboard Controls")



st.sidebar.subheader("📊 Chart Settings")
time_horizon = st.sidebar.selectbox("Time Window",
                                    ["Last 1 Hour", "Last 6 Hours", "Last 12 Hours", "Last 24 Hours", "All Data"],
                                    index=3)

st.sidebar.subheader("🔄 Live Refresh")
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh Rate (seconds)", min_value=1, max_value=10, value=3)


# --- Data Fetchers ---
def fetch_url_json(url, timeout=3):
    """Generic JSON fetcher."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return data if isinstance(data, dict) else {"raw_value": data}
    except Exception as e:
        return {"error": str(e)}
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


# --- Render Helper for Dynamic Key Display ---
def render_plant_tab(tab_name, data_dict):
    st.subheader(f"{tab_name} Live Data")

    if not data_dict or "error" in data_dict:
        st.warning(f"Unable to fetch live data for {tab_name}. (Check URL or connection)")
        return

    # Automatically display all key-value pairs received from Firebase
    keys = list(data_dict.keys())
    if keys:
        cols = st.columns(min(len(keys), 4))
        for idx, (key, val) in enumerate(data_dict.items()):
            col = cols[idx % 4]
            # Format numbers cleanly if numeric
            if isinstance(val, (int, float)):
                val_str = f"{val:.2f}"
            else:
                val_str = str(val)
            col.metric(label=key.upper(), value=val_str)

    with st.expander(f"🔍 View Raw JSON Payload ({tab_name})"):
        st.json(data_dict)


# --- Main Dashboard ---
st.title("⚡ EGB PLC Power Plants - Remote Monitor")

# Fetch Data
main_data = fetch_url_json(LIVE_URL)
s120_data = fetch_url_json(S120_LIVE_URL)
h412_data = fetch_url_json(H412_LIVE_URL)

# Tabbed Layout
tab1, tab2, tab3 = st.tabs(["🏭 Siddhirganj 335MW", "🏭 S120 Unit", "🏭 H412 Unit"])

with tab1:
    render_plant_tab("Siddhirganj 335MW", main_data)

with tab2:
    render_plant_tab("S120 Generation Unit", s120_data)

with tab3:
    render_plant_tab("H412 Generation Unit", h412_data)

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

    st.line_chart(data=df_hist, x="Live Time", y="Gross MW")
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

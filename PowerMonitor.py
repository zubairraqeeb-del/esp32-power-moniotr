import streamlit as st
import pandas as pd
import urllib.request
import json
import time
import math
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

# --- SMTP Configuration for mail.egcb.com.bd ---
# In production, set these inside .streamlit/secrets.toml
SMTP_SERVER = st.secrets.get("SMTP_SERVER", "mail.egcb.com.bd")
SMTP_PORT = int(st.secrets.get("SMTP_PORT", 587))  # standard TLS port (or 465 for SSL)
SENDER_EMAIL = st.secrets.get("SENDER_EMAIL", "noreply@egcb.com.bd")
SENDER_PASSWORD = st.secrets.get("SENDER_PASSWORD", "YourWebmailPasswordHere")


def send_otp_email(receiver_email, otp_code):
    """Sends a 6-digit OTP code to the specified email via Webmail SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🔐 Your Security Key / OTP - EGB PLC Power Monitor"
        msg["From"] = f"EGB PLC Power Monitor <{SENDER_EMAIL}>"
        msg["To"] = receiver_email

        body_text = f"""
Hello,

Your One-Time Password (OTP) to access the EGB PLC Power Plants Monitoring Portal is:

{otp_code}

This key is valid for 5 minutes. Please do not share this code with anyone.

Regards,
EGB PLC Systems Team
"""
        body_html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 500px; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
              <h2 style="color: #0d6efd;">⚡ EGB PLC Power Plants</h2>
              <p>Hello,</p>
              <p>Your One-Time Password (OTP) to access the live monitoring portal is:</p>
              <div style="background-color: #f4f4f4; padding: 15px; text-align: center; border-radius: 5px; font-size: 24px; font-weight: bold; letter-spacing: 4px; color: #000;">
                {otp_code}
              </div>
              <p style="margin-top: 15px; font-size: 13px; color: #666;">This key is valid for <strong>5 minutes</strong>. If you did not request this, please ignore this email.</p>
              <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
              <p style="font-size: 11px; color: #999;">EGB PLC Automated System Notice</p>
            </div>
          </body>
        </html>
        """

        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        # Connect to SMTP Server
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            server.starttls()

        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        server.quit()
        return True, "Success"
    except Exception as e:
        return False, str(e)


def check_password():
    """Handles the 2-Step Email OTP Authentication process."""
    if st.session_state.get("authenticated", False):
        return True

    if "auth_step" not in st.session_state:
        st.session_state["auth_step"] = "enter_email"

    st.title("🔒 EGB PLC Power Plants Portal")

    # STEP 1: Enter Corporate Email
    if st.session_state["auth_step"] == "enter_email":
        st.subheader("Step 1: Verify Corporate Identity")
        st.markdown("Enter your official email address ending in `@egcb.com.bd` to receive a login security key.")

        with st.form("email_form"):
            user_email = st.text_input("Corporate Email Address", placeholder="e.g. zubair.uddin@egcb.com.bd").strip().lower()
            submit_email = st.form_submit_button("Send Security Key (OTP)", use_container_width=True)

            if submit_email:
                if not user_email.endswith("@egcb.com.bd"):
                    st.error("Access Restricted: Please enter a valid '@egcb.com.bd' email address.")
                else:
                    otp = f"{random.randint(100000, 999999)}"
                    with st.spinner("Connecting to Webmail server & dispatching OTP..."):
                        success, err_msg = send_otp_email(user_email, otp)
                        if success:
                            st.session_state["user_email"] = user_email
                            st.session_state["generated_otp"] = otp
                            st.session_state["otp_timestamp"] = time.time()
                            st.session_state["auth_step"] = "enter_otp"
                            st.success(f"Security key sent to {user_email}")
                            st.rerun()
                        else:
                            st.error(f"Failed to send email via SMTP ({SMTP_SERVER}): {err_msg}")

    # STEP 2: Enter OTP
    elif st.session_state["auth_step"] == "enter_otp":
        st.subheader("Step 2: Enter Security Key")
        st.info(f"A 6-digit OTP has been sent to **{st.session_state.get('user_email')}**. Check your webmail inbox.")

        with st.form("otp_form"):
            input_otp = st.text_input("Enter 6-Digit Security Key (OTP)", type="password").strip()
            submit_otp = st.form_submit_button("Verify & Access Dashboard", use_container_width=True)

            if submit_otp:
                # 5-minute expiry check (300 seconds)
                if time.time() - st.session_state.get("otp_timestamp", 0) > 300:
                    st.error("The security key has expired (valid for 5 minutes). Please request a new key.")
                elif input_otp == st.session_state.get("generated_otp"):
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = st.session_state.get("user_email")
                    st.success("Authentication successful!")
                    st.rerun()
                else:
                    st.error("Invalid Security Key. Please verify from your webmail and try again.")

        if st.button("← Change Email Address", use_container_width=True):
            st.session_state["auth_step"] = "enter_email"
            st.rerun()

    return False


# Halt execution until authenticated
if not check_password():
    st.stop()


# --- Firebase Endpoints ---
LIVE_URL = "https://power-monitor-660f6-default-rtdb.asia-southeast1.firebasedatabase.app/live.json"
HIST_URL = "https://power-monitor-660f6-default-rtdb.asia-southeast1.firebasedatabase.app/history.json"

S120_LIVE_URL = "https://h412-egb-web-dashboard-default-rtdb.asia-southeast1.firebasedatabase.app/s120_live_generation.json"
H412_LIVE_URL = "https://h412-egb-web-dashboard-default-rtdb.asia-southeast1.firebasedatabase.app/h412_live_generation.json"
SONAGAZI_LIVE_URL = "https://power-monitor-660f6-default-rtdb.asia-southeast1.firebasedatabase.app/sonagazi_live.json"

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
    """Fetches historical data containing metrics for all 4 plants."""
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
                    mw_75 = float(val.get("total_mw_75", 0.0) or val.get("total_mw", 0.0) or 0.0)

                    records.append({
                        "Live Time": live_timestamp,
                        "Siddhirganj 335MW": mw_335,
                        "Haripur 412MW": mw_412,
                        "Siddhirganj 2x120MW": mw_120,
                        "Sonagazi 75MW": mw_75
                    })
                return pd.DataFrame(records)
    except Exception:
        pass
    return pd.DataFrame(columns=["Live Time", "Siddhirganj 335MW", "Haripur 412MW", "Siddhirganj 2x120MW", "Sonagazi 75MW"])

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

# Session User & Logout
st.sidebar.markdown(f"👤 Logged in: **{st.session_state.get('user', 'User')}**")
if st.sidebar.button("🚪 Log Out", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["auth_step"] = "enter_email"
    st.rerun()

st.sidebar.markdown("---")
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
live_data_75 = fetch_url_json(SONAGAZI_LIVE_URL)

# Fetch History dataset
df_hist_all = fetch_history_data()
df_hist_filtered = apply_time_filter(df_hist_all, time_horizon)

# Tabbed Layout
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏭 Siddhirganj 335MW", 
    "🏭 Haripur 412MW", 
    "🏭 Siddhirganj 2x120MW", 
    "☀️ Sonagazi 75MW",
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

    t1_m1, t1_m2, t1_m3, t1_m4 = st.columns(4)
    t1_m1.metric(label="GT MW", value=f"{gt_mw_335:.2f} MW")
    t1_m2.metric(label="GT MVAR", value=f"{gt_mvar_335:.2f} MVAR")
    t1_m3.metric(label="ST MW", value=f"{st_mw_335:.2f} MW")
    t1_m4.metric(label="ST MVAR", value=f"{st_mvar_335:.2f} MVAR")

    t1_c1, t1_c2, t1_c3, t1_c4 = st.columns(4)
    t1_c1.metric(label="Gross MW", value=f"{gross_mw_335:.2f} MW")
    t1_c2.metric(label="Gross MVAR", value=f"{gross_mvar_335:.2f} MVAR")
    t1_c3.metric(label="GT Power Factor", value=f"{gt_pf_335:.3f}")
    t1_c4.metric(label="ST Power Factor", value=f"{st_pf_335:.3f}")

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

    t2_m1, t2_m2, t2_m3, t2_m4 = st.columns(4)
    t2_m1.metric(label="GT MW", value=f"{gt_mw_412:.2f} MW")
    t2_m2.metric(label="GT MVAR", value=f"{gt_mvar_412:.2f} MVAR")
    t2_m3.metric(label="ST MW", value=f"{st_mw_412:.2f} MW")
    t2_m4.metric(label="ST MVAR", value=f"{st_mvar_412:.2f} MVAR")

    t2_c1, t2_c2, t2_c3, t2_c4 = st.columns(4)
    t2_c1.metric(label="Gross MW", value=f"{gross_mw_412:.2f} MW")
    t2_c2.metric(label="Gross MVAR", value=f"{gross_mvar_412:.2f} MVAR")
    t2_c3.metric(label="GT Power Factor", value=f"{gt_pf_412:.3f}")
    t2_c4.metric(label="ST Power Factor", value=f"{st_pf_412:.3f}")

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

    t3_m1, t3_m2, t3_m3, t3_m4 = st.columns(4)
    t3_m1.metric(label="GT1 MW", value=f"{gt1_mw_120:.2f} MW")
    t3_m2.metric(label="GT1 MVAR", value=f"{gt1_mvar_120:.2f} MVAR")
    t3_m3.metric(label="GT2 MW", value=f"{gt2_mw_120:.2f} MW")
    t3_m4.metric(label="GT2 MVAR", value=f"{gt2_mvar_120:.2f} MVAR")

    t3_c1, t3_c2, t3_c3, t3_c4 = st.columns(4)
    t3_c1.metric(label="Gross MW", value=f"{gross_mw_120:.2f} MW")
    t3_c2.metric(label="Gross MVAR", value=f"{gross_mvar_120:.2f} MVAR")
    t3_c3.metric(label="GT1 Power Factor", value=f"{gt1_pf_120:.3f}")
    t3_c4.metric(label="GT2 Power Factor", value=f"{gt2_pf_120:.3f}")

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


# ------------------ TAB 4: Sonagazi 75MW ------------------
with tab4:
    st.subheader("Sonagazi 75MW Overview")

    total_mw_75 = float(live_data_75.get("total_mw", 0.0))
    total_mvar_75 = float(live_data_75.get("total_mvar", 0.0))
    pf_75 = float(live_data_75.get("pf", calc_pf(total_mw_75, total_mvar_75)))

    t4_c1, t4_c2, t4_c3 = st.columns(3)
    t4_c1.metric(label="Total MW", value=f"{total_mw_75:.2f} MW")
    t4_c2.metric(label="Total MVAR", value=f"{total_mvar_75:.2f} MVAR")
    t4_c3.metric(label="Power Factor", value=f"{pf_75:.3f}")

    st.markdown("---")

    st.subheader("📈 Historical Trend Analytics (Sonagazi 75MW)")
    if not df_hist_filtered.empty:
        st.line_chart(data=df_hist_filtered, x="Live Time", y="Sonagazi 75MW")
    else:
        st.info("No historical data available in Firebase yet.")

    with st.expander("📥 View & Export Sonagazi 75MW Historical CSV Data"):
        if not df_hist_filtered.empty:
            df_75_csv = df_hist_filtered[["Live Time", "Sonagazi 75MW"]]
            st.dataframe(df_75_csv, use_container_width=True)
            st.download_button(
                label="Download Sonagazi 75MW History as CSV",
                data=df_75_csv.to_csv(index=False).encode('utf-8'),
                file_name="sonagazi_75mw_generation_history.csv",
                mime="text/csv"
            )


# ------------------ TAB 5: Comparative Analytics ------------------
with tab5:
    st.subheader("📊 Cross-Plant Comparative Trend Analysis")

    total_live_mw = gross_mw_335 + gross_mw_412 + gross_mw_120 + total_mw_75
    
    t5_c1, t5_c2, t5_c3, t5_c4, t5_c5 = st.columns(5)
    t5_c1.metric(label="Total Fleet Live MW", value=f"{total_live_mw:.2f} MW")
    t5_c2.metric(label="Siddhirganj 335MW", value=f"{gross_mw_335:.1f} MW")
    t5_c3.metric(label="Haripur 412MW", value=f"{gross_mw_412:.1f} MW")
    t5_c4.metric(label="Siddhirganj 2x120MW", value=f"{gross_mw_120:.1f} MW")
    t5_c5.metric(label="Sonagazi 75MW", value=f"{total_mw_75:.1f} MW")

    st.markdown("---")

    selected_plants = st.multiselect(
        "Select Plants to Include in Trend Comparison:",
        options=["Siddhirganj 335MW", "Haripur 412MW", "Siddhirganj 2x120MW", "Sonagazi 75MW"],
        default=["Siddhirganj 335MW", "Haripur 412MW", "Siddhirganj 2x120MW", "Sonagazi 75MW"]
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

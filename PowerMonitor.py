# ------------------ TAB 4: Sonagazi 75MW ------------------
with tab4:
    st.subheader("Sonagazi 75MW Overview")

    total_mw_75 = float(live_data_75.get("total_mw", 0.0))
    total_mvar_75 = float(live_data_75.get("total_mvar", 0.0))
    pf_75 = float(live_data_75.get("pf", calc_pf(total_mw_75, total_mvar_75)))

    # Unique column variables for Tab 4
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
    
    # Unique column variables for Tab 5
    t5_c1, t5_c2, t5_c3, t5_c4, t5_c5 = st.columns(5)
    t5_c1.metric(label="Total Fleet Live MW", value=f"{total_live_mw:.2f} MW")
    t5_c2.metric(label="Siddhirganj 335MW", value=f"{gross_mw_335:.1f} MW")
    t5_c3.metric(label="Haripur 412MW", value=f"{gross_mw_412:.1f} MW")
    t5_c4.metric(label="Siddhirganj 2x120MW Share", value=f"{gross_mw_120:.1f} MW")
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

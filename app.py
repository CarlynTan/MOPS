import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from datetime import date

st.set_page_config(page_title="Taiwan & Korea Semi Monitor", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@300;400;500;600&display=swap');
        html, body, [class*="css"], [class*="st-"], .stDataFrame, .stSelectbox,
        .stMultiSelect, .stCheckbox, .stTab, button, input, textarea {
            font-family: 'Barlow Condensed', sans-serif !important;
        }
        .stTabs [data-baseweb="tab"] { font-size: 16px; }
    </style>
""", unsafe_allow_html=True)

PROJECT_REF = st.secrets["PROJECT_REF"]
DB_PASSWORD  = st.secrets["DB_PASSWORD"]

WATCHLIST = {
    "2330":"TSMC","2317":"Hon Hai","6669":"Wiwynn","3231":"Wistron",
    "3105":"Win Semicon","6488":"GlobalWafers","5483":"SAS",
    "3008":"Largan","2454":"MediaTek","2303":"UMC",
    "4938":"Pegatron","6770":"Powerchip","5347":"Vanguard Semi",
    "2382":"Quanta","2408":"Nanya Tech","2379":"Realtek",
    "3034":"Novatek","3450":"Elite Laser","3406":"Genius Optical",
    "3037":"Unimicron","3189":"Kinsus","8046":"Nanya PCB",
    "3711":"ASE Technology","6239":"Powertech","2449":"King Yuan",
}

SUBSECTORS = {
    "Silicon Materials":["6488","5483"],
    "IC Designers":["2454","2379","3034"],
    "Foundry":["2330","2303","5347","3105"],
    "Memory (IDM)":["6770","2408"],
    "OSAT (Packaging & Testing)":["3711","6239","2449"],
    "PCB Firms":["3037","3189","8046"],
    "ODM / EMS (Assembly)":["2317","6669","3231","2382","4938"],
    "Optics / Optoelectronics":["3008","3406","3450"],
}

WATCHLIST_DISPLAY = {
    "2330":"2330 TSMC 台積電","2317":"2317 Hon Hai 鴻海",
    "6669":"6669 Wiwynn 緯穎","3231":"3231 Wistron 緯創",
    "3105":"3105 Win Semicon 穩懋","6488":"6488 GlobalWafers 環球晶",
    "5483":"5483 SAS 中美晶","3008":"3008 Largan 大立光",
    "2454":"2454 MediaTek 聯發科","2303":"2303 UMC 聯電",
    "4938":"4938 Pegatron 和碩","6770":"6770 Powerchip 力積電",
    "5347":"5347 Vanguard Semi 世界先進","2382":"2382 Quanta 廣達",
    "2408":"2408 Nanya Tech 南亞科","2379":"2379 Realtek 瑞昱",
    "3034":"3034 Novatek 聯詠","3450":"3450 Elite Laser 晶睿",
    "3406":"3406 Genius Optical 玉晶光","3037":"3037 Unimicron 欣興",
    "3189":"3189 Kinsus 景碩","8046":"8046 Nanya PCB 南電",
    "3711":"3711 ASE Technology 日月光","6239":"6239 Powertech 力成",
    "2449":"2449 King Yuan 京元電子",
}

WATCHLIST_FULLNAME = {
    "2330":"2330 | TSMC | 台積電","2317":"2317 | Hon Hai | 鴻海",
    "6669":"6669 | Wiwynn | 緯穎","3231":"3231 | Wistron | 緯創",
    "3105":"3105 | Win Semicon | 穩懋","6488":"6488 | GlobalWafers | 環球晶",
    "5483":"5483 | SAS | 中美晶","3008":"3008 | Largan | 大立光",
    "2454":"2454 | MediaTek | 聯發科","2303":"2303 | UMC | 聯電",
    "4938":"4938 | Pegatron | 和碩","6770":"6770 | Powerchip | 力積電",
    "5347":"5347 | Vanguard Semi | 世界先進","2382":"2382 | Quanta | 廣達",
    "2408":"2408 | Nanya Tech | 南亞科","2379":"2379 | Realtek | 瑞昱",
    "3034":"3034 | Novatek | 聯詠","3450":"3450 | Elite Laser | 晶睿",
    "3406":"3406 | Genius Optical | 玉晶光","3037":"3037 | Unimicron | 欣興",
    "3189":"3189 | Kinsus | 景碩","8046":"8046 | Nanya PCB | 南電",
    "3711":"3711 | ASE Technology | 日月光","6239":"6239 | Powertech | 力成",
    "2449":"2449 | King Yuan | 京元電子",
}

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

BRAND_COLORS = [
    "#1D9E75","#378ADD","#E8642A","#9B59B6","#F39C12","#E74C3C",
    "#2ECC71","#3498DB","#1ABC9C","#D35400","#8E44AD","#27AE60",
]

PCT_COL_CONFIG = st.column_config.NumberColumn(format="%.1f%%")

@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql://postgres.{PROJECT_REF}:{DB_PASSWORD}"
        f"@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
    )

@st.cache_data(ttl=1)
def load_revenue():
    engine = get_engine()
    df = pd.read_sql("SELECT stock_id, report_month, rev_current, yoy_pct, mom_pct FROM monthly_revenue ORDER BY stock_id, report_month", engine)
    df["stock_id"] = df["stock_id"].astype(str)
    df = df[df["stock_id"].isin(WATCHLIST.keys())]
    df["company"]      = df["stock_id"].map(WATCHLIST)
    df["company_full"] = df["stock_id"].map(WATCHLIST_FULLNAME)
    def roc(ym):
        try:
            p = str(ym).split('_')
            return pd.Timestamp(year=int(p[0])+1911, month=int(p[1]), day=1)
        except: return pd.NaT
    df["date"] = df["report_month"].apply(roc)
    return df.dropna(subset=["date"])

@st.cache_data(ttl=1)
def load_prices():
    engine = get_engine()
    s1 = "','".join([f"{k}.TW"  for k in WATCHLIST])
    s2 = "','".join([f"{k}.TWO" for k in WATCHLIST])
    df = pd.read_sql(f"SELECT date,symbol,open,close FROM stock_prices WHERE symbol IN ('{s1}','{s2}') ORDER BY symbol,date", engine)
    df["stock_id"] = df["symbol"].str.replace(".TWO","").str.replace(".TW","")
    df["date"]  = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df.groupby(["stock_id","month"]).agg(m_open=("open","first"),m_close=("close","last")).reset_index()

@st.cache_data(ttl=1)
def load_annual():
    engine = get_engine()
    syms = "','".join([f"{k}.TW" for k in WATCHLIST]+[f"{k}.TWO" for k in WATCHLIST])
    df = pd.read_sql(f"SELECT symbol,year,year_open,year_close FROM stock_annual_k2 WHERE symbol IN ('{syms}') ORDER BY symbol,year", engine)
    df["stock_id"] = df["symbol"].str.replace(".TWO","").str.replace(".TW","")
    df["company"]  = df["stock_id"].map(WATCHLIST)
    df["annual_return"] = ((df["year_close"]-df["year_open"])/df["year_open"]*100).round(1)
    return df

@st.cache_data(ttl=1)
def load_fx():
    try:
        engine = get_engine()
        df = pd.read_sql("SELECT month,twd_per_usd FROM fx_rates ORDER BY month", engine)
        df["month"] = pd.to_datetime(df["month"])
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=1)
def load_korea():
    try:
        engine = get_engine()
        df = pd.read_sql("SELECT * FROM korea_trade ORDER BY date", engine)
        df["date"] = pd.to_datetime(df["date"])
        return df
    except: return pd.DataFrame()

rev_df    = load_revenue()
price_df  = load_prices()
annual_df = load_annual()
fx_df     = load_fx()
kr_df     = load_korea()

def get_cycle_position(company, df6m):
    rows = df6m[df6m["company"]==company].sort_values("date")
    if len(rows) < 4: return "⬜ N/A"
    curr  = rows["6M Avg YoY%"].iloc[-1]
    prev3 = rows["6M Avg YoY%"].iloc[-4:-1].mean()
    if pd.isna(curr): return "⬜ N/A"
    if curr > 15 and curr >= prev3:   return "🟢 Expansion"
    elif curr > 0  and curr >= prev3: return "🔵 Recovery"
    elif curr > 0  and curr < prev3:  return "🟡 Slowdown"
    else:                             return "🔴 Contraction"

def flag_anomalies(df, rev_col="rev_current", window=6, threshold=1.8):
    df = df.copy().sort_values(["company","date"])
    df["_roll_mean"] = df.groupby("company")[rev_col].transform(lambda x: x.rolling(window,min_periods=3).mean())
    df["_roll_std"]  = df.groupby("company")[rev_col].transform(lambda x: x.rolling(window,min_periods=3).std())
    df["_z"]         = (df[rev_col]-df["_roll_mean"]) / df["_roll_std"].replace(0,np.nan)
    df["_anom_high"] = df["_z"] >  threshold
    df["_anom_low"]  = df["_z"] < -threshold
    return df

def make_chart(df, x, y, color, labels, chart_type, colors=BRAND_COLORS):
    if chart_type == "Line":
        fig = px.line(df,x=x,y=y,color=color,labels=labels,color_discrete_sequence=colors)
        fig.update_traces(line=dict(width=2))
    elif chart_type == "Bar":
        fig = px.bar(df,x=x,y=y,color=color,barmode="group",labels=labels,color_discrete_sequence=colors)
    else:
        fig = go.Figure()
        for idx,comp in enumerate(df[color].unique()):
            c = colors[idx%len(colors)]
            sub = df[df[color]==comp]
            fig.add_trace(go.Bar(x=sub[x],y=sub[y],name=f"{comp} (bar)",marker_color=c,opacity=0.4))
            fig.add_trace(go.Scatter(x=sub[x],y=sub[y],name=f"{comp} (line)",line=dict(color=c,width=2)))
    fig.update_layout(
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
        hovermode="x unified",plot_bgcolor="white",
        yaxis=dict(gridcolor="#eeeeee"),xaxis=dict(gridcolor="#eeeeee"),
    )
    return fig

# ── Top-level selector ────────────────────────────────────────────────────────
dashboard = st.radio(
    "Select Dashboard",
    ["🇹🇼 Taiwan Semi Monitor","🇰🇷 Korea Trade Monitor"],
    horizontal=True, key="dashboard_select"
)
st.divider()

# =============================================================================
# 🇹🇼 TAIWAN
# =============================================================================
if dashboard == "🇹🇼 Taiwan Semi Monitor":

    def apply_date_filter(df, date_col="date"):
        return df[(df[date_col].dt.year.isin(selected_years))&(df[date_col].dt.month.isin(selected_months))]

    def aggregate_if_needed(df, rev_col, do_sum, label="Sector Total"):
        if not do_sum: return df
        # Sum revenue only — never sum % columns
        agg = df.groupby("date")[[rev_col]].sum().reset_index()
        agg["company"] = label
        agg["company_full"] = label
        agg["stock_id"] = "SUM"
        # Recalculate YoY and MoM from the summed revenue
        agg = agg.sort_values("date")
        agg["yoy_pct"] = agg[rev_col].pct_change(12) * 100
        agg["mom_pct"] = agg[rev_col].pct_change(1) * 100
        return agg

    def render_rev_table(base_df, rev_col, unit_label, s3a, s6a, s3y, s6y, fmt="0f"):
        tbl = flag_anomalies(base_df, rev_col)
        tbl = tbl.sort_values(["company","date"])
        tbl["3M Avg Rev"]  = tbl.groupby("company")[rev_col].transform(lambda x: x.rolling(3,min_periods=1).mean())
        tbl["6M Avg Rev"]  = tbl.groupby("company")[rev_col].transform(lambda x: x.rolling(6,min_periods=1).mean())
        tbl["3M Avg YoY%"] = tbl.groupby("company")["3M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
        tbl["6M Avg YoY%"] = tbl.groupby("company")["6M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
        tbl = apply_date_filter(tbl)
        tbl = tbl.sort_values(["company","date"],ascending=[True,False])

        # Format revenue columns as strings (not sortable numerically but that's ok for revenue)
        nf = lambda x: (f"{x:,.2f}" if fmt=="2f" else f"{x:,.0f}") if pd.notna(x) else ""
        tbl["rev_fmt"]    = tbl[rev_col].apply(nf)
        tbl["3M Avg Rev"] = tbl["3M Avg Rev"].apply(nf)
        tbl["6M Avg Rev"] = tbl["6M Avg Rev"].apply(nf)
        # Keep all % columns numeric — column_config handles display

        show = ["company_full","date","rev_fmt"]
        if s3a: show += ["3M Avg Rev"]
        if s6a: show += ["6M Avg Rev"]
        if s3y: show += ["3M Avg YoY%"]
        if s6y: show += ["6M Avg YoY%"]
        show += [c for c in ["yoy_pct","mom_pct"] if c in tbl.columns]

        out = tbl[show].copy().rename(columns={
            "company_full":"Company","date":"Sort Date",
            "rev_fmt":f"Revenue ({unit_label})",
            "yoy_pct":"YoY %","mom_pct":"MoM %",
        })

        has_anomaly = tbl["_anom_high"].any() or tbl["_anom_low"].any()

        def highlight_anomaly(row):
            idx = row.name
            styles = [""] * len(row)
            if idx in tbl.index:
                rev_col_pos = list(out.columns).index(f"Revenue ({unit_label})")
                if tbl.loc[idx,"_anom_high"]: styles[rev_col_pos] = "background-color: #d4edda"
                elif tbl.loc[idx,"_anom_low"]: styles[rev_col_pos] = "background-color: #f8d7da"
            return styles

        col_config = {
            "Sort Date":  st.column_config.DateColumn("Month", format="MMM-YYYY"),
            "YoY %":      st.column_config.NumberColumn("YoY %",      format="%.1f%%"),
            "MoM %":      st.column_config.NumberColumn("MoM %",      format="%.1f%%"),
            "3M Avg YoY%":st.column_config.NumberColumn("3M Avg YoY%",format="%.1f%%"),
            "6M Avg YoY%":st.column_config.NumberColumn("6M Avg YoY%",format="%.1f%%"),
        }

        st.dataframe(out.style.apply(highlight_anomaly,axis=1),
                     column_config=col_config, use_container_width=True)

        if has_anomaly:
            st.caption("🟩 Light green = revenue significantly above recent trend  ·  🟥 Light red = significantly below  ·  z-score > 1.8 from 6-month rolling average.")

    with st.sidebar:
        st.header("Filter")
        available_years  = sorted(rev_df["date"].dt.year.unique().tolist(),reverse=True)
        available_months = sorted(rev_df["date"].dt.month.unique().tolist())
        selected_years  = st.multiselect("Year",  options=available_years,  default=available_years,  format_func=str)
        selected_months = st.multiselect("Month", options=available_months, default=available_months, format_func=lambda x: MONTH_NAMES[x])
        if not selected_years or not selected_months:
            st.warning("Select at least one year and month."); st.stop()
        subsector = st.selectbox("Sub-sector", options=["All"]+list(SUBSECTORS.keys()))
        available = list(WATCHLIST.keys()) if subsector=="All" else SUBSECTORS[subsector]
        selected  = st.multiselect("Stocks", options=available, default=available, format_func=lambda x: WATCHLIST_DISPLAY[x])
        if not selected:
            st.warning("Select at least one stock."); st.stop()
        st.divider()
        group_sum = st.toggle("📊 Sector total (sum selected)", value=False)
        st.divider()
        latest_month = rev_df["date"].max()
        st.caption(f"📅 Data as of **{latest_month.strftime('%b %Y')}**")
        st.caption("Source: MOPS / Yahoo Finance")
        st.caption(f"Last refreshed: {date.today().strftime('%d %b %Y')}")

    st.title("Taiwan Semi Monitor")
    st.caption(f"Covering {len(WATCHLIST)} companies · Data as of {latest_month.strftime('%b %Y')} · Source: MOPS / Yahoo Finance")
    st.divider()

    tab1,tab2,tab3,tab4,tab5,tab6,tab7 = st.tabs([
        "📊 Revenue (TWD)","💵 Revenue (USD)","🔀 TWD vs USD",
        "📈 Growth Momentum","📉 3M Avg YoY","📉 6M Avg YoY",
        "🔗 Price vs Fundamentals",
    ])

    with tab1:
        st.subheader("Monthly Revenue (TWD thousands)")
        ct1 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="ct1")
        base1 = aggregate_if_needed(rev_df[rev_df["stock_id"].isin(selected)].copy(),"rev_current",group_sum)
        f1 = apply_date_filter(base1)
        if f1.empty: st.warning("No data.")
        else:
            st.plotly_chart(make_chart(f1,"date","rev_current","company",{"rev_current":"Revenue (TWD k)","date":"Month"},ct1),use_container_width=True,key="pc1")
            st.markdown("**Optional columns**")
            c1,c2,c3,c4=st.columns(4)
            s3a=c1.checkbox("3M Avg Rev",key="t1_3a"); s6a=c2.checkbox("6M Avg Rev",key="t1_6a")
            s3y=c3.checkbox("3M Avg YoY%",key="t1_3y"); s6y=c4.checkbox("6M Avg YoY%",key="t1_6y")
            render_rev_table(base1,"rev_current","TWD k",s3a,s6a,s3y,s6y)

    with tab2:
        st.subheader("Monthly Revenue (USD millions)")
        ct2 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="ct2")
        if fx_df.empty: st.error("FX data not available.")
        else:
            lf = fx_df.sort_values("month").iloc[-1]
            st.info(f"💱 Latest FX: **1 USD = {lf['twd_per_usd']:.4f} TWD** (as of {lf['month'].strftime('%b %Y')})  \n**Methodology:** Monthly TWD revenue ÷ monthly avg TWD/USD rate (Yahoo Finance: TWD=X).")
            base2 = rev_df[rev_df["stock_id"].isin(selected)].copy()
            base2 = base2.merge(fx_df.rename(columns={"month":"date"}),on="date",how="left")
            base2["rev_usd"] = base2["rev_current"]/base2["twd_per_usd"]/1000
            base2 = aggregate_if_needed(base2,"rev_usd",group_sum)
            f2 = apply_date_filter(base2)
            if f2.empty: st.warning("No data.")
            else:
                st.plotly_chart(make_chart(f2,"date","rev_usd","company",{"rev_usd":"Revenue (USD mn)","date":"Month"},ct2),use_container_width=True,key="pc2")
                st.markdown("**Optional columns**")
                c1,c2,c3,c4=st.columns(4)
                s3a=c1.checkbox("3M Avg Rev",key="t2_3a"); s6a=c2.checkbox("6M Avg Rev",key="t2_6a")
                s3y=c3.checkbox("3M Avg YoY%",key="t2_3y"); s6y=c4.checkbox("6M Avg YoY%",key="t2_6y")
                render_rev_table(base2,"rev_usd","USD mn",s3a,s6a,s3y,s6y,fmt="2f")

    with tab3:
        st.subheader("Revenue: TWD vs USD — Side by Side")
        ct3 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="ct3")
        if fx_df.empty: st.error("FX data not available.")
        else:
            base3 = rev_df[rev_df["stock_id"].isin(selected)].copy()
            base3 = base3.merge(fx_df.rename(columns={"month":"date"}),on="date",how="left")
            base3["rev_usd"] = base3["rev_current"]/base3["twd_per_usd"]/1000
            f3t = apply_date_filter(aggregate_if_needed(base3.copy(),"rev_current",group_sum))
            f3u = apply_date_filter(aggregate_if_needed(base3.copy(),"rev_usd",group_sum))
            if f3t.empty: st.warning("No data.")
            else:
                cl,cr = st.columns(2)
                with cl:
                    st.markdown("**Revenue in TWD (thousands)**")
                    st.plotly_chart(make_chart(f3t,"date","rev_current","company",{"rev_current":"TWD k","date":"Month"},ct3),use_container_width=True,key="pc3l")
                with cr:
                    st.markdown("**Revenue in USD (millions)**")
                    st.plotly_chart(make_chart(f3u,"date","rev_usd","company",{"rev_usd":"USD mn","date":"Month"},ct3),use_container_width=True,key="pc3r")

    with tab4:
        st.subheader("Year-on-Year Revenue Growth (%)")
        ct4 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="ct4")
        base4 = aggregate_if_needed(rev_df[rev_df["stock_id"].isin(selected)].dropna(subset=["yoy_pct"]).copy(),"rev_current",group_sum)
        f4 = apply_date_filter(base4)
        if f4.empty: st.warning("No data.")
        else:
            fig4 = make_chart(f4,"date","yoy_pct","company",{"yoy_pct":"YoY %","date":"Month"},ct4)
            fig4.add_hline(y=0,line_dash="dash",line_color="gray",opacity=0.5)
            st.plotly_chart(fig4,use_container_width=True,key="pc4")
            tbl4 = f4[["company_full","date","yoy_pct","mom_pct"]].copy().sort_values(["company_full","date"],ascending=[True,False])
            tbl4 = tbl4.rename(columns={"company_full":"Company","date":"Sort Date","yoy_pct":"YoY %","mom_pct":"MoM %"})
            st.dataframe(tbl4, column_config={
                "Sort Date": st.column_config.DateColumn("Month", format="MMM-YYYY"),
                "YoY %":     st.column_config.NumberColumn("YoY %", format="%.1f%%"),
                "MoM %":     st.column_config.NumberColumn("MoM %", format="%.1f%%"),
            }, use_container_width=True)

    with tab5:
        st.subheader("3-Month Average YoY Growth (%)")
        ct5 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="ct5")
        base5 = aggregate_if_needed(rev_df[rev_df["stock_id"].isin(selected)].copy(),"rev_current",group_sum)
        base5 = base5.sort_values(["company","date"])
        base5["3M Avg Rev"]  = base5.groupby("company")["rev_current"].transform(lambda x: x.rolling(3,min_periods=1).mean())
        base5["3M Avg YoY%"] = base5.groupby("company")["3M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
        f5 = apply_date_filter(base5).dropna(subset=["3M Avg YoY%"])
        if f5.empty: st.warning("No data.")
        else:
            fig5 = make_chart(f5,"date","3M Avg YoY%","company",{"3M Avg YoY%":"3M Avg YoY %","date":"Month"},ct5)
            fig5.add_hline(y=0,line_dash="dash",line_color="gray",opacity=0.5)
            st.plotly_chart(fig5,use_container_width=True,key="pc5")
            t5 = f5[["company_full","date","rev_current","3M Avg Rev","3M Avg YoY%","mom_pct"]].copy().sort_values(["company_full","date"],ascending=[True,False])
            t5["rev_current"] = t5["rev_current"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
            t5["3M Avg Rev"]  = t5["3M Avg Rev"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
            t5 = t5.rename(columns={"company_full":"Company","date":"Sort Date","rev_current":"Revenue (TWD k)","3M Avg Rev":"3M Avg Rev (TWD k)","mom_pct":"MoM %"})
            st.dataframe(t5, column_config={
                "Sort Date":          st.column_config.DateColumn("Month", format="MMM-YYYY"),
                "3M Avg YoY%":        st.column_config.NumberColumn("3M Avg YoY%", format="%.1f%%"),
                "MoM %":              st.column_config.NumberColumn("MoM %",        format="%.1f%%"),
            }, use_container_width=True)

    with tab6:
        st.subheader("6-Month Average YoY Growth (%)")
        ct6 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="ct6")
        base6 = aggregate_if_needed(rev_df[rev_df["stock_id"].isin(selected)].copy(),"rev_current",group_sum)
        base6 = base6.sort_values(["company","date"])
        base6["6M Avg Rev"]  = base6.groupby("company")["rev_current"].transform(lambda x: x.rolling(6,min_periods=1).mean())
        base6["6M Avg YoY%"] = base6.groupby("company")["6M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
        f6 = apply_date_filter(base6).dropna(subset=["6M Avg YoY%"])
        if f6.empty: st.warning("No data.")
        else:
            fig6 = make_chart(f6,"date","6M Avg YoY%","company",{"6M Avg YoY%":"6M Avg YoY %","date":"Month"},ct6)
            fig6.add_hline(y=0,line_dash="dash",line_color="gray",opacity=0.5)
            st.plotly_chart(fig6,use_container_width=True,key="pc6")
            t6 = f6[["company_full","date","rev_current","6M Avg Rev","6M Avg YoY%","mom_pct"]].copy().sort_values(["company_full","date"],ascending=[True,False])
            t6["rev_current"] = t6["rev_current"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
            t6["6M Avg Rev"]  = t6["6M Avg Rev"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
            t6 = t6.rename(columns={"company_full":"Company","date":"Sort Date","rev_current":"Revenue (TWD k)","6M Avg Rev":"6M Avg Rev (TWD k)","mom_pct":"MoM %"})
            st.dataframe(t6, column_config={
                "Sort Date":   st.column_config.DateColumn("Month", format="MMM-YYYY"),
                "6M Avg YoY%": st.column_config.NumberColumn("6M Avg YoY%", format="%.1f%%"),
                "MoM %":       st.column_config.NumberColumn("MoM %",        format="%.1f%%"),
            }, use_container_width=True)

    with tab7:
        st.subheader("Price vs Fundamentals")
        if len(selected)==1:
            sid = selected[0]
            rev = apply_date_filter(rev_df[rev_df["stock_id"]==sid][["date","yoy_pct","rev_current"]].dropna(subset=["yoy_pct"]))
            price = apply_date_filter(price_df[price_df["stock_id"]==sid][["month","m_close"]].rename(columns={"month":"date"}))
            merged = pd.merge(rev,price,on="date",how="inner").sort_values("date")
            if merged.empty: st.warning("No overlapping dates.")
            else:
                merged["price_mom_chg"] = merged["m_close"].pct_change(1)*100
                merged["price_3m_chg"]  = merged["m_close"].pct_change(3)*100
                pv = st.radio("Price return",["MoM Change","3M Change","Both"],horizontal=True,key="pv")
                max_abs = max(merged["price_mom_chg"].abs().max() if pv!="3M Change" else 0,
                              merged["price_3m_chg"].abs().max() if pv!="MoM Change" else 0)
                fig7 = go.Figure()
                fig7.add_trace(go.Bar(x=merged["date"],y=merged["yoy_pct"],name="Revenue YoY %",marker_color="#1D9E75",opacity=0.7))
                if pv in ["MoM Change","Both"]:
                    fig7.add_trace(go.Scatter(x=merged["date"],y=merged["price_mom_chg"],name="Price MoM %",line=dict(color="#378ADD",width=2.5,dash="dot"),yaxis="y2"))
                if pv in ["3M Change","Both"]:
                    fig7.add_trace(go.Scatter(x=merged["date"],y=merged["price_3m_chg"],name="Price 3M Chg %",line=dict(color="#E8642A",width=2.5),yaxis="y2"))
                fig7.update_layout(title=WATCHLIST_DISPLAY.get(sid,sid),
                    yaxis=dict(title="Revenue YoY %",gridcolor="#eeeeee",zeroline=True,zerolinecolor="#cccccc"),
                    yaxis2=dict(title="Price Return %",overlaying="y",side="right",gridcolor="#eeeeee",range=[-max_abs*1.6,max_abs*1.6],zeroline=True,zerolinecolor="#cccccc"),
                    hovermode="x unified",plot_bgcolor="white",bargap=0.2,
                    legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
                st.plotly_chart(fig7,use_container_width=True,key="pc7a")
                st.divider()
                st.markdown("**Log Scale — Revenue vs Share Price**")
                st.caption("Parallel lines = revenue and price growing at similar rates. Divergence signals re-rating or de-rating.")
                ml = merged[(merged["m_close"]>0)&(merged["rev_current"]>0)].copy()
                fig7b = go.Figure()
                fig7b.add_trace(go.Scatter(x=ml["date"],y=np.log(ml["rev_current"]),name="ln(Revenue TWD k)",line=dict(color="#1D9E75",width=2)))
                fig7b.add_trace(go.Scatter(x=ml["date"],y=np.log(ml["m_close"]),name="ln(Share Price TWD)",line=dict(color="#378ADD",width=2),yaxis="y2"))
                fig7b.update_layout(title=f"{WATCHLIST_DISPLAY.get(sid,sid)} — Log Scale",
                    yaxis=dict(title="ln(Revenue)",gridcolor="#eeeeee"),
                    yaxis2=dict(title="ln(Share Price)",overlaying="y",side="right",gridcolor="#eeeeee"),
                    hovermode="x unified",plot_bgcolor="white",
                    legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
                st.plotly_chart(fig7b,use_container_width=True,key="pc7b")
        else:
            st.info("💡 Select a **single stock** to see Revenue vs Price chart.")
            ann = annual_df[annual_df["stock_id"].isin(selected)].copy()
            ann = ann[ann["year"].astype(str).str[:4].astype(int).isin(selected_years)]
            if not ann.empty:
                fig7c = px.bar(ann,x="year",y="annual_return",color="company",barmode="group",
                               labels={"annual_return":"Annual Return %","year":"Year"},
                               title="Annual Stock Return (%)",color_discrete_sequence=BRAND_COLORS)
                fig7c.add_hline(y=0,line_dash="dash",line_color="gray",opacity=0.5)
                fig7c.update_layout(plot_bgcolor="white",yaxis=dict(gridcolor="#eeeeee"),xaxis=dict(gridcolor="#eeeeee"),
                                    legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
                st.plotly_chart(fig7c,use_container_width=True,key="pc7c")

    #with tab8:
        st.subheader("Revenue Heatmap")
        st.info("💡 Most useful when **5 or more companies** are selected.")
        hm_metric = st.radio("Metric",["Both","YoY %","Revenue (TWD mn)"],horizontal=True,key="hm_metric")
        hm_base = rev_df[rev_df["stock_id"].isin(selected)].copy()
        hm_base["rev_mn"] = hm_base["rev_current"]/1000
        hm_base = apply_date_filter(hm_base)
        n_months = len(hm_base["date"].unique()) if not hm_base.empty else 0
        show_text = n_months <= 24
        if not show_text: st.caption("ℹ️ Text labels hidden — more than 24 months selected. Hover to see values.")
        def render_heatmap(df,val_col,title,fmt_str,color_scale,key):
            pivot = df.pivot_table(index="company",columns="date",values=val_col,aggfunc="mean")
            pivot.columns = [c.strftime("%b-%y") for c in pivot.columns]
            z_text = [[fmt_str.format(v) if pd.notna(v) else "" for v in row] for row in pivot.values] if show_text else None
            fig = go.Figure(data=go.Heatmap(z=pivot.values,x=pivot.columns.tolist(),y=pivot.index.tolist(),
                colorscale=color_scale,zmid=0 if "%" in fmt_str else None,
                text=z_text,texttemplate="%{text}" if show_text else "",
                hovertemplate="Company: %{y}<br>Month: %{x}<br>Value: %{z:.1f}<extra></extra>"))
            fig.update_layout(title=title,height=max(300,len(pivot)*40+100),xaxis=dict(tickangle=-45),margin=dict(l=150,r=20,t=60,b=80))
            st.plotly_chart(fig,use_container_width=True,key=key)
        if not hm_base.empty:
            if hm_metric in ["YoY %","Both"]: render_heatmap(hm_base,"yoy_pct","YoY Revenue Growth (%)","{:.1f}%","RdYlGn","hm1")
            if hm_metric in ["Revenue (TWD mn)","Both"]: render_heatmap(hm_base,"rev_mn","Monthly Revenue (TWD millions)","{:,.1f}","Blues","hm2")

   # with tab9:
        st.subheader("Cycle Positioning")
        st.markdown("""
        ### How cycle position is determined
        **Step 1 — Compute 6M Avg YoY%:** 6-month rolling average revenue vs same period prior year.
        **Step 2 — Assess direction:** Latest reading vs average of prior 3 readings.
        **Step 3 — Assign phase**
        """)
        st.dataframe(pd.DataFrame({
            "Phase":["🟢 Expansion","🔵 Recovery","🟡 Slowdown","🔴 Contraction"],
            "Condition":["6M Avg YoY > 15% AND accelerating","6M Avg YoY > 0% AND accelerating","6M Avg YoY > 0% BUT decelerating","6M Avg YoY < 0%"],
            "Interpretation":["Strong broad-based demand","Recovery underway","Momentum fading — watch for cycle peak","Demand contraction — inventory correction likely"]
        }),use_container_width=True,hide_index=True)
        st.divider()
        cyc9 = rev_df[rev_df["stock_id"].isin(selected)].copy().sort_values(["company","date"])
        cyc9["6M Avg Rev"]  = cyc9.groupby("company")["rev_current"].transform(lambda x: x.rolling(6,min_periods=1).mean())
        cyc9["6M Avg YoY%"] = cyc9.groupby("company")["6M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
        cyc9_f = apply_date_filter(cyc9)
        if not cyc9_f.empty:
            latest9 = cyc9.groupby("company").last().reset_index()
            latest9["Cycle"] = latest9["company"].apply(lambda c: get_cycle_position(c,cyc9))
            latest9["6M Avg YoY%"] = latest9["6M Avg YoY%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
            st.markdown("### Current Positioning")
            ce,cr,cs,cc = st.columns(4)
            ce.markdown("**🟢 Expansion**"); cr.markdown("**🔵 Recovery**")
            cs.markdown("**🟡 Slowdown**"); cc.markdown("**🔴 Contraction**")
            CYCLE_COLORS = {"🟢 Expansion":"#d4edda","🔵 Recovery":"#d0e8f5","🟡 Slowdown":"#fff3cd","🔴 Contraction":"#f8d7da","⬜ N/A":"#f0f0f0"}
            for _,row in latest9.iterrows():
                pos=row["Cycle"]; color=CYCLE_COLORS.get(pos,"#f0f0f0")
                card=f"""<div style="background:{color};border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:14px;"><b>{row['company']}</b><br><span style="font-size:12px;color:#555;">6M Avg YoY: {row['6M Avg YoY%']}</span></div>"""
                if "Expansion" in pos: ce.markdown(card,unsafe_allow_html=True)
                elif "Recovery" in pos: cr.markdown(card,unsafe_allow_html=True)
                elif "Slowdown" in pos: cs.markdown(card,unsafe_allow_html=True)
                else: cc.markdown(card,unsafe_allow_html=True)
            st.divider()
            fig9 = px.line(cyc9_f,x="date",y="6M Avg YoY%",color="company",color_discrete_sequence=BRAND_COLORS)
            fig9.add_hline(y=0,line_dash="dash",line_color="#E74C3C",opacity=0.6,annotation_text="Contraction")
            fig9.add_hline(y=15,line_dash="dash",line_color="#1D9E75",opacity=0.6,annotation_text="Expansion")
            fig9.add_hrect(y0=15,y1=200,fillcolor="#1D9E75",opacity=0.04,line_width=0)
            fig9.add_hrect(y0=0,y1=15,fillcolor="#378ADD",opacity=0.04,line_width=0)
            fig9.add_hrect(y0=-200,y1=0,fillcolor="#E74C3C",opacity=0.04,line_width=0)
            fig9.update_traces(line=dict(width=2))
            fig9.update_layout(hovermode="x unified",plot_bgcolor="white",
                               yaxis=dict(gridcolor="#eeeeee",zeroline=True,zerolinecolor="#cccccc"),
                               xaxis=dict(gridcolor="#eeeeee"),
                               legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            st.plotly_chart(fig9,use_container_width=True,key="pc9")

   # with tab10:
        st.subheader("Cross-Sector Lead-Lag Analysis")
        with st.expander("📖 Methodology",expanded=False):
            st.markdown("""
            For each pair (A,B) and lag k: **corr(A(t), B(t+k))** over a rolling window.
            Peak correlation = lag where alignment is strongest. Positive lag = row leads column.
            Signal options: 6M Avg YoY% (smoothest) → 3M Avg YoY% → raw YoY% → MoM% (noisiest).
            """)
        if len(selected)<2: st.warning("Select at least 2 companies.")
        else:
            cc1,cc2,cc3 = st.columns(3)
            signal_choice = cc1.selectbox("Signal",["6M Avg YoY%","3M Avg YoY%","YoY %","MoM %"],key="ll_signal")
            max_lag = cc2.slider("Max lag (months)",3,12,6,key="ll_lag")
            roll_window = cc3.slider("Rolling window (months)",12,60,24,step=6,key="ll_win")
            ll = rev_df[rev_df["stock_id"].isin(selected)].copy().sort_values(["company","date"])
            if signal_choice=="6M Avg YoY%":
                ll["_r"]=ll.groupby("company")["rev_current"].transform(lambda x:x.rolling(6,min_periods=3).mean())
                ll["_sig"]=ll.groupby("company")["_r"].transform(lambda x:x.pct_change(12)*100)
            elif signal_choice=="3M Avg YoY%":
                ll["_r"]=ll.groupby("company")["rev_current"].transform(lambda x:x.rolling(3,min_periods=2).mean())
                ll["_sig"]=ll.groupby("company")["_r"].transform(lambda x:x.pct_change(12)*100)
            elif signal_choice=="YoY %": ll["_sig"]=ll["yoy_pct"]
            else: ll["_sig"]=ll["mom_pct"]
            ll=ll.dropna(subset=["_sig"])
            pivot_ll=ll.pivot_table(index="date",columns="company",values="_sig").sort_index()
            companies=pivot_ll.columns.tolist()
            lags=list(range(-max_lag,max_lag+1))
            cutoff=pivot_ll.index.max()-pd.DateOffset(months=roll_window)
            pivot_roll=pivot_ll[pivot_ll.index>=cutoff].copy()
            if len(pivot_roll)<6: st.warning("Not enough data.")
            else:
                n=len(companies)
                pcv=np.full((n,n),np.nan); plv=np.zeros((n,n),dtype=int)
                for i,a in enumerate(companies):
                    for j,b in enumerate(companies):
                        if i==j: pcv[i,j]=1.0; plv[i,j]=0; continue
                        br,bk=-999,0
                        for k in lags:
                            comb=pd.concat([pivot_roll[a],pivot_roll[b].shift(-k)],axis=1).dropna()
                            if len(comb)<6: continue
                            r=comb.iloc[:,0].corr(comb.iloc[:,1])
                            if pd.notna(r) and r>br: br,bk=r,k
                        pcv[i,j]=round(br,2) if br!=-999 else np.nan; plv[i,j]=bk
                pcd=pd.DataFrame(pcv,index=companies,columns=companies)
                pld=pd.DataFrame(plv,index=companies,columns=companies)
                cell_text=[[f"{pcd.iloc[i,j]:.2f}<br>({'+' if pld.iloc[i,j]>=0 else ''}{pld.iloc[i,j]}m)" for j in range(n)] for i in range(n)]
                fig_hm=go.Figure(data=go.Heatmap(z=pcd.values,x=companies,y=companies,colorscale="RdYlGn",
                    zmin=-1,zmax=1,zmid=0,text=cell_text,texttemplate="%{text}",
                    hovertemplate="Row:%{y}<br>Col:%{x}<br>Corr:%{z:.2f}<extra></extra>"))
                fig_hm.update_layout(height=max(400,n*50+120),xaxis=dict(tickangle=-45,title="Lagging →"),
                    yaxis=dict(title="Leading ↑"),margin=dict(l=150,r=20,t=40,b=120))
                st.plotly_chart(fig_hm,use_container_width=True,key="pc10_hm")
                st.markdown("### Strongest Lead-Lag Pairs")
                pairs=[]
                for i,a in enumerate(companies):
                    for j,b in enumerate(companies):
                        if i>=j: continue
                        r=pcd.iloc[i,j]; k=pld.iloc[i,j]
                        if pd.notna(r):
                            leader,lagger,lm=(a,b,k) if k>=0 else (b,a,abs(k))
                            pairs.append({"Leading":leader,"Lagging":lagger,"Lead (mths)":lm,"Peak Corr":f"{r:.2f}","Signal":"Strong" if r>0.7 else("Moderate" if r>0.4 else "Weak")})
                st.dataframe(pd.DataFrame(pairs).sort_values("Peak Corr",ascending=False).head(15),use_container_width=True,hide_index=True)
                st.divider()
                st.markdown("### Drill-Down")
                da=st.selectbox("Company A",companies,key="drill_a")
                db=st.selectbox("Company B",[c for c in companies if c!=da],key="drill_b")
                if da and db:
                    ia=companies.index(da); ib=companies.index(db)
                    rl=int(pld.iloc[ia,ib]); rc=pcd.iloc[ia,ib]
                    if rl>=0: leader,lagger,lm,ss,anc=da,db,rl,db,da
                    else: leader,lagger,lm,ss,anc=db,da,abs(rl),da,db
                    if lm==0: st.info(f"**{da}** and **{db}** move contemporaneously (corr: {rc:.2f})")
                    else:
                        st.info(f"**{leader}** leads **{lagger}** by **{lm} month(s)** · peak corr: **{rc:.2f}** · window: {roll_window}m · signal: {signal_choice}")
                        s_anc=pivot_ll[anc].rename(f"{anc} — actual")
                        s_sh=pivot_ll[ss].shift(-rl).rename(f"{lagger} — shifted +{lm}m")
                        dm=pd.concat([s_anc,s_sh],axis=1).dropna().reset_index()
                        dm=dm.melt(id_vars="date",var_name="Series",value_name=signal_choice)
                        fd=px.line(dm,x="date",y=signal_choice,color="Series",color_discrete_sequence=["#1D9E75","#378ADD"],
                                   title=f"{leader} vs {lagger} (shifted +{lm}m)")
                        fd.add_hline(y=0,line_dash="dash",line_color="gray",opacity=0.4)
                        fd.update_traces(line=dict(width=2))
                        fd.update_layout(hovermode="x unified",plot_bgcolor="white",
                                         yaxis=dict(gridcolor="#eeeeee"),xaxis=dict(gridcolor="#eeeeee"),
                                         legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
                        st.plotly_chart(fd,use_container_width=True,key="pc10_drill")

# =============================================================================
# 🇰🇷 KOREA
# =============================================================================
else:
    with st.sidebar:
        st.header("Filter")
        if not kr_df.empty:
            kr_years  = sorted(kr_df["date"].dt.year.unique().tolist(),reverse=True)
            kr_months = sorted(kr_df["date"].dt.month.unique().tolist())
            kr_sel_years  = st.multiselect("Year",  options=kr_years,  default=kr_years,  format_func=str,key="kr_y")
            kr_sel_months = st.multiselect("Month", options=kr_months, default=kr_months, format_func=lambda x: MONTH_NAMES[x],key="kr_m")
            if not kr_sel_years or not kr_sel_months:
                st.warning("Select at least one year and month."); st.stop()
        st.divider()
        latest_kr = kr_df["date"].max() if not kr_df.empty else None
        if latest_kr: st.caption(f"📅 Data as of **{latest_kr.strftime('%d %b %Y')}**")
        st.caption("Source: MOTIE / Korea Customs")
        st.caption(f"Last refreshed: {date.today().strftime('%d %b %Y')}")

    if kr_df.empty:
        st.title("Korea Trade Monitor · Semiconductor")
        st.warning("No Korea trade data available. Run the upload cell in Colab first.")
        st.stop()

    def kr_date_filter(df):
        return df[(df["date"].dt.year.isin(kr_sel_years))&(df["date"].dt.month.isin(kr_sel_months))]

    def get_latest_val(row, cols):
        for col in cols:
            v = row.get(col)
            if pd.notna(v) and (v or 0) > 0:
                return v, col
        return None, None

    CHECKPOINT_LABEL = {
        "exp_semi":         "Full month",
        "exp_25d_semi":     "25-day",
        "exp_20d_semi":     "20-day",
        "exp_10d_semi":     "10-day",
        "imp_20d_semi":     "20-day",
        "imp_10d_semi":     "10-day",
        "imp_20d_sme":      "20-day",
        "imp_10d_sme":      "10-day",
        "exp_20d_semi_yoy": "20-day YoY",
        "exp_10d_semi_yoy": "10-day YoY",
        "imp_20d_semi_yoy": "20-day YoY",
        "imp_10d_semi_yoy": "10-day YoY",
        "imp_20d_sme_yoy":  "20-day YoY",
        "imp_10d_sme_yoy":  "10-day YoY",
    }

    latest_date = kr_df["date"].max()
    latest_row  = kr_df[kr_df["date"]==latest_date].iloc[0]

    # ── Monitor period selector ───────────────────────────────────────────────
    st.markdown("""
        <style>
        .kr-header { font-size: 28px; font-weight: 600; margin-bottom: 2px; }
        .kr-sub { font-size: 14px; color: #666; margin-bottom: 16px; }
        .kr-card {
            background: white;
            border-radius: 12px;
            border: 1px solid #e8e8e8;
            padding: 18px 20px;
            margin-bottom: 4px;
        }
        .kr-card-label { font-size: 12px; color: #888; margin-bottom: 4px; }
        .kr-card-value { font-size: 26px; font-weight: 600; color: #1a1a1a; }
        .kr-card-yoy { font-size: 18px; font-weight: 600; margin-top: 6px; }
        .kr-card-sub { font-size: 12px; color: #aaa; margin-top: 4px; }
        .kr-up   { color: #1D9E75; }
        .kr-down { color: #E74C3C; }
        .kr-flat { color: #888; }
        .kr-badge { display:inline-block; font-size:11px; padding:2px 8px; border-radius:10px; background:#f0f0f0; color:#555; margin-left:6px; }
        .kr-badge-est  { background:#fff3cd; color:#856404; }
        .kr-badge-full { background:#d4edda; color:#155724; }
        .kr-divider { border-top:1px solid #eeeeee; margin:16px 0; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="kr-header">🇰🇷 Korea Semiconductor Trade Monitor</div>', unsafe_allow_html=True)

    # Monitor period controls
    mc1, mc2, mc3 = st.columns([1,1,2])
    with mc1:
        monitor_mode = st.radio(
            "Monitor view",
            ["Latest", "Select period"],
            horizontal=False, key="kr_monitor_mode"
        )
    with mc2:
        if monitor_mode == "Select period":
            all_dates = sorted(kr_df["date"].unique().tolist(), reverse=True)
            sel_date  = st.selectbox(
                "Month",
                options=all_dates,
                format_func=lambda d: pd.Timestamp(d).strftime("%b %Y"),
                key="kr_sel_date"
            )
            monitor_checkpoint = st.radio(
                "Checkpoint",
                ["10-day","20-day","Full month"],
                horizontal=False, key="kr_mon_cp"
            )
        else:
            sel_date = latest_date
            monitor_checkpoint = None

    # Get monitor row
    monitor_date = pd.Timestamp(sel_date) if monitor_mode == "Select period" else latest_date
    mon_rows = kr_df[kr_df["date"]==monitor_date]
    if mon_rows.empty:
        st.warning(f"No data for {monitor_date.strftime('%b %Y')}.")
        st.stop()
    mon_row = mon_rows.iloc[0]

    # Determine which columns to use based on checkpoint selection
    if monitor_mode == "Latest":
        exp_val, exp_col = get_latest_val(mon_row, ["exp_semi","exp_25d_semi","exp_20d_semi","exp_10d_semi"])
        exp_yoy, _       = get_latest_val(mon_row, ["exp_20d_semi_yoy","exp_10d_semi_yoy"])
        imp_val, imp_col = get_latest_val(mon_row, ["imp_20d_semi","imp_10d_semi"])
        imp_yoy, _       = get_latest_val(mon_row, ["imp_20d_semi_yoy","imp_10d_semi_yoy"])
        sme_val, sme_col = get_latest_val(mon_row, ["imp_20d_sme","imp_10d_sme"])
        sme_yoy, _       = get_latest_val(mon_row, ["imp_20d_sme_yoy","imp_10d_sme_yoy"])
    elif monitor_checkpoint == "10-day":
        exp_val, exp_col = mon_row.get("exp_10d_semi"), "exp_10d_semi"
        exp_yoy          = mon_row.get("exp_10d_semi_yoy")
        imp_val, imp_col = mon_row.get("imp_10d_semi"), "imp_10d_semi"
        imp_yoy          = mon_row.get("imp_10d_semi_yoy")
        sme_val, sme_col = mon_row.get("imp_10d_sme"), "imp_10d_sme"
        sme_yoy          = mon_row.get("imp_10d_sme_yoy")
    elif monitor_checkpoint == "20-day":
        exp_val, exp_col = mon_row.get("exp_20d_semi"), "exp_20d_semi"
        exp_yoy          = mon_row.get("exp_20d_semi_yoy")
        imp_val, imp_col = mon_row.get("imp_20d_semi"), "imp_20d_semi"
        imp_yoy          = mon_row.get("imp_20d_semi_yoy")
        sme_val, sme_col = mon_row.get("imp_20d_sme"), "imp_20d_sme"
        sme_yoy          = mon_row.get("imp_20d_sme_yoy")
    else:  # Full month
        exp_val, exp_col = mon_row.get("exp_semi"), "exp_semi"
        exp_yoy          = None
        imp_val, imp_col = mon_row.get("imp_20d_semi"), "imp_20d_semi"
        imp_yoy          = mon_row.get("imp_20d_semi_yoy")
        sme_val, sme_col = mon_row.get("imp_20d_sme"), "imp_20d_sme"
        sme_yoy          = mon_row.get("imp_20d_sme_yoy")

    exp_label = CHECKPOINT_LABEL.get(exp_col, "—") if exp_col else "—"
    imp_label = CHECKPOINT_LABEL.get(imp_col, "—") if imp_col else "—"
    sme_label = CHECKPOINT_LABEL.get(sme_col, "—") if sme_col else "—"
    is_full   = exp_col == "exp_semi"

    st.markdown(
        f'<div class="kr-sub">Last updated: <b>{monitor_date.strftime("%d %b %Y")}</b> · '
        f'Source: MOTIE / Korea Customs</div>',
        unsafe_allow_html=True
    )

    # ── Headline cards ────────────────────────────────────────────────────────
    def fmt_val(v):
        if not v or pd.isna(v): return "—"
        return f"USD {v/1000:.1f}bn" if v >= 1000 else f"USD {v:.0f}mn"

    def fmt_yoy_card(v):
        if v is None or pd.isna(v): return '<span class="kr-flat">YoY: —</span>'
        arrow = "▲" if v >= 0 else "▼"
        cls   = "kr-up" if v >= 0 else "kr-down"
        sign  = "+" if v >= 0 else ""
        return f'<span class="{cls}">{arrow} {sign}{v:.1f}% YoY</span>'

    def badge(label, full=False):
        cls = "kr-badge-full" if full else "kr-badge-est"
        return f'<span class="kr-badge {cls}">{label}</span>'

    c1,c2,c3,c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="kr-card">
            <div class="kr-card-label">Semiconductor Exports {badge(exp_label, is_full)}</div>
            <div class="kr-card-value">{fmt_val(exp_val)}</div>
            <div class="kr-card-yoy">{fmt_yoy_card(exp_yoy)}</div>
            <div class="kr-card-sub">{monitor_date.strftime('%b %Y')}</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="kr-card">
            <div class="kr-card-label">Semiconductor Imports {badge(imp_label)}</div>
            <div class="kr-card-value">{fmt_val(imp_val)}</div>
            <div class="kr-card-yoy">{fmt_yoy_card(imp_yoy)}</div>
            <div class="kr-card-sub">{monitor_date.strftime('%b %Y')}</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="kr-card">
            <div class="kr-card-label">SME Imports {badge(sme_label)}</div>
            <div class="kr-card-value">{fmt_val(sme_val)}</div>
            <div class="kr-card-yoy">{fmt_yoy_card(sme_yoy)}</div>
            <div class="kr-card-sub">{monitor_date.strftime('%b %Y')}</div>
        </div>""", unsafe_allow_html=True)

    with c4:
        e20 = mon_row.get("exp_20d_semi") or mon_row.get("exp_10d_semi")
        i20 = mon_row.get("imp_20d_semi") or mon_row.get("imp_10d_semi")
        bal = (e20 - i20) if (e20 and i20 and pd.notna(e20) and pd.notna(i20)) else None
        bal_color = "#1D9E75" if (bal or 0) >= 0 else "#E74C3C"
        bal_str   = f'<span style="color:{bal_color};font-size:26px;font-weight:600;">{fmt_val(abs(bal)) if bal else "—"}</span>'
        bal_sign  = "Surplus" if (bal or 0) >= 0 else "Deficit"
        st.markdown(f"""
        <div class="kr-card">
            <div class="kr-card-label">Trade Balance (Exp − Imp)</div>
            {bal_str}
            <div class="kr-card-yoy"><span style="color:{bal_color};">{bal_sign}</span></div>
            <div class="kr-card-sub">Interim basis · {monitor_date.strftime('%b %Y')}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="kr-divider"></div>', unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    kr_tab1, kr_tab2, kr_tab3 = st.tabs([
        "📤 Semiconductor Exports",
        "📥 Imports & Equipment",
        "🌏 China Exposure"
    ])

    # ── Tab 1: Exports ────────────────────────────────────────────────────────
    with kr_tab1:
        st.subheader("Semiconductor Exports (USD millions)")

        period_opt = st.radio(
            "Data to display",
            ["Full month (where available)", "20-day checkpoint", "10-day checkpoint"],
            horizontal=True, key="kr_exp_period"
        )
        if period_opt == "Full month (where available)":
            val_col = "exp_semi"; yoy_src = None
        elif period_opt == "20-day checkpoint":
            val_col = "exp_20d_semi"; yoy_src = "exp_20d_semi_yoy"
        else:
            val_col = "exp_10d_semi"; yoy_src = "exp_10d_semi_yoy"

        exp_ts = kr_df[["date",val_col]].dropna(subset=[val_col]).copy()
        exp_ts = exp_ts[exp_ts[val_col]>0].sort_values("date")

        if exp_ts.empty:
            st.warning("No data for selected period.")
        else:
            exp_ts["prior_year"] = exp_ts[val_col].shift(12)
            exp_ts["is_est"]     = exp_ts["date"]==latest_date
            exp_f = kr_date_filter(exp_ts)

            kr_ct1 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="kr_ct1")
            fig_e  = go.Figure()
            conf_e = exp_f[~exp_f["is_est"]]; est_e = exp_f[exp_f["is_est"]]

            if kr_ct1 in ["Bar","Both"]:
                fig_e.add_trace(go.Bar(x=conf_e["date"],y=conf_e[val_col],name="Exports",marker_color="#1D9E75",opacity=0.7))
                if not est_e.empty:
                    fig_e.add_trace(go.Bar(x=est_e["date"],y=est_e[val_col],name="Est.",marker_color="#9B59B6",opacity=0.7))
            if kr_ct1 in ["Line","Both"]:
                fig_e.add_trace(go.Scatter(x=conf_e["date"],y=conf_e[val_col],name="Exports",line=dict(color="#1D9E75",width=2)))
                if not est_e.empty:
                    fig_e.add_trace(go.Scatter(x=est_e["date"],y=est_e[val_col],mode="markers",
                        marker=dict(symbol="diamond",size=10,color="#9B59B6"),name=f"Est. {latest_date.strftime('%b %Y')}"))
            prior_e = exp_f.dropna(subset=["prior_year"])
            if not prior_e.empty:
                fig_e.add_trace(go.Scatter(x=prior_e["date"],y=prior_e["prior_year"],
                    name="Prior year",line=dict(color="#1D9E75",width=1.5,dash="dot"),opacity=0.5))
            fig_e.update_layout(hovermode="x unified",plot_bgcolor="white",
                yaxis=dict(title="USD mn",gridcolor="#eeeeee"),xaxis=dict(gridcolor="#eeeeee"),
                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            st.plotly_chart(fig_e,use_container_width=True,key="kr_exp_main")

            # YoY chart
            if yoy_src:
                yoy_f = kr_date_filter(kr_df[["date",yoy_src]].dropna(subset=[yoy_src]).copy())
                if not yoy_f.empty:
                    cy = ["#1D9E75" if (v or 0)>=0 else "#E74C3C" for v in yoy_f[yoy_src]]
                    fig_ey = go.Figure()
                    fig_ey.add_trace(go.Bar(x=yoy_f["date"],y=yoy_f[yoy_src],marker_color=cy,opacity=0.8,name="YoY %"))
                    fig_ey.add_hline(y=0,line_dash="dash",line_color="gray",opacity=0.5)
                    fig_ey.update_layout(title=f"Export YoY % ({period_opt})",hovermode="x unified",plot_bgcolor="white",
                        yaxis=dict(title="YoY %",gridcolor="#eeeeee",zeroline=True,zerolinecolor="#cccccc"),xaxis=dict(gridcolor="#eeeeee"))
                    st.plotly_chart(fig_ey,use_container_width=True,key="kr_exp_yoy")
            else:
                exp_full = kr_df[["date","exp_semi"]].dropna(subset=["exp_semi"]).copy()
                exp_full = exp_full[exp_full["exp_semi"]>0].sort_values("date")
                exp_full["yoy"] = exp_full["exp_semi"].pct_change(12)*100
                exp_full = kr_date_filter(exp_full).dropna(subset=["yoy"])
                if not exp_full.empty:
                    cy2 = ["#1D9E75" if (v or 0)>=0 else "#E74C3C" for v in exp_full["yoy"]]
                    fig_ey2 = go.Figure()
                    fig_ey2.add_trace(go.Bar(x=exp_full["date"],y=exp_full["yoy"],marker_color=cy2,opacity=0.8,name="YoY %"))
                    fig_ey2.add_hline(y=0,line_dash="dash",line_color="gray",opacity=0.5)
                    fig_ey2.update_layout(title="Export YoY % (full month)",hovermode="x unified",plot_bgcolor="white",
                        yaxis=dict(title="YoY %",gridcolor="#eeeeee",zeroline=True,zerolinecolor="#cccccc"),xaxis=dict(gridcolor="#eeeeee"))
                    st.plotly_chart(fig_ey2,use_container_width=True,key="kr_exp_yoy2")

            st.markdown("**Data Table**")
            tbl_e = kr_date_filter(kr_df[["date","exp_semi","exp_10d_semi","exp_10d_semi_yoy",
                                            "exp_20d_semi","exp_20d_semi_yoy","exp_25d_semi"]].copy()).sort_values("date",ascending=False)
            tbl_e["status"] = tbl_e["date"].apply(lambda d: "⚠️ Est." if d==latest_date and not is_full else ("✅" if d==latest_date else ""))
            for col in ["exp_semi","exp_10d_semi","exp_20d_semi","exp_25d_semi"]:
                tbl_e[col] = tbl_e[col].apply(lambda x: f"{x:,.1f}" if pd.notna(x) else "—")
            st.dataframe(tbl_e.rename(columns={"date":"Month","status":"Status","exp_semi":"Full Month",
                "exp_10d_semi":"10-Day","exp_10d_semi_yoy":"10D YoY%","exp_20d_semi":"20-Day",
                "exp_20d_semi_yoy":"20D YoY%","exp_25d_semi":"25-Day"}),
                column_config={
                    "Month":    st.column_config.DateColumn("Month",format="MMM-YYYY"),
                    "10D YoY%": st.column_config.NumberColumn(format="%.1f%%"),
                    "20D YoY%": st.column_config.NumberColumn(format="%.1f%%"),
                }, use_container_width=True)
            st.caption(f"All values USD millions · Last updated: {latest_date.strftime('%d %b %Y')}")

    # ── Tab 2: Imports & Equipment ────────────────────────────────────────────
    with kr_tab2:
        st.subheader("Semiconductor Imports & Equipment (USD millions)")
        st.caption("SME = Semiconductor Manufacturing Equipment. Rising SME imports signal capacity expansion 6-12 months ahead.")

        period_opt2 = st.radio("Data to display",["20-day checkpoint","10-day checkpoint"],horizontal=True,key="kr_imp_period")
        if period_opt2 == "20-day checkpoint":
            imp_vc="imp_20d_semi"; imp_yc="imp_20d_semi_yoy"; sme_vc="imp_20d_sme"; sme_yc="imp_20d_sme_yoy"
        else:
            imp_vc="imp_10d_semi"; imp_yc="imp_10d_semi_yoy"; sme_vc="imp_10d_sme"; sme_yc="imp_10d_sme_yoy"

        st.markdown("### Semiconductor Imports")
        imp_ts = kr_df[["date",imp_vc]].dropna(subset=[imp_vc]).copy()
        imp_ts = imp_ts[imp_ts[imp_vc]>0].sort_values("date")
        imp_ts["prior_year"] = imp_ts[imp_vc].shift(12)
        imp_ts["is_est"]     = imp_ts["date"]==latest_date
        imp_f = kr_date_filter(imp_ts)

        if not imp_f.empty:
            kr_ct2 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="kr_ct2")
            fig_i  = go.Figure()
            conf_i = imp_f[~imp_f["is_est"]]; est_i = imp_f[imp_f["is_est"]]
            if kr_ct2 in ["Bar","Both"]:
                fig_i.add_trace(go.Bar(x=conf_i["date"],y=conf_i[imp_vc],name="Semi Imports",marker_color="#378ADD",opacity=0.7))
                if not est_i.empty:
                    fig_i.add_trace(go.Bar(x=est_i["date"],y=est_i[imp_vc],name="Est.",marker_color="#9B59B6",opacity=0.7))
            if kr_ct2 in ["Line","Both"]:
                fig_i.add_trace(go.Scatter(x=conf_i["date"],y=conf_i[imp_vc],name="Semi Imports",line=dict(color="#378ADD",width=2)))
                if not est_i.empty:
                    fig_i.add_trace(go.Scatter(x=est_i["date"],y=est_i[imp_vc],mode="markers",
                        marker=dict(symbol="diamond",size=10,color="#9B59B6"),name=f"Est. {latest_date.strftime('%b %Y')}"))
            prior_i = imp_f.dropna(subset=["prior_year"])
            if not prior_i.empty:
                fig_i.add_trace(go.Scatter(x=prior_i["date"],y=prior_i["prior_year"],
                    name="Prior year",line=dict(color="#378ADD",width=1.5,dash="dot"),opacity=0.5))
            fig_i.update_layout(hovermode="x unified",plot_bgcolor="white",
                yaxis=dict(title="USD mn",gridcolor="#eeeeee"),xaxis=dict(gridcolor="#eeeeee"),
                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            st.plotly_chart(fig_i,use_container_width=True,key="kr_imp_main")

            iy_f = kr_date_filter(kr_df[["date",imp_yc]].dropna(subset=[imp_yc]).copy())
            if not iy_f.empty:
                ci = ["#1D9E75" if (v or 0)>=0 else "#E74C3C" for v in iy_f[imp_yc]]
                fig_iy = go.Figure()
                fig_iy.add_trace(go.Bar(x=iy_f["date"],y=iy_f[imp_yc],marker_color=ci,opacity=0.8,name="YoY %"))
                fig_iy.add_hline(y=0,line_dash="dash",line_color="gray",opacity=0.5)
                fig_iy.update_layout(title="Semi Import YoY %",hovermode="x unified",plot_bgcolor="white",
                    yaxis=dict(title="YoY %",gridcolor="#eeeeee",zeroline=True,zerolinecolor="#cccccc"),xaxis=dict(gridcolor="#eeeeee"))
                st.plotly_chart(fig_iy,use_container_width=True,key="kr_imp_yoy")

        st.divider()
        st.markdown("### Equipment (SME) Imports")
        sme_ts = kr_df[["date",sme_vc]].dropna(subset=[sme_vc]).copy()
        sme_ts = sme_ts[sme_ts[sme_vc]>0].sort_values("date")
        sme_ts["prior_year"] = sme_ts[sme_vc].shift(12)
        sme_ts["is_est"]     = sme_ts["date"]==latest_date
        sme_f = kr_date_filter(sme_ts)

        if not sme_f.empty:
            fig_s  = go.Figure()
            conf_s = sme_f[~sme_f["is_est"]]; est_s = sme_f[sme_f["is_est"]]
            fig_s.add_trace(go.Bar(x=conf_s["date"],y=conf_s[sme_vc],name="SME Imports",marker_color="#E8642A",opacity=0.7))
            if not est_s.empty:
                fig_s.add_trace(go.Bar(x=est_s["date"],y=est_s[sme_vc],name="Est.",marker_color="#9B59B6",opacity=0.7))
            prior_s = sme_f.dropna(subset=["prior_year"])
            if not prior_s.empty:
                fig_s.add_trace(go.Scatter(x=prior_s["date"],y=prior_s["prior_year"],
                    name="Prior year",line=dict(color="#E8642A",width=1.5,dash="dot"),opacity=0.5))
            fig_s.update_layout(hovermode="x unified",plot_bgcolor="white",
                yaxis=dict(title="USD mn",gridcolor="#eeeeee"),xaxis=dict(gridcolor="#eeeeee"),
                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            st.plotly_chart(fig_s,use_container_width=True,key="kr_sme_main")

            sy_f = kr_date_filter(kr_df[["date",sme_yc]].dropna(subset=[sme_yc]).copy())
            if not sy_f.empty:
                cs = ["#1D9E75" if (v or 0)>=0 else "#E74C3C" for v in sy_f[sme_yc]]
                fig_sy = go.Figure()
                fig_sy.add_trace(go.Bar(x=sy_f["date"],y=sy_f[sme_yc],marker_color=cs,opacity=0.8,name="YoY %"))
                fig_sy.add_hline(y=0,line_dash="dash",line_color="gray",opacity=0.5)
                fig_sy.update_layout(title="SME Import YoY %",hovermode="x unified",plot_bgcolor="white",
                    yaxis=dict(title="YoY %",gridcolor="#eeeeee",zeroline=True,zerolinecolor="#cccccc"),xaxis=dict(gridcolor="#eeeeee"))
                st.plotly_chart(fig_sy,use_container_width=True,key="kr_sme_yoy")

        st.divider()
        st.markdown("### Semi Imports vs SME — Dual Axis")
        st.caption("SME rising while semi imports flat = capacity build without demand pull. Both rising = full expansion.")
        dual = kr_date_filter(kr_df[["date",imp_vc,sme_vc]].dropna(subset=[imp_vc,sme_vc]).copy())
        if not dual.empty:
            dual["is_est"] = dual["date"]==latest_date
            fig_d = go.Figure()
            fig_d.add_trace(go.Scatter(x=dual["date"],y=dual[imp_vc],name="Semi Imports",line=dict(color="#378ADD",width=2)))
            fig_d.add_trace(go.Scatter(x=dual["date"],y=dual[sme_vc],name="SME Imports",line=dict(color="#E8642A",width=2),yaxis="y2"))
            est_d = dual[dual["is_est"]]
            if not est_d.empty:
                fig_d.add_trace(go.Scatter(x=est_d["date"],y=est_d[imp_vc],mode="markers",
                    marker=dict(symbol="diamond",size=10,color="#378ADD"),name="Est. Semi"))
                fig_d.add_trace(go.Scatter(x=est_d["date"],y=est_d[sme_vc],mode="markers",
                    marker=dict(symbol="diamond",size=10,color="#E8642A"),name="Est. SME",yaxis="y2"))
            fig_d.update_layout(
                yaxis=dict(title="Semi Imports (USD mn)",gridcolor="#eeeeee"),
                yaxis2=dict(title="SME Imports (USD mn)",overlaying="y",side="right",gridcolor="#eeeeee"),
                hovermode="x unified",plot_bgcolor="white",
                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            st.plotly_chart(fig_d,use_container_width=True,key="kr_dual")

        st.markdown("**Data Table**")
        tbl_i = kr_date_filter(kr_df[["date","imp_10d_semi","imp_10d_sme","imp_10d_semi_yoy","imp_10d_sme_yoy",
                                        "imp_20d_semi","imp_20d_sme","imp_20d_semi_yoy","imp_20d_sme_yoy"]].copy()).sort_values("date",ascending=False)
        for col in ["imp_10d_semi","imp_10d_sme","imp_20d_semi","imp_20d_sme"]:
            tbl_i[col] = tbl_i[col].apply(lambda x: f"{x:,.1f}" if pd.notna(x) else "—")
        st.dataframe(tbl_i.rename(columns={"date":"Month","imp_10d_semi":"10D Semi","imp_10d_sme":"10D SME",
            "imp_10d_semi_yoy":"10D Semi YoY%","imp_10d_sme_yoy":"10D SME YoY%",
            "imp_20d_semi":"20D Semi","imp_20d_sme":"20D SME",
            "imp_20d_semi_yoy":"20D Semi YoY%","imp_20d_sme_yoy":"20D SME YoY%"}),
            column_config={
                "Month":          st.column_config.DateColumn("Month",format="MMM-YYYY"),
                "10D Semi YoY%":  st.column_config.NumberColumn(format="%.1f%%"),
                "10D SME YoY%":   st.column_config.NumberColumn(format="%.1f%%"),
                "20D Semi YoY%":  st.column_config.NumberColumn(format="%.1f%%"),
                "20D SME YoY%":   st.column_config.NumberColumn(format="%.1f%%"),
            }, use_container_width=True)
        st.caption(f"All values USD millions · SME = Semiconductor Manufacturing Equipment · Last updated: {latest_date.strftime('%d %b %Y')}")

    # ── Tab 3: China Exposure ─────────────────────────────────────────────────
    with kr_tab3:
        st.subheader("China Exposure (USD millions)")
        st.caption("China share = China-bound exports as % of total interim exports. Declining share may signal trade diversion.")

        period_opt3 = st.radio("Checkpoint",["20-day","10-day"],horizontal=True,key="kr_china_period")
        if period_opt3 == "20-day":
            e_tot="exp_20d_semi"; e_cn="exp_20d_china"; i_tot="imp_20d_semi"; i_cn="imp_20d_china"
        else:
            e_tot="exp_10d_semi"; e_cn="exp_10d_china"; i_tot="imp_10d_semi"; i_cn="imp_10d_china"

        st.markdown("### Export Destination: China vs Non-China")
        china_e = kr_df[["date",e_tot,e_cn]].dropna(subset=[e_tot,e_cn]).copy()
        china_e = china_e[(china_e[e_tot]>0)&(china_e[e_cn]>0)].sort_values("date")
        china_e["china_share"] = china_e[e_cn]/china_e[e_tot]*100
        china_e["non_china"]   = china_e[e_tot]-china_e[e_cn]
        china_ef = kr_date_filter(china_e)

        if not china_ef.empty:
            fig_ce = go.Figure()
            fig_ce.add_trace(go.Bar(x=china_ef["date"],y=china_ef[e_cn],name="China",marker_color="#E74C3C",opacity=0.8))
            fig_ce.add_trace(go.Bar(x=china_ef["date"],y=china_ef["non_china"],name="Non-China",marker_color="#378ADD",opacity=0.8))
            fig_ce.update_layout(barmode="stack",hovermode="x unified",plot_bgcolor="white",
                yaxis=dict(title="USD mn",gridcolor="#eeeeee"),xaxis=dict(gridcolor="#eeeeee"),
                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            st.plotly_chart(fig_ce,use_container_width=True,key="kr_china_stack")

            fig_cs = go.Figure()
            fig_cs.add_trace(go.Scatter(x=china_ef["date"],y=china_ef["china_share"],
                name="China share %",line=dict(color="#E74C3C",width=2),
                fill="tozeroy",fillcolor="rgba(231,76,60,0.08)"))
            fig_cs.update_layout(title="China's Share of Semiconductor Exports (%)",
                hovermode="x unified",plot_bgcolor="white",
                yaxis=dict(title="%",gridcolor="#eeeeee",range=[0,100]),xaxis=dict(gridcolor="#eeeeee"))
            st.plotly_chart(fig_cs,use_container_width=True,key="kr_china_share")
        else:
            st.warning("No China export data available for selected period.")

        st.divider()
        st.markdown("### Import Origin: China vs Non-China")
        china_i = kr_df[["date",i_tot,i_cn]].dropna(subset=[i_tot,i_cn]).copy()
        china_i = china_i[(china_i[i_tot]>0)&(china_i[i_cn]>0)].sort_values("date")
        china_i["non_china"]   = china_i[i_tot]-china_i[i_cn]
        china_i["china_share"] = china_i[i_cn]/china_i[i_tot]*100
        china_if = kr_date_filter(china_i)

        if not china_if.empty:
            fig_ci = go.Figure()
            fig_ci.add_trace(go.Bar(x=china_if["date"],y=china_if[i_cn],name="China",marker_color="#E74C3C",opacity=0.8))
            fig_ci.add_trace(go.Bar(x=china_if["date"],y=china_if["non_china"],name="Non-China",marker_color="#378ADD",opacity=0.8))
            fig_ci.update_layout(barmode="stack",hovermode="x unified",plot_bgcolor="white",
                yaxis=dict(title="USD mn",gridcolor="#eeeeee"),xaxis=dict(gridcolor="#eeeeee"),
                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            st.plotly_chart(fig_ci,use_container_width=True,key="kr_china_imp_stack")

            fig_cis = go.Figure()
            fig_cis.add_trace(go.Scatter(x=china_if["date"],y=china_if["china_share"],
                name="China share %",line=dict(color="#9B59B6",width=2),
                fill="tozeroy",fillcolor="rgba(155,89,182,0.08)"))
            fig_cis.update_layout(title="China's Share of Semiconductor Imports (%)",
                hovermode="x unified",plot_bgcolor="white",
                yaxis=dict(title="%",gridcolor="#eeeeee",range=[0,100]),xaxis=dict(gridcolor="#eeeeee"))
            st.plotly_chart(fig_cis,use_container_width=True,key="kr_china_imp_share")
        else:
            st.warning("No China import data available for selected period.")

        st.caption(f"All values USD millions · Last updated: {latest_date.strftime('%d %b %Y')}")

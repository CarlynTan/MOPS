import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from datetime import date

st.set_page_config(page_title="Taiwan Semi Monitor", layout="wide")

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

@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql://postgres.{PROJECT_REF}:{DB_PASSWORD}"
        f"@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
    )

@st.cache_data(ttl=3600)
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

@st.cache_data(ttl=3600)
def load_prices():
    engine = get_engine()
    s1 = "','".join([f"{k}.TW"  for k in WATCHLIST])
    s2 = "','".join([f"{k}.TWO" for k in WATCHLIST])
    df = pd.read_sql(f"SELECT date,symbol,open,close FROM stock_prices WHERE symbol IN ('{s1}','{s2}') ORDER BY symbol,date", engine)
    df["stock_id"] = df["symbol"].str.replace(".TWO","").str.replace(".TW","")
    df["date"]  = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df.groupby(["stock_id","month"]).agg(m_open=("open","first"),m_close=("close","last")).reset_index()

@st.cache_data(ttl=3600)
def load_annual():
    engine = get_engine()
    syms = "','".join([f"{k}.TW" for k in WATCHLIST]+[f"{k}.TWO" for k in WATCHLIST])
    df = pd.read_sql(f"SELECT symbol,year,year_open,year_close FROM stock_annual_k2 WHERE symbol IN ('{syms}') ORDER BY symbol,year", engine)
    df["stock_id"] = df["symbol"].str.replace(".TWO","").str.replace(".TW","")
    df["company"]  = df["stock_id"].map(WATCHLIST)
    df["annual_return"] = ((df["year_close"]-df["year_open"])/df["year_open"]*100).round(1)
    return df

@st.cache_data(ttl=3600)
def load_fx():
    try:
        engine = get_engine()
        df = pd.read_sql("SELECT month,twd_per_usd FROM fx_rates ORDER BY month", engine)
        df["month"] = pd.to_datetime(df["month"])
        return df
    except: return pd.DataFrame()

rev_df    = load_revenue()
price_df  = load_prices()
annual_df = load_annual()
fx_df     = load_fx()

def apply_date_filter(df, date_col="date"):
    return df[(df[date_col].dt.year.isin(selected_years))&(df[date_col].dt.month.isin(selected_months))]

def aggregate_if_needed(df, rev_col, do_sum, label="Sector Total"):
    if not do_sum: return df
    num_cols = [c for c in [rev_col,"yoy_pct","mom_pct"] if c in df.columns]
    agg = df.groupby("date")[num_cols].sum().reset_index()
    agg["company"] = label
    agg["company_full"] = label
    agg["stock_id"] = "SUM"
    return agg

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

def render_rev_table(base_df, rev_col, unit_label, s3a, s6a, s3y, s6y, fmt="0f"):
    tbl = flag_anomalies(base_df, rev_col)
    tbl = tbl.sort_values(["company","date"])
    tbl["3M Avg Rev"]  = tbl.groupby("company")[rev_col].transform(lambda x: x.rolling(3,min_periods=1).mean())
    tbl["6M Avg Rev"]  = tbl.groupby("company")[rev_col].transform(lambda x: x.rolling(6,min_periods=1).mean())
    tbl["3M Avg YoY%"] = tbl.groupby("company")["3M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
    tbl["6M Avg YoY%"] = tbl.groupby("company")["6M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
    tbl = apply_date_filter(tbl)
    tbl = tbl.sort_values(["company","date"],ascending=[True,False])

    nf = lambda x: (f"{x:,.2f}" if fmt=="2f" else f"{x:,.0f}") if pd.notna(x) else ""
    pf = lambda x: f"{x:.1f}%" if pd.notna(x) else ""

    tbl["rev_fmt"]     = tbl[rev_col].apply(nf)
    tbl["3M Avg Rev"]  = tbl["3M Avg Rev"].apply(nf)
    tbl["6M Avg Rev"]  = tbl["6M Avg Rev"].apply(nf)
    for col in ["yoy_pct","mom_pct","3M Avg YoY%","6M Avg YoY%"]:
        if col in tbl.columns: tbl[col] = tbl[col].apply(pf)

    show = ["company_full","date","rev_fmt"]
    if s3a: show += ["3M Avg Rev"]
    if s6a: show += ["6M Avg Rev"]
    if s3y: show += ["3M Avg YoY%"]
    if s6y: show += ["6M Avg YoY%"]
    show += [c for c in ["yoy_pct","mom_pct"] if c in tbl.columns]

    out = tbl[show].copy().rename(columns={
        "company_full":"Company","date":"Sort Date",
        "rev_fmt":f"Revenue ({unit_label})","yoy_pct":"YoY %","mom_pct":"MoM %"
    })

    has_anomaly = tbl["_anom_high"].any() or tbl["_anom_low"].any()

    def highlight_anomaly(row):
        idx  = row.name
        orig = tbl.iloc[tbl.index.get_loc(idx)] if idx in tbl.index else None
        styles = [""] * len(row)
        if orig is not None:
            rev_col_pos = list(out.columns).index(f"Revenue ({unit_label})")
            if tbl.loc[idx,"_anom_high"]:
                styles[rev_col_pos] = "background-color: #d4edda"
            elif tbl.loc[idx,"_anom_low"]:
                styles[rev_col_pos] = "background-color: #f8d7da"
        return styles

    styled = out.style.apply(highlight_anomaly, axis=1)
    st.dataframe(
        styled,
        column_config={"Sort Date": st.column_config.DateColumn("Month", format="MMM-YYYY")},
        use_container_width=True
    )

    if has_anomaly:
        st.caption(
            "🟩 Light green = revenue significantly above recent trend (positive outlier)  ·  "
            "🟥 Light red = revenue significantly below recent trend (negative outlier)  ·  "
            "Determined by z-score > 1.8 standard deviations from the 6-month rolling average."
        )

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filter")
    available_years  = sorted(rev_df["date"].dt.year.unique().tolist(),reverse=True)
    available_months = sorted(rev_df["date"].dt.month.unique().tolist())
    selected_years  = st.multiselect("Year",  options=available_years,  default=available_years,  format_func=str)
    selected_months = st.multiselect("Month", options=available_months, default=available_months, format_func=lambda x: MONTH_NAMES[x])
    if not selected_years or not selected_months:
        st.warning("Select at least one year and month.")
        st.stop()
    subsector = st.selectbox("Sub-sector", options=["All"]+list(SUBSECTORS.keys()))
    available = list(WATCHLIST.keys()) if subsector=="All" else SUBSECTORS[subsector]
    selected  = st.multiselect("Stocks", options=available, default=available, format_func=lambda x: WATCHLIST_DISPLAY[x])
    if not selected:
        st.warning("Select at least one stock.")
        st.stop()
    st.divider()
    group_sum = st.toggle("📊 Sector total (sum selected)", value=False,
                          help="Sum revenue across selected companies — removes market share noise.")
    st.divider()
    latest_month = rev_df["date"].max()
    st.caption(f"📅 Data as of **{latest_month.strftime('%b %Y')}**")
    st.caption("Source: MOPS / Yahoo Finance")
    st.caption(f"Last refreshed: {date.today().strftime('%d %b %Y')}")

st.title("Taiwan Semi Monitor")
st.caption(f"Covering {len(WATCHLIST)} companies across {len(SUBSECTORS)} sub-sectors · Data as of {latest_month.strftime('%b %Y')} · Source: MOPS / Yahoo Finance")
st.divider()

tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8,tab9 = st.tabs([
    "📊 Revenue (TWD)","💵 Revenue (USD)","🔀 TWD vs USD",
    "📈 Growth Momentum","📉 3M Avg YoY","📉 6M Avg YoY",
    "🔗 Price vs Fundamentals","🌡️ Heatmap","🔄 Cycle Position",
])

# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Monthly Revenue (TWD thousands)")
    ct1 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="ct1")
    base1 = rev_df[rev_df["stock_id"].isin(selected)].copy()
    base1 = aggregate_if_needed(base1,"rev_current",group_sum)
    f1    = apply_date_filter(base1)
    if f1.empty:
        st.warning("No data.")
    else:
        st.plotly_chart(make_chart(f1,"date","rev_current","company",{"rev_current":"Revenue (TWD k)","date":"Month"},ct1),use_container_width=True,key="pc1")
        st.markdown("**Optional columns**")
        c1,c2,c3,c4 = st.columns(4)
        s3a=c1.checkbox("3M Avg Rev",key="t1_3a"); s6a=c2.checkbox("6M Avg Rev",key="t1_6a")
        s3y=c3.checkbox("3M Avg YoY%",key="t1_3y"); s6y=c4.checkbox("6M Avg YoY%",key="t1_6y")
        render_rev_table(base1,"rev_current","TWD k",s3a,s6a,s3y,s6y)

# ── Tab 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Monthly Revenue (USD millions)")
    ct2 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="ct2")
    if fx_df.empty:
        st.error("FX data not available.")
    else:
        lf = fx_df.sort_values("month").iloc[-1]
        st.info(f"💱 Latest FX: **1 USD = {lf['twd_per_usd']:.4f} TWD** (as of {lf['month'].strftime('%b %Y')})  \n**Methodology:** Monthly TWD revenue ÷ monthly avg TWD/USD rate (Yahoo Finance: TWD=X).")
        base2 = rev_df[rev_df["stock_id"].isin(selected)].copy()
        base2 = base2.merge(fx_df.rename(columns={"month":"date"}),on="date",how="left")
        base2["rev_usd"] = base2["rev_current"]/base2["twd_per_usd"]/1000
        base2 = aggregate_if_needed(base2,"rev_usd",group_sum)
        f2    = apply_date_filter(base2)
        if f2.empty:
            st.warning("No data.")
        else:
            st.plotly_chart(make_chart(f2,"date","rev_usd","company",{"rev_usd":"Revenue (USD mn)","date":"Month"},ct2),use_container_width=True,key="pc2")
            st.markdown("**Optional columns**")
            c1,c2,c3,c4 = st.columns(4)
            s3a=c1.checkbox("3M Avg Rev",key="t2_3a"); s6a=c2.checkbox("6M Avg Rev",key="t2_6a")
            s3y=c3.checkbox("3M Avg YoY%",key="t2_3y"); s6y=c4.checkbox("6M Avg YoY%",key="t2_6y")
            render_rev_table(base2,"rev_usd","USD mn",s3a,s6a,s3y,s6y,fmt="2f")

# ── Tab 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Revenue: TWD vs USD — Side by Side")
    st.caption("Divergence between TWD and USD lines reflects FX impact on reported revenue trends.")
    ct3 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="ct3")
    if fx_df.empty:
        st.error("FX data not available.")
    else:
        base3 = rev_df[rev_df["stock_id"].isin(selected)].copy()
        base3 = base3.merge(fx_df.rename(columns={"month":"date"}),on="date",how="left")
        base3["rev_usd"] = base3["rev_current"]/base3["twd_per_usd"]/1000
        b3t = aggregate_if_needed(base3.copy(),"rev_current",group_sum)
        b3u = aggregate_if_needed(base3.copy(),"rev_usd",group_sum)
        f3t = apply_date_filter(b3t); f3u = apply_date_filter(b3u)
        if f3t.empty:
            st.warning("No data.")
        else:
            cl,cr = st.columns(2)
            with cl:
                st.markdown("**Revenue in TWD (thousands)**")
                st.plotly_chart(make_chart(f3t,"date","rev_current","company",{"rev_current":"TWD k","date":"Month"},ct3),use_container_width=True,key="pc3l")
            with cr:
                st.markdown("**Revenue in USD (millions)**")
                st.plotly_chart(make_chart(f3u,"date","rev_usd","company",{"rev_usd":"USD mn","date":"Month"},ct3),use_container_width=True,key="pc3r")

# ── Tab 4 ─────────────────────────────────────────────────────────────────────
with tab4:
    st.subheader("Year-on-Year Revenue Growth (%)")
    ct4 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="ct4")
    base4 = rev_df[rev_df["stock_id"].isin(selected)].dropna(subset=["yoy_pct"]).copy()
    base4 = aggregate_if_needed(base4,"rev_current",group_sum)
    f4    = apply_date_filter(base4)
    if f4.empty:
        st.warning("No data.")
    else:
        fig4 = make_chart(f4,"date","yoy_pct","company",{"yoy_pct":"YoY %","date":"Month"},ct4)
        fig4.add_hline(y=0,line_dash="dash",line_color="gray",opacity=0.5)
        st.plotly_chart(fig4,use_container_width=True,key="pc4")
        tbl4 = f4[["company_full","date","yoy_pct","mom_pct"]].copy().sort_values(["company_full","date"],ascending=[True,False])
        for col in ["yoy_pct","mom_pct"]:
            tbl4[col] = tbl4[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        tbl4 = tbl4.rename(columns={"company_full":"Company","date":"Sort Date","yoy_pct":"YoY %","mom_pct":"MoM %"})
        st.dataframe(tbl4,column_config={"Sort Date":st.column_config.DateColumn("Month",format="MMM-YYYY")},use_container_width=True)

# ── Tab 5 ─────────────────────────────────────────────────────────────────────
with tab5:
    st.subheader("3-Month Average YoY Growth (%)")
    st.caption("3M rolling average revenue vs same period prior year.")
    ct5 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="ct5")
    base5 = rev_df[rev_df["stock_id"].isin(selected)].copy()
    base5 = aggregate_if_needed(base5,"rev_current",group_sum)
    base5 = base5.sort_values(["company","date"])
    base5["3M Avg Rev"]  = base5.groupby("company")["rev_current"].transform(lambda x: x.rolling(3,min_periods=1).mean())
    base5["3M Avg YoY%"] = base5.groupby("company")["3M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
    f5 = apply_date_filter(base5).dropna(subset=["3M Avg YoY%"])
    if f5.empty:
        st.warning("No data.")
    else:
        fig5 = make_chart(f5,"date","3M Avg YoY%","company",{"3M Avg YoY%":"3M Avg YoY %","date":"Month"},ct5)
        fig5.add_hline(y=0,line_dash="dash",line_color="gray",opacity=0.5)
        st.plotly_chart(fig5,use_container_width=True,key="pc5")
        t5 = f5[["company_full","date","rev_current","3M Avg Rev","3M Avg YoY%","mom_pct"]].copy().sort_values(["company_full","date"],ascending=[True,False])
        t5["rev_current"] = t5["rev_current"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        t5["3M Avg Rev"]  = t5["3M Avg Rev"].apply(lambda x: f"{x:,.0f}"  if pd.notna(x) else "")
        t5["3M Avg YoY%"] = t5["3M Avg YoY%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        t5["mom_pct"]     = t5["mom_pct"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        t5 = t5.rename(columns={"company_full":"Company","date":"Sort Date","rev_current":"Revenue (TWD k)","3M Avg Rev":"3M Avg Rev (TWD k)","mom_pct":"MoM %"})
        st.dataframe(t5,column_config={"Sort Date":st.column_config.DateColumn("Month",format="MMM-YYYY")},use_container_width=True)

# ── Tab 6 ─────────────────────────────────────────────────────────────────────
with tab6:
    st.subheader("6-Month Average YoY Growth (%)")
    st.caption("6M rolling average revenue vs same period prior year. Best for identifying structural cycle turns.")
    ct6 = st.radio("Chart type",["Line","Bar","Both"],horizontal=True,key="ct6")
    base6 = rev_df[rev_df["stock_id"].isin(selected)].copy()
    base6 = aggregate_if_needed(base6,"rev_current",group_sum)
    base6 = base6.sort_values(["company","date"])
    base6["6M Avg Rev"]  = base6.groupby("company")["rev_current"].transform(lambda x: x.rolling(6,min_periods=1).mean())
    base6["6M Avg YoY%"] = base6.groupby("company")["6M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
    f6 = apply_date_filter(base6).dropna(subset=["6M Avg YoY%"])
    if f6.empty:
        st.warning("No data.")
    else:
        fig6 = make_chart(f6,"date","6M Avg YoY%","company",{"6M Avg YoY%":"6M Avg YoY %","date":"Month"},ct6)
        fig6.add_hline(y=0,line_dash="dash",line_color="gray",opacity=0.5)
        st.plotly_chart(fig6,use_container_width=True,key="pc6")
        t6 = f6[["company_full","date","rev_current","6M Avg Rev","6M Avg YoY%","mom_pct"]].copy().sort_values(["company_full","date"],ascending=[True,False])
        t6["rev_current"] = t6["rev_current"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        t6["6M Avg Rev"]  = t6["6M Avg Rev"].apply(lambda x: f"{x:,.0f}"  if pd.notna(x) else "")
        t6["6M Avg YoY%"] = t6["6M Avg YoY%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        t6["mom_pct"]     = t6["mom_pct"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        t6 = t6.rename(columns={"company_full":"Company","date":"Sort Date","rev_current":"Revenue (TWD k)","6M Avg Rev":"6M Avg Rev (TWD k)","mom_pct":"MoM %"})
        st.dataframe(t6,column_config={"Sort Date":st.column_config.DateColumn("Month",format="MMM-YYYY")},use_container_width=True)

# ── Tab 7 ─────────────────────────────────────────────────────────────────────
with tab7:
    st.subheader("Price vs Fundamentals")
    if len(selected)==1:
        sid   = selected[0]
        rev   = rev_df[rev_df["stock_id"]==sid][["date","yoy_pct","rev_current"]].dropna(subset=["yoy_pct"])
        rev   = apply_date_filter(rev)
        price = price_df[price_df["stock_id"]==sid][["month","m_close"]].rename(columns={"month":"date"})
        price = apply_date_filter(price)
        merged = pd.merge(rev,price,on="date",how="inner").sort_values("date")
        if merged.empty:
            st.warning("No overlapping dates.")
        else:
            merged["price_mom_chg"] = merged["m_close"].pct_change(1)*100
            merged["price_3m_chg"]  = merged["m_close"].pct_change(3)*100
            pv = st.radio("Price return",["MoM Change","3M Change","Both"],horizontal=True,key="pv")
            max_abs = max(
                merged["price_mom_chg"].abs().max() if pv!="3M Change" else 0,
                merged["price_3m_chg"].abs().max()  if pv!="MoM Change" else 0
            )
            fig7 = go.Figure()
            fig7.add_trace(go.Bar(x=merged["date"],y=merged["yoy_pct"],name="Revenue YoY %",marker_color="#1D9E75",opacity=0.7))
            if pv in ["MoM Change","Both"]:
                fig7.add_trace(go.Scatter(x=merged["date"],y=merged["price_mom_chg"],name="Price MoM %",line=dict(color="#378ADD",width=2.5,dash="dot"),yaxis="y2"))
            if pv in ["3M Change","Both"]:
                fig7.add_trace(go.Scatter(x=merged["date"],y=merged["price_3m_chg"],name="Price 3M Chg %",line=dict(color="#E8642A",width=2.5),yaxis="y2"))
            fig7.update_layout(
                title=WATCHLIST_DISPLAY.get(sid,sid),
                yaxis=dict(title="Revenue YoY %",gridcolor="#eeeeee",zeroline=True,zerolinecolor="#cccccc"),
                yaxis2=dict(title="Price Return %",overlaying="y",side="right",gridcolor="#eeeeee",
                            range=[-max_abs*1.6,max_abs*1.6],zeroline=True,zerolinecolor="#cccccc"),
                hovermode="x unified",plot_bgcolor="white",bargap=0.2,
                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
            )
            st.plotly_chart(fig7,use_container_width=True,key="pc7a")
            st.divider()
            st.markdown("**Log Scale — Revenue vs Share Price**")
            st.caption("Parallel lines = revenue and price growing at similar rates. Divergence signals re-rating or de-rating.")
            ml = merged[(merged["m_close"]>0)&(merged["rev_current"]>0)].copy()
            fig7b = go.Figure()
            fig7b.add_trace(go.Scatter(x=ml["date"],y=np.log(ml["rev_current"]),name="ln(Revenue TWD k)",line=dict(color="#1D9E75",width=2)))
            fig7b.add_trace(go.Scatter(x=ml["date"],y=np.log(ml["m_close"]),name="ln(Share Price TWD)",line=dict(color="#378ADD",width=2),yaxis="y2"))
            fig7b.update_layout(
                title=f"{WATCHLIST_DISPLAY.get(sid,sid)} — Log Scale",
                yaxis=dict(title="ln(Revenue)",gridcolor="#eeeeee"),
                yaxis2=dict(title="ln(Share Price)",overlaying="y",side="right",gridcolor="#eeeeee"),
                hovermode="x unified",plot_bgcolor="white",
                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
            )
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

# ── Tab 8: Heatmap ────────────────────────────────────────────────────────────
with tab8:
    st.subheader("Revenue Heatmap")
    st.info("💡 This heatmap is most useful when **5 or more companies** are selected. With fewer selections, patterns across companies may not be meaningful.")
    hm_metric = st.radio("Metric",["YoY %","Revenue (TWD mn)","Both"],horizontal=True,key="hm_metric")

    hm_base = rev_df[rev_df["stock_id"].isin(selected)].copy()
    hm_base["rev_mn"] = hm_base["rev_current"] / 1000
    hm_base = apply_date_filter(hm_base)

    def render_heatmap(df, val_col, title, fmt_str, color_scale, key):
        pivot = df.pivot_table(index="company",columns="date",values=val_col,aggfunc="mean")
        pivot.columns = [c.strftime("%b-%y") for c in pivot.columns]
        z_text = [[fmt_str.format(v) if pd.notna(v) else "" for v in row] for row in pivot.values]
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=color_scale,
            zmid=0 if "%" in fmt_str else None,
            text=z_text,
            texttemplate="%{text}",
            hovertemplate="Company: %{y}<br>Month: %{x}<br>Value: %{text}<extra></extra>",
        ))
        fig.update_layout(
            title=title,
            height=max(300,len(pivot)*40+100),
            xaxis=dict(tickangle=-45),
            margin=dict(l=150,r=20,t=60,b=80),
        )
        st.plotly_chart(fig,use_container_width=True,key=key)

    if hm_base.empty:
        st.warning("No data.")
    else:
        if hm_metric in ["YoY %","Both"]:
            render_heatmap(hm_base,"yoy_pct","YoY Revenue Growth (%)","{:.1f}%","RdYlGn","hm1")
        if hm_metric in ["Revenue (TWD mn)","Both"]:
            render_heatmap(hm_base,"rev_mn","Monthly Revenue (TWD millions)","{:,.1f}","Blues","hm2")

# ── Tab 9: Cycle Position ─────────────────────────────────────────────────────
with tab9:
    st.subheader("Cycle Positioning")

    st.markdown("""
    ### How cycle position is determined

    Each company is assigned a cycle phase based on two dimensions of its **6-month average YoY revenue growth**:

    **Step 1 — Compute 6M Avg YoY%**
    For each month, we calculate a 6-month rolling average of monthly revenue, then compare it to the
    same 6-month rolling average from exactly 12 months prior. This smooths out seasonal noise and
    one-off distortions (e.g. holiday pull-forward, lunar new year effects).

    **Step 2 — Assess direction**
    We compare the latest 6M Avg YoY% reading against the average of the three preceding readings.
    This tells us whether the trend is **accelerating** (getting better) or **decelerating** (getting worse).

    **Step 3 — Assign phase**
    """)

    cycle_table = pd.DataFrame({
        "Phase":     ["🟢 Expansion","🔵 Recovery","🟡 Slowdown","🔴 Contraction"],
        "Condition": [
            "6M Avg YoY > 15% AND trend accelerating",
            "6M Avg YoY > 0% AND trend accelerating",
            "6M Avg YoY > 0% BUT trend decelerating",
            "6M Avg YoY < 0%",
        ],
        "Interpretation": [
            "Strong broad-based demand; pricing power typically intact",
            "Recovery underway; demand improving from a low base",
            "Growth positive but momentum fading; watch for cycle peak",
            "Demand contraction; inventory correction likely in progress",
        ]
    })
    st.dataframe(cycle_table, use_container_width=True, hide_index=True)

    st.caption("The 15% threshold for Expansion vs Recovery is calibrated for Taiwan semiconductor companies, which historically show high revenue volatility. It can be adjusted based on sub-sector norms.")

    st.divider()

    cyc9 = rev_df[rev_df["stock_id"].isin(selected)].copy().sort_values(["company","date"])
    cyc9["6M Avg Rev"]  = cyc9.groupby("company")["rev_current"].transform(lambda x: x.rolling(6,min_periods=1).mean())
    cyc9["6M Avg YoY%"] = cyc9.groupby("company")["6M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
    cyc9_filtered = apply_date_filter(cyc9)

    if cyc9_filtered.empty:
        st.warning("No data.")
    else:
        latest9 = cyc9.groupby("company").last().reset_index()
        latest9["Cycle"] = latest9["company"].apply(lambda c: get_cycle_position(c, cyc9))
        latest9["6M Avg YoY%"] = latest9["6M Avg YoY%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")

        st.markdown("### Current Positioning")
        col_exp,col_rec,col_slow,col_cont = st.columns(4)
        col_exp.markdown("**🟢 Expansion**")
        col_rec.markdown("**🔵 Recovery**")
        col_slow.markdown("**🟡 Slowdown**")
        col_cont.markdown("**🔴 Contraction**")

        CYCLE_COLORS = {
            "🟢 Expansion":"#d4edda","🔵 Recovery":"#d0e8f5",
            "🟡 Slowdown":"#fff3cd","🔴 Contraction":"#f8d7da","⬜ N/A":"#f0f0f0"
        }

        for _,row in latest9.iterrows():
            pos   = row["Cycle"]
            color = CYCLE_COLORS.get(pos,"#f0f0f0")
            card  = f"""<div style="background:{color};border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:14px;">
                <b>{row['company']}</b><br>
                <span style="font-size:12px;color:#555;">6M Avg YoY: {row['6M Avg YoY%']}</span>
            </div>"""
            if "Expansion"  in pos: col_exp.markdown(card,  unsafe_allow_html=True)
            elif "Recovery" in pos: col_rec.markdown(card,  unsafe_allow_html=True)
            elif "Slowdown" in pos: col_slow.markdown(card, unsafe_allow_html=True)
            else:                   col_cont.markdown(card, unsafe_allow_html=True)

        st.divider()
        st.markdown("### 6M Avg YoY Trend — Cycle View")

        fig9 = px.line(cyc9_filtered,x="date",y="6M Avg YoY%",color="company",
                       labels={"6M Avg YoY%":"6M Avg YoY %","date":"Month"},
                       color_discrete_sequence=BRAND_COLORS)
        fig9.add_hline(y=0, line_dash="dash",line_color="#E74C3C",opacity=0.6,annotation_text="Contraction threshold")
        fig9.add_hline(y=15,line_dash="dash",line_color="#1D9E75",opacity=0.6,annotation_text="Expansion threshold")
        fig9.add_hrect(y0=15,  y1=200,  fillcolor="#1D9E75",opacity=0.04,line_width=0)
        fig9.add_hrect(y0=0,   y1=15,   fillcolor="#378ADD",opacity=0.04,line_width=0)
        fig9.add_hrect(y0=-200,y1=0,    fillcolor="#E74C3C",opacity=0.04,line_width=0)
        fig9.update_traces(line=dict(width=2))
        fig9.update_layout(
            hovermode="x unified",plot_bgcolor="white",
            yaxis=dict(gridcolor="#eeeeee",zeroline=True,zerolinecolor="#cccccc"),
            xaxis=dict(gridcolor="#eeeeee"),
            legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
        )
        st.plotly_chart(fig9,use_container_width=True,key="pc9")

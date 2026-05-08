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
        .metric-card {
            background-color: #f8f9fa;
            border-left: 4px solid #1D9E75;
            padding: 10px 16px;
            border-radius: 4px;
            margin-bottom: 8px;
        }
    </style>
""", unsafe_allow_html=True)

PROJECT_REF = st.secrets["PROJECT_REF"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]

WATCHLIST = {
    "2330": "TSMC", "2317": "Hon Hai", "6669": "Wiwynn", "3231": "Wistron",
    "3105": "Win Semicon", "6488": "GlobalWafers", "5483": "SAS",
    "3008": "Largan", "2454": "MediaTek", "2303": "UMC",
    "4938": "Pegatron", "6770": "Powerchip", "5347": "Vanguard Semi",
    "2382": "Quanta", "2408": "Nanya Tech", "2379": "Realtek",
    "3034": "Novatek", "3450": "Elite Laser", "3406": "Genius Optical",
    "3037": "Unimicron", "3189": "Kinsus", "8046": "Nanya PCB",
    "3711": "ASE Technology", "6239": "Powertech", "2449": "King Yuan",
}

SUBSECTORS = {
    "Silicon Materials": ["6488", "5483"],
    "IC Designers": ["2454", "2379", "3034"],
    "Foundry": ["2330", "2303", "5347", "3105"],
    "Memory (IDM)": ["6770", "2408"],
    "OSAT (Packaging & Testing)": ["3711", "6239", "2449"],
    "PCB Firms": ["3037", "3189", "8046"],
    "ODM / EMS (Assembly)": ["2317", "6669", "3231", "2382", "4938"],
    "Optics / Optoelectronics": ["3008", "3406", "3450"],
}

WATCHLIST_DISPLAY = {
    "2330": "2330 TSMC 台積電", "2317": "2317 Hon Hai 鴻海",
    "6669": "6669 Wiwynn 緯穎", "3231": "3231 Wistron 緯創",
    "3105": "3105 Win Semicon 穩懋", "6488": "6488 GlobalWafers 環球晶",
    "5483": "5483 SAS 中美晶", "3008": "3008 Largan 大立光",
    "2454": "2454 MediaTek 聯發科", "2303": "2303 UMC 聯電",
    "4938": "4938 Pegatron 和碩", "6770": "6770 Powerchip 力積電",
    "5347": "5347 Vanguard Semi 世界先進", "2382": "2382 Quanta 廣達",
    "2408": "2408 Nanya Tech 南亞科", "2379": "2379 Realtek 瑞昱",
    "3034": "3034 Novatek 聯詠", "3450": "3450 Elite Laser 晶睿",
    "3406": "3406 Genius Optical 玉晶光", "3037": "3037 Unimicron 欣興",
    "3189": "3189 Kinsus 景碩", "8046": "8046 Nanya PCB 南電",
    "3711": "3711 ASE Technology 日月光", "6239": "6239 Powertech 力成",
    "2449": "2449 King Yuan 京元電子",
}

WATCHLIST_FULLNAME = {
    "2330": "2330 | TSMC | 台積電", "2317": "2317 | Hon Hai | 鴻海",
    "6669": "6669 | Wiwynn | 緯穎", "3231": "3231 | Wistron | 緯創",
    "3105": "3105 | Win Semicon | 穩懋", "6488": "6488 | GlobalWafers | 環球晶",
    "5483": "5483 | SAS | 中美晶", "3008": "3008 | Largan | 大立光",
    "2454": "2454 | MediaTek | 聯發科", "2303": "2303 | UMC | 聯電",
    "4938": "4938 | Pegatron | 和碩", "6770": "6770 | Powerchip | 力積電",
    "5347": "5347 | Vanguard Semi | 世界先進", "2382": "2382 | Quanta | 廣達",
    "2408": "2408 | Nanya Tech | 南亞科", "2379": "2379 | Realtek | 瑞昱",
    "3034": "3034 | Novatek | 聯詠", "3450": "3450 | Elite Laser | 晶睿",
    "3406": "3406 | Genius Optical | 玉晶光", "3037": "3037 | Unimicron | 欣興",
    "3189": "3189 | Kinsus | 景碩", "8046": "8046 | Nanya PCB | 南電",
    "3711": "3711 | ASE Technology | 日月光", "6239": "6239 | Powertech | 力成",
    "2449": "2449 | King Yuan | 京元電子",
}

MONTH_NAMES = {
    1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May", 6:"Jun",
    7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"
}

BRAND_COLORS = [
    "#1D9E75", "#378ADD", "#E8642A", "#9B59B6",
    "#F39C12", "#E74C3C", "#2ECC71", "#3498DB",
    "#1ABC9C", "#D35400", "#8E44AD", "#27AE60",
]

@st.cache_resource
def get_engine():
    try:
        return create_engine(
            f"postgresql://postgres.{PROJECT_REF}:{DB_PASSWORD}"
            f"@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
        )
    except Exception as e:
        st.error(f"❌ Failed to connect to database: {e}")
        st.stop()

@st.cache_data(ttl=3600)
def load_revenue():
    try:
        engine = get_engine()
        df = pd.read_sql("""
            SELECT stock_id, report_month, rev_current, yoy_pct, mom_pct
            FROM monthly_revenue
            ORDER BY stock_id, report_month
        """, engine)
        df["stock_id"] = df["stock_id"].astype(str)
        df = df[df["stock_id"].isin(WATCHLIST.keys())]
        df["company"] = df["stock_id"].map(WATCHLIST)
        df["company_full"] = df["stock_id"].map(WATCHLIST_FULLNAME)
        def roc_to_date(ym):
            try:
                parts = str(ym).split('_')
                return pd.Timestamp(year=int(parts[0])+1911, month=int(parts[1]), day=1)
            except:
                return pd.NaT
        df["date"] = df["report_month"].apply(roc_to_date)
        df = df.dropna(subset=["date"])
        df["date_display"] = df["date"].dt.strftime("%b-%Y")
        return df
    except Exception as e:
        st.error(f"❌ Failed to load revenue data: {e}")
        st.stop()

@st.cache_data(ttl=3600)
def load_prices():
    try:
        engine = get_engine()
        symbols_tw  = "','".join([f"{k}.TW"  for k in WATCHLIST.keys()])
        symbols_two = "','".join([f"{k}.TWO" for k in WATCHLIST.keys()])
        df = pd.read_sql(f"""
            SELECT date, symbol, open, close
            FROM stock_prices
            WHERE symbol IN ('{symbols_tw}', '{symbols_two}')
            ORDER BY symbol, date
        """, engine)
        df["stock_id"] = df["symbol"].str.replace(".TWO","").str.replace(".TW","")
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
        monthly = df.groupby(["stock_id","month"]).agg(
            m_open=("open","first"), m_close=("close","last")
        ).reset_index()
        return monthly
    except Exception as e:
        st.error(f"❌ Failed to load price data: {e}")
        st.stop()

@st.cache_data(ttl=3600)
def load_annual():
    try:
        engine = get_engine()
        symbols = "','".join(
            [f"{k}.TW" for k in WATCHLIST.keys()] +
            [f"{k}.TWO" for k in WATCHLIST.keys()]
        )
        df = pd.read_sql(f"""
            SELECT symbol, year, year_open, year_close, year_high, year_low
            FROM stock_annual_k2
            WHERE symbol IN ('{symbols}')
            ORDER BY symbol, year
        """, engine)
        df["stock_id"] = df["symbol"].str.replace(".TWO","").str.replace(".TW","")
        df["company"] = df["stock_id"].map(WATCHLIST)
        df["annual_return"] = ((df["year_close"]-df["year_open"])/df["year_open"]*100).round(1)
        return df
    except Exception as e:
        st.error(f"❌ Failed to load annual data: {e}")
        st.stop()

@st.cache_data(ttl=3600)
def load_fx():
    try:
        engine = get_engine()
        df = pd.read_sql("SELECT month, twd_per_usd FROM fx_rates ORDER BY month", engine)
        df["month"] = pd.to_datetime(df["month"])
        return df
    except Exception as e:
        st.warning(f"FX data not available: {e}")
        return pd.DataFrame()

rev_df    = load_revenue()
price_df  = load_prices()
annual_df = load_annual()
fx_df     = load_fx()

def apply_date_filter(df, date_col="date"):
    return df[
        (df[date_col].dt.year.isin(selected_years)) &
        (df[date_col].dt.month.isin(selected_months))
    ]

def make_chart(df, x, y, color, labels, chart_type, color_seq=BRAND_COLORS, key_suffix=""):
    if chart_type == "Line":
        fig = px.line(df, x=x, y=y, color=color, labels=labels, color_discrete_sequence=color_seq)
        fig.update_traces(line=dict(width=2))
    elif chart_type == "Bar":
        fig = px.bar(df, x=x, y=y, color=color, barmode="group", labels=labels, color_discrete_sequence=color_seq)
    else:  # Both
        fig = go.Figure()
        colors = color_seq
        companies = df[color].unique()
        for idx, comp in enumerate(companies):
            c = colors[idx % len(colors)]
            sub = df[df[color] == comp]
            fig.add_trace(go.Bar(x=sub[x], y=sub[y], name=f"{comp} (bar)",
                                 marker_color=c, opacity=0.4, showlegend=True))
            fig.add_trace(go.Scatter(x=sub[x], y=sub[y], name=f"{comp} (line)",
                                     line=dict(color=c, width=2), showlegend=True))
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified", plot_bgcolor="white",
        yaxis=dict(gridcolor="#eeeeee"),
        xaxis=dict(gridcolor="#eeeeee"),
    )
    return fig

def aggregate_if_needed(df, rev_col, group_sum, label="Sector Total"):
    if not group_sum:
        return df
    agg = df.groupby("date").agg(
        **{rev_col: (rev_col, "sum"),
           "yoy_pct": ("yoy_pct", "mean"),
           "mom_pct": ("mom_pct", "mean")}
    ).reset_index()
    agg["company"] = label
    agg["company_full"] = label
    agg["stock_id"] = "SUM"
    return agg

with st.sidebar:
    st.header("Filter")

    available_years  = sorted(rev_df["date"].dt.year.unique().tolist(), reverse=True)
    available_months = sorted(rev_df["date"].dt.month.unique().tolist())

    selected_years = st.multiselect(
        "Filter by year", options=available_years, default=available_years,
        format_func=lambda x: str(x)
    )
    selected_months = st.multiselect(
        "Filter by month", options=available_months, default=available_months,
        format_func=lambda x: MONTH_NAMES[x]
    )

    if not selected_years or not selected_months:
        st.warning("Please select at least one year and one month.")
        st.stop()

    subsector = st.selectbox("Filter by sub-sector", options=["All"] + list(SUBSECTORS.keys()))

    if subsector == "All":
        available = list(WATCHLIST.keys())
        default_options = list(WATCHLIST.keys())
    else:
        available = SUBSECTORS[subsector]
        default_options = SUBSECTORS[subsector]

    selected = st.multiselect(
        "Select stocks", options=available, default=default_options,
        format_func=lambda x: WATCHLIST_DISPLAY[x]
    )

    if not selected:
        st.warning("Please select at least one stock.")
        st.stop()

    st.divider()
    group_sum = st.toggle(
        "📊 Show sector total (sum selected)",
        value=False,
        help="Aggregate revenue across all selected companies into one line. "
             "Useful for sub-sector analysis to remove market share noise."
    )

    st.divider()
    latest_month = rev_df["date"].max()
    st.caption(f"📅 Data as of **{latest_month.strftime('%b %Y')}**")
    st.caption("Source: MOPS / Yahoo Finance")
    st.caption(f"Last refreshed: {date.today().strftime('%d %b %Y')}")

st.title("M* Taiwan Semi Monitor")
st.caption(
    f"Covering {len(WATCHLIST)} companies across {len(SUBSECTORS)} sub-sectors · "
    f"Data as of {latest_month.strftime('%b %Y')} · Source: MOPS / Yahoo Finance"
)
st.divider()

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Revenue (TWD)",
    "💵 Revenue (USD)",
    "🔀 TWD vs USD",
    "📈 Growth Momentum",
    "📉 3M Avg YoY",
    "📉 6M Avg YoY",
    "🔗 Price vs Fundamentals",
])

# ── Tab 1: Revenue TWD ────────────────────────────────────────────────────────
with tab1:
    st.subheader("Monthly Revenue (TWD thousands)")
    chart_type = st.radio("Chart type", ["Line", "Bar", "Both"], horizontal=True, key="ct_t1")

    filtered = rev_df[rev_df["stock_id"].isin(selected)].copy()
    filtered = apply_date_filter(filtered)
    filtered = aggregate_if_needed(filtered, "rev_current", group_sum)

    if filtered.empty:
        st.warning("No data available.")
    else:
        fig = make_chart(filtered, "date", "rev_current", "company",
                         {"rev_current": "Revenue (TWD k)", "date": "Month"}, chart_type)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Optional columns**")
        c1, c2, c3, c4 = st.columns(4)
        with c1: s3a = st.checkbox("3M Avg Rev",  key="t1_3a")
        with c2: s6a = st.checkbox("6M Avg Rev",  key="t1_6a")
        with c3: s3y = st.checkbox("3M Avg YoY%", key="t1_3y")
        with c4: s6y = st.checkbox("6M Avg YoY%", key="t1_6y")

        tbl = rev_df[rev_df["stock_id"].isin(selected)].copy()
        tbl = aggregate_if_needed(tbl, "rev_current", group_sum)
        tbl = tbl.sort_values(["company","date"])
        tbl["3M Avg Rev"]  = tbl.groupby("company")["rev_current"].transform(lambda x: x.rolling(3,min_periods=1).mean())
        tbl["6M Avg Rev"]  = tbl.groupby("company")["rev_current"].transform(lambda x: x.rolling(6,min_periods=1).mean())
        tbl["3M Avg YoY%"] = tbl.groupby("company")["3M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
        tbl["6M Avg YoY%"] = tbl.groupby("company")["6M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
        tbl = apply_date_filter(tbl)
        tbl = tbl.sort_values(["company","date"], ascending=[True,False])
        for col in ["rev_current","3M Avg Rev","6M Avg Rev"]:
            tbl[col] = tbl[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        for col in ["yoy_pct","mom_pct","3M Avg YoY%","6M Avg YoY%"]:
            if col in tbl.columns:
                tbl[col] = tbl[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")

        show_cols = ["company_full","date","rev_current"]
        if s3a: show_cols += ["3M Avg Rev"]
        if s6a: show_cols += ["6M Avg Rev"]
        if s3y: show_cols += ["3M Avg YoY%"]
        if s6y: show_cols += ["6M Avg YoY%"]
        show_cols += ["yoy_pct","mom_pct"]
        tbl2 = tbl[show_cols].rename(columns={
            "company_full":"Company","date":"Sort Date","rev_current":"Revenue (TWD k)",
            "yoy_pct":"YoY %","mom_pct":"MoM %"
        })
        st.dataframe(tbl2, column_config={
            "Sort Date": st.column_config.DateColumn("Month", format="MMM-YYYY"),
        }, use_container_width=True)

# ── Tab 2: Revenue USD ────────────────────────────────────────────────────────
with tab2:
    st.subheader("Monthly Revenue (USD millions)")
    chart_type = st.radio("Chart type", ["Line", "Bar", "Both"], horizontal=True, key="ct_t2")

    if fx_df.empty:
        st.error("FX rate data not available.")
    else:
        latest_fx      = fx_df.sort_values("month").iloc[-1]
        latest_fx_date = latest_fx["month"].strftime("%b %Y")
        latest_fx_rate = latest_fx["twd_per_usd"]
        st.info(
            f"💱 Latest FX rate: **1 USD = {latest_fx_rate:.4f} TWD** (as of {latest_fx_date})  \n"
            f"**Methodology:** Each month's TWD revenue divided by that month's average TWD/USD rate "
            f"(Yahoo Finance ticker: TWD=X). Monthly average of daily closing rates."
        )

        rev_usd = rev_df[rev_df["stock_id"].isin(selected)].copy()
        rev_usd = rev_usd.merge(fx_df.rename(columns={"month":"date"}), on="date", how="left")
        rev_usd["rev_usd"] = rev_usd["rev_current"] / rev_usd["twd_per_usd"] / 1000
        rev_usd = aggregate_if_needed(rev_usd, "rev_usd", group_sum)
        rev_usd_filtered = apply_date_filter(rev_usd)

        if rev_usd_filtered.empty:
            st.warning("No data available.")
        else:
            fig = make_chart(rev_usd_filtered, "date", "rev_usd", "company",
                             {"rev_usd":"Revenue (USD mn)","date":"Month"}, chart_type)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("**Optional columns**")
            c1, c2, c3, c4 = st.columns(4)
            with c1: s3a = st.checkbox("3M Avg Rev",  key="t2_3a")
            with c2: s6a = st.checkbox("6M Avg Rev",  key="t2_6a")
            with c3: s3y = st.checkbox("3M Avg YoY%", key="t2_3y")
            with c4: s6y = st.checkbox("6M Avg YoY%", key="t2_6y")

            tbl = rev_usd.sort_values(["company","date"])
            tbl["3M Avg Rev"]  = tbl.groupby("company")["rev_usd"].transform(lambda x: x.rolling(3,min_periods=1).mean())
            tbl["6M Avg Rev"]  = tbl.groupby("company")["rev_usd"].transform(lambda x: x.rolling(6,min_periods=1).mean())
            tbl["3M Avg YoY%"] = tbl.groupby("company")["3M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
            tbl["6M Avg YoY%"] = tbl.groupby("company")["6M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
            tbl = apply_date_filter(tbl)
            tbl = tbl.sort_values(["company","date"], ascending=[True,False])
            for col in ["rev_usd","3M Avg Rev","6M Avg Rev"]:
                tbl[col] = tbl[col].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
            for col in ["yoy_pct","mom_pct","3M Avg YoY%","6M Avg YoY%"]:
                if col in tbl.columns:
                    tbl[col] = tbl[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")

            show_cols = ["company_full","date","rev_usd"]
            if s3a: show_cols += ["3M Avg Rev"]
            if s6a: show_cols += ["6M Avg Rev"]
            if s3y: show_cols += ["3M Avg YoY%"]
            if s6y: show_cols += ["6M Avg YoY%"]
            show_cols += ["yoy_pct","mom_pct"]
            tbl2 = tbl[show_cols].rename(columns={
                "company_full":"Company","date":"Sort Date","rev_usd":"Revenue (USD mn)",
                "yoy_pct":"YoY %","mom_pct":"MoM %"
            })
            st.dataframe(tbl2, column_config={
                "Sort Date": st.column_config.DateColumn("Month", format="MMM-YYYY"),
            }, use_container_width=True)

# ── Tab 3: TWD vs USD comparison ──────────────────────────────────────────────
with tab3:
    st.subheader("Revenue: TWD vs USD — Side by Side")
    st.caption(
        "Compare revenue growth expressed in TWD vs USD. Divergence between the two reflects "
        "TWD/USD currency moves — useful for understanding FX impact on reported revenue trends."
    )
    chart_type = st.radio("Chart type", ["Line", "Bar", "Both"], horizontal=True, key="ct_t3")

    if fx_df.empty:
        st.error("FX rate data not available.")
    else:
        base = rev_df[rev_df["stock_id"].isin(selected)].copy()
        base = base.merge(fx_df.rename(columns={"month":"date"}), on="date", how="left")
        base["rev_usd"] = base["rev_current"] / base["twd_per_usd"] / 1000

        base_twd = aggregate_if_needed(base.copy(), "rev_current", group_sum)
        base_usd = aggregate_if_needed(base.copy(), "rev_usd", group_sum)

        base_twd_f = apply_date_filter(base_twd)
        base_usd_f = apply_date_filter(base_usd)

        if base_twd_f.empty:
            st.warning("No data available.")
        else:
            col_left, col_right = st.columns(2)
            with col_left:
                st.markdown("**Revenue in TWD (thousands)**")
                fig_twd = make_chart(base_twd_f, "date", "rev_current", "company",
                                     {"rev_current":"Revenue (TWD k)","date":"Month"}, chart_type, key_suffix="t3l")
                st.plotly_chart(fig_twd, use_container_width=True)
            with col_right:
                st.markdown("**Revenue in USD (millions)**")
                fig_usd = make_chart(base_usd_f, "date", "rev_usd", "company",
                                     {"rev_usd":"Revenue (USD mn)","date":"Month"}, chart_type, key_suffix="t3r")
                st.plotly_chart(fig_usd, use_container_width=True)

# ── Tab 4: Growth Momentum ────────────────────────────────────────────────────
with tab4:
    st.subheader("Year-on-Year Revenue Growth (%)")
    chart_type = st.radio("Chart type", ["Line", "Bar", "Both"], horizontal=True, key="ct_t4")

    filtered2 = rev_df[rev_df["stock_id"].isin(selected)].dropna(subset=["yoy_pct"]).copy()
    filtered2 = aggregate_if_needed(filtered2, "rev_current", group_sum)
    filtered2 = apply_date_filter(filtered2)

    if filtered2.empty:
        st.warning("No YoY data available.")
    else:
        fig2 = make_chart(filtered2, "date", "yoy_pct", "company",
                          {"yoy_pct":"YoY Growth %","date":"Month"}, chart_type)
        fig2.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        st.plotly_chart(fig2, use_container_width=True)

        yoy_tbl = filtered2[["company_full","date","yoy_pct","mom_pct"]].copy()
        yoy_tbl = yoy_tbl.sort_values(["company_full","date"], ascending=[True,False])
        for col in ["yoy_pct","mom_pct"]:
            yoy_tbl[col] = yoy_tbl[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        yoy_tbl = yoy_tbl.rename(columns={
            "company_full":"Company","date":"Sort Date","yoy_pct":"YoY %","mom_pct":"MoM %"
        })
        st.dataframe(yoy_tbl, column_config={
            "Sort Date": st.column_config.DateColumn("Month", format="MMM-YYYY"),
        }, use_container_width=True)

# ── Tab 5: 3M Avg YoY ────────────────────────────────────────────────────────
with tab5:
    st.subheader("3-Month Average YoY Growth (%)")
    st.caption("3M rolling average revenue vs same period prior year. Reduces single-month noise.")
    chart_type = st.radio("Chart type", ["Line", "Bar", "Both"], horizontal=True, key="ct_t5")

    roll_df = rev_df[rev_df["stock_id"].isin(selected)].copy()
    roll_df = aggregate_if_needed(roll_df, "rev_current", group_sum)
    roll_df = roll_df.sort_values(["company","date"])
    roll_df["3M Avg Rev"]  = roll_df.groupby("company")["rev_current"].transform(lambda x: x.rolling(3,min_periods=1).mean())
    roll_df["3M Avg YoY%"] = roll_df.groupby("company")["3M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
    roll_df = apply_date_filter(roll_df)
    roll_df = roll_df.dropna(subset=["3M Avg YoY%"])

    if roll_df.empty:
        st.warning("No data available.")
    else:
        fig4 = make_chart(roll_df, "date", "3M Avg YoY%", "company",
                          {"3M Avg YoY%":"3M Avg YoY %","date":"Month"}, chart_type)
        fig4.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        st.plotly_chart(fig4, use_container_width=True)

        t4 = roll_df[["company_full","date","rev_current","3M Avg Rev","3M Avg YoY%","mom_pct"]].copy()
        t4 = t4.sort_values(["company_full","date"], ascending=[True,False])
        t4["rev_current"] = t4["rev_current"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        t4["3M Avg Rev"]  = t4["3M Avg Rev"].apply(lambda x: f"{x:,.0f}"  if pd.notna(x) else "")
        t4["3M Avg YoY%"] = t4["3M Avg YoY%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        t4["mom_pct"]     = t4["mom_pct"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        t4 = t4.rename(columns={
            "company_full":"Company","date":"Sort Date",
            "rev_current":"Revenue (TWD k)","3M Avg Rev":"3M Avg Rev (TWD k)",
            "3M Avg YoY%":"3M Avg YoY%","mom_pct":"MoM %"
        })
        st.dataframe(t4, column_config={
            "Sort Date": st.column_config.DateColumn("Month", format="MMM-YYYY"),
        }, use_container_width=True)

# ── Tab 6: 6M Avg YoY ────────────────────────────────────────────────────────
with tab6:
    st.subheader("6-Month Average YoY Growth (%)")
    st.caption("6M rolling average revenue vs same period prior year. Best for identifying structural cycle turns.")
    chart_type = st.radio("Chart type", ["Line", "Bar", "Both"], horizontal=True, key="ct_t6")

    roll6_df = rev_df[rev_df["stock_id"].isin(selected)].copy()
    roll6_df = aggregate_if_needed(roll6_df, "rev_current", group_sum)
    roll6_df = roll6_df.sort_values(["company","date"])
    roll6_df["6M Avg Rev"]  = roll6_df.groupby("company")["rev_current"].transform(lambda x: x.rolling(6,min_periods=1).mean())
    roll6_df["6M Avg YoY%"] = roll6_df.groupby("company")["6M Avg Rev"].transform(lambda x: x.pct_change(12)*100)
    roll6_df = apply_date_filter(roll6_df)
    roll6_df = roll6_df.dropna(subset=["6M Avg YoY%"])

    if roll6_df.empty:
        st.warning("No data available.")
    else:
        fig5 = make_chart(roll6_df, "date", "6M Avg YoY%", "company",
                          {"6M Avg YoY%":"6M Avg YoY %","date":"Month"}, chart_type)
        fig5.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        st.plotly_chart(fig5, use_container_width=True)

        t5 = roll6_df[["company_full","date","rev_current","6M Avg Rev","6M Avg YoY%","mom_pct"]].copy()
        t5 = t5.sort_values(["company_full","date"], ascending=[True,False])
        t5["rev_current"] = t5["rev_current"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        t5["6M Avg Rev"]  = t5["6M Avg Rev"].apply(lambda x: f"{x:,.0f}"  if pd.notna(x) else "")
        t5["6M Avg YoY%"] = t5["6M Avg YoY%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        t5["mom_pct"]     = t5["mom_pct"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        t5 = t5.rename(columns={
            "company_full":"Company","date":"Sort Date",
            "rev_current":"Revenue (TWD k)","6M Avg Rev":"6M Avg Rev (TWD k)",
            "6M Avg YoY%":"6M Avg YoY%","mom_pct":"MoM %"
        })
        st.dataframe(t5, column_config={
            "Sort Date": st.column_config.DateColumn("Month", format="MMM-YYYY"),
        }, use_container_width=True)

# ── Tab 7: Price vs Fundamentals ──────────────────────────────────────────────
with tab7:
    st.subheader("Price vs Fundamentals")

    if len(selected) == 1:
        sid   = selected[0]
        rev   = rev_df[rev_df["stock_id"]==sid][["date","yoy_pct","rev_current"]].dropna(subset=["yoy_pct"])
        rev   = apply_date_filter(rev)
        price = price_df[price_df["stock_id"]==sid][["month","m_close"]].rename(columns={"month":"date"})
        price = apply_date_filter(price)
        merged = pd.merge(rev, price, on="date", how="inner").sort_values("date")

        if merged.empty:
            st.warning("No overlapping dates between revenue and price data.")
        else:
            merged["price_mom_chg"] = merged["m_close"].pct_change(1) * 100
            merged["price_3m_chg"]  = merged["m_close"].pct_change(3) * 100

            price_view = st.radio(
                "Price return to display",
                ["MoM Change", "3M Change", "Both"],
                horizontal=True, key="price_view"
            )

            max_abs = max(
                merged["price_mom_chg"].abs().max() if price_view != "3M Change" else 0,
                merged["price_3m_chg"].abs().max()  if price_view != "MoM Change" else 0
            )
            price_range = [-max_abs * 1.6, max_abs * 1.6]

            fig3 = go.Figure()
            fig3.add_trace(go.Bar(
                x=merged["date"], y=merged["yoy_pct"],
                name="Revenue YoY %",
                marker_color="#1D9E75", opacity=0.7
            ))
            if price_view in ["MoM Change", "Both"]:
                fig3.add_trace(go.Scatter(
                    x=merged["date"], y=merged["price_mom_chg"],
                    name="Price MoM %",
                    line=dict(color="#378ADD", width=2.5, dash="dot"),
                    yaxis="y2"
                ))
            if price_view in ["3M Change", "Both"]:
                fig3.add_trace(go.Scatter(
                    x=merged["date"], y=merged["price_3m_chg"],
                    name="Price 3M Chg %",
                    line=dict(color="#E8642A", width=2.5),
                    yaxis="y2"
                ))
            fig3.update_layout(
                title=f"{WATCHLIST_DISPLAY.get(sid, sid)}",
                yaxis=dict(title="Revenue YoY %", gridcolor="#eeeeee",
                           zeroline=True, zerolinecolor="#cccccc"),
                yaxis2=dict(title="Price Return %", overlaying="y", side="right",
                            gridcolor="#eeeeee", range=price_range,
                            zeroline=True, zerolinecolor="#cccccc"),
                hovermode="x unified", plot_bgcolor="white", bargap=0.2,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig3, use_container_width=True)

            st.divider()
            st.markdown("**Log Scale — Revenue vs Share Price**")
            st.caption(
                "Log scale shows proportional growth rates. Parallel lines = revenue and price "
                "growing at similar rates. Divergence signals re-rating or de-rating."
            )
            merged_log = merged[(merged["m_close"]>0) & (merged["rev_current"]>0)].copy()
            fig_log = go.Figure()
            fig_log.add_trace(go.Scatter(
                x=merged_log["date"], y=np.log(merged_log["rev_current"]),
                name="ln(Revenue TWD k)", line=dict(color="#1D9E75", width=2)
            ))
            fig_log.add_trace(go.Scatter(
                x=merged_log["date"], y=np.log(merged_log["m_close"]),
                name="ln(Share Price TWD)", line=dict(color="#378ADD", width=2),
                yaxis="y2"
            ))
            fig_log.update_layout(
                title=f"{WATCHLIST_DISPLAY.get(sid, sid)} — Log Scale",
                yaxis=dict(title="ln(Revenue)", gridcolor="#eeeeee",
                           zeroline=True, zerolinecolor="#cccccc"),
                yaxis2=dict(title="ln(Share Price)", overlaying="y", side="right",
                            gridcolor="#eeeeee"),
                hovermode="x unified", plot_bgcolor="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_log, use_container_width=True)

    else:
        st.info("💡 Select a **single stock** to see the Revenue vs Price chart.")
        ann = annual_df[annual_df["stock_id"].isin(selected)].copy()
        ann = ann[ann["year"].astype(str).str[:4].astype(int).isin(selected_years)]
        if ann.empty:
            st.warning("No annual return data available.")
        else:
            fig_ann = px.bar(
                ann, x="year", y="annual_return", color="company", barmode="group",
                labels={"annual_return":"Annual Return %","year":"Year"},
                title="Annual Stock Return (%)", color_discrete_sequence=BRAND_COLORS
            )
            fig_ann.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig_ann.update_layout(
                plot_bgcolor="white",
                yaxis=dict(gridcolor="#eeeeee"),
                xaxis=dict(gridcolor="#eeeeee"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_ann, use_container_width=True)

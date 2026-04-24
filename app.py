import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine

st.set_page_config(page_title="Taiwan Stock Dashboard", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@300;400;500;600&display=swap');
        html, body, [class*="css"], [class*="st-"], .stDataFrame, .stSelectbox,
        .stMultiSelect, .stCheckbox, .stTab, button, input, textarea {
            font-family: 'Barlow Condensed', sans-serif !important;
        }
    </style>
""", unsafe_allow_html=True)

PROJECT_REF = "fovemqafkhburqnpshrv"
DB_PASSWORD = "97mISQEJOcIoKlSg"

@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql://postgres.{PROJECT_REF}:{DB_PASSWORD}"
        f"@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
    )

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
    "Foundry": ["2330", "2303", "5347", "3105"],
    "Memory (IDM)": ["6770", "2408"],
    "IC Designers": ["2454", "2379", "3034"],
    "OSAT (Packaging)": ["3711", "6239", "2449"],
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
    "2330": "2330 台積電", "2317": "2317 鴻海",
    "6669": "6669 緯穎", "3231": "3231 緯創",
    "3105": "3105 穩懋", "6488": "6488 環球晶",
    "5483": "5483 中美晶", "3008": "3008 大立光",
    "2454": "2454 聯發科", "2303": "2303 聯電",
    "4938": "4938 和碩", "6770": "6770 力積電",
    "5347": "5347 世界先進", "2382": "2382 廣達",
    "2408": "2408 南亞科", "2379": "2379 瑞昱",
    "3034": "3034 聯詠", "3450": "3450 晶睿",
    "3406": "3406 玉晶光", "3037": "3037 欣興",
    "3189": "3189 景碩", "8046": "8046 南電",
    "3711": "3711 日月光", "6239": "6239 力成",
    "2449": "2449 京元電子",
}

MONTH_NAMES = {
    1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May", 6:"Jun",
    7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"
}

# ── Load data first so sidebar can use real date ranges ──────────
rev_df    = load_revenue()
price_df  = load_prices()
annual_df = load_annual()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filter")

    # Date filters
    available_years  = sorted(rev_df["date"].dt.year.unique().tolist(), reverse=True)
    available_months = sorted(rev_df["date"].dt.month.unique().tolist())

    selected_years = st.multiselect(
        "Filter by year",
        options=available_years,
        default=available_years,
        format_func=lambda x: str(x)
    )

    selected_months = st.multiselect(
        "Filter by month",
        options=available_months,
        default=available_months,
        format_func=lambda x: MONTH_NAMES[x]
    )

    if not selected_years or not selected_months:
        st.warning("Please select at least one year and one month.")
        st.stop()

    # Subsector + stock filters
    subsector = st.selectbox(
        "Filter by sub-sector",
        options=["All"] + list(SUBSECTORS.keys())
    )

    if subsector == "All":
        available = list(WATCHLIST.keys())
        default_options = list(WATCHLIST.keys())
    else:
        available = SUBSECTORS[subsector]
        default_options = SUBSECTORS[subsector]

    selected = st.multiselect(
        "Select stocks",
        options=available,
        default=default_options,
        format_func=lambda x: WATCHLIST_DISPLAY[x]
    )

    if not selected:
        st.warning("Please select at least one stock.")
        st.stop()

# ── Data loaders ──────────────────────────────────────────────────────────────
@st.cache_data
def load_revenue():
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
            year = int(parts[0]) + 1911
            month = int(parts[1])
            return pd.Timestamp(year=year, month=month, day=1)
        except:
            return pd.NaT

    df["date"] = df["report_month"].apply(roc_to_date)
    df = df.dropna(subset=["date"])
    df["date_display"] = df["date"].dt.strftime("%b-%Y")
    return df

@st.cache_data
def load_prices():
    engine = get_engine()
    symbols_tw  = "','".join([f"{k}.TW"  for k in WATCHLIST.keys()])
    symbols_two = "','".join([f"{k}.TWO" for k in WATCHLIST.keys()])
    df = pd.read_sql(f"""
        SELECT date, symbol, open, close
        FROM stock_prices
        WHERE symbol IN ('{symbols_tw}', '{symbols_two}')
        ORDER BY symbol, date
    """, engine)
    df["stock_id"] = df["symbol"].str.replace(".TWO", "").str.replace(".TW", "")
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby(["stock_id", "month"]).agg(
        m_open=("open", "first"),
        m_close=("close", "last")
    ).reset_index()
    return monthly

@st.cache_data
def load_annual():
    engine = get_engine()
    symbols = "','".join(
        [f"{k}.TW"  for k in WATCHLIST.keys()] +
        [f"{k}.TWO" for k in WATCHLIST.keys()]
    )
    df = pd.read_sql(f"""
        SELECT symbol, year, year_open, year_close, year_high, year_low
        FROM stock_annual_k2
        WHERE symbol IN ('{symbols}')
        ORDER BY symbol, year
    """, engine)
    df["stock_id"] = df["symbol"].str.replace(".TWO", "").str.replace(".TW", "")
    df["company"] = df["stock_id"].map(WATCHLIST)
    df["annual_return"] = ((df["year_close"] - df["year_open"]) / df["year_open"] * 100).round(1)
    return df

# ── Helper: apply date filter ─────────────────────────────────────────────────
def apply_date_filter(df, date_col="date"):
    return df[
        (df[date_col].dt.year.isin(selected_years)) &
        (df[date_col].dt.month.isin(selected_months))
    ]

# ── Main ──────────────────────────────────────────────────────────────────────
st.title("Taiwan Stock Dashboard")

tab1, tab2, tab3 = st.tabs(["Monthly Revenue", "YoY Growth", "Revenue vs Price"])

# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Monthly revenue (TWD thousands)")
    filtered = rev_df[rev_df["stock_id"].isin(selected)].copy()
    filtered = apply_date_filter(filtered)

    filtered["rev_display"] = filtered["rev_current"].apply(
        lambda x: f"{x:,.0f}" if pd.notna(x) else ""
    )

    fig = px.line(filtered, x="date", y="rev_current", color="company",
                  labels={"rev_current": "Revenue (TWD thousands)", "date": "Month"})
    st.plotly_chart(fig, use_container_width=True)

    # Checkboxes
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        show_3m_avg = st.checkbox("3M Avg Revenue", value=False)
    with col2:
        show_6m_avg = st.checkbox("6M Avg Revenue", value=False)
    with col3:
        show_3m_yoy = st.checkbox("3M Avg YoY%", value=False)
    with col4:
        show_6m_yoy = st.checkbox("6M Avg YoY%", value=False)

    # Rolling averages (compute on full unfiltered stock data, then filter)
    table_df = rev_df[rev_df["stock_id"].isin(selected)].copy()
    table_df = table_df.sort_values(["company", "date"], ascending=[True, True])
    table_df["3M Avg Rev"] = (
        table_df.groupby("company")["rev_current"]
        .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )
    table_df["6M Avg Rev"] = (
        table_df.groupby("company")["rev_current"]
        .transform(lambda x: x.rolling(6, min_periods=1).mean())
    )
    table_df["3M Avg YoY%"] = (
        table_df.groupby("company")["3M Avg Rev"]
        .transform(lambda x: x.pct_change(12) * 100)
    )
    table_df["6M Avg YoY%"] = (
        table_df.groupby("company")["6M Avg Rev"]
        .transform(lambda x: x.pct_change(12) * 100)
    )

    # Apply date filter after rolling calc
    table_df = apply_date_filter(table_df)
    table_df = table_df.sort_values(["company", "date"], ascending=[True, False])

    # Add rev_display
    table_df["rev_display"] = table_df["rev_current"].apply(
        lambda x: f"{x:,.0f}" if pd.notna(x) else ""
    )

    # Format columns
    for col in ["3M Avg Rev", "6M Avg Rev"]:
        table_df[col] = table_df[col].apply(
            lambda x: f"{x:,.0f}" if pd.notna(x) else ""
        )
    for col in ["yoy_pct", "mom_pct", "3M Avg YoY%", "6M Avg YoY%"]:
        table_df[col] = table_df[col].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else ""
        )

    # Build columns dynamically
    all_cols = ["company_full", "date", "rev_display"]
    if show_3m_avg:
        all_cols += ["3M Avg Rev"]
    if show_6m_avg:
        all_cols += ["6M Avg Rev"]
    if show_3m_yoy:
        all_cols += ["3M Avg YoY%"]
    if show_6m_yoy:
        all_cols += ["6M Avg YoY%"]
    all_cols += ["yoy_pct", "mom_pct"]

    display_df = table_df[all_cols].copy()
    display_df = display_df.rename(columns={
        "company_full": "Company",
        "date":         "Sort Date",
        "rev_display":  "Revenue (TWD k)",
        "yoy_pct":      "YoY %",
        "mom_pct":      "MoM %",
    })

    column_config = {
        "Sort Date":       st.column_config.DateColumn("Month", format="MMM-YYYY"),
        "Company":         st.column_config.TextColumn("Company",         width="small"),
        "Revenue (TWD k)": st.column_config.TextColumn("Revenue (TWD k)", width="medium"),
        "3M Avg Rev":      st.column_config.TextColumn("3M Avg Rev",      width="medium"),
        "6M Avg Rev":      st.column_config.TextColumn("6M Avg Rev",      width="medium"),
        "YoY %":           st.column_config.TextColumn("YoY %",           width="small"),
        "3M Avg YoY%":     st.column_config.TextColumn("3M Avg YoY%",     width="small"),
        "6M Avg YoY%":     st.column_config.TextColumn("6M Avg YoY%",     width="small"),
        "MoM %":           st.column_config.TextColumn("MoM %",           width="small"),
    }

    column_order = ["Company", "Sort Date", "Revenue (TWD k)"]
    if show_3m_avg:
        column_order += ["3M Avg Rev"]
    if show_6m_avg:
        column_order += ["6M Avg Rev"]
    if show_3m_yoy:
        column_order += ["3M Avg YoY%"]
    if show_6m_yoy:
        column_order += ["6M Avg YoY%"]
    column_order += ["YoY %", "MoM %"]

    st.dataframe(
        display_df,
        column_config=column_config,
        column_order=column_order,
        use_container_width=True
    )

# ── Tab 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Year-on-year revenue growth (%)")
    filtered2 = rev_df[rev_df["stock_id"].isin(selected)].dropna(subset=["yoy_pct"]).copy()
    filtered2 = apply_date_filter(filtered2)
    fig = px.line(filtered2, x="date", y="yoy_pct", color="company",
                  labels={"yoy_pct": "YoY Growth %", "date": "Month"})
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

# ── Tab 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Revenue YoY vs stock price performance")
    if len(selected) == 1:
        sid   = selected[0]
        rev   = rev_df[rev_df["stock_id"] == sid][["date", "yoy_pct"]].dropna()
        rev   = apply_date_filter(rev)
        price = price_df[price_df["stock_id"] == sid][["month", "m_close"]].rename(columns={"month": "date"})
        price = apply_date_filter(price)
        merged = pd.merge(rev, price, on="date", how="inner")

        if len(merged) == 0:
            st.warning("No overlapping dates between revenue and price data.")
            st.write("Revenue dates sample:", rev["date"].head())
            st.write("Price dates sample:",   price["date"].head())
        else:
            merged["price_chg"] = merged["m_close"].pct_change() * 100
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=merged["date"], y=merged["yoy_pct"],
                                     name="Revenue YoY %", line=dict(color="#1D9E75")))
            fig.add_trace(go.Scatter(x=merged["date"], y=merged["price_chg"],
                                     name="Price MoM %", line=dict(color="#378ADD"), yaxis="y2"))
            fig.update_layout(
                yaxis2=dict(overlaying="y", side="right"),
                title=f"{sid} {WATCHLIST[sid]}"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        ann = annual_df[annual_df["stock_id"].isin(selected)].copy()
        # Filter annual by selected years
        ann = ann[ann["year"].astype(str).str[:4].astype(int).isin(selected_years)]
        fig = px.bar(ann, x="year", y="annual_return", color="company", barmode="group",
                     labels={"annual_return": "Annual Return %", "year": "Year"},
                     title="Annual stock return (%)")
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig, use_container_width=True)

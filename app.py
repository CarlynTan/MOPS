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
        engine = create_engine(
            f"postgresql://postgres.{PROJECT_REF}:{DB_PASSWORD}"
            f"@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
        )
        return engine
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
                year = int(parts[0]) + 1911
                month = int(parts[1])
                return pd.Timestamp(year=year, month=month, day=1)
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
        df["stock_id"] = df["symbol"].str.replace(".TWO", "").str.replace(".TW", "")
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
        monthly = df.groupby(["stock_id", "month"]).agg(
            m_open=("open", "first"),
            m_close=("close", "last")
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

with st.sidebar:
    st.header("Filter")

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

    subsector = st.selectbox(
        "Filter by sub-sector",
        options=["All"] + list(SUBSECTORS.keys())
    )

    if subsector == "All":
        available     = list(WATCHLIST.keys())
        default_options = list(WATCHLIST.keys())
    else:
        available     = SUBSECTORS[subsector]
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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Revenue (TWD)",
    "💵 Revenue (USD)",
    "📈 Growth Momentum",
    "📉 3M Avg YoY Trend",
    "📉 6M Avg YoY Trend",
    "🔗 Price vs Fundamentals",
])

# ── Helper: build revenue table ───────────────────────────────────────────────
def build_revenue_table(filtered_df, show_3m_avg, show_6m_avg, show_3m_yoy, show_6m_yoy,
                         rev_col="rev_current", unit_label="TWD k"):
    table_df = rev_df[rev_df["stock_id"].isin(selected)].copy()
    if rev_col != "rev_current":
        table_df = table_df.merge(
            fx_df.rename(columns={"month": "date"}), on="date", how="left"
        )
        table_df[rev_col] = table_df["rev_current"] / table_df["twd_per_usd"] / 1000
    table_df = table_df.sort_values(["company", "date"], ascending=[True, True])
    table_df["3M Avg Rev"] = (
        table_df.groupby("company")[rev_col]
        .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )
    table_df["6M Avg Rev"] = (
        table_df.groupby("company")[rev_col]
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
    table_df = apply_date_filter(table_df)
    table_df = table_df.sort_values(["company", "date"], ascending=[True, False])
    table_df["rev_display"] = table_df[rev_col].apply(
        lambda x: f"{x:,.0f}" if pd.notna(x) else ""
    )
    for col in ["3M Avg Rev", "6M Avg Rev"]:
        table_df[col] = table_df[col].apply(
            lambda x: f"{x:,.0f}" if pd.notna(x) else ""
        )
    for col in ["yoy_pct", "mom_pct", "3M Avg YoY%", "6M Avg YoY%"]:
        if col in table_df.columns:
            table_df[col] = table_df[col].apply(
                lambda x: f"{x:.1f}%" if pd.notna(x) else ""
            )
    all_cols = ["company_full", "date", "rev_display"]
    if show_3m_avg: all_cols += ["3M Avg Rev"]
    if show_6m_avg: all_cols += ["6M Avg Rev"]
    if show_3m_yoy: all_cols += ["3M Avg YoY%"]
    if show_6m_yoy: all_cols += ["6M Avg YoY%"]
    all_cols += ["yoy_pct", "mom_pct"]
    display_df = table_df[all_cols].copy()
    display_df = display_df.rename(columns={
        "company_full": "Company",
        "date":         "Sort Date",
        "rev_display":  f"Revenue ({unit_label})",
        "yoy_pct":      "YoY %",
        "mom_pct":      "MoM %",
    })
    column_config = {
        "Sort Date":              st.column_config.DateColumn("Month", format="MMM-YYYY"),
        "Company":                st.column_config.TextColumn("Company",           width="small"),
        f"Revenue ({unit_label})": st.column_config.TextColumn(f"Revenue ({unit_label})", width="medium"),
        "3M Avg Rev":             st.column_config.TextColumn("3M Avg Rev",        width="medium"),
        "6M Avg Rev":             st.column_config.TextColumn("6M Avg Rev",        width="medium"),
        "YoY %":                  st.column_config.TextColumn("YoY %",             width="small"),
        "3M Avg YoY%":            st.column_config.TextColumn("3M Avg YoY%",       width="small"),
        "6M Avg YoY%":            st.column_config.TextColumn("6M Avg YoY%",       width="small"),
        "MoM %":                  st.column_config.TextColumn("MoM %",             width="small"),
    }
    column_order = ["Company", "Sort Date", f"Revenue ({unit_label})"]
    if show_3m_avg: column_order += ["3M Avg Rev"]
    if show_6m_avg: column_order += ["6M Avg Rev"]
    if show_3m_yoy: column_order += ["3M Avg YoY%"]
    if show_6m_yoy: column_order += ["6M Avg YoY%"]
    column_order += ["YoY %", "MoM %"]
    return display_df, column_config, column_order

# ── Tab 1: Revenue (TWD) ──────────────────────────────────────────────────────
with tab1:
    st.subheader("Monthly Revenue (TWD thousands)")

    filtered = rev_df[rev_df["stock_id"].isin(selected)].copy()
    filtered = apply_date_filter(filtered)

    if filtered.empty:
        st.warning("No data available for the selected filters.")
    else:
        fig = px.line(
            filtered, x="date", y="rev_current", color="company",
            labels={"rev_current": "Revenue (TWD thousands)", "date": "Month"},
            color_discrete_sequence=BRAND_COLORS
        )
        fig.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified", plot_bgcolor="white",
            yaxis=dict(gridcolor="#eeeeee"),
            xaxis=dict(gridcolor="#eeeeee"),
        )
        fig.update_traces(line=dict(width=2))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Optional columns**")
        col1, col2, col3, col4 = st.columns(4)
        with col1: show_3m_avg = st.checkbox("3M Avg Revenue", value=False, key="t1_3m_avg")
        with col2: show_6m_avg = st.checkbox("6M Avg Revenue", value=False, key="t1_6m_avg")
        with col3: show_3m_yoy = st.checkbox("3M Avg YoY%",   value=False, key="t1_3m_yoy")
        with col4: show_6m_yoy = st.checkbox("6M Avg YoY%",   value=False, key="t1_6m_yoy")

        display_df, column_config, column_order = build_revenue_table(
            filtered, show_3m_avg, show_6m_avg, show_3m_yoy, show_6m_yoy,
            rev_col="rev_current", unit_label="TWD k"
        )
        st.dataframe(display_df, column_config=column_config,
                     column_order=column_order, use_container_width=True)

# ── Tab 2: Revenue (USD) ──────────────────────────────────────────────────────
with tab2:
    st.subheader("Monthly Revenue (USD millions)")

    if fx_df.empty:
        st.error("FX rate data not available. Please upload fx_rates table to Supabase.")
    else:
        latest_fx = fx_df.sort_values("month").iloc[-1]
        latest_fx_date = latest_fx["month"].strftime("%b %Y")
        latest_fx_rate = latest_fx["twd_per_usd"]

        st.info(
            f"💱 Latest FX rate: **1 USD = {latest_fx_rate:.4f} TWD** (as of {latest_fx_date})  \n"
            f"**Methodology:** Each month's TWD revenue is divided by that month's average TWD/USD "
            f"exchange rate sourced from Yahoo Finance (ticker: TWD=X). Monthly average of daily "
            f"closing rates is used to smooth intra-month volatility."
        )

        rev_usd = rev_df[rev_df["stock_id"].isin(selected)].copy()
        rev_usd = rev_usd.merge(
            fx_df.rename(columns={"month": "date"}), on="date", how="left"
        )
        rev_usd["rev_usd"] = rev_usd["rev_current"] / rev_usd["twd_per_usd"] / 1000
        rev_usd = apply_date_filter(rev_usd)

        if rev_usd.empty:
            st.warning("No data available for the selected filters.")
        else:
            fig_usd = px.line(
                rev_usd, x="date", y="rev_usd", color="company",
                labels={"rev_usd": "Revenue (USD millions)", "date": "Month"},
                color_discrete_sequence=BRAND_COLORS
            )
            fig_usd.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode="x unified", plot_bgcolor="white",
                yaxis=dict(gridcolor="#eeeeee"),
                xaxis=dict(gridcolor="#eeeeee"),
            )
            fig_usd.update_traces(line=dict(width=2))
            st.plotly_chart(fig_usd, use_container_width=True)

            st.markdown("**Optional columns**")
            col1, col2, col3, col4 = st.columns(4)
            with col1: show_3m_avg = st.checkbox("3M Avg Revenue", value=False, key="t2_3m_avg")
            with col2: show_6m_avg = st.checkbox("6M Avg Revenue", value=False, key="t2_6m_avg")
            with col3: show_3m_yoy = st.checkbox("3M Avg YoY%",   value=False, key="t2_3m_yoy")
            with col4: show_6m_yoy = st.checkbox("6M Avg YoY%",   value=False, key="t2_6m_yoy")

            rev_usd_table = rev_df[rev_df["stock_id"].isin(selected)].copy()
            rev_usd_table = rev_usd_table.merge(
                fx_df.rename(columns={"month": "date"}), on="date", how="left"
            )
            rev_usd_table["rev_usd"] = rev_usd_table["rev_current"] / rev_usd_table["twd_per_usd"] / 1000
            rev_usd_table = rev_usd_table.sort_values(["company", "date"], ascending=[True, True])
            rev_usd_table["3M Avg Rev"] = (
                rev_usd_table.groupby("company")["rev_usd"]
                .transform(lambda x: x.rolling(3, min_periods=1).mean())
            )
            rev_usd_table["6M Avg Rev"] = (
                rev_usd_table.groupby("company")["rev_usd"]
                .transform(lambda x: x.rolling(6, min_periods=1).mean())
            )
            rev_usd_table["3M Avg YoY%"] = (
                rev_usd_table.groupby("company")["3M Avg Rev"]
                .transform(lambda x: x.pct_change(12) * 100)
            )
            rev_usd_table["6M Avg YoY%"] = (
                rev_usd_table.groupby("company")["6M Avg Rev"]
                .transform(lambda x: x.pct_change(12) * 100)
            )
            rev_usd_table = apply_date_filter(rev_usd_table)
            rev_usd_table = rev_usd_table.sort_values(["company", "date"], ascending=[True, False])
            rev_usd_table["rev_display"] = rev_usd_table["rev_usd"].apply(
                lambda x: f"{x:,.2f}" if pd.notna(x) else ""
            )
            for col in ["3M Avg Rev", "6M Avg Rev"]:
                rev_usd_table[col] = rev_usd_table[col].apply(
                    lambda x: f"{x:,.2f}" if pd.notna(x) else ""
                )
            for col in ["yoy_pct", "mom_pct", "3M Avg YoY%", "6M Avg YoY%"]:
                if col in rev_usd_table.columns:
                    rev_usd_table[col] = rev_usd_table[col].apply(
                        lambda x: f"{x:.1f}%" if pd.notna(x) else ""
                    )
            all_cols = ["company_full", "date", "rev_display"]
            if show_3m_avg: all_cols += ["3M Avg Rev"]
            if show_6m_avg: all_cols += ["6M Avg Rev"]
            if show_3m_yoy: all_cols += ["3M Avg YoY%"]
            if show_6m_yoy: all_cols += ["6M Avg YoY%"]
            all_cols += ["yoy_pct", "mom_pct"]
            display_usd = rev_usd_table[all_cols].copy()
            display_usd = display_usd.rename(columns={
                "company_full": "Company", "date": "Sort Date",
                "rev_display": "Revenue (USD mn)", "yoy_pct": "YoY %", "mom_pct": "MoM %",
            })
            col_cfg_usd = {
                "Sort Date":        st.column_config.DateColumn("Month", format="MMM-YYYY"),
                "Company":          st.column_config.TextColumn("Company",          width="small"),
                "Revenue (USD mn)": st.column_config.TextColumn("Revenue (USD mn)", width="medium"),
                "3M Avg Rev":       st.column_config.TextColumn("3M Avg Rev",       width="medium"),
                "6M Avg Rev":       st.column_config.TextColumn("6M Avg Rev",       width="medium"),
                "YoY %":            st.column_config.TextColumn("YoY %",            width="small"),
                "3M Avg YoY%":      st.column_config.TextColumn("3M Avg YoY%",      width="small"),
                "6M Avg YoY%":      st.column_config.TextColumn("6M Avg YoY%",      width="small"),
                "MoM %":            st.column_config.TextColumn("MoM %",            width="small"),
            }
            col_order_usd = ["Company", "Sort Date", "Revenue (USD mn)"]
            if show_3m_avg: col_order_usd += ["3M Avg Rev"]
            if show_6m_avg: col_order_usd += ["6M Avg Rev"]
            if show_3m_yoy: col_order_usd += ["3M Avg YoY%"]
            if show_6m_yoy: col_order_usd += ["6M Avg YoY%"]
            col_order_usd += ["YoY %", "MoM %"]
            st.dataframe(display_usd, column_config=col_cfg_usd,
                         column_order=col_order_usd, use_container_width=True)

# ── Tab 3: Growth Momentum ────────────────────────────────────────────────────
with tab3:
    st.subheader("Year-on-Year Revenue Growth (%)")

    filtered2 = rev_df[rev_df["stock_id"].isin(selected)].dropna(subset=["yoy_pct"]).copy()
    filtered2 = apply_date_filter(filtered2)

    if filtered2.empty:
        st.warning("No YoY data available for the selected filters.")
    else:
        fig2 = px.line(
            filtered2, x="date", y="yoy_pct", color="company",
            labels={"yoy_pct": "YoY Growth %", "date": "Month"},
            color_discrete_sequence=BRAND_COLORS
        )
        fig2.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig2.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified", plot_bgcolor="white",
            yaxis=dict(gridcolor="#eeeeee", zeroline=True, zerolinecolor="#cccccc"),
            xaxis=dict(gridcolor="#eeeeee"),
        )
        fig2.update_traces(line=dict(width=2))
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("**YoY Growth Data**")
        yoy_table = filtered2[["company_full", "date", "yoy_pct", "mom_pct"]].copy()
        yoy_table = yoy_table.sort_values(["company_full", "date"], ascending=[True, False])
        yoy_table["yoy_pct"] = yoy_table["yoy_pct"].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else ""
        )
        yoy_table["mom_pct"] = yoy_table["mom_pct"].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else ""
        )
        yoy_table = yoy_table.rename(columns={
            "company_full": "Company", "date": "Sort Date",
            "yoy_pct": "YoY %", "mom_pct": "MoM %",
        })
        st.dataframe(
            yoy_table,
            column_config={
                "Sort Date": st.column_config.DateColumn("Month", format="MMM-YYYY"),
                "Company":   st.column_config.TextColumn("Company", width="small"),
                "YoY %":     st.column_config.TextColumn("YoY %",   width="small"),
                "MoM %":     st.column_config.TextColumn("MoM %",   width="small"),
            },
            column_order=["Company", "Sort Date", "YoY %", "MoM %"],
            use_container_width=True
        )

# ── Tab 4: 3M Avg YoY Trend ───────────────────────────────────────────────────
with tab4:
    st.subheader("3-Month Average YoY Growth (%)")
    st.caption("Smoothed YoY: 3M rolling average revenue vs same period prior year.")

    chart_type_3m = st.radio("Chart type", ["Line", "Bar"], horizontal=True, key="chart_3m")

    roll_df = rev_df[rev_df["stock_id"].isin(selected)].copy()
    roll_df = roll_df.sort_values(["company", "date"], ascending=[True, True])
    roll_df["3M Avg Rev"] = (
        roll_df.groupby("company")["rev_current"]
        .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )
    roll_df["3M Avg YoY%"] = (
        roll_df.groupby("company")["3M Avg Rev"]
        .transform(lambda x: x.pct_change(12) * 100)
    )
    roll_df = apply_date_filter(roll_df)
    roll_df = roll_df.dropna(subset=["3M Avg YoY%"])

    if roll_df.empty:
        st.warning("No data available for the selected filters.")
    else:
        if chart_type_3m == "Line":
            fig4 = px.line(
                roll_df, x="date", y="3M Avg YoY%", color="company",
                labels={"3M Avg YoY%": "3M Avg YoY %", "date": "Month"},
                color_discrete_sequence=BRAND_COLORS
            )
        else:
            fig4 = px.bar(
                roll_df, x="date", y="3M Avg YoY%", color="company",
                barmode="group",
                labels={"3M Avg YoY%": "3M Avg YoY %", "date": "Month"},
                color_discrete_sequence=BRAND_COLORS
            )
        fig4.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig4.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified", plot_bgcolor="white",
            yaxis=dict(gridcolor="#eeeeee", zeroline=True, zerolinecolor="#cccccc"),
            xaxis=dict(gridcolor="#eeeeee"),
        )
        if chart_type_3m == "Line":
            fig4.update_traces(line=dict(width=2))
        st.plotly_chart(fig4, use_container_width=True)

        t4 = roll_df[["company_full", "date", "rev_current", "3M Avg Rev", "3M Avg YoY%", "mom_pct"]].copy()
        t4 = t4.sort_values(["company_full", "date"], ascending=[True, False])
        t4["rev_current"] = t4["rev_current"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        t4["3M Avg Rev"]  = t4["3M Avg Rev"].apply(lambda x: f"{x:,.0f}"  if pd.notna(x) else "")
        t4["3M Avg YoY%"] = t4["3M Avg YoY%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        t4["mom_pct"]     = t4["mom_pct"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        t4 = t4.rename(columns={
            "company_full": "Company", "date": "Sort Date",
            "rev_current": "Revenue (TWD k)", "3M Avg Rev": "3M Avg Rev (TWD k)",
            "3M Avg YoY%": "3M Avg YoY%", "mom_pct": "MoM %"
        })
        st.dataframe(
            t4,
            column_config={
                "Sort Date":           st.column_config.DateColumn("Month", format="MMM-YYYY"),
                "Company":             st.column_config.TextColumn("Company",             width="small"),
                "Revenue (TWD k)":     st.column_config.TextColumn("Revenue (TWD k)",     width="medium"),
                "3M Avg Rev (TWD k)":  st.column_config.TextColumn("3M Avg Rev (TWD k)",  width="medium"),
                "3M Avg YoY%":         st.column_config.TextColumn("3M Avg YoY%",         width="small"),
                "MoM %":               st.column_config.TextColumn("MoM %",               width="small"),
            },
            column_order=["Company", "Sort Date", "Revenue (TWD k)", "3M Avg Rev (TWD k)", "3M Avg YoY%", "MoM %"],
            use_container_width=True
        )

# ── Tab 5: 6M Avg YoY Trend ───────────────────────────────────────────────────
with tab5:
    st.subheader("6-Month Average YoY Growth (%)")
    st.caption("Smoothed YoY: 6M rolling average revenue vs same period prior year.")

    chart_type_6m = st.radio("Chart type", ["Line", "Bar"], horizontal=True, key="chart_6m")

    roll6_df = rev_df[rev_df["stock_id"].isin(selected)].copy()
    roll6_df = roll6_df.sort_values(["company", "date"], ascending=[True, True])
    roll6_df["6M Avg Rev"] = (
        roll6_df.groupby("company")["rev_current"]
        .transform(lambda x: x.rolling(6, min_periods=1).mean())
    )
    roll6_df["6M Avg YoY%"] = (
        roll6_df.groupby("company")["6M Avg Rev"]
        .transform(lambda x: x.pct_change(12) * 100)
    )
    roll6_df = apply_date_filter(roll6_df)
    roll6_df = roll6_df.dropna(subset=["6M Avg YoY%"])

    if roll6_df.empty:
        st.warning("No data available for the selected filters.")
    else:
        if chart_type_6m == "Line":
            fig5 = px.line(
                roll6_df, x="date", y="6M Avg YoY%", color="company",
                labels={"6M Avg YoY%": "6M Avg YoY %", "date": "Month"},
                color_discrete_sequence=BRAND_COLORS
            )
        else:
            fig5 = px.bar(
                roll6_df, x="date", y="6M Avg YoY%", color="company",
                barmode="group",
                labels={"6M Avg YoY%": "6M Avg YoY %", "date": "Month"},
                color_discrete_sequence=BRAND_COLORS
            )
        fig5.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig5.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified", plot_bgcolor="white",
            yaxis=dict(gridcolor="#eeeeee", zeroline=True, zerolinecolor="#cccccc"),
            xaxis=dict(gridcolor="#eeeeee"),
        )
        if chart_type_6m == "Line":
            fig5.update_traces(line=dict(width=2))
        st.plotly_chart(fig5, use_container_width=True)

        t5 = roll6_df[["company_full", "date", "rev_current", "6M Avg Rev", "6M Avg YoY%", "mom_pct"]].copy()
        t5 = t5.sort_values(["company_full", "date"], ascending=[True, False])
        t5["rev_current"] = t5["rev_current"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        t5["6M Avg Rev"]  = t5["6M Avg Rev"].apply(lambda x: f"{x:,.0f}"  if pd.notna(x) else "")
        t5["6M Avg YoY%"] = t5["6M Avg YoY%"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        t5["mom_pct"]     = t5["mom_pct"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
        t5 = t5.rename(columns={
            "company_full": "Company", "date": "Sort Date",
            "rev_current": "Revenue (TWD k)", "6M Avg Rev": "6M Avg Rev (TWD k)",
            "6M Avg YoY%": "6M Avg YoY%", "mom_pct": "MoM %"
        })
        st.dataframe(
            t5,
            column_config={
                "Sort Date":           st.column_config.DateColumn("Month", format="MMM-YYYY"),
                "Company":             st.column_config.TextColumn("Company",             width="small"),
                "Revenue (TWD k)":     st.column_config.TextColumn("Revenue (TWD k)",     width="medium"),
                "6M Avg Rev (TWD k)":  st.column_config.TextColumn("6M Avg Rev (TWD k)",  width="medium"),
                "6M Avg YoY%":         st.column_config.TextColumn("6M Avg YoY%",         width="small"),
                "MoM %":               st.column_config.TextColumn("MoM %",               width="small"),
            },
            column_order=["Company", "Sort Date", "Revenue (TWD k)", "6M Avg Rev (TWD k)", "6M Avg YoY%", "MoM %"],
            use_container_width=True
        )

# ── Tab 6: Price vs Fundamentals ──────────────────────────────────────────────
with tab6:
    st.subheader("Price vs Fundamentals")

    if len(selected) == 1:
        sid   = selected[0]
        rev   = rev_df[rev_df["stock_id"] == sid][["date", "yoy_pct", "rev_current"]].dropna(subset=["yoy_pct"])
        rev   = apply_date_filter(rev)
        price = price_df[price_df["stock_id"] == sid][["month", "m_close"]].rename(columns={"month": "date"})
        price = apply_date_filter(price)
        merged = pd.merge(rev, price, on="date", how="inner")

        if merged.empty:
            st.warning("No overlapping dates between revenue and price data for this stock.")
        else:
            merged = merged.sort_values("date")
            merged["price_3m_chg"] = merged["m_close"].pct_change(3) * 100

            use_log = st.checkbox("Log scale — Revenue vs Share Price", value=False)

            if use_log:
                merged_log = merged.dropna(subset=["m_close", "rev_current"])
                merged_log = merged_log[merged_log["m_close"] > 0]
                merged_log = merged_log[merged_log["rev_current"] > 0]

                fig_log = go.Figure()
                fig_log.add_trace(go.Scatter(
                    x=merged_log["date"],
                    y=np.log(merged_log["rev_current"]),
                    name="ln(Revenue TWD k)",
                    line=dict(color="#1D9E75", width=2)
                ))
                fig_log.add_trace(go.Scatter(
                    x=merged_log["date"],
                    y=np.log(merged_log["m_close"]),
                    name="ln(Share Price TWD)",
                    line=dict(color="#378ADD", width=2),
                    yaxis="y2"
                ))
                fig_log.update_layout(
                    title=f"{WATCHLIST_DISPLAY.get(sid, sid)} — Log Scale: Revenue vs Share Price",
                    yaxis=dict(
                        title="ln(Revenue)",
                        gridcolor="#eeeeee",
                        zeroline=True, zerolinecolor="#cccccc"
                    ),
                    yaxis2=dict(
                        title="ln(Share Price)",
                        overlaying="y", side="right",
                        gridcolor="#eeeeee"
                    ),
                    hovermode="x unified", plot_bgcolor="white",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig_log, use_container_width=True)
                st.caption(
                    "Log scale shows proportional growth rates. Parallel lines indicate revenue and "
                    "price growing at similar rates; divergence signals re-rating or de-rating."
                )

            else:
                fig3 = go.Figure()
                fig3.add_trace(go.Bar(
                    x=merged["date"], y=merged["yoy_pct"],
                    name="Revenue YoY %",
                    marker_color="#1D9E75",
                    opacity=0.75,
                    yaxis="y"
                ))
                fig3.add_trace(go.Scatter(
                    x=merged["date"], y=merged["price_3m_chg"],
                    name="Price 3M Chg %",
                    line=dict(color="#378ADD", width=2.5),
                    yaxis="y2"
                ))
                max_abs_price = merged["price_3m_chg"].abs().max()
                price_range = [-max_abs_price * 1.5, max_abs_price * 1.5]

                fig3.update_layout(
                    title=f"{WATCHLIST_DISPLAY.get(sid, sid)}",
                    yaxis=dict(
                        title="Revenue YoY %",
                        gridcolor="#eeeeee",
                        zeroline=True, zerolinecolor="#cccccc"
                    ),
                    yaxis2=dict(
                        title="Price 3M Chg %",
                        overlaying="y", side="right",
                        gridcolor="#eeeeee",
                        range=price_range,
                        zeroline=True, zerolinecolor="#cccccc"
                    ),
                    hovermode="x unified", plot_bgcolor="white",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    bargap=0.2,
                )
                st.plotly_chart(fig3, use_container_width=True)

    else:
        st.info(
            "💡 Select a **single stock** from the sidebar to see the Revenue YoY vs Price chart. "
            "With multiple stocks selected, the annual return comparison is shown below."
        )
        ann = annual_df[annual_df["stock_id"].isin(selected)].copy()
        ann = ann[ann["year"].astype(str).str[:4].astype(int).isin(selected_years)]

        if ann.empty:
            st.warning("No annual return data available for the selected filters.")
        else:
            fig_ann = px.bar(
                ann, x="year", y="annual_return", color="company",
                barmode="group",
                labels={"annual_return": "Annual Return %", "year": "Year"},
                title="Annual Stock Return (%)",
                color_discrete_sequence=BRAND_COLORS
            )
            fig_ann.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig_ann.update_layout(
                plot_bgcolor="white",
                yaxis=dict(gridcolor="#eeeeee"),
                xaxis=dict(gridcolor="#eeeeee"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_ann, use_container_width=True)

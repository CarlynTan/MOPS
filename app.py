import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine

st.cache_data.clear()

st.set_page_config(page_title="Taiwan Stock Dashboard", layout="wide")

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
    "3037": "Unimicron", "3189": "Kinsus", "8046": "Nanya PCB"
}

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
    return df

@st.cache_data
def load_prices():
    engine = get_engine()
    symbols_tw = "','".join([f"{k}.TW" for k in WATCHLIST.keys()])
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
        [f"{k}.TW" for k in WATCHLIST.keys()] +
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

st.title("Taiwan Stock Dashboard")

rev_df = load_revenue()
price_df = load_prices()
annual_df = load_annual()

with st.sidebar:
    st.header("Filter")
    selected = st.multiselect(
        "Select stocks",
        options=list(WATCHLIST.keys()),
        default=["2330", "2454", "2317"],
        format_func=lambda x: f"{x} {WATCHLIST[x]}"
    )
    if not selected:
        st.warning("Please select at least one stock.")
        st.stop()

tab1, tab2, tab3 = st.tabs(["Monthly Revenue", "YoY Growth", "Revenue vs Price"])

with tab1:
    st.subheader("Monthly revenue (TWD thousands)")
    filtered = rev_df[rev_df["stock_id"].isin(selected)]
    fig = px.line(filtered, x="date", y="rev_current", color="company",
                  labels={"rev_current": "Revenue", "date": "Month"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        filtered[["company", "date", "rev_current", "yoy_pct", "mom_pct"]]
        .sort_values(["company", "date"], ascending=[True, False])
        .rename(columns={"company": "Company", "date": "Month",
                         "rev_current": "Revenue", "yoy_pct": "YoY %", "mom_pct": "MoM %"}),
        use_container_width=True
    )

with tab2:
    st.subheader("Year-on-year revenue growth (%)")
    filtered = rev_df[rev_df["stock_id"].isin(selected)].dropna(subset=["yoy_pct"])
    fig = px.line(filtered, x="date", y="yoy_pct", color="company",
                  labels={"yoy_pct": "YoY Growth %", "date": "Month"})
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Revenue YoY vs stock price performance")
    if len(selected) == 1:
        sid = selected[0]
        rev = rev_df[rev_df["stock_id"] == sid][["date", "yoy_pct"]].dropna()
        price = price_df[price_df["stock_id"] == sid][["month", "m_close"]].rename(columns={"month": "date"})
        merged = pd.merge(rev, price, on="date", how="inner")

        st.write(f"Debug — rev rows: {len(rev)}, price rows: {len(price)}, merged rows: {len(merged)}")

        if len(merged) == 0:
            st.warning("No overlapping dates between revenue and price data.")
            st.write("Revenue dates sample:", rev["date"].head())
            st.write("Price dates sample:", price["date"].head())
        else:
            merged["price_chg"] = merged["m_close"].pct_change() * 100
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=merged["date"], y=merged["yoy_pct"], name="Revenue YoY %", line=dict(color="#1D9E75")))
            fig.add_trace(go.Scatter(x=merged["date"], y=merged["price_chg"], name="Price MoM %", line=dict(color="#378ADD"), yaxis="y2"))
            fig.update_layout(yaxis2=dict(overlaying="y", side="right"), title=f"{sid} {WATCHLIST[sid]}")
            st.plotly_chart(fig, use_container_width=True)
    else:
        ann = annual_df[annual_df["stock_id"].isin(selected)]
        fig = px.bar(ann, x="year", y="annual_return", color="company", barmode="group", labels={"annual_return": "Annual Return %", "year": "Year"}, title="Annual stock return (%)")
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig, use_container_width=True)

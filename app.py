import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from engine import fetch_active_markets, fetch_event_markets, run_simulation, fetch_crypto_price
from datetime import datetime

st.set_page_config(
    page_title="Arbitrage Pro | Polymarket Scanner",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .main {
        background: #0e1117;
        color: #e0e0e0;
    }
    .stMetric {
        background: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #4e73df;
    }
    .market-card {
        background: #1e2130;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #2e3148;
    }
    .arb-alert {
        color: #1cc88a;
        font-weight: bold;
    }
    .stButton>button {
        border-radius: 8px;
        background-color: #4e73df;
        color: white;
        border: none;
    }
    .stExpander {
        border: 1px solid #2e3148 !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

def render_simulation_graph(paths, strikes, market_type, asset_name):
    fig = go.Figure()
    n_steps = paths.shape[0]
    x = list(range(n_steps))
    for i in range(min(50, paths.shape[1])):
        fig.add_trace(go.Scatter(y=paths[:, i], mode='lines', line=dict(width=0.5, color='rgba(78, 115, 223, 0.2)'), showlegend=False))
    
    avg_path = np.mean(paths, axis=1)
    fig.add_trace(go.Scatter(y=avg_path, mode='lines', line=dict(width=2, color='#4e73df'), name='Mean Path'))
    
    for s in strikes:
        fig.add_trace(go.Scatter(x=[0, n_steps], y=[s, s], mode='lines', line=dict(dash='dash', color='#e74a3b'), name=f'Strike ${s:,.0f}'))
    
    fig.update_layout(
        title=f"Monte Carlo Simulation: {asset_name}",
        xaxis_title="Simulation Steps (Hourly)",
        yaxis_title="Price ($)",
        template="plotly_dark",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("Arbitrage")
    st.subheader("Quantitative Analysis & Prediction for Prediction Markets")
    
    if "prices" not in st.session_state:
        with st.spinner("Fetching live market data..."):
            st.session_state.prices = {
                "Bitcoin": fetch_crypto_price("BTC/USDT") or 95000.0
            }

    st.sidebar.metric("BTC Price", f"${st.session_state.prices['Bitcoin']:,.0f}")

    st.sidebar.divider()
    st.sidebar.header("Event Scanner")
    custom_url = st.sidebar.text_input("Polymarket Event URL", placeholder="https://polymarket.com/event/...")
    
    if custom_url and st.sidebar.button("Scan Event"):
        with st.spinner("Analyzing markets..."):
            st.session_state.custom_markets = fetch_event_markets(custom_url)
            if not st.session_state.custom_markets:
                st.sidebar.error("No compatible markets found.")

    if st.sidebar.button("Refresh All Markets"):
        st.session_state.market_list = fetch_active_markets()

    if "market_list" not in st.session_state:
        st.session_state.market_list = fetch_active_markets()

    markets_to_show = []
    if "custom_markets" in st.session_state:
        markets_to_show = st.session_state.custom_markets
        st.info(f"Showing {len(markets_to_show)} markets from custom event.")
        if st.button("Clear Custom View"):
            del st.session_state.custom_markets
            st.rerun()
    else:
        markets_to_show = st.session_state.market_list

    if not markets_to_show:
        st.warning("No active markets found.")
        return

    df = pd.DataFrame(markets_to_show)
    df['DateStr'] = df['Expiry'].dt.strftime("%B %d, %Y")
    dates = sorted(df['DateStr'].unique(), key=lambda x: datetime.strptime(x, "%B %d, %Y"))
    
    for date_str in dates:
        st.markdown(f"### {date_str}")
        date_df = df[df['DateStr'] == date_str].sort_values("Strike")
        
        for _, m in date_df.iterrows():
            with st.expander(f"{m['Market']} | Poly: {m['Poly Prob']:.1%}"):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.write("**Parameters**")
                    st.write(f"- Asset: `{m['Asset']}`")
                    st.write(f"- Market Type: `{m['Market Type']}`")
                    if m['Market Type'] == 'between':
                        st.write(f"- Range: `${m['Strikes'][0]:,.0f}` - `${m['Strikes'][1]:,.0f}`")
                    else:
                        st.write(f"- Strike: `${m['Strike']:,.0f}`")
                
                with col2:
                    st.write("**Valuation**")
                    asset_price = st.session_state.prices.get(m['Asset'], 1.0)
                    
                    sim_key = f"sim_{m['id']}"
                    if sim_key not in st.session_state:
                        if st.button("Run MC Engine", key=f"btn_{m['id']}"):
                            with st.spinner("Simulating..."):
                                prob, paths = run_simulation(m, asset_price)
                                st.session_state[sim_key] = {"prob": prob, "paths": paths}
                                st.rerun()
                    
                    if sim_key in st.session_state:
                        prob = st.session_state[sim_key]['prob']
                        poly_prob = m['Poly Prob']
                        delta = prob - poly_prob
                        
                        st.metric("Model Probability", f"{prob:.1%}", delta=f"{delta:+.1%}")
                        st.progress(prob)
                        st.write(f"Polymarket Odds: {poly_prob:.1%}")
                        
                        if abs(delta) > 0.05:
                            st.success(f" ARBITRAGE DETECTED: {delta:+.1%}")

                if sim_key in st.session_state:
                    if st.checkbox("Show Simulation Graph", key=f"chk_{m['id']}"):
                        render_simulation_graph(
                            st.session_state[sim_key]['paths'], 
                            m['Strikes'], 
                            m['Market Type'], 
                            m['Asset']
                        )

if __name__ == "__main__":
    main()

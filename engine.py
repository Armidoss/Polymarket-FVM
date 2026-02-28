import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil import parser
import json
import re
import ccxt

GAMMA_API = "https://gamma-api.polymarket.com"

def get_crypto_markets(asset="Bitcoin"):
    try:
        query_map = {
            "Bitcoin": ["Bitcoin", "BTC"],
            "Ethereum": ["Ethereum", "ETH"],
            "Solana": ["Solana", "SOL"]
        }
        queries = query_map.get(asset, [asset])
        all_markets = []
        for q in queries:
            params = {
                "limit": 500,
                "active": "true",
                "archived": "false",
                "closed": "false",
                "query": q,
                "order": "volume24hr",
                "ascending": "false"
            }
            response = requests.get(f"{GAMMA_API}/markets", params=params)
            if response.status_code == 200:
                all_markets.extend(response.json())
        seen_ids = set()
        unique_markets = []
        keywords = [k.lower() for k in queries]
        for m in all_markets:
            mid = m.get('id') or m.get('conditionId')
            if not mid or mid in seen_ids:
                continue
            question = m.get('question', '').lower()
            slug = m.get('slug', '').lower()
            if any(kw in question or kw in slug for kw in keywords):
                seen_ids.add(mid)
                unique_markets.append(m)
        return unique_markets
    except:
        return []

def get_event_by_slug(slug):
    try:
        params = {"slug": slug}
        response = requests.get(f"{GAMMA_API}/events", params=params)
        if response.status_code == 200:
            events = response.json()
            if events:
                return events[0]
        return None
    except:
        return None

def fetch_crypto_price(symbol='BTC/USDT'):
    try:
        exchange = ccxt.binance()
        ticker = exchange.fetch_ticker(symbol)
        return float(ticker['last'])
    except:
        return None

def simulate_gbm(S0, mu, sigma, T, dt, n_paths):
    n_steps = int(T / dt)
    paths = np.zeros((n_steps + 1, n_paths))
    paths[0] = S0
    for t in range(1, n_steps + 1):
        z = np.random.standard_normal(n_paths)
        paths[t] = paths[t-1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z)
    return paths

def parse_market_list(raw_markets):
    parsed_markets = []
    for m in raw_markets:
        try:
            question = m.get('question', '')
            q_lower = question.lower()
            slug_lower = m.get('slug', '').lower()
            if "ethereum" in q_lower or "eth" in q_lower or "ethereum" in slug_lower or "eth" in slug_lower:
                asset_type = "Ethereum"
            elif "solana" in q_lower or "sol" in q_lower or "solana" in slug_lower or "sol" in slug_lower:
                asset_type = "Solana"
            elif "bitcoin" in q_lower or "btc" in q_lower or "bitcoin" in slug_lower or "btc" in slug_lower:
                asset_type = "Bitcoin"
            else:
                asset_type = m.get('asset_type', 'Other')
            price_matches = re.finditer(r'(\$)?(\d{1,3}(?:,\d{3})*|\d+(?:\.\d+)?)\s*(k|K)?', question)
            strikes = []
            for match in price_matches:
                has_dollar = match.group(1) is not None
                raw_val = match.group(2).replace(',', '')
                multiplier = match.group(3)
                val = float(raw_val)
                is_explicit = has_dollar or multiplier is not None
                if multiplier and multiplier.lower() == 'k':
                    val *= 1000
                if asset_type == "Bitcoin" and 2020 <= val <= 2035:
                    if not is_explicit:
                        continue
                min_price = 1000 if asset_type == "Bitcoin" else 50 if asset_type == "Ethereum" else 5
                if is_explicit or val > min_price:
                    strikes.append(val)
            strikes = sorted(list(set(strikes)))
            if not strikes and asset_type != 'Other':
                continue
            if not strikes and asset_type == 'Other':
                 strikes = [0]
            market_type = "above"
            if "between" in q_lower or "range" in q_lower:
                if len(strikes) >= 2:
                    market_type = "between"
            elif "dip" in q_lower or "drop" in q_lower:
                market_type = "touch_down"
            elif "reach" in q_lower or "hit" in q_lower or "touch" in q_lower:
                market_type = "touch_up"
            elif any(word in q_lower for word in ["below", "lower", "<"]):
                market_type = "below"
            elif any(word in q_lower for word in ["above", "higher", ">"]):
                market_type = "above"
            if 'endDate' in m:
                expiry = parser.parse(m['endDate']).replace(tzinfo=None)
            else:
                continue
            now = datetime.utcnow()
            diff = expiry - now
            days_remaining = diff.total_seconds() / 86400
            if days_remaining <= 0:
                continue
            try:
                outcome_prices = json.loads(m.get('outcomePrices', '["0", "0"]'))
                poly_prob = float(outcome_prices[0])
            except:
                poly_prob = 0.0
            parsed_markets.append({
                "id": m.get('id') or m.get('conditionId'),
                "Market": question,
                "Asset": asset_type,
                "Strike": strikes[0] if strikes else 0,
                "Strikes": strikes,
                "Market Type": market_type,
                "Expiry": expiry,
                "Days Left": days_remaining,
                "Poly Prob": poly_prob
            })
        except:
            continue
    return parsed_markets

def fetch_active_markets():
    all_crypto_markets = []
    assets = ["Bitcoin"]
    for asset in assets:
        markets = get_crypto_markets(asset)
        for m in markets:
            m["asset_type"] = asset
            all_crypto_markets.append(m)
    return parse_market_list(all_crypto_markets)

def fetch_event_markets(url):
    try:
        slug = url.rstrip('/').split('/')[-1].split('?')[0]
        event_data = get_event_by_slug(slug)
        if not event_data or 'markets' not in event_data:
            return []
        return parse_market_list(event_data['markets'])
    except:
        return []

def run_simulation(market_data, current_price, n_paths=5000):
    try:
        asset_type = market_data.get('Asset', 'Bitcoin')
        vol_map = {"Bitcoin": 0.6, "Ethereum": 0.7, "Solana": 0.9}
        sigma = vol_map.get(asset_type, 0.7)
        T_years = market_data['Days Left'] / 365.25
        dt_hourly = 1 / (365.25 * 24)
        paths = simulate_gbm(current_price, 0.05, sigma, T_years, dt_hourly, n_paths)
        final_prices = paths[-1, :]
        strikes = market_data.get('Strikes', [market_data.get('Strike', 0)])
        m_type = market_data.get('Market Type', 'above')
        if m_type == "above":
            mc_prob = np.mean(final_prices > strikes[0])
        elif m_type == "below":
            mc_prob = np.mean(final_prices < strikes[0])
        elif m_type == "between" and len(strikes) >= 2:
            mc_prob = np.mean((final_prices >= strikes[0]) & (final_prices <= strikes[1]))
        elif m_type == "touch_down":
            min_prices = np.min(paths, axis=0)
            mc_prob = np.mean(min_prices <= strikes[0])
        elif m_type == "touch_up":
            max_prices = np.max(paths, axis=0)
            mc_prob = np.mean(max_prices >= strikes[0])
        else:
            mc_prob = np.mean(final_prices > strikes[0])
        return float(mc_prob), paths
    except:
        return 0.0, None

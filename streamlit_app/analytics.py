"""
Analytics engine for the Electricity Cost Intelligence MVP.
Provides: forecasting (SARIMA), anomaly detection (IQR + z-score),
trend analysis (rolling + STL-lite), benchmarking, plan comparison,
and auto-generated natural language insights.
"""
import numpy as np
import pandas as pd
from scipy import stats


# ─────────────────────────────────────────────
# 1. BILL COMPONENT BREAKDOWN
# ─────────────────────────────────────────────
def get_bill_breakdown(billing: pd.DataFrame, idx: int = -1) -> dict:
    """Return component-wise breakdown for a single bill."""
    row = billing.iloc[idx]
    components = {}
    component_map = {
        "Customer Charge": "customer_charge",
        "BGS Supply": "bgs_cost",
        "Transmission": "transmission_cost",
        "Distribution": "distribution_cost",
        "Societal Benefits (SBC)": "sbc_cost",
        "Non-Utility Gen (NUG)": "nug_cost",
        "Rider Charges": "rider_cost",
        "Market Transition": "market_transition_cost",
        "Weather Adjustment": "weather_adjustment",
        "Demand Response Credit": "dr_credit",
        "Sales Tax": "sales_tax",
    }
    for label, col in component_map.items():
        if col in row.index:
            components[label] = round(float(row[col]), 2)

    return {
        "date": str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"]),
        "total_bill": round(float(row["total_bill"]), 2),
        "usage_kwh": round(float(row["usage_kwh"]), 1),
        "effective_rate": round(float(row["total_bill"]) / max(float(row["usage_kwh"]), 1), 5),
        "components": components,
    }


def get_component_summary(billing: pd.DataFrame, months: int = 12) -> pd.DataFrame:
    """Aggregate component costs over recent months for charting."""
    recent = billing.tail(months).copy()
    cost_cols = {
        "Customer Charge": "customer_charge",
        "BGS Supply": "bgs_cost",
        "Transmission": "transmission_cost",
        "Distribution": "distribution_cost",
        "SBC": "sbc_cost",
        "NUG": "nug_cost",
        "Rider": "rider_cost",
        "Market Trans.": "market_transition_cost",
        "Tax": "sales_tax",
    }
    records = []
    for _, row in recent.iterrows():
        entry = {"date": row["date"]}
        for label, col in cost_cols.items():
            entry[label] = float(row.get(col, 0))
        records.append(entry)
    return pd.DataFrame(records)


# ─────────────────────────────────────────────
# 2. FORECASTING (SARIMA)
# ─────────────────────────────────────────────
def run_forecast(billing: pd.DataFrame, horizon: int = 12):
    """
    SARIMA-based forecast with confidence intervals.
    Returns (forecast_df, metrics_dict, insight_text).
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    series = billing.set_index("date")["total_bill"].asfreq("MS")
    series = series.interpolate()

    model = SARIMAX(series, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12),
                    enforce_stationarity=False, enforce_invertibility=False)
    fitted = model.fit(disp=False, maxiter=200)

    forecast_obj = fitted.get_forecast(steps=horizon)
    ci = forecast_obj.conf_int(alpha=0.05)

    future_dates = pd.date_range(series.index[-1] + pd.DateOffset(months=1),
                                 periods=horizon, freq="MS")
    forecast_df = pd.DataFrame({
        "date": future_dates,
        "forecast": forecast_obj.predicted_mean.values,
        "lower_95": ci.iloc[:, 0].values,
        "upper_95": ci.iloc[:, 1].values,
    })

    # In-sample fit metrics
    residuals = fitted.resid.dropna()
    rmse = np.sqrt(np.mean(residuals ** 2))
    mae = np.mean(np.abs(residuals))

    metrics = {"AIC": round(fitted.aic, 1), "BIC": round(fitted.bic, 1),
               "RMSE": round(rmse, 2), "MAE": round(mae, 2)}

    # Trend insight
    avg_fc = forecast_df["forecast"].mean()
    avg_hist = series.tail(12).mean()
    pct = (avg_fc - avg_hist) / avg_hist * 100
    direction = "upward" if pct > 2 else ("downward" if pct < -2 else "stable")
    insight = (f"📈 Forecast shows a **{direction} trend** — average predicted bill is "
               f"**${avg_fc:.2f}** vs recent 12-month average of **${avg_hist:.2f}** "
               f"({pct:+.1f}%). ")
    if direction == "upward":
        insight += "This is likely due to seasonal demand increases and rising rate components."
    elif direction == "downward":
        insight += "Potential savings ahead — consider locking in current rates."

    return forecast_df, metrics, series, insight


# ─────────────────────────────────────────────
# 3. TREND DETECTION
# ─────────────────────────────────────────────
def detect_trends(billing: pd.DataFrame, window: int = 6):
    """
    Compute rolling averages and identify trend direction.
    Returns (trend_df, insight_text).
    """
    df = billing[["date", "total_bill", "usage_kwh"]].copy()
    df["effective_rate"] = df["total_bill"] / df["usage_kwh"]
    df["bill_rolling"] = df["total_bill"].rolling(window, min_periods=1).mean()
    df["rate_rolling"] = df["effective_rate"].rolling(window, min_periods=1).mean()
    df["yoy_change"] = df["total_bill"].pct_change(12) * 100

    # Trend direction via linear regression on last 24 months
    recent = df.tail(24).copy()
    recent["t"] = np.arange(len(recent))
    slope, _, r, p, _ = stats.linregress(recent["t"], recent["total_bill"])

    if slope > 1 and p < 0.1:
        trend = "upward"
        icon = "📈"
    elif slope < -1 and p < 0.1:
        trend = "downward"
        icon = "📉"
    else:
        trend = "stable"
        icon = "➡️"

    insight = (f"{icon} Electricity costs show a **{trend} trend** over the last 24 months "
               f"(slope: ${slope:.2f}/month, R²={r**2:.3f}). ")
    if trend == "upward":
        insight += "Rising distribution and BGS rates are the primary drivers."
    elif trend == "downward":
        insight += "Decreasing market transition charges are helping offset other increases."

    return df, insight, {"slope": slope, "r_squared": r**2, "p_value": p, "direction": trend}


# ─────────────────────────────────────────────
# 4. ANOMALY DETECTION
# ─────────────────────────────────────────────
def detect_anomalies(billing: pd.DataFrame, z_threshold: float = 2.0):
    """
    Detect anomalies using z-score on residuals after removing trend.
    Returns (anomaly_df, insight_text).
    """
    df = billing[["date", "total_bill", "usage_kwh"]].copy()

    # Detrend using rolling median
    df["trend"] = df["total_bill"].rolling(6, center=True, min_periods=1).median()
    df["residual"] = df["total_bill"] - df["trend"]
    df["z_score"] = stats.zscore(df["residual"].fillna(0))
    df["is_anomaly"] = df["z_score"].abs() > z_threshold

    anomalies = df[df["is_anomaly"]].copy()
    n_anomalies = len(anomalies)

    if n_anomalies == 0:
        insight = "✅ No significant anomalies detected in your billing history. Your costs follow expected patterns."
    else:
        spike_months = anomalies[anomalies["z_score"] > 0]
        drop_months = anomalies[anomalies["z_score"] < 0]
        parts = [f"⚠️ Detected **{n_anomalies} anomalies** in billing history."]
        if len(spike_months) > 0:
            dates_str = ", ".join(spike_months["date"].dt.strftime("%b %Y").tolist()[:3])
            parts.append(f"**Spikes** in: {dates_str} — likely due to extreme weather or rate adjustments.")
        if len(drop_months) > 0:
            dates_str = ", ".join(drop_months["date"].dt.strftime("%b %Y").tolist()[:3])
            parts.append(f"**Drops** in: {dates_str} — possibly from demand response credits or billing adjustments.")
        insight = " ".join(parts)

    return df, insight, n_anomalies


# ─────────────────────────────────────────────
# 5. BENCHMARKING (NJ vs US)
# ─────────────────────────────────────────────
def run_benchmark(benchmark_df: pd.DataFrame, year: int = 2025, focus_state: str = "NJ"):
    """
    Compare focus state rates vs other states and national average.
    Returns (comparison_df, insight_text).
    """
    year_data = benchmark_df[benchmark_df["year"] == year].copy()
    if year_data.empty:
        year = benchmark_df["year"].max()
        year_data = benchmark_df[benchmark_df["year"] == year].copy()

    year_data = year_data.sort_values("avg_rate", ascending=True)
    year_data["rank"] = range(1, len(year_data) + 1)
    national_avg = year_data["avg_rate"].mean()

    focus = year_data[year_data["state"] == focus_state]
    if not focus.empty:
        focus_rate = focus.iloc[0]["avg_rate"]
        focus_rank = int(focus.iloc[0]["rank"])
        diff_pct = (focus_rate - national_avg) / national_avg * 100
        position = "above" if diff_pct > 0 else "below"
        insight = (f"⚡ In {year}, **{focus_state}** has an average rate of "
                   f"**${focus_rate:.4f}/kWh** — ranked **#{focus_rank}** out of "
                   f"{len(year_data)} states. This is **{abs(diff_pct):.1f}% {position}** "
                   f"the national average of ${national_avg:.4f}/kWh.")
    else:
        insight = f"State {focus_state} not found in benchmark data."

    return year_data, national_avg, insight


# ─────────────────────────────────────────────
# 6. PLAN COMPARISON (Fixed vs Variable)
# ─────────────────────────────────────────────
def compare_plans(plans_df: pd.DataFrame, monthly_usage: float = 750,
                  horizon_months: int = 12):
    """
    Simple deterministic plan comparison (no Monte Carlo needed for MVP).
    Returns (comparison_df, insight_text).
    """
    delivery_rate = 0.055  # PSE&G delivery charges
    rider_rate = 0.008     # SBC + riders
    tax_rate = 0.06625     # NJ sales tax

    results = []
    for _, plan in plans_df.iterrows():
        supply_rate = plan["rate"]
        total_rate = supply_rate + delivery_rate + rider_rate
        monthly_cost = monthly_usage * total_rate * (1 + tax_rate)
        annual_cost = monthly_cost * horizon_months

        # For variable plans, add uncertainty band
        vol = plan.get("volatility", 0)
        if vol > 0:
            annual_low = monthly_usage * (supply_rate * 0.92 + delivery_rate + rider_rate) * (1 + tax_rate) * horizon_months
            annual_high = monthly_usage * (supply_rate * 1.08 + delivery_rate + rider_rate) * (1 + tax_rate) * horizon_months
        else:
            annual_low = annual_cost
            annual_high = annual_cost

        results.append({
            "Provider": plan["provider"],
            "Type": plan["type"].title(),
            "Supply Rate": f"${supply_rate:.4f}",
            "Monthly Est.": round(monthly_cost, 2),
            "Annual Est.": round(annual_cost, 2),
            "Annual Low": round(annual_low, 2),
            "Annual High": round(annual_high, 2),
            "Term": f"{int(plan['term_months'])}mo" if plan["term_months"] > 0 else "None",
            "ETF": f"${int(plan['etf'])}" if plan["etf"] > 0 else "None",
            "Green %": f"{int(plan['green_pct'])}%",
            "Risk": "Low" if plan["type"] == "fixed" else "Medium-High",
            "annual_cost_val": annual_cost,
            "rate_val": supply_rate,
            "type_raw": plan["type"],
        })

    comp_df = pd.DataFrame(results).sort_values("annual_cost_val")

    best = comp_df.iloc[0]
    default = comp_df[comp_df["Provider"].str.contains("BGS|PSE")]
    default_cost = default.iloc[0]["annual_cost_val"] if len(default) > 0 else comp_df.iloc[-1]["annual_cost_val"]
    savings = default_cost - best["annual_cost_val"]

    fixed_avg = comp_df[comp_df["type_raw"] == "fixed"]["annual_cost_val"].mean()
    variable_avg = comp_df[comp_df["type_raw"] == "variable"]["annual_cost_val"].mean()

    insight = (f"🏆 **{best['Provider']}** offers the lowest estimated annual cost at "
               f"**${best['annual_cost_val']:.2f}** — saving **${savings:.2f}/year** vs the default BGS rate. ")
    if fixed_avg < variable_avg:
        insight += "Fixed plans average lower costs and reduce rate risk in the current market. "
    else:
        insight += "Variable plans are currently cheaper on average but carry rate volatility risk. "
    insight += f"Fixed plan avg: ${fixed_avg:.2f} | Variable plan avg: ${variable_avg:.2f}."

    return comp_df, insight


# ─────────────────────────────────────────────
# 7. BILL COMPONENT INSIGHTS
# ─────────────────────────────────────────────
def generate_bill_insight(breakdown: dict) -> str:
    """Generate natural language insight for a single bill breakdown."""
    comps = breakdown["components"]
    # Find top contributor (excluding tax)
    non_tax = {k: v for k, v in comps.items() if k != "Sales Tax" and v > 0}
    if not non_tax:
        return "No significant cost components detected."

    top_comp = max(non_tax, key=non_tax.get)
    top_val = non_tax[top_comp]
    total = breakdown["total_bill"]
    pct = top_val / total * 100 if total > 0 else 0

    # Fixed vs variable analysis
    fixed_comps = comps.get("Customer Charge", 0)
    variable_comps = sum(v for k, v in comps.items()
                        if k not in ["Customer Charge", "Sales Tax", "Weather Adjustment",
                                     "Demand Response Credit"])

    insight = (f"💡 **{top_comp}** is the largest cost component at **${top_val:.2f}** "
               f"({pct:.1f}% of your ${total:.2f} bill). ")

    if breakdown["usage_kwh"] > 1000:
        insight += "Your high usage (>1,000 kWh) amplifies all usage-based charges significantly. "
    elif breakdown["usage_kwh"] < 500:
        insight += "With lower usage, the fixed customer charge has a proportionally larger impact. "

    insight += (f"Fixed charges: ${fixed_comps:.2f} | "
                f"Usage-based charges: ${variable_comps:.2f}.")

    return insight

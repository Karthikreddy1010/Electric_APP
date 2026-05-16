/**
 * ElectricAI Dashboard — Client Application
 * Connects to FastAPI backend and renders interactive Plotly charts.
 */

const API_BASE = 'http://localhost:8000';

// ===== Plotly Theme =====
const PLOTLY_LAYOUT = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: 'Inter, sans-serif', color: '#94a3b8', size: 12 },
    margin: { l: 50, r: 20, t: 30, b: 40 },
    xaxis: {
        gridcolor: 'rgba(99,102,241,0.08)',
        zerolinecolor: 'rgba(99,102,241,0.15)',
    },
    yaxis: {
        gridcolor: 'rgba(99,102,241,0.08)',
        zerolinecolor: 'rgba(99,102,241,0.15)',
    },
    legend: { orientation: 'h', y: -0.15, font: { size: 11 } },
    hoverlabel: {
        bgcolor: '#1e293b',
        bordercolor: '#6366f1',
        font: { family: 'Inter', color: '#f1f5f9' },
    },
};

const COLORS = {
    primary: '#6366f1',
    secondary: '#8b5cf6',
    teal: '#14b8a6',
    amber: '#f59e0b',
    rose: '#f43f5e',
    sky: '#38bdf8',
    emerald: '#10b981',
    components: ['#6366f1', '#8b5cf6', '#14b8a6', '#f59e0b', '#38bdf8', '#f43f5e', '#10b981'],
};

const PLOTLY_CONFIG = { responsive: true, displayModeBar: false };

// ===== Tab Navigation =====
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', () => {
        // Deactivate all
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        
        // Activate target
        link.classList.add('active');
        const tabId = 'tab-' + link.dataset.tab;
        const targetTab = document.getElementById(tabId);
        if (targetTab) {
            targetTab.classList.add('active');
            
            // Special handling for Impact tab (rankings)
            if (link.dataset.tab === 'impact') {
                loadImpactRanking();
            }

            // Special handling for Geo Insights map rendering
            if (link.dataset.tab === 'geo-insights') {
                initGeo().then(() => {
                    if (geoMap) {
                        setTimeout(() => {
                            geoMap.invalidateSize();
                        }, 200);
                    }
                });
            }
        }
    });
});

// ===== API Helpers =====
async function apiGet(endpoint) {
    const resp = await fetch(`${API_BASE}${endpoint}`);
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    return resp.json();
}

async function apiPost(endpoint, body) {
    const resp = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    return resp.json();
}

function showLoading(text = 'Processing...') {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

function formatCurrency(val) {
    return '$' + Number(val).toFixed(2);
}

// ===== Initialization =====
async function init() {
    try {
        const health = await apiGet('/health');
        document.getElementById('api-status-dot').classList.add('connected');
        document.getElementById('api-status-text').textContent = 'Connected';
        await loadOverview();
    } catch (e) {
        document.getElementById('api-status-dot').classList.add('error');
        document.getElementById('api-status-text').textContent = 'API Offline';
        console.error('Init failed:', e);
        renderDemoMode();
    }
}

// ===== OVERVIEW TAB =====
async function loadOverview() {
    try {
        const breakdown = await apiGet('/bill-breakdown?months=24');
        const trends = await apiGet('/trends?months=36');

        if (breakdown.length > 0) {
            const latest = breakdown[breakdown.length - 1];
            const prev = breakdown.length > 1 ? breakdown[breakdown.length - 2] : null;

            document.getElementById('kpi-bill-value').textContent = formatCurrency(latest.total_bill);
            document.getElementById('kpi-usage-value').textContent = latest.usage_kwh.toFixed(0) + ' kWh';
            document.getElementById('kpi-rate-value').textContent = '$' + latest.effective_rate.toFixed(4) + '/kWh';

            if (prev) {
                const billChange = ((latest.total_bill - prev.total_bill) / prev.total_bill * 100);
                const changeEl = document.getElementById('kpi-bill-change');
                changeEl.textContent = (billChange >= 0 ? '▲' : '▼') + ' ' + Math.abs(billChange).toFixed(1) + '% vs prior month';
                changeEl.className = 'kpi-change ' + (billChange >= 0 ? 'positive' : 'negative');
            }

            renderBreakdownChart(breakdown);
        }

        if (trends.months) {
            renderTrendChart(trends);
        }

        // Quick forecast for KPI
        try {
            const forecast = await apiPost('/forecast', { months_ahead: 1, model_type: 'ensemble' });
            if (forecast.forecasts && forecast.forecasts.length > 0) {
                document.getElementById('kpi-forecast-value').textContent = formatCurrency(forecast.forecasts[0].forecast);
            }
        } catch (e) { /* forecast optional */ }

    } catch (e) {
        console.error('Overview load error:', e);
    }
}

function renderBreakdownChart(data) {
    const months = document.getElementById('breakdown-months').value;
    const sliced = data.slice(-parseInt(months));
    const dates = sliced.map(d => d.date);
    const components = ['bgs', 'transmission', 'distribution', 'sbc', 'nug', 'tax'];
    const labels = ['Generation (BGS)', 'Transmission', 'Distribution', 'SBC', 'NUG', 'Tax'];

    const traces = components.map((comp, i) => ({
        x: dates,
        y: sliced.map(d => d.components[comp] || 0),
        name: labels[i],
        type: 'bar',
        marker: { color: COLORS.components[i], opacity: 0.85 },
    }));

    Plotly.newPlot('chart-breakdown', traces, {
        ...PLOTLY_LAYOUT,
        barmode: 'stack',
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: 'Cost ($)', tickprefix: '$' },
        xaxis: { ...PLOTLY_LAYOUT.xaxis, title: '' },
    }, PLOTLY_CONFIG);
}

function renderTrendChart(data) {
    const trace1 = {
        x: data.months, y: data.total_bills,
        name: 'Total Bill', type: 'scatter', mode: 'lines+markers',
        line: { color: COLORS.primary, width: 2.5 },
        marker: { size: 4, color: COLORS.primary },
    };

    const trace2 = {
        x: data.months, y: data.yoy_changes,
        name: 'YoY Change %', type: 'bar', yaxis: 'y2',
        marker: {
            color: data.yoy_changes.map(v => v > 0 ? COLORS.rose : COLORS.emerald),
            opacity: 0.5,
        },
    };

    Plotly.newPlot('chart-trend', [trace1, trace2], {
        ...PLOTLY_LAYOUT,
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: 'Bill ($)', tickprefix: '$' },
        yaxis2: {
            ...PLOTLY_LAYOUT.yaxis,
            title: 'YoY %', overlaying: 'y', side: 'right',
            ticksuffix: '%', showgrid: false,
        },
    }, PLOTLY_CONFIG);
}

// ===== FORECAST TAB =====
async function runForecast() {
    showLoading('Running forecast models...');
    try {
        const horizon = parseInt(document.getElementById('forecast-horizon').value);
        const model = document.getElementById('forecast-model').value;
        const result = await apiPost('/forecast', {
            months_ahead: horizon, model_type: model, include_ci: true,
        });
        renderForecastChart(result);
    } catch (e) {
        alert('Forecast error: ' + e.message);
    } finally {
        hideLoading();
    }
}

function renderForecastChart(result) {
    const months = result.forecasts.map(f => f.month);
    const forecasts = result.forecasts.map(f => f.forecast);
    const lower = result.forecasts.map(f => f.lower);
    const upper = result.forecasts.map(f => f.upper);

    const traces = [
        {
            x: months, y: upper, name: 'Upper CI',
            type: 'scatter', mode: 'lines',
            line: { color: 'transparent' }, showlegend: false,
        },
        {
            x: months, y: lower, name: '95% CI',
            type: 'scatter', mode: 'lines',
            line: { color: 'transparent' },
            fill: 'tonexty',
            fillcolor: 'rgba(99,102,241,0.15)',
        },
        {
            x: months, y: forecasts, name: 'Forecast',
            type: 'scatter', mode: 'lines+markers',
            line: { color: COLORS.primary, width: 3 },
            marker: { size: 6, color: COLORS.primary },
        },
    ];

    Plotly.newPlot('chart-forecast', traces, {
        ...PLOTLY_LAYOUT,
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: 'Predicted Bill ($)', tickprefix: '$' },
        margin: { ...PLOTLY_LAYOUT.margin, t: 40 },
    }, PLOTLY_CONFIG);
}

// ===== IMPACT TAB =====
async function runImpact() {
    showLoading('Analyzing bill impact drivers...');
    try {
        const topN = parseInt(document.getElementById('impact-topn').value);
        const result = await apiPost('/impact', { top_n: topN });
        renderImpactCharts(result);
    } catch (e) {
        alert('Impact analysis error: ' + e.message);
    } finally {
        hideLoading();
    }
}

function renderImpactCharts(result) {
    // SHAP waterfall – reverse a copy so top_drivers is not mutated before table render
    const drivers = [...result.top_drivers].reverse();
    const shapTrace = {
        y: drivers.map(d => d.feature.replace(/_/g, ' ')),
        x: drivers.map(d => d.shap_value),
        type: 'bar', orientation: 'h',
        marker: {
            color: drivers.map(d => d.shap_value > 0 ? COLORS.rose : COLORS.emerald),
            opacity: 0.8,
        },
    };

    Plotly.newPlot('chart-shap', [shapTrace], {
        ...PLOTLY_LAYOUT,
        xaxis: { ...PLOTLY_LAYOUT.xaxis, title: 'SHAP Value ($)' },
        margin: { ...PLOTLY_LAYOUT.margin, l: 180 },
    }, PLOTLY_CONFIG);

    // Category donut
    const cats = result.category_impacts;
    const catLabels = Object.keys(cats);
    const catValues = catLabels.map(k => cats[k].absolute || cats[k].pct || 0);

    Plotly.newPlot('chart-categories', [{
        labels: catLabels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
        values: catValues,
        type: 'pie', hole: 0.55,
        marker: { colors: COLORS.components },
        textinfo: 'label+percent',
        textfont: { color: '#f1f5f9', size: 12 },
    }], {
        ...PLOTLY_LAYOUT,
        showlegend: false,
    }, PLOTLY_CONFIG);

    // Impact table
    const tableHTML = `<table class="data-table">
        <thead><tr><th>Feature</th><th>SHAP Value</th><th>Direction</th><th>Magnitude</th></tr></thead>
        <tbody>${result.top_drivers.map(d => `
            <tr>
                <td>${d.feature}</td>
                <td>${d.shap_value.toFixed(4)}</td>
                <td style="color:${d.direction === 'increases' ? COLORS.rose : COLORS.emerald}">${d.direction === 'increases' ? '▲' : '▼'} ${d.direction}</td>
                <td>${d.magnitude}</td>
            </tr>
        `).join('')}</tbody>
    </table>`;
    document.getElementById('impact-table').innerHTML = tableHTML;
}

// ===== BENCHMARK TAB =====
async function runBenchmark() {
    showLoading('Loading state comparisons...');
    try {
        const year = parseInt(document.getElementById('benchmark-year').value);
        const result = await apiPost('/benchmark', { year, compare_state: 'NJ' });
        renderBenchmarkMap(result);
        renderBenchmarkTable(result);
    } catch (e) {
        alert('Benchmark error: ' + e.message);
    } finally {
        hideLoading();
    }
}

function renderBenchmarkMap(result) {
    const states = result.states;
    const trace = {
        type: 'choropleth',
        locationmode: 'USA-states',
        locations: states.map(s => s.state),
        z: states.map(s => s.avg_rate * 100), // cents/kWh
        text: states.map(s => `${s.state}: ${(s.avg_rate * 100).toFixed(1)}¢/kWh\n$${s.avg_bill.toFixed(0)}/mo`),
        colorscale: [
            [0, '#10b981'], [0.25, '#14b8a6'], [0.5, '#f59e0b'],
            [0.75, '#f97316'], [1, '#f43f5e'],
        ],
        colorbar: {
            title: { text: '¢/kWh', font: { color: '#94a3b8' } },
            tickfont: { color: '#94a3b8' },
            bgcolor: 'rgba(0,0,0,0)',
        },
        hoverinfo: 'text',
    };

    Plotly.newPlot('chart-benchmark-map', [trace], {
        ...PLOTLY_LAYOUT,
        geo: {
            scope: 'usa',
            bgcolor: 'rgba(0,0,0,0)',
            lakecolor: 'rgba(99,102,241,0.1)',
            landcolor: '#1e293b',
            showlakes: true,
            projection: { type: 'albers usa' },
        },
        margin: { l: 0, r: 0, t: 10, b: 0 },
    }, PLOTLY_CONFIG);
}

function renderBenchmarkTable(result) {
    const sorted = result.states.sort((a, b) => b.avg_rate - a.avg_rate);
    const tableHTML = `<table class="data-table">
        <thead><tr><th>Rank</th><th>State</th><th>Rate (¢/kWh)</th><th>Avg Bill</th><th>vs National Avg</th></tr></thead>
        <tbody>${sorted.map((s, i) => {
            const isNJ = s.state === 'NJ';
            const diff = ((s.avg_rate - result.national_avg) / result.national_avg * 100).toFixed(1);
            return `<tr class="${isNJ ? 'highlight-row' : ''}">
                <td>${i + 1}</td>
                <td>${s.state}${isNJ ? ' ⬅' : ''}</td>
                <td>${(s.avg_rate * 100).toFixed(1)}¢</td>
                <td>${formatCurrency(s.avg_bill)}</td>
                <td style="color:${diff > 0 ? COLORS.rose : COLORS.emerald}">${diff > 0 ? '+' : ''}${diff}%</td>
            </tr>`;
        }).join('')}</tbody>
    </table>`;
    document.getElementById('benchmark-table').innerHTML = tableHTML;
}

// ===== PLANS TAB =====
async function runSimulation() {
    showLoading('Running Monte Carlo simulation...');
    try {
        const result = await apiPost('/plan-simulation', {
            monthly_usage_kwh: parseFloat(document.getElementById('plan-usage').value),
            usage_growth_pct: parseFloat(document.getElementById('plan-growth').value),
            n_simulations: parseInt(document.getElementById('plan-sims').value),
            horizon_months: 12,
        });
        renderPlanCharts(result);
        renderPlanTable(result);
    } catch (e) {
        alert('Simulation error: ' + e.message);
    } finally {
        hideLoading();
    }
}

function renderPlanCharts(result) {
    const plans = result.comparison;

    // Cost comparison bar chart
    const costTrace = {
        x: plans.map(p => p.provider),
        y: plans.map(p => p.expected_annual_cost),
        type: 'bar',
        marker: {
            color: plans.map((p, i) => i === 0 ? COLORS.emerald : COLORS.components[i % COLORS.components.length]),
            opacity: 0.85,
        },
        error_y: {
            type: 'data',
            array: plans.map(p => p.std_annual_cost),
            visible: true,
            color: '#94a3b8',
        },
    };

    Plotly.newPlot('chart-plan-cost', [costTrace], {
        ...PLOTLY_LAYOUT,
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: 'Annual Cost ($)', tickprefix: '$' },
        xaxis: { ...PLOTLY_LAYOUT.xaxis, tickangle: -30 },
    }, PLOTLY_CONFIG);

    // Risk scatter
    const riskTrace = {
        x: plans.map(p => p.std_annual_cost),
        y: plans.map(p => p.expected_annual_cost),
        text: plans.map(p => p.provider),
        mode: 'markers+text',
        type: 'scatter',
        textposition: 'top center',
        textfont: { size: 10, color: '#94a3b8' },
        marker: {
            size: plans.map(p => Math.max(10, p.risk_score)),
            color: plans.map((p, i) => COLORS.components[i % COLORS.components.length]),
            opacity: 0.7,
            line: { width: 1, color: '#fff' },
        },
    };

    Plotly.newPlot('chart-plan-risk', [riskTrace], {
        ...PLOTLY_LAYOUT,
        xaxis: { ...PLOTLY_LAYOUT.xaxis, title: 'Risk (Std Dev $)' },
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: 'Expected Annual Cost ($)', tickprefix: '$' },
        showlegend: false,
    }, PLOTLY_CONFIG);

    // Recommendation
    const rec = document.getElementById('plan-recommendation');
    rec.style.display = 'flex';
    document.getElementById('rec-title').textContent = `Recommended: ${result.recommended}`;
    document.getElementById('rec-detail').textContent =
        `Estimated savings of ${formatCurrency(result.savings_vs_default)}/year vs default BGS supply`;
}

function renderPlanTable(result) {
    const plans = result.comparison;
    const tableHTML = `<table class="data-table">
        <thead><tr>
            <th>Provider</th><th>Type</th><th>Rate</th>
            <th>Expected Annual</th><th>P5 (Best)</th><th>P95 (Worst)</th>
            <th>Risk Score</th>
        </tr></thead>
        <tbody>${plans.map((p, i) => `
            <tr class="${i === 0 ? 'highlight-row' : ''}">
                <td>${p.provider}${i === 0 ? ' 🏆' : ''}</td>
                <td>${p.plan_type}</td>
                <td>${(p.rate * 100).toFixed(2)}¢</td>
                <td>${formatCurrency(p.expected_annual_cost)}</td>
                <td>${formatCurrency(p.p5_annual_cost)}</td>
                <td>${formatCurrency(p.p95_annual_cost)}</td>
                <td>${p.risk_score}%</td>
            </tr>
        `).join('')}</tbody>
    </table>`;
    document.getElementById('plan-table').innerHTML = tableHTML;
}

// ===== Demo Mode (no API) =====
function renderDemoMode() {
    document.getElementById('kpi-bill-value').textContent = '$142.38';
    document.getElementById('kpi-usage-value').textContent = '847 kWh';
    document.getElementById('kpi-rate-value').textContent = '$0.1681/kWh';
    document.getElementById('kpi-forecast-value').textContent = '$138.50';
    document.getElementById('kpi-bill-change').textContent = '▲ 3.2% vs prior month';
    document.getElementById('kpi-bill-change').className = 'kpi-change positive';

    // Demo breakdown
    const demoMonths = Array.from({ length: 12 }, (_, i) => {
        const d = new Date(2025, i);
        return d.toISOString().slice(0, 7);
    });
    const demoTraces = [
        { x: demoMonths, y: demoMonths.map(() => 55 + Math.random() * 20), name: 'Generation', type: 'bar', marker: { color: COLORS.components[0] } },
        { x: demoMonths, y: demoMonths.map(() => 12 + Math.random() * 5), name: 'Transmission', type: 'bar', marker: { color: COLORS.components[1] } },
        { x: demoMonths, y: demoMonths.map(() => 28 + Math.random() * 8), name: 'Distribution', type: 'bar', marker: { color: COLORS.components[2] } },
        { x: demoMonths, y: demoMonths.map(() => 4 + Math.random() * 2), name: 'SBC', type: 'bar', marker: { color: COLORS.components[3] } },
        { x: demoMonths, y: demoMonths.map(() => 8 + Math.random() * 3), name: 'Tax', type: 'bar', marker: { color: COLORS.components[4] } },
    ];
    Plotly.newPlot('chart-breakdown', demoTraces, {
        ...PLOTLY_LAYOUT, barmode: 'stack',
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: 'Cost ($)', tickprefix: '$' },
    }, PLOTLY_CONFIG);

    // Demo trend
    const trendMonths = Array.from({ length: 36 }, (_, i) => {
        const d = new Date(2023, i);
        return d.toISOString().slice(0, 7);
    });
    const bills = trendMonths.map((_, i) => 110 + 20 * Math.sin(i * Math.PI / 6) + Math.random() * 15 + i * 0.5);
    Plotly.newPlot('chart-trend', [{
        x: trendMonths, y: bills, name: 'Total Bill',
        type: 'scatter', mode: 'lines+markers',
        line: { color: COLORS.primary, width: 2.5 },
        marker: { size: 3 },
    }], {
        ...PLOTLY_LAYOUT,
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: 'Bill ($)', tickprefix: '$' },
    }, PLOTLY_CONFIG);
}

// ===== Breakdown months selector =====
document.getElementById('breakdown-months')?.addEventListener('change', async () => {
    try {
        const months = parseInt(document.getElementById('breakdown-months').value);
        const data = await apiGet(`/bill-breakdown?months=${months}`);
        renderBreakdownChart(data);
    } catch (e) { /* fallback to current view */ }
});

document.getElementById('trend-months')?.addEventListener('change', async () => {
    try {
        const months = parseInt(document.getElementById('trend-months').value);
        const data = await apiGet(`/trends?months=${months}`);
        renderTrendChart(data);
    } catch (e) { /* fallback to current view */ }
});

// ===== Boot =====
document.addEventListener('DOMContentLoaded', init);
// ===== GEO INSIGHTS TAB =====
let geoInitialized = false;
let geoMap = null;
let geoGeoJSON = null;
let geoMonths = [];
let geoMode = 'bill'; // 'bill' or 'price'
let geoSelectedRegion = 'NJ';
let geoCurrentMonthIndex = 83;
let geoPlaying = false;
let geoPlayInterval = null;

async function initGeo() {
    if (geoInitialized) return;
    showLoading('Loading Geo Data...');
    try {
        const meta = await apiGet('/geo/meta');
        geoMonths = meta.months;
        geoCurrentMonthIndex = geoMonths.length - 1;
        
        // Setup slider
        const slider = document.getElementById('timeline-slider');
        slider.max = geoMonths.length - 1;
        slider.value = geoCurrentMonthIndex;
        updateMonthDisplay();

        // Load US States GeoJSON from jsDelivr CDN (more reliable than raw.githubusercontent)
        const geoJSONUrl = 'https://cdn.jsdelivr.net/gh/PublicaMundi/MappingAPI@master/data/geojson/us-states.json';
        const geoResp = await fetch(geoJSONUrl);
        geoGeoJSON = await geoResp.json();

        // Initialize Map if not already done
        if (!geoMap) {
            geoMap = L.map('map', {
                center: [37.8, -96],
                zoom: 4,
                zoomControl: false,
                attributionControl: false
            });
            L.control.zoom({ position: 'topright' }).addTo(geoMap);
        }

        await updateGeoView();
        geoInitialized = true;
    } catch (e) {
        console.error('Geo init failed:', e);
        // Fallback or error UI
        document.getElementById('map').innerHTML = '<div style="padding: 20px; color: var(--accent-rose);">Failed to load map data. Please check your internet connection.</div>';
    } finally {
        hideLoading();
    }
}

function updateMonthDisplay() {
    const m = geoMonths[geoCurrentMonthIndex];
    if (!m) return;
    const [y, mo] = m.split('-');
    const date = new Date(y, mo - 1);
    document.getElementById('current-month-display').textContent = date.toLocaleString('default', { month: 'short', year: 'numeric' });
}

async function setGeoMode(mode) {
    geoMode = mode;
    document.getElementById('mode-bill').classList.toggle('active', mode === 'bill');
    document.getElementById('mode-price').classList.toggle('active', mode === 'price');
    await updateGeoView();
}

async function onTimelineChange(index) {
    geoCurrentMonthIndex = parseInt(index);
    updateMonthDisplay();
    await updateGeoView(false); // Update map only, don't re-fetch trend
}

function toggleTimelinePlay() {
    geoPlaying = !geoPlaying;
    const btn = document.getElementById('play-timeline');
    btn.textContent = geoPlaying ? '⏸ Pause' : '▶ Play';
    btn.classList.toggle('playing', geoPlaying);

    if (geoPlaying) {
        geoPlayInterval = setInterval(async () => {
            geoCurrentMonthIndex++;
            if (geoCurrentMonthIndex >= geoMonths.length) {
                geoCurrentMonthIndex = 0;
            }
            document.getElementById('timeline-slider').value = geoCurrentMonthIndex;
            updateMonthDisplay();
            await updateGeoView(false);
        }, 800);
    } else {
        clearInterval(geoPlayInterval);
    }
}

async function updateGeoView(updateDetails = true) {
    if (!geoMap || !geoGeoJSON) return;
    const month = geoMonths[geoCurrentMonthIndex];
    
    try {
        const resp = await apiGet(`/geo/data?month=${month}&type=${geoMode}`);
        const dataMap = {};
        resp.data.forEach(d => dataMap[d.state] = d);

        // Remove old layer
        if (window.geoLayer) geoMap.removeLayer(window.geoLayer);

        window.geoLayer = L.geoJson(geoGeoJSON, {
            style: (feature) => {
                const stateData = dataMap[feature.id];
                const val = stateData ? stateData.value : 0;
                return {
                    fillColor: getGeoColor(val, geoMode),
                    weight: 1.5,
                    opacity: 1,
                    color: 'rgba(99, 102, 241, 0.4)',
                    fillOpacity: 0.7
                };
            },
            onEachFeature: (feature, layer) => {
                const stateData = dataMap[feature.id];
                layer.on({
                    mouseover: (e) => {
                        const l = e.target;
                        l.setStyle({ fillOpacity: 0.9, weight: 2, color: '#fff' });
                        const popup = L.popup({ closeButton: false, offset: L.point(0, -10) })
                            .setLatLng(e.latlng)
                            .setContent(`<b>${feature.properties.name}</b><br>${geoMode === 'bill' ? 'Avg Bill: ' + formatCurrency(stateData.avg_bill) : 'Avg Price: $' + stateData.avg_price.toFixed(4)}`)
                            .openOn(geoMap);
                    },
                    mouseout: (e) => {
                        window.geoLayer.resetStyle(e.target);
                        geoMap.closePopup();
                    },
                    click: async () => {
                        geoSelectedRegion = feature.id;
                        document.getElementById('selected-region-name').textContent = feature.properties.name;
                        await loadGeoRegionDetails();
                    }
                });
            }
        }).addTo(geoMap);

        updateGeoLegend(geoMode);

        if (updateDetails) {
            await loadGeoRegionDetails();
        }
    } catch (e) {
        console.error('Geo update failed:', e);
    }
}

function getGeoColor(d, mode) {
    if (mode === 'bill') {
        return d > 200 ? '#f43f5e' :
               d > 180 ? '#fb7185' :
               d > 160 ? '#f59e0b' :
               d > 140 ? '#14b8a6' :
               d > 120 ? '#10b981' :
                         '#059669';
    } else {
        return d > 0.22 ? '#f43f5e' :
               d > 0.19 ? '#fb7185' :
               d > 0.17 ? '#f59e0b' :
               d > 0.15 ? '#14b8a6' :
               d > 0.13 ? '#10b981' :
                          '#059669';
    }
}

function updateGeoLegend(mode) {
    const legend = document.getElementById('map-legend');
    const grades = mode === 'bill' ? [120, 140, 160, 180, 200] : [0.13, 0.15, 0.17, 0.19, 0.22];
    const labels = [];
    
    legend.innerHTML = `<div class="legend-title">${mode === 'bill' ? 'Avg Bill ($)' : 'Price ($/kWh)'}</div>`;
    const scale = document.createElement('div');
    scale.className = 'legend-scale';

    for (let i = 0; i < grades.length; i++) {
        const item = document.createElement('div');
        item.className = 'legend-item';
        const color = getGeoColor(grades[i] + (mode === 'bill' ? 1 : 0.01), mode);
        item.innerHTML = `<div class="legend-color" style="background:${color}"></div> <span>${grades[i]}${grades[i+1] ? '&ndash;' + grades[i+1] : '+'}</span>`;
        scale.appendChild(item);
    }
    legend.appendChild(scale);
}

async function loadGeoRegionDetails() {
    const month = geoMonths[geoCurrentMonthIndex];
    try {
        const [detail, trend] = await Promise.all([
            apiGet(`/geo/detail?state=${geoSelectedRegion}&month=${month}`),
            apiGet(`/geo/trend?region=${geoSelectedRegion}&type=${geoMode}`)
        ]);

        // Update Detail Panel
        document.getElementById('detail-bill').textContent = formatCurrency(detail.avg_bill);
        document.getElementById('detail-price').textContent = '$' + detail.avg_rate.toFixed(4);
        document.getElementById('detail-usage').textContent = detail.usage_kwh + ' kWh';
        
        const vsNat = geoMode === 'bill' ? detail.vs_national_bill_pct : detail.vs_national_rate_pct;
        const vsNatEl = document.getElementById('detail-vs-nat');
        vsNatEl.textContent = (vsNat >= 0 ? '+' : '') + vsNat + '%';
        vsNatEl.style.color = vsNat > 0 ? 'var(--accent-rose)' : 'var(--accent-emerald)';
        
        const barFill = document.getElementById('detail-vs-nat-bar');
        barFill.style.width = Math.min(Math.abs(vsNat) * 2, 100) + '%';
        barFill.style.background = vsNat > 0 ? 'var(--accent-rose)' : 'var(--accent-emerald)';

        // Render Trend Chart
        Plotly.newPlot('geo-trend-chart', [{
            x: trend.months,
            y: trend.values,
            type: 'scatter',
            mode: 'lines',
            line: { color: COLORS.primary, width: 3, shape: 'spline' },
            fill: 'tozeroy',
            fillcolor: 'rgba(99, 102, 241, 0.1)',
            hovertemplate: '%{x}: %{y}<extra></extra>'
        }], {
            ...PLOTLY_LAYOUT,
            xaxis: { ...PLOTLY_LAYOUT.xaxis, tickformat: '%Y' },
            yaxis: { ...PLOTLY_LAYOUT.yaxis, tickprefix: geoMode === 'bill' ? '$' : '' }
        }, PLOTLY_CONFIG);

        document.getElementById('geo-growth-value').textContent = (trend.total_growth_pct >= 0 ? '+' : '') + trend.total_growth_pct + '%';

        // Render Breakdown Chart
        const components = detail.components;
        if (components) {
            Plotly.newPlot('geo-breakdown-chart', [{
                values: Object.values(components),
                labels: Object.keys(components).map(k => k.toUpperCase()),
                type: 'pie',
                hole: 0.6,
                marker: { colors: COLORS.components },
                textinfo: 'none',
                hovertemplate: '%{label}: $%{value}<extra></extra>'
            }], {
                ...PLOTLY_LAYOUT,
                showlegend: true,
                legend: { orientation: 'v', x: 1.1, y: 0.5 },
                margin: { l: 0, r: 100, t: 0, b: 0 }
            }, PLOTLY_CONFIG);
        }

    } catch (e) {
        console.error('Region detail failed:', e);
    }
}

function resetGeoView() {
    if (geoMap) geoMap.setView([37.8, -96], 4);
    geoSelectedRegion = 'NJ';
    document.getElementById('selected-region-name').textContent = 'New Jersey';
    loadGeoRegionDetails();
}

// ===== Bill Impact Engine (Deterministic + Causal) =====

async function loadImpactRanking() {
    try {
        const data = await apiGet('/impact/rank');
        const tbody = document.getElementById('rank-table-body');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        data.rankings.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.label}</td>
                <td>${item.share_pct}%</td>
                <td>${item.elasticity}</td>
                <td><span class="badge" style="background: var(--bg-card); border: 1px solid var(--accent-blue);">${item.type}</span></td>
            `;
            tbody.appendChild(row);
        });
    } catch (e) {
        console.error('Failed to load rankings:', e);
    }
}

async function runSensitivityTest() {
    const component = document.getElementById('sensitivity-comp').value;
    const pct = parseFloat(document.getElementById('sensitivity-pct').value);
    
    showLoading();
    try {
        // 1. Get Deterministic Impact
        const res = await apiPost('/impact/sensitivity', {
            component: component,
            change_pct: pct
        });
        
        document.getElementById('sensitivity-results').style.display = 'flex';
        document.getElementById('sim-new-bill').innerText = `$${res.new_bill.toFixed(2)}`;
        
        const impactText = `${res.absolute_impact >= 0 ? '+' : ''}$${res.absolute_impact.toFixed(2)}`;
        document.getElementById('sim-abs-impact').innerText = impactText;
        
        // 2. Get Causal Insight (DoWhy)
        const causal = await apiPost('/impact/causal', {
            treatment: component
        });
        
        const causalBox = document.getElementById('causal-insight-box');
        if (causal.causal_effect_estimate) {
            causalBox.style.display = 'block';
            let insight = causal.interpretation;
            
            // Add MC uncertainty note if what-if was run (simplified here)
            // In a real app we'd call /impact/what-if for multiple changes
            insight += `\n\n(Note: Simulation includes a 95% confidence interval of $${res.confidence_interval?.[0].toFixed(2)} to $${res.confidence_interval?.[1].toFixed(2)} based on demand elasticity variance).`;
            
            document.getElementById('causal-text').innerText = insight;
        } else {
            causalBox.style.display = 'none';
        }
        
    } catch (e) {
        console.error('Sensitivity test failed:', e);
        alert('Failed to run simulation. Please try again.');
    } finally {
        hideLoading();
    }
}

// Attach listeners if needed (already in HTML onclick)


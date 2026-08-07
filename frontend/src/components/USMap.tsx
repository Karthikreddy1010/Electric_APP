import { memo, useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import { feature } from 'topojson-client';
import type { FeatureCollection } from 'geojson';

const geoUrl = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

const STATE_MAPPING: Record<string, string> = {
  "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
  "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
  "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
  "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
  "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
  "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
  "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
  "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
  "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
  "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
};

export interface StateCoverageInfo {
  state: string;
  name: string;
  tier: 'complete' | 'most' | 'limited' | 'none';
  price: string;
  bill: string;
  usage: string;
  zipCount: number;
  utility: string;
  grid: string;
}

export const STATE_COVERAGE_MAP: Record<string, StateCoverageInfo> = {
  NJ: { state: 'NJ', name: 'New Jersey', tier: 'complete', price: '$0.3126/kWh', bill: '$184.50', usage: '590 kWh', zipCount: 598, utility: 'PSE&G / JCP&L', grid: 'PJM' },
  NY: { state: 'NY', name: 'New York', tier: 'complete', price: '$0.2450/kWh', bill: '$210.40', usage: '858 kWh', zipCount: 1794, utility: 'ConEd / National Grid', grid: 'NYISO' },
  PA: { state: 'PA', name: 'Pennsylvania', tier: 'complete', price: '$0.1820/kWh', bill: '$142.80', usage: '785 kWh', zipCount: 1450, utility: 'PECO / PPL', grid: 'PJM' },
  DE: { state: 'DE', name: 'Delaware', tier: 'most', price: '$0.1680/kWh', bill: '$148.00', usage: '880 kWh', zipCount: 75, utility: 'Delmarva Power', grid: 'PJM' },
  MD: { state: 'MD', name: 'Maryland', tier: 'most', price: '$0.1740/kWh', bill: '$154.00', usage: '885 kWh', zipCount: 450, utility: 'BGE / Pepco', grid: 'PJM' },
  CT: { state: 'CT', name: 'Connecticut', tier: 'most', price: '$0.2980/kWh', bill: '$215.00', usage: '721 kWh', zipCount: 280, utility: 'Eversource CT', grid: 'ISO-NE' },
  MA: { state: 'MA', name: 'Massachusetts', tier: 'most', price: '$0.2850/kWh', bill: '$198.50', usage: '696 kWh', zipCount: 520, utility: 'National Grid MA', grid: 'ISO-NE' },
  CA: { state: 'CA', name: 'California', tier: 'most', price: '$0.2940/kWh', bill: '$225.00', usage: '765 kWh', zipCount: 1760, utility: 'PG&E / SCE', grid: 'CAISO' },
  TX: { state: 'TX', name: 'Texas', tier: 'most', price: '$0.1450/kWh', bill: '$158.00', usage: '1089 kWh', zipCount: 1920, utility: 'Oncor / CenterPoint', grid: 'ERCOT' },
  FL: { state: 'FL', name: 'Florida', tier: 'most', price: '$0.1580/kWh', bill: '$178.00', usage: '1126 kWh', zipCount: 980, utility: 'FPL / Duke FL', grid: 'FRCC' },
  OH: { state: 'OH', name: 'Ohio', tier: 'most', price: '$0.1510/kWh', bill: '$139.00', usage: '920 kWh', zipCount: 1200, utility: 'AEP Ohio / Duke', grid: 'PJM' },
  IL: { state: 'IL', name: 'Illinois', tier: 'most', price: '$0.1620/kWh', bill: '$128.00', usage: '790 kWh', zipCount: 1350, utility: 'ComEd / Ameren', grid: 'MISO' },
  VA: { state: 'VA', name: 'Virginia', tier: 'limited', price: '$0.1460/kWh', bill: '$145.00', usage: '890 kWh', zipCount: 890, utility: 'Dominion Energy', grid: 'PJM' },
  NC: { state: 'NC', name: 'North Carolina', tier: 'limited', price: '$0.1380/kWh', bill: '$138.00', usage: '950 kWh', zipCount: 810, utility: 'Duke Energy NC', grid: 'SERC' },
  GA: { state: 'GA', name: 'Georgia', tier: 'limited', price: '$0.1420/kWh', bill: '$142.00', usage: '980 kWh', zipCount: 740, utility: 'Georgia Power', grid: 'SERC' },
  MI: { state: 'MI', name: 'Michigan', tier: 'limited', price: '$0.1840/kWh', bill: '$148.00', usage: '720 kWh', zipCount: 950, utility: 'DTE / Consumers', grid: 'MISO' },
  WA: { state: 'WA', name: 'Washington', tier: 'limited', price: '$0.1120/kWh', bill: '$118.00', usage: '990 kWh', zipCount: 620, utility: 'Puget Sound Energy', grid: 'NWPP' },
  OR: { state: 'OR', name: 'Oregon', tier: 'limited', price: '$0.1240/kWh', bill: '$126.00', usage: '910 kWh', zipCount: 480, utility: 'Portland General', grid: 'NWPP' },
  CO: { state: 'CO', name: 'Colorado', tier: 'limited', price: '$0.1560/kWh', bill: '$134.00', usage: '710 kWh', zipCount: 520, utility: 'Xcel Energy CO', grid: 'PSCO' },
  AZ: { state: 'AZ', name: 'Arizona', tier: 'limited', price: '$0.1490/kWh', bill: '$162.00', usage: '1020 kWh', zipCount: 410, utility: 'APS / SRP', grid: 'AZNM' },
};

interface USMapProps {
  data?: { state: string; value: number }[];
  selectedState?: string;
  onStateClick?: (state: string) => void;
  onStateHover?: (state: string | null) => void;
}

const USMap = ({ selectedState = 'NJ', onStateClick, onStateHover }: USMapProps) => {
  const [geoJson, setGeoJson] = useState<FeatureCollection | null>(null);
  const [loadError, setLoadError] = useState<boolean>(false);

  useEffect(() => {
    fetch(geoUrl)
      .then(res => {
        if (!res.ok) throw new Error('CDN map fetch failed');
        return res.json();
      })
      .then(topology => {
        // @ts-ignore
        const geo = feature(topology, topology.objects.states) as unknown as FeatureCollection;
        setGeoJson(geo);
      })
      .catch(err => {
        console.error('[USMap] Error loading 50-state TopoJSON topology:', err);
        setLoadError(true);
      });
  }, []);

  const getTierStyle = (stateAbbr: string, isSelected: boolean) => {
    const coverage = STATE_COVERAGE_MAP[stateAbbr];
    const tier = coverage ? coverage.tier : 'none';

    let fillColor = '#E2E8F0'; // Default gray for unsupported states
    let fillOpacity = 0.55;

    if (tier === 'complete') {
      fillColor = '#1D4ED8'; // Dark Blue
      fillOpacity = 0.85;
    } else if (tier === 'most') {
      fillColor = '#3B82F6'; // Medium Blue
      fillOpacity = 0.75;
    } else if (tier === 'limited') {
      fillColor = '#93C5FD'; // Light Blue
      fillOpacity = 0.7;
    }

    return {
      fillColor,
      weight: isSelected ? 3.5 : 0.6,
      opacity: 1,
      color: isSelected ? '#EF4444' : '#FFFFFF',
      fillOpacity: isSelected ? 0.95 : fillOpacity,
    };
  };

  if (loadError) {
    return (
      <div className="w-full h-full min-h-[400px] flex flex-col items-center justify-center bg-slate-50 text-slate-700 p-6 space-y-2">
        <span className="font-bold text-sm">50-State Topology Map Loading Fallback</span>
        <span className="text-xs text-slate-500">Select any state from the dropdown to load state ZIP boundaries.</span>
      </div>
    );
  }

  if (!geoJson) {
    return (
      <div className="w-full h-full min-h-[400px] flex items-center justify-center bg-slate-50 text-xs font-bold text-[#1B365D]">
        Loading 50-State National Topology &amp; Coverage Map...
      </div>
    );
  }

  return (
    <div className="w-full h-full min-h-[400px] relative z-0">
      <MapContainer 
        key={`us-map-50-states-${selectedState}`}
        center={[37.8, -96.0]} 
        zoom={4} 
        scrollWheelZoom={false}
        className="w-full h-full"
        style={{ background: '#F8FAFC' }}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />

        <GeoJSON
          key={`us-geojson-${selectedState}`}
          data={geoJson}
          style={(feature) => {
            const stateAbbr = STATE_MAPPING[feature?.properties?.name || ''];
            const isSelected = selectedState === stateAbbr;
            return getTierStyle(stateAbbr, isSelected);
          }}
          onEachFeature={(feature, layer) => {
            const stateAbbr = STATE_MAPPING[feature.properties?.name || ''];
            const coverage = STATE_COVERAGE_MAP[stateAbbr];

            // Render rich tooltip card on hover
            const name = feature.properties?.name || stateAbbr;
            const tierText = coverage
              ? coverage.tier === 'complete' ? 'Complete Analytics Available'
                : coverage.tier === 'most' ? 'Most Datasets Available'
                : 'Limited Datasets Available'
              : 'No Analytics Available';

            const popupContent = `
              <div style="font-family: sans-serif; font-size: 11px; padding: 4px; color: #1E293B;">
                <strong style="font-size: 13px; color: #1B365D; display: block; margin-bottom: 2px;">${name} (${stateAbbr})</strong>
                <span style="display: inline-block; padding: 2px 6px; background: ${
                  coverage?.tier === 'complete' ? '#DBEAFE; color: #1E40AF;' : coverage?.tier === 'most' ? '#E0F2FE; color: #0369A1;' : coverage?.tier === 'limited' ? '#FEF3C7; color: #92400E;' : '#F1F5F9; color: #64748B;'
                } border-radius: 4px; font-weight: bold; margin-bottom: 4px;">${tierText}</span>
                ${coverage ? `
                  <div style="margin-top: 4px; border-top: 1px solid #E2E8F0; padding-top: 4px;">
                    <div>Average Price: <strong>${coverage.price}</strong></div>
                    <div>Average Bill: <strong>${coverage.bill}</strong></div>
                    <div>Monthly Usage: <strong>${coverage.usage}</strong></div>
                    <div>Utilities: <strong>${coverage.utility}</strong></div>
                    <div>ZCTA Boundaries: <strong>${coverage.zipCount.toLocaleString()} ZIPs</strong></div>
                    <div>Grid Operator: <strong>${coverage.grid}</strong></div>
                  </div>
                ` : '<div style="color: #94A3B8; margin-top: 4px;">No analytics dataset uploaded for this state.</div>'}
              </div>
            `;

            layer.bindTooltip(popupContent, { sticky: true });

            layer.on({
              mouseover: (e) => {
                const l = e.target;
                l.setStyle({
                  weight: 2.5,
                  color: "#3B82F6"
                });
                l.bringToFront();
                if (onStateHover) onStateHover(stateAbbr);
              },
              mouseout: (e) => {
                const l = e.target;
                const isSelected = selectedState === stateAbbr;
                l.setStyle(getTierStyle(stateAbbr, isSelected));
                if (onStateHover) onStateHover(null);
              },
              click: () => {
                console.log(`[USMap Coverage] State clicked: ${stateAbbr} (${name})`);
                if (stateAbbr && onStateClick) {
                  onStateClick(stateAbbr);
                }
              }
            });
          }}
        />
      </MapContainer>

      {/* ── National Data Availability Coverage Legend ───────────────────── */}
      <div className="absolute bottom-4 left-4 z-10 bg-white/95 backdrop-blur-xs p-3 rounded-xl border border-gray-200 shadow-md text-xs space-y-1.5 font-sans pointer-events-none">
        <strong className="text-[11px] uppercase tracking-wider text-gray-700 block mb-1">
          National Data Availability &amp; Coverage Legend
        </strong>

        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-xs bg-[#1D4ED8] inline-block border border-blue-900" />
          <span className="text-gray-800 font-medium">Complete Analytics (ZCTAs, Rates, EIA, Weather)</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-xs bg-[#3B82F6] inline-block border border-blue-700" />
          <span className="text-gray-800 font-medium">Most Datasets Available (Rates, Utilities, Grid)</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-xs bg-[#93C5FD] inline-block border border-blue-400" />
          <span className="text-gray-800 font-medium">Limited Datasets (EIA Retail Benchmarks)</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-xs bg-[#E2E8F0] inline-block border border-gray-300" />
          <span className="text-gray-500 font-medium">No Analytics Available (Gray)</span>
        </div>

        <div className="flex items-center gap-2 pt-1 border-t border-gray-100">
          <span className="w-3.5 h-3.5 rounded-xs bg-[#1D4ED8] inline-block border-2 border-[#EF4444]" />
          <span className="text-gray-900 font-bold">Selected Active Region (Red Selection Outline)</span>
        </div>
      </div>
    </div>
  );
};

export default memo(USMap, (prev, next) => {
  return (
    prev.selectedState === next.selectedState
  );
});

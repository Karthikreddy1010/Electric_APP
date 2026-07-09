import { memo, useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import { scaleQuantile } from 'd3-scale';
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

interface USMapProps {
  data: { state: string; value: number }[];
  selectedState?: string;
  onStateClick?: (state: string) => void;
  onStateHover?: (state: string | null) => void;
  colorRange?: string[];
}

const USMap = ({ data, selectedState, onStateClick, onStateHover, colorRange = ["#E2E8F0", "#2563EB"] }: USMapProps) => {
  const [geoJson, setGeoJson] = useState<FeatureCollection | null>(null);

  useEffect(() => {
    fetch(geoUrl)
      .then(res => res.json())
      .then(topology => {
        // @ts-ignore
        const geo = feature(topology, topology.objects.states) as unknown as FeatureCollection;
        setGeoJson(geo);
      });
  }, []);

  const colorScale = scaleQuantile<string>()
    .domain(data.map(d => d.value))
    .range(colorRange);

  if (!geoJson) return <div className="w-full h-full min-h-[400px] flex items-center justify-center bg-slate-50">Loading Map...</div>;

  return (
    <div className="w-full h-full min-h-[400px] relative z-0">
      <MapContainer 
        center={[39.8, -98.5]} 
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
          data={geoJson}
          style={(feature) => {
            const stateAbbr = STATE_MAPPING[feature?.properties?.name];
            const cur = data.find(s => s.state === stateAbbr);
            const isSelected = selectedState === stateAbbr;
            
            return {
              fillColor: cur ? colorScale(cur.value) : "#F1F5F9",
              weight: isSelected ? 2 : 0.5,
              opacity: 1,
              color: isSelected ? "#2563EB" : "#FFFFFF",
              fillOpacity: 0.8
            };
          }}
          onEachFeature={(feature, layer) => {
            const stateAbbr = STATE_MAPPING[feature.properties.name];
            
            layer.on({
              mouseover: (e) => {
                const l = e.target;
                l.setStyle({
                  fillOpacity: 1,
                  weight: 2,
                  color: "#3B82F6"
                });
                l.bringToFront();
                if (onStateHover) onStateHover(stateAbbr);
              },
              mouseout: (e) => {
                const l = e.target;
                const isSelected = selectedState === stateAbbr;
                l.setStyle({
                  weight: isSelected ? 2 : 0.5,
                  color: isSelected ? "#2563EB" : "#FFFFFF",
                  fillOpacity: 0.8
                });
                if (onStateHover) onStateHover(null);
              },
              click: () => {
                if (onStateClick) onStateClick(stateAbbr);
              }
            });
          }}
        />
      </MapContainer>
    </div>
  );
};

export default memo(USMap, (prev, next) => {
  return (
    prev.data === next.data &&
    prev.selectedState === next.selectedState &&
    prev.colorRange?.[0] === next.colorRange?.[0] &&
    prev.colorRange?.[1] === next.colorRange?.[1]
  );
});

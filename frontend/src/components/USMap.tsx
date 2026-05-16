import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { scaleQuantile } from 'd3-scale';

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
  colorRange?: string[];
}

const USMap = ({ data, selectedState, onStateClick, colorRange = ["#E2E8F0", "#2563EB"] }: USMapProps) => {
  const colorScale = scaleQuantile<string>()
    .domain(data.map(d => d.value))
    .range(colorRange);

  return (
    <div className="w-full h-full min-h-[400px]">
      <ComposableMap projection="geoAlbersUsa" className="w-full h-full">
        <Geographies geography={geoUrl}>
          {({ geographies }: { geographies: any[] }) =>
            geographies.map((geo: any) => {
              const stateAbbr = STATE_MAPPING[geo.properties.name];
              const cur = data.find(s => s.state === stateAbbr);
              const isSelected = selectedState === stateAbbr;
              
              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  onClick={() => onStateClick?.(stateAbbr)}
                  fill={cur ? colorScale(cur.value) : "#F1F5F9"}
                  stroke={isSelected ? "#000" : "#FFF"}
                  strokeWidth={isSelected ? 2 : 0.5}
                  style={{
                    default: { outline: "none" },
                    hover: { fill: "#3B82F6", outline: "none", cursor: "pointer" },
                    pressed: { outline: "none" },
                  }}
                />
              );
            })
          }
        </Geographies>
      </ComposableMap>
    </div>
  );
};

export default USMap;

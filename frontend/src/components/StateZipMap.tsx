import { useMemo } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { scaleQuantile, scaleOrdinal } from 'd3-scale';

interface StateZipMapProps {
  geoJsonData: any;
  viewMode: 'bill' | 'rate' | 'utility';
  selectedZip?: string | null;
  onZipClick?: (zip: string) => void;
  onZipHover?: (zip: string | null) => void;
}

const UTILITY_COLORS = [
  "#3B82F6", // Blue
  "#10B981", // Emerald
  "#F59E0B", // Amber
  "#EC4899", // Pink
  "#8B5CF6", // Purple
  "#EF4444", // Red
  "#06B6D4", // Cyan
  "#14B8A6", // Teal
];

const StateZipMap = ({
  geoJsonData,
  viewMode,
  selectedZip,
  onZipClick,
  onZipHover
}: StateZipMapProps) => {
  
  // Calculate center and scale dynamically to fit the state's GeoJSON bounding box
  const projectionParams = useMemo(() => {
    if (!geoJsonData || !geoJsonData.features || geoJsonData.features.length === 0) {
      return { center: [-74.4057, 40.0583] as [number, number], scale: 8000 };
    }
    
    let minLon = 180, maxLon = -180;
    let minLat = 90, maxLat = -90;
    
    geoJsonData.features.forEach((feature: any) => {
      if (!feature.geometry) return;
      const coords = feature.geometry.coordinates;
      const type = feature.geometry.type;
      
      const processCoord = (coord: number[]) => {
        const [lon, lat] = coord;
        if (lon < minLon) minLon = lon;
        if (lon > maxLon) maxLon = lon;
        if (lat < minLat) minLat = lat;
        if (lat > maxLat) maxLat = lat;
      };
      
      if (type === "Polygon") {
        coords[0].forEach(processCoord);
      } else if (type === "MultiPolygon") {
        coords.forEach((polygon: any) => {
          if (polygon[0]) {
            polygon[0].forEach(processCoord);
          }
        });
      }
    });
    
    if (minLon > maxLon || minLat > maxLat) {
      return { center: [-74.4057, 40.0583] as [number, number], scale: 8000 };
    }
    
    const center: [number, number] = [
      (minLon + maxLon) / 2,
      (minLat + maxLat) / 2
    ];
    
    const dLon = maxLon - minLon;
    const dLat = maxLat - minLat;
    const maxDiff = Math.max(dLon, dLat);
    
    // Scale heuristic for geoMercator with standard SVG dimensions
    const scale = (450 / (maxDiff || 0.1)) * 55;
    
    return { center, scale };
  }, [geoJsonData]);

  // Compute color scales based on rate values or utility identifiers
  const colorScale = useMemo(() => {
    if (!geoJsonData || !geoJsonData.features) return null;
    
    if (viewMode === 'utility') {
      const utilities = new Set<string>();
      geoJsonData.features.forEach((f: any) => {
        if (f.properties.primary_utility) {
          utilities.add(f.properties.primary_utility);
        }
      });
      const utilsList = Array.from(utilities);
      const scale = scaleOrdinal<string>()
        .domain(utilsList)
        .range(UTILITY_COLORS.slice(0, utilsList.length || 1));
      return (val: any) => scale(val);
    } else {
      const values = geoJsonData.features
        .map((f: any) => f.properties.residential_rate)
        .filter((v: any) => v != null && !isNaN(v));
        
      if (values.length === 0) return () => "#E2E8F0";
      
      const scale = scaleQuantile<string>()
        .domain(values)
        .range(["#EFF6FF", "#DBEAFE", "#93C5FD", "#3B82F6", "#1D4ED8"]);
      return (val: any) => scale(val);
    }
  }, [geoJsonData, viewMode]);

  return (
    <div className="w-full h-full min-h-[500px] flex items-center justify-center relative">
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{
          center: projectionParams.center,
          scale: projectionParams.scale
        }}
        className="w-full h-full max-h-[550px]"
      >
        <Geographies geography={geoJsonData}>
          {({ geographies }) =>
            geographies.map((geo) => {
              const zip = geo.properties.zip_code;
              const rate = geo.properties.residential_rate;
              const utility = geo.properties.primary_utility;
              const isSelected = selectedZip === zip;
              
              let fillVal = "#E2E8F0";
              if (colorScale) {
                fillVal = viewMode === 'utility' ? colorScale(utility) : colorScale(rate);
              }
              
              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  onClick={() => onZipClick?.(zip)}
                  onMouseEnter={() => onZipHover?.(zip)}
                  onMouseLeave={() => onZipHover?.(null)}
                  fill={fillVal}
                  stroke={isSelected ? "#EF4444" : "#FFFFFF"}
                  strokeWidth={isSelected ? 1.5 : 0.2}
                  style={{
                    default: { outline: "none", transition: "all 150ms ease" },
                    hover: { fill: "#F87171", stroke: "#EF4444", strokeWidth: 1, outline: "none", cursor: "pointer" },
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

export default StateZipMap;

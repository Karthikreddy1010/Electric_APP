import { useMemo, memo, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import { scaleQuantile, scaleOrdinal } from 'd3-scale';
import L from 'leaflet';

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

// Helper component to auto-fit map bounds to the GeoJSON layer
const MapFitter = ({ geoJsonData, selectedZip }: { geoJsonData: any, selectedZip?: string | null }) => {
  const map = useMap();
  const fittedRef = useRef<string | null>(null);
  
  useEffect(() => {
    if (geoJsonData && geoJsonData.features && geoJsonData.features.length > 0) {
      const key = `${geoJsonData.features.length}-${selectedZip}`;
      if (fittedRef.current === key) return;
      
      const geojsonLayer = L.geoJSON(geoJsonData);
      const bounds = geojsonLayer.getBounds();
      
      if (bounds.isValid()) {
        fittedRef.current = key;
        if (selectedZip) {
          // Find the specific feature and fly to its bounds with some padding
          const selectedFeature = geoJsonData.features.find((f: any) => f.properties.zip_code === selectedZip);
          if (selectedFeature) {
            const selectedLayer = L.geoJSON(selectedFeature);
            map.flyToBounds(selectedLayer.getBounds(), { padding: [50, 50], duration: 1.5 });
            return;
          }
        }
        // Default fit to entire state
        map.flyToBounds(bounds, { padding: [20, 20], duration: 1.5 });
      }
    }
  }, [geoJsonData, selectedZip, map]);

  return null;
};

const StateZipMap = ({
  geoJsonData,
  viewMode,
  selectedZip,
  onZipClick,
  onZipHover
}: StateZipMapProps) => {

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

  if (!geoJsonData || !geoJsonData.features) {
    return <div className="w-full h-full min-h-[500px] flex items-center justify-center bg-slate-50 text-slate-400 font-bold">Loading Boundary Data...</div>;
  }

  return (
    <div className="w-full h-full min-h-[500px] relative z-0">
      <MapContainer 
        center={[40.0583, -74.4057]} // Default NJ center
        zoom={7} 
        className="w-full h-full absolute inset-0"
        style={{ background: '#F8FAFC' }}
        zoomControl={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />
        
        <MapFitter geoJsonData={geoJsonData} selectedZip={selectedZip} />
        
        <GeoJSON
          key={`${viewMode}-${selectedZip}`} // Force re-render of styles on mode change
          data={geoJsonData}
          style={(feature) => {
            const zip = feature?.properties?.zip_code;
            const rate = feature?.properties?.residential_rate;
            const utility = feature?.properties?.primary_utility;
            const isSelected = selectedZip === zip;
            
            let fillVal = "#E2E8F0";
            if (colorScale) {
              fillVal = viewMode === 'utility' ? colorScale(utility) : colorScale(rate);
            }
            
            return {
              fillColor: fillVal,
              weight: isSelected ? 3 : 0.5,
              opacity: 1,
              color: isSelected ? "#EF4444" : "#FFFFFF",
              fillOpacity: isSelected ? 0.9 : 0.65
            };
          }}
          onEachFeature={(feature, layer) => {
            const zip = feature.properties.zip_code;
            
            layer.on({
              mouseover: (e) => {
                const l = e.target;
                l.setStyle({
                  fillOpacity: 0.9,
                  weight: 2,
                  color: "#F87171"
                });
                l.bringToFront();
                if (onZipHover) onZipHover(zip);
              },
              mouseout: (e) => {
                const l = e.target;
                const isSelected = selectedZip === zip;
                l.setStyle({
                  weight: isSelected ? 3 : 0.5,
                  color: isSelected ? "#EF4444" : "#FFFFFF",
                  fillOpacity: isSelected ? 0.9 : 0.65
                });
                if (!isSelected) {
                  l.bringToBack();
                }
                if (onZipHover) onZipHover(null);
              },
              click: () => {
                if (onZipClick) onZipClick(zip);
              }
            });
          }}
        />
      </MapContainer>
    </div>
  );
};

export default memo(StateZipMap, (prev, next) => {
  return (
    prev.geoJsonData === next.geoJsonData &&
    prev.viewMode === next.viewMode &&
    prev.selectedZip === next.selectedZip
  );
});

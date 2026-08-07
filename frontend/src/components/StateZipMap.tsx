import { useMemo, memo, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import { scaleQuantile, scaleOrdinal } from 'd3-scale';
import L from 'leaflet';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface StateZipMapProps {
  geoJsonData: any;
  viewMode: 'bill' | 'rate' | 'utility';
  selectedState?: string;
  selectedZip?: string | null;
  onZipClick?: (zip: string) => void;
  onZipHover?: (zip: string | null) => void;
  onRetry?: () => void;
  isLoading?: boolean;
  error?: string | null;
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
const MapFitter = ({ geoJsonData, selectedState, selectedZip }: { geoJsonData: any; selectedState?: string; selectedZip?: string | null }) => {
  const map = useMap();
  const fittedRef = useRef<string | null>(null);

  useEffect(() => {
    if (geoJsonData && geoJsonData.features && geoJsonData.features.length > 0) {
      const key = `${selectedState}-${geoJsonData.features.length}-${selectedZip || 'none'}`;
      if (fittedRef.current === key) return;

      const geojsonLayer = L.geoJSON(geoJsonData);
      const bounds = geojsonLayer.getBounds();

      if (bounds.isValid()) {
        fittedRef.current = key;
        
        // If a selected ZIP exists and belongs to the currently loaded state's features
        if (selectedZip) {
          const selectedFeature = geoJsonData.features.find((f: any) => f.properties?.zip_code === selectedZip);
          if (selectedFeature) {
            const selectedLayer = L.geoJSON(selectedFeature);
            const selectedBounds = selectedLayer.getBounds();
            if (selectedBounds.isValid()) {
              console.log(`[GIS Map] Auto-zooming to selected ZIP ${selectedZip} in ${selectedState}`, selectedBounds);
              map.flyToBounds(selectedBounds, { padding: [60, 60], duration: 1.5, maxZoom: 13 });
              return;
            }
          }
        }

        // Default fit to entire state bounds
        console.log(`[GIS Map] Auto-fitting map to state ${selectedState} bounds`, bounds);
        map.flyToBounds(bounds, { padding: [30, 30], duration: 1.2 });
      }
    }
  }, [geoJsonData, selectedState, selectedZip, map]);

  return null;
};

const StateZipMap = ({
  geoJsonData,
  viewMode,
  selectedState = 'NJ',
  selectedZip,
  onZipClick,
  onZipHover,
  onRetry,
  isLoading = false,
  error = null,
}: StateZipMapProps) => {
  // Normalize GeoJSON (unpack API envelope { success: true, data: { type: 'FeatureCollection', features: [] } } if present)
  const normalizedGeoJson = useMemo(() => {
    if (!geoJsonData) return null;
    if (geoJsonData.features && Array.isArray(geoJsonData.features)) {
      return geoJsonData;
    }
    if (geoJsonData.data && geoJsonData.data.features && Array.isArray(geoJsonData.data.features)) {
      return geoJsonData.data;
    }
    return null;
  }, [geoJsonData]);

  // Compute color scales based on rate values or utility identifiers
  const colorScale = useMemo(() => {
    if (!normalizedGeoJson || !normalizedGeoJson.features) return null;

    if (viewMode === 'utility') {
      const utilities = new Set<string>();
      normalizedGeoJson.features.forEach((f: any) => {
        if (f.properties?.primary_utility) {
          utilities.add(f.properties.primary_utility);
        }
      });
      const utilsList = Array.from(utilities);
      const scale = scaleOrdinal<string>()
        .domain(utilsList)
        .range(UTILITY_COLORS.slice(0, utilsList.length || 1));
      return (val: any) => scale(val);
    } else {
      const values = normalizedGeoJson.features
        .map((f: any) => f.properties?.residential_rate)
        .filter((v: any) => v != null && !isNaN(v));

      if (values.length === 0) return () => "#E2E8F0";

      const scale = scaleQuantile<string>()
        .domain(values)
        .range(["#EFF6FF", "#DBEAFE", "#93C5FD", "#3B82F6", "#1D4ED8"]);
      return (val: any) => scale(val);
    }
  }, [normalizedGeoJson, viewMode]);

  // Render Loading state
  if (isLoading) {
    return (
      <div className="w-full h-full min-h-[480px] flex flex-col items-center justify-center bg-slate-50 text-slate-600 gap-3">
        <RefreshCw size={24} className="animate-spin text-[#1B365D]" />
        <span className="text-xs font-bold uppercase tracking-wider">Fetching {selectedState} ZCTA GeoJSON Boundary Datasets...</span>
      </div>
    );
  }

  // Render Error state
  if (error) {
    return (
      <div className="w-full h-full min-h-[480px] flex flex-col items-center justify-center bg-red-50 text-red-700 p-6 space-y-3 border border-red-200 rounded-xl">
        <AlertCircle size={28} className="text-red-600" />
        <span className="text-sm font-bold">GIS Boundary Data Error ({selectedState})</span>
        <p className="text-xs text-red-600 text-center max-w-md">{error}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-4 py-1.5 bg-red-600 hover:bg-red-700 text-white font-bold text-xs rounded-lg transition-colors cursor-pointer"
          >
            Retry Loading {selectedState} Boundaries
          </button>
        )}
      </div>
    );
  }

  // Render Empty/Missing FeatureCollection state
  if (!normalizedGeoJson || !normalizedGeoJson.features || normalizedGeoJson.features.length === 0) {
    return (
      <div className="w-full h-full min-h-[480px] flex flex-col items-center justify-center bg-amber-50 text-amber-800 p-6 space-y-3 border border-amber-200 rounded-xl">
        <AlertCircle size={28} className="text-amber-600" />
        <span className="text-sm font-bold">No ZIP Boundary Geometries Found for {selectedState}</span>
        <p className="text-xs text-amber-700 text-center max-w-md">
          Boundary dataset for {selectedState} contained 0 polygon features. Verify database cache or backend shapefiles.
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-4 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-lg transition-colors cursor-pointer"
          >
            Refetch GIS Boundaries
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="w-full h-full min-h-[480px] relative z-0">
      <MapContainer
        key={`leaflet-map-${selectedState}-${normalizedGeoJson.features.length}`}
        center={[39.8, -98.5]}
        zoom={6}
        className="w-full h-full absolute inset-0"
        style={{ background: '#F8FAFC' }}
        zoomControl={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />

        <MapFitter geoJsonData={normalizedGeoJson} selectedState={selectedState} selectedZip={selectedZip} />

        <GeoJSON
          key={`geojson-layer-${selectedState}-${viewMode}-${selectedZip || 'none'}-${normalizedGeoJson.features.length}`}
          data={normalizedGeoJson}
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
              weight: isSelected ? 3.5 : 0.6,
              opacity: 1,
              color: isSelected ? "#EF4444" : "#FFFFFF",
              fillOpacity: isSelected ? 0.95 : 0.65,
            };
          }}
          onEachFeature={(feature, layer) => {
            const zip = feature.properties?.zip_code;

            layer.on({
              mouseover: (e) => {
                const l = e.target;
                l.setStyle({
                  fillOpacity: 0.95,
                  weight: 2.5,
                  color: "#F87171",
                });
                l.bringToFront();
                if (onZipHover) onZipHover(zip);
              },
              mouseout: (e) => {
                const l = e.target;
                const isSelected = selectedZip === zip;
                l.setStyle({
                  weight: isSelected ? 3.5 : 0.6,
                  color: isSelected ? "#EF4444" : "#FFFFFF",
                  fillOpacity: isSelected ? 0.95 : 0.65,
                });
                if (!isSelected) {
                  l.bringToBack();
                }
                if (onZipHover) onZipHover(null);
              },
              click: () => {
                console.log(`[GIS Map] ZIP clicked: ${zip}`);
                if (onZipClick) onZipClick(zip);
              },
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
    prev.selectedState === next.selectedState &&
    prev.selectedZip === next.selectedZip &&
    prev.isLoading === next.isLoading &&
    prev.error === next.error
  );
});

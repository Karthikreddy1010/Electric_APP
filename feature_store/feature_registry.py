"""
Central Feature Registry — Tracks all engineered features with metadata.

Every engineered feature in the pipeline is registered here with its:
  - name, source dataset, units, calculation logic
  - dependencies, version, owner module

This supports:
  - AI Assistant queries ("What features power the forecast?")
  - Feature lineage & dependency tracking
  - Automated documentation generation
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class FeatureDefinition:
    """Metadata definition for an engineered feature."""
    name: str
    source: str
    units: str
    calculation: str
    dependencies: List[str]
    category: str  # temperature, solar, wind, humidity, precipitation, temporal, interaction, derived
    version: str = "v1.0"
    owner: str = "data_pipeline"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "units": self.units,
            "calculation": self.calculation,
            "dependencies": self.dependencies,
            "category": self.category,
            "version": self.version,
            "owner": self.owner,
            "description": self.description,
        }


class FeatureRegistry:
    """Singleton registry for all engineered features."""

    def __init__(self):
        self._features: Dict[str, FeatureDefinition] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register all NREL weather + solar engineered features."""

        # ── Temperature Features ─────────────────────────────────────────
        self.register(FeatureDefinition(
            name="hdd", source="NREL NASA POWER / Open-Meteo", units="°C·day",
            calculation="max(18°C - T2M_daily_avg, 0)",
            dependencies=["T2M"], category="temperature",
            description="Heating Degree Days (base 18°C)"
        ))
        self.register(FeatureDefinition(
            name="cdd", source="NREL NASA POWER / Open-Meteo", units="°C·day",
            calculation="max(T2M_daily_avg - 18°C, 0)",
            dependencies=["T2M"], category="temperature",
            description="Cooling Degree Days (base 18°C)"
        ))
        self.register(FeatureDefinition(
            name="heat_index_c", source="NREL NASA POWER", units="°C",
            calculation="Steadman formula: f(T2M, RH2M) when T > 80°F",
            dependencies=["T2M", "RH2M"], category="temperature",
            description="Heat index (perceived temperature in hot/humid conditions)"
        ))
        self.register(FeatureDefinition(
            name="wind_chill_c", source="NREL NASA POWER", units="°C",
            calculation="Environment Canada formula: f(T2M, WS10M) when T < 10°C and wind > 1.3 m/s",
            dependencies=["T2M", "WS10M"], category="temperature",
            description="Wind chill (perceived temperature in cold/windy conditions)"
        ))
        self.register(FeatureDefinition(
            name="apparent_temp_c", source="NREL NASA POWER", units="°C",
            calculation="heat_index when T >= 27°C, wind_chill when T <= 10°C, else T2M",
            dependencies=["heat_index_c", "wind_chill_c", "T2M"], category="temperature",
            description="Composite perceived temperature"
        ))
        self.register(FeatureDefinition(
            name="temp_anomaly", source="NREL NASA POWER", units="°C",
            calculation="T2M - historical_mean(T2M, same calendar hour/day, 10-year)",
            dependencies=["T2M"], category="temperature",
            description="Temperature deviation from historical average"
        ))

        # ── Solar Features ───────────────────────────────────────────────
        self.register(FeatureDefinition(
            name="daily_solar_kwh_m2", source="NREL NASA POWER", units="kWh/m²",
            calculation="sum(ALLSKY_SFC_SW_DWN hourly) / 1000",
            dependencies=["ALLSKY_SFC_SW_DWN"], category="solar",
            description="Daily cumulative solar energy per square meter"
        ))
        self.register(FeatureDefinition(
            name="solar_intensity_wm2", source="NREL NASA POWER", units="W/m²",
            calculation="ALLSKY_SFC_SW_DWN (instantaneous)",
            dependencies=["ALLSKY_SFC_SW_DWN"], category="solar",
            description="Instantaneous solar irradiance"
        ))
        self.register(FeatureDefinition(
            name="clearness_index_avg", source="NREL NASA POWER", units="dimensionless",
            calculation="daily mean(ALLSKY_KT)",
            dependencies=["ALLSKY_KT"], category="solar",
            description="Average clearness index (1.0 = perfectly clear, 0.0 = fully overcast)"
        ))
        self.register(FeatureDefinition(
            name="cloudiness_indicator", source="NREL NASA POWER", units="dimensionless",
            calculation="1.0 - ALLSKY_KT",
            dependencies=["ALLSKY_KT"], category="solar",
            description="Cloud cover proxy (inverse of clearness index)"
        ))
        self.register(FeatureDefinition(
            name="solar_potential_index", source="NREL NASA POWER", units="score (0-100)",
            calculation="50 * (daily_solar_kwh_m2 / max_solar) + 50 * clearness_index_avg",
            dependencies=["daily_solar_kwh_m2", "clearness_index_avg"], category="solar",
            description="Solar generation potential score"
        ))

        # ── Wind Features ────────────────────────────────────────────────
        self.register(FeatureDefinition(
            name="wind_dir_sin", source="NREL NASA POWER", units="dimensionless",
            calculation="sin(WD10M in radians)",
            dependencies=["WD10M"], category="wind",
            description="Wind direction sine component (circular encoding)"
        ))
        self.register(FeatureDefinition(
            name="wind_dir_cos", source="NREL NASA POWER", units="dimensionless",
            calculation="cos(WD10M in radians)",
            dependencies=["WD10M"], category="wind",
            description="Wind direction cosine component (circular encoding)"
        ))
        self.register(FeatureDefinition(
            name="wind_category", source="NREL NASA POWER", units="categorical",
            calculation="Calm (<2 m/s), Breeze (2-6), Strong (6-11), High (>11)",
            dependencies=["WS10M"], category="wind",
            description="Wind speed category classification"
        ))

        # ── Humidity Features ────────────────────────────────────────────
        self.register(FeatureDefinition(
            name="humidity_category", source="NREL NASA POWER", units="categorical",
            calculation="Low (<40%), Moderate (40-70%), High (>70%)",
            dependencies=["RH2M"], category="humidity",
            description="Relative humidity category classification"
        ))

        # ── Precipitation Features ───────────────────────────────────────
        self.register(FeatureDefinition(
            name="rain_flag", source="NREL NASA POWER", units="boolean",
            calculation="1 if PRECTOTCORR > 0 else 0",
            dependencies=["PRECTOTCORR"], category="precipitation",
            description="Binary precipitation indicator"
        ))
        self.register(FeatureDefinition(
            name="heavy_rain_flag", source="NREL NASA POWER", units="boolean",
            calculation="1 if PRECTOTCORR > 5.0 mm/h else 0",
            dependencies=["PRECTOTCORR"], category="precipitation",
            description="Heavy rainfall indicator"
        ))

        # ── Interaction Features ─────────────────────────────────────────
        self.register(FeatureDefinition(
            name="temp_x_humidity", source="NREL NASA POWER", units="°C·%",
            calculation="T2M × RH2M",
            dependencies=["T2M", "RH2M"], category="interaction",
            description="Temperature–humidity interaction for HVAC load modeling"
        ))
        self.register(FeatureDefinition(
            name="temp_x_solar", source="NREL NASA POWER", units="°C·W/m²",
            calculation="T2M × ALLSKY_SFC_SW_DWN",
            dependencies=["T2M", "ALLSKY_SFC_SW_DWN"], category="interaction",
            description="Temperature–solar interaction for net energy modeling"
        ))
        self.register(FeatureDefinition(
            name="temp_x_rain", source="NREL NASA POWER", units="°C·mm/h",
            calculation="T2M × PRECTOTCORR",
            dependencies=["T2M", "PRECTOTCORR"], category="interaction",
            description="Temperature–rainfall interaction"
        ))

        # ── Derived Composite Features ───────────────────────────────────
        self.register(FeatureDefinition(
            name="weather_severity_score", source="NREL NASA POWER", units="score (0-100)",
            calculation="f(temp_deviation, precipitation, wind_max, humidity_deviation, cloudiness)",
            dependencies=["T2M", "PRECTOTCORR", "WS10M", "RH2M", "ALLSKY_KT"],
            category="derived",
            description="Daily composite weather severity index"
        ))
        self.register(FeatureDefinition(
            name="consec_hot_days", source="NREL NASA POWER", units="days",
            calculation="Consecutive days where temp_max > 32°C",
            dependencies=["T2M"], category="derived",
            description="Running count of consecutive extreme heat days (heatwave detection)"
        ))
        self.register(FeatureDefinition(
            name="consec_rain_days", source="NREL NASA POWER", units="days",
            calculation="Consecutive days with precipitation > 1mm",
            dependencies=["PRECTOTCORR"], category="derived",
            description="Running count of consecutive rainy days"
        ))
        self.register(FeatureDefinition(
            name="weather_confidence_score", source="NREL NASA POWER", units="score (0-1)",
            calculation="1.0 - (missing_value_fraction + sentinel_fraction)",
            dependencies=[], category="derived",
            description="Data quality and completeness index"
        ))

    def register(self, feature: FeatureDefinition):
        """Register a feature definition."""
        self._features[feature.name] = feature

    def get(self, name: str) -> Optional[FeatureDefinition]:
        """Look up a feature by name."""
        return self._features.get(name)

    def list_all(self) -> List[Dict[str, Any]]:
        """Return all registered features as dicts."""
        return [f.to_dict() for f in self._features.values()]

    def list_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Return features filtered by category."""
        return [
            f.to_dict() for f in self._features.values()
            if f.category == category
        ]

    def list_categories(self) -> List[str]:
        """Return unique feature categories."""
        return sorted(set(f.category for f in self._features.values()))

    def get_dependencies(self, name: str) -> List[str]:
        """Return the dependency chain for a feature."""
        feat = self.get(name)
        if not feat:
            return []
        return feat.dependencies

    def summary(self) -> Dict[str, Any]:
        """Return a summary of the registry."""
        categories = {}
        for f in self._features.values():
            categories.setdefault(f.category, []).append(f.name)
        return {
            "total_features": len(self._features),
            "categories": {k: len(v) for k, v in categories.items()},
            "feature_names": list(self._features.keys()),
        }


# Global singleton
feature_registry = FeatureRegistry()

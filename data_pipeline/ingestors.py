"""
Data ingestion modules for pulling from external APIs.
Provides both live API and local-file fallback modes.
"""
import pandas as pd
import requests
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class EIAIngestor:
    """Pull billing/tariff data from EIA API v2."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.eia.gov/v2"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.params = {"api_key": api_key}
    
    def get_state_electricity_prices(self, state: str = "NJ", 
                                      start_year: int = 2019) -> pd.DataFrame:
        """Fetch average retail electricity prices by state from EIA."""
        url = f"{self.base_url}/electricity/retail-sales"
        params = {
            "frequency": "monthly",
            "data[0]": "price",
            "data[1]": "revenue",
            "data[2]": "sales",
            "facets[stateid][]": state,
            "facets[sectorid][]": "RES",
            "start": f"{start_year}-01",
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": 5000,
        }
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()["response"]["data"]
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["period"])
            return df
        except Exception as e:
            logger.error(f"EIA API error: {e}")
            raise


class NOAAIngestor:
    """Pull weather data from NOAA Climate Data Online."""
    
    def __init__(self, token: str, base_url: str = "https://www.ncdc.noaa.gov/cdo-web/api/v2"):
        self.token = token
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers["token"] = token
    
    def get_daily_weather(self, station_id: str = "GHCND:USW00014734",
                          start_date: str = "2019-01-01",
                          end_date: str = "2025-12-31") -> pd.DataFrame:
        """Fetch daily temperature data from NOAA for HDD/CDD calculation."""
        url = f"{self.base_url}/data"
        all_data = []
        # NOAA limits to 1 year per request
        for year in range(int(start_date[:4]), int(end_date[:4]) + 1):
            params = {
                "datasetid": "GHCND",
                "stationid": station_id,
                "datatypeid": "TAVG,TMAX,TMIN",
                "startdate": f"{year}-01-01",
                "enddate": f"{year}-12-31",
                "units": "standard",
                "limit": 1000,
            }
            try:
                resp = self.session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                results = resp.json().get("results", [])
                all_data.extend(results)
            except Exception as e:
                logger.warning(f"NOAA API error for {year}: {e}")
        
        if not all_data:
            return pd.DataFrame()
        df = pd.DataFrame(all_data)
        df["date"] = pd.to_datetime(df["date"])
        return df


class PJMIngestor:
    """Pull wholesale market data from PJM API."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.pjm.com/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers["Ocp-Apim-Subscription-Key"] = api_key
    
    def get_lmp_data(self, zone: str = "PSEG",
                     start_date: str = "2019-01-01") -> pd.DataFrame:
        """Fetch Locational Marginal Prices for a PJM zone."""
        url = f"{self.base_url}/da_hrl_lmps"
        params = {
            "pnode_name": zone,
            "datetime_beginning_ept": f"{start_date} 00:00",
            "rowCount": 50000,
            "sort": "datetime_beginning_ept",
        }
        try:
            resp = self.session.get(url, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            df = pd.DataFrame(data)
            return df
        except Exception as e:
            logger.error(f"PJM API error: {e}")
            raise


def load_from_parquet(data_dir: str, dataset_name: str) -> pd.DataFrame:
    """Fallback: load pre-generated data from local Parquet files."""
    path = Path(data_dir) / f"{dataset_name}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    csv_path = Path(data_dir) / f"{dataset_name}.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path, parse_dates=["date"] if "date" in 
                           pd.read_csv(csv_path, nrows=0).columns else None)
    raise FileNotFoundError(f"No data found at {path} or {csv_path}")

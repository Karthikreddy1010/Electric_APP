"""
Phase 4 — API-First Live Knowledge Provider.

Modular retrieval architecture that routes live queries through an
API-first cascade. Internet search is strictly a LAST RESORT.

Provider Hierarchy (Execution Priority):
    1. OfficialAPIProvider    — EIA, PJM, NOAA, Utility APIs
    2. GovernmentProvider     — DOE, IRS, State Energy Offices (.gov)
    3. UtilityProvider        — PSE&G, JCP&L, ACE portals
    4. NewsProvider           — Industry news (Utility Dive, etc.)
    5. TrustedSearchProvider  — Pluggable search engine (Google/Bing/Brave/Tavily/Perplexity)

Design Rules:
    - LiveKnowledgeProvider NEVER executes for deterministic calculations
    - LiveKnowledgeProvider NEVER executes first in the pipeline
    - API calls always take priority over web scraping
    - Each sub-provider implements a common interface
    - Results carry full provenance metadata
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from api.services.llm.freshness import freshness_manager

logger = logging.getLogger(__name__)


# ── Base Provider Interface ────────────────────────────────────────────────

class BaseKnowledgeProvider(ABC):
    """Abstract base for all live knowledge sub-providers."""

    name: str = "base"
    source_tier: int = 6
    connector_id: str = "unknown"

    @abstractmethod
    def retrieve(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Retrieve knowledge from this provider.

        Returns list of dicts, each containing:
            - content: str
            - source: str
            - provider: str
            - timestamp: str (ISO-8601)
            - confidence: float
            - retrieval_method: str
            - source_tier: int
            - connector_id: str
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is currently available."""
        ...

    def _build_result(
        self, content: str, source: str, confidence: float = 0.8,
        retrieval_method: str = "api", extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Helper to build standardized result dict with provenance."""
        result = {
            "content": content,
            "source": source,
            "provider": self.name,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "confidence": confidence,
            "retrieval_method": retrieval_method,
            "source_tier": self.source_tier,
            "connector_id": self.connector_id,
            "freshness_score": freshness_manager.calculate_freshness_score(
                self.connector_id, time.time()
            ),
        }
        if extra:
            result.update(extra)
        return result


# ── Sub-Provider 1: Official API Provider ──────────────────────────────────

class OfficialAPIProvider(BaseKnowledgeProvider):
    """
    Retrieves data from official energy APIs.
    Priority 1 — always checked first before any web retrieval.

    Supported connectors:
        - EIA (Energy Information Administration)
        - PJM (Regional Transmission Organization)
        - NOAA (National Oceanic and Atmospheric Administration)
        - Utility APIs (PSE&G, JCP&L, ACE direct APIs)
    """

    name = "OfficialAPIProvider"
    source_tier = 2  # Tier 2: Official APIs
    connector_id = "official_api"

    # Known API endpoints registry
    _API_ENDPOINTS = {
        "eia": {
            "name": "EIA",
            "connector_id": "eia",
            "base_url": "https://api.eia.gov/v2/",
            "description": "Energy Information Administration — retail prices, generation, fuel mix",
            "keywords": ["eia", "electricity price", "retail rate", "generation", "fuel mix",
                         "energy production", "power plant", "eia-861", "eia-923"],
        },
        "pjm": {
            "name": "PJM",
            "connector_id": "pjm",
            "base_url": "https://api.pjm.com/api/v1/",
            "description": "PJM Interconnection — wholesale LMP, capacity, fuel mix",
            "keywords": ["pjm", "lmp", "wholesale", "locational marginal", "capacity market",
                         "grid operator", "interconnection", "auction"],
        },
        "noaa": {
            "name": "NOAA",
            "connector_id": "noaa",
            "base_url": "https://www.ncdc.noaa.gov/cdo-web/api/v2/",
            "description": "NOAA Climate — degree days (CDD/HDD), temperature, weather",
            "keywords": ["noaa", "weather", "temperature", "degree day", "cdd", "hdd",
                         "climate", "heat wave", "cooling", "heating"],
        },
        "utility_api": {
            "name": "Utility APIs",
            "connector_id": "utility_api",
            "base_url": "",
            "description": "Direct utility company APIs (PSE&G, JCP&L, ACE)",
            "keywords": ["pseg", "pse&g", "jcpl", "jcp&l", "ace", "atlantic city",
                         "utility rate", "rate case", "bgss"],
        },
    }

    def is_available(self) -> bool:
        return True  # API endpoints are always available (may return errors)

    def retrieve(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Route query to matching API connectors and aggregate results."""
        query_lower = query.lower()
        results = []

        for api_key, api_config in self._API_ENDPOINTS.items():
            # Check if query matches this API's domain
            if any(kw in query_lower for kw in api_config["keywords"]):
                connector_id = api_config["connector_id"]
                api_result = self._query_api(api_key, api_config, query)
                if api_result:
                    freshness_manager.record_refresh(connector_id)
                    results.append(self._build_result(
                        content=api_result["content"],
                        source=api_config["name"],
                        confidence=api_result.get("confidence", 0.92),
                        retrieval_method="official_api",
                        extra={
                            "connector_id": connector_id,
                            "api_endpoint": api_config["base_url"],
                            "source_tier": 2,
                        }
                    ))

        return results

    def _query_api(self, api_key: str, config: Dict, query: str) -> Optional[Dict[str, Any]]:
        """
        Query a specific API endpoint.
        In production, this would make actual HTTP calls.
        Currently returns structured mock data for integration testing.
        """
        if api_key == "eia":
            return {
                "content": (
                    "EIA Retail Electricity Data: NJ residential average rate is $0.1840/kWh "
                    "(as of latest reporting period). National residential average is $0.1680/kWh. "
                    "Source: EIA-861, EIA Retail Electricity Monthly."
                ),
                "confidence": 0.93,
            }
        elif api_key == "pjm":
            return {
                "content": (
                    "PJM Market Data: Current average LMP is $38.50/MWh for the PSEG zone. "
                    "Fuel mix: Natural Gas 42%, Nuclear 34%, Renewables 14%, Coal 10%. "
                    "Source: PJM Interconnection real-time data."
                ),
                "confidence": 0.94,
            }
        elif api_key == "noaa":
            return {
                "content": (
                    "NOAA Climate Data: Current Cooling Degree Days (CDD) index is 245 for NJ region. "
                    "Heating Degree Days (HDD) is 12. Temperature anomaly: +3.2°F above baseline. "
                    "Source: NOAA National Centers for Environmental Information."
                ),
                "confidence": 0.95,
            }
        elif api_key == "utility_api":
            return {
                "content": (
                    "Utility Rate Data: PSE&G RS rate schedule includes fixed service charge $8.24/month, "
                    "BGS supply rate $0.1080/kWh, delivery charges based on volumetric usage. "
                    "Source: PSE&G official tariff schedule."
                ),
                "confidence": 0.96,
            }
        return None


# ── Sub-Provider 2: Government Provider ────────────────────────────────────

class GovernmentProvider(BaseKnowledgeProvider):
    """
    Retrieves data from official government websites and agencies.
    Priority 2 — after official APIs.

    Sources: DOE, IRS (EV incentives), State Energy Offices, NJ BPU, EPA
    """

    name = "GovernmentProvider"
    source_tier = 3  # Tier 3: Official Government
    connector_id = "government"

    _GOV_DOMAINS = {
        "doe": {
            "name": "Department of Energy",
            "url": "https://www.energy.gov",
            "keywords": ["doe", "department of energy", "federal incentive", "ev incentive",
                         "energy efficiency", "weatherization", "solar incentive"],
        },
        "irs": {
            "name": "IRS (Tax Credits)",
            "url": "https://www.irs.gov",
            "keywords": ["irs", "tax credit", "ev tax", "clean vehicle", "energy credit",
                         "inflation reduction act", "ira", "26 usc"],
        },
        "nj_bpu": {
            "name": "NJ Board of Public Utilities",
            "url": "https://nj.gov/bpu/",
            "keywords": ["bpu", "board of public utilities", "nj regulation", "rate case",
                         "clean energy program", "community solar", "net metering"],
        },
        "epa": {
            "name": "Environmental Protection Agency",
            "url": "https://www.epa.gov",
            "keywords": ["epa", "emission", "carbon", "environmental", "air quality",
                         "greenhouse gas", "clean air"],
        },
    }

    def is_available(self) -> bool:
        return True

    def retrieve(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        results = []

        for domain_key, domain in self._GOV_DOMAINS.items():
            if any(kw in query_lower for kw in domain["keywords"]):
                result_content = self._fetch_gov_data(domain_key, domain, query)
                if result_content:
                    freshness_manager.record_refresh("government")
                    results.append(self._build_result(
                        content=result_content,
                        source=domain["name"],
                        confidence=0.88,
                        retrieval_method="government_website",
                        extra={"connector_id": "government", "domain_url": domain["url"]},
                    ))

        return results

    def _fetch_gov_data(self, key: str, domain: Dict, query: str) -> Optional[str]:
        """Fetch data from government source. Production: HTTP scrape / API call."""
        if key == "doe":
            return (
                "Federal energy incentives include the Residential Clean Energy Credit (30% of cost "
                "for solar, wind, geothermal, and battery storage), the Energy Efficient Home Improvement "
                "Credit (up to $3,200/year), and various state-level rebate programs administered through "
                "utility companies. Source: Department of Energy."
            )
        elif key == "irs":
            return (
                "The Clean Vehicle Credit (30D) provides up to $7,500 for new qualifying EVs and "
                "$4,000 for used EVs (25E). The Residential Clean Energy Credit (25D) covers 30% of "
                "solar panel, battery storage, and geothermal heat pump costs through 2032. "
                "Source: IRS.gov."
            )
        elif key == "nj_bpu":
            return (
                "NJ BPU oversees utility rate cases, clean energy programs, and grid modernization. "
                "Current programs include NJ SREC-II for solar, Community Solar Energy Pilot, "
                "and the NJ WARM/COOL Advantage for HVAC incentives. Source: NJ BPU."
            )
        return None


# ── Sub-Provider 3: Utility Provider ───────────────────────────────────────

class UtilityProvider(BaseKnowledgeProvider):
    """
    Retrieves data from official utility company portals.
    Priority 3 — after APIs and government.

    Sources: PSE&G, JCP&L, ACE official websites
    """

    name = "UtilityProvider"
    source_tier = 3  # Tier 3: Official Utilities
    connector_id = "utility"

    _UTILITY_PORTALS = {
        "pseg": {
            "name": "PSE&G",
            "url": "https://www.pseg.com",
            "keywords": ["pseg", "pse&g", "public service electric", "pseg rate"],
        },
        "jcpl": {
            "name": "JCP&L (FirstEnergy)",
            "url": "https://www.firstenergycorp.com/jcpl",
            "keywords": ["jcpl", "jcp&l", "jersey central", "firstenergy"],
        },
        "ace": {
            "name": "Atlantic City Electric",
            "url": "https://www.atlanticcityelectric.com",
            "keywords": ["ace", "atlantic city electric", "pepco holdings"],
        },
    }

    def is_available(self) -> bool:
        return True

    def retrieve(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        results = []

        for key, portal in self._UTILITY_PORTALS.items():
            if any(kw in query_lower for kw in portal["keywords"]):
                content = self._fetch_utility_data(key, portal, query)
                if content:
                    freshness_manager.record_refresh("utility")
                    results.append(self._build_result(
                        content=content,
                        source=portal["name"],
                        confidence=0.88,
                        retrieval_method="utility_portal",
                        extra={"connector_id": "utility", "portal_url": portal["url"]},
                    ))

        return results

    def _fetch_utility_data(self, key: str, portal: Dict, query: str) -> Optional[str]:
        """Fetch data from utility portal. Production: HTTP scrape."""
        if key == "pseg":
            return (
                "PSE&G serves approximately 2.3 million electric customers in New Jersey. "
                "Current residential rate schedule (RS) includes a monthly service charge of $8.24, "
                "BGS supply charges, and volumetric delivery charges. PSE&G is regulated by the NJ BPU. "
                "Source: PSE&G official website."
            )
        elif key == "jcpl":
            return (
                "JCP&L (Jersey Central Power & Light), a FirstEnergy company, serves approximately "
                "1.1 million customers in central and northern New Jersey. Rate schedules are available "
                "through the FirstEnergy portal. Source: JCP&L / FirstEnergy."
            )
        return None


# ── Sub-Provider 4: News Provider ──────────────────────────────────────────

class NewsProvider(BaseKnowledgeProvider):
    """
    Retrieves data from trusted energy industry news sources.
    Priority 4 — after APIs, government, and utilities.

    Sources: Utility Dive, Greentech Media, Energy Storage News
    """

    name = "NewsProvider"
    source_tier = 5  # Tier 5: Trusted News
    connector_id = "news"

    _TRUSTED_SOURCES = [
        {"name": "Utility Dive", "url": "https://www.utilitydive.com"},
        {"name": "Greentech Media", "url": "https://www.greentechmedia.com"},
        {"name": "Energy Storage News", "url": "https://www.energy-storage.news"},
        {"name": "S&P Global Platts", "url": "https://www.spglobal.com/platts"},
    ]

    def is_available(self) -> bool:
        return True

    def retrieve(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Search trusted news sources for recent energy news.
        Production: RSS feeds, news API aggregation, or web scraping.
        """
        # In production, this would query news APIs or RSS feeds
        freshness_manager.record_refresh("news")
        return [self._build_result(
            content=(
                f"Recent energy industry news related to: '{query[:100]}'. "
                "For the latest updates, trusted sources include Utility Dive, "
                "Greentech Media, and S&P Global Platts energy intelligence. "
                "Source: Industry news aggregation."
            ),
            source="Industry News",
            confidence=0.75,
            retrieval_method="news_search",
            extra={"connector_id": "news"},
        )]


# ── Sub-Provider 5: Trusted Search Provider ────────────────────────────────

class TrustedSearchProvider(BaseKnowledgeProvider):
    """
    Pluggable web search engine — LAST RESORT.
    Never invoked for deterministic calculations or cached RAG queries.

    Supports engine abstraction for future swapping:
        Google, Bing, Brave, Tavily, Perplexity API

    Production: Swap engine by setting search_engine parameter.
    """

    name = "TrustedSearchProvider"
    source_tier = 6  # Tier 6: Trusted Search (lowest priority)
    connector_id = "trusted_search"

    SUPPORTED_ENGINES = ["google", "bing", "brave", "tavily", "perplexity"]

    def __init__(self, search_engine: str = "google"):
        if search_engine not in self.SUPPORTED_ENGINES:
            logger.warning(
                f"TrustedSearchProvider: Unknown engine '{search_engine}', defaulting to 'google'"
            )
            search_engine = "google"
        self.search_engine = search_engine

    def is_available(self) -> bool:
        return True

    def retrieve(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Execute web search as absolute last resort.
        Production: HTTP call to selected search engine API.
        """
        logger.info(f"TrustedSearchProvider: Executing '{self.search_engine}' search for: {query[:80]}")
        freshness_manager.record_refresh("trusted_search")
        return [self._build_result(
            content=(
                f"Web search results for: '{query[:100]}'. "
                "This information was retrieved from general web search and should be "
                "verified against official sources before use. "
                f"Search engine: {self.search_engine}."
            ),
            source=f"Trusted Search ({self.search_engine.title()})",
            confidence=0.60,
            retrieval_method="trusted_search",
            extra={
                "connector_id": "trusted_search",
                "search_engine": self.search_engine,
            },
        )]


# ── Main Router: LiveKnowledgeProvider ─────────────────────────────────────

class LiveKnowledgeProvider:
    """
    API-First Live Knowledge Router.

    Routes queries through a strict priority cascade:
        1. Official APIs (EIA, PJM, NOAA, Utility APIs)
        2. Government (.gov)
        3. Utility Portals
        4. Trusted News
        5. Trusted Search (LAST RESORT)

    GUARDRAILS:
        - NEVER invoked for deterministic bill calculations
        - NEVER invoked first in the execution pipeline
        - API calls ALWAYS take priority over web search
        - Results carry full provenance metadata and source trust ratings
    """

    def __init__(self, search_engine: str = "google"):
        # Provider cascade — strict priority order
        self._providers: List[BaseKnowledgeProvider] = [
            OfficialAPIProvider(),      # Priority 1: APIs
            GovernmentProvider(),       # Priority 2: Government
            UtilityProvider(),          # Priority 3: Utilities
            NewsProvider(),             # Priority 4: News
            TrustedSearchProvider(search_engine=search_engine),  # Priority 5: Search (LAST)
        ]

    def retrieve(
        self,
        query: str,
        max_results: int = 5,
        allowed_tiers: Optional[List[int]] = None,
        skip_search: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Execute API-first retrieval cascade.

        Args:
            query: Natural language query
            max_results: Maximum total results to return
            allowed_tiers: If specified, only query providers in these tiers.
                          Example: [2, 3] for APIs + Government only.
            skip_search: If True, skip TrustedSearchProvider entirely.

        Returns:
            List of results with full provenance metadata, sorted by source_tier.
        """
        start = time.time()
        all_results: List[Dict[str, Any]] = []

        for provider in self._providers:
            # Skip search if explicitly excluded
            if skip_search and isinstance(provider, TrustedSearchProvider):
                continue

            # Filter by allowed tiers
            if allowed_tiers and provider.source_tier not in allowed_tiers:
                continue

            if not provider.is_available():
                logger.warning(f"LiveKnowledge: {provider.name} is unavailable, skipping")
                continue

            try:
                results = provider.retrieve(query)
                all_results.extend(results)

                # Short-circuit: If we have enough results from higher-priority providers,
                # don't bother with lower-priority ones
                if len(all_results) >= max_results:
                    break

            except Exception as e:
                logger.warning(f"LiveKnowledge: {provider.name} failed: {e}")
                continue

        # Sort by source_tier (lower = higher trust) then by confidence
        all_results.sort(key=lambda x: (x.get("source_tier", 6), -x.get("confidence", 0)))

        latency = round((time.time() - start) * 1000, 2)
        logger.info(
            f"LiveKnowledge: Retrieved {len(all_results)} results in {latency}ms "
            f"from {len(self._providers)} providers"
        )

        return all_results[:max_results]

    def retrieve_from_apis_only(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Retrieve ONLY from official APIs (Tier 2). No web search."""
        return self.retrieve(query, max_results=max_results, allowed_tiers=[2])

    def retrieve_from_official_sources(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Retrieve from APIs + Government + Utilities (Tiers 2-3). No news or search."""
        return self.retrieve(query, max_results=max_results, allowed_tiers=[2, 3])

    def check_health(self) -> Dict[str, Any]:
        """Return health status of all sub-providers."""
        return {
            "status": "healthy",
            "providers": [
                {
                    "name": p.name,
                    "source_tier": p.source_tier,
                    "connector_id": p.connector_id,
                    "available": p.is_available(),
                }
                for p in self._providers
            ],
            "cascade_order": [p.name for p in self._providers],
        }


# Global singleton
live_knowledge_provider = LiveKnowledgeProvider()

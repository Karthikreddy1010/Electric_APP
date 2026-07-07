from api.routes.tariffs import router
from api.routes.service_territory import router as r2
from api.services.tariff_service import get_default_residential_tariff, get_tariff_by_zip
from api.services.service_territory_service import get_county_utilities, get_state_utilities, get_utility_service_area, get_service_statistics
print("All imports OK")

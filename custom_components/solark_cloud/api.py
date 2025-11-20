"""API client for Sol-Ark Cloud."""
import logging
from typing import Any, Dict, Optional
import asyncio
import aiohttp
from datetime import datetime

_LOGGER = logging.getLogger(__name__)


class SolArkCloudAPIError(Exception):
    """Exception for Sol-Ark Cloud API errors."""


class SolArkCloudAPI:
    """Sol-Ark Cloud API client."""

    def __init__(
        self,
        username: str,
        password: str,
        plant_id: str,
        base_url: str = "https://api.solarkcloud.com",
        auth_mode: str = "auto",
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        """Initialize the API client."""
        self.username = username
        self.password = password
        self.plant_id = plant_id
        self.base_url = base_url.rstrip("/")
        self.auth_mode = auth_mode
        self._session = session
        self._own_session = session is None
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    async def __aenter__(self):
        """Async enter."""
        if self._own_session:
            self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        """Async exit."""
        if self._own_session and self._session:
            await self._session.close()

    def _get_headers(self, mode: str = "strict") -> Dict[str, str]:
        """Get headers based on auth mode."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        if mode == "strict":
            headers.update({
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/",
            })
        
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        auth_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Make an API request."""
        if not self._session:
            raise SolArkCloudAPIError("Session not initialized")

        mode = auth_mode or self.auth_mode
        url = f"{self.base_url}{endpoint}"
        
        headers = self._get_headers(mode if mode != "auto" else "strict")
        
        try:
            async with self._session.request(
                method,
                url,
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                result = await response.json()
                
                # Check for API-level errors
                if isinstance(result, dict):
                    if result.get("code") != "0" and result.get("code") != 0:
                        error_msg = result.get("msg", "Unknown error")
                        raise SolArkCloudAPIError(f"API error: {error_msg}")
                
                return result
                
        except aiohttp.ClientError as err:
            # If strict mode failed and we're in auto mode, try legacy
            if mode == "auto":
                _LOGGER.debug("Strict mode failed, trying legacy mode")
                return await self._request(method, endpoint, data, "legacy")
            raise SolArkCloudAPIError(f"Request failed: {err}") from err
        except asyncio.TimeoutError as err:
            raise SolArkCloudAPIError("Request timeout") from err

    async def login(self) -> bool:
        """Authenticate with Sol-Ark Cloud."""
        try:
            data = {
                "username": self.username,
                "password": self.password,
            }
            
            result = await self._request("POST", "/rest/account/login", data)
            
            # Extract token from response
            if isinstance(result, dict):
                # Different possible response structures
                self._token = result.get("token") or result.get("access_token")
                
                if not self._token:
                    # Some APIs return nested data
                    if "data" in result and isinstance(result["data"], dict):
                        self._token = result["data"].get("token")
                
                if self._token:
                    _LOGGER.debug("Successfully authenticated with Sol-Ark Cloud")
                    return True
            
            raise SolArkCloudAPIError("No token in login response")
            
        except SolArkCloudAPIError:
            raise
        except Exception as err:
            raise SolArkCloudAPIError(f"Login failed: {err}") from err

    async def get_plant_data(self) -> Dict[str, Any]:
        """Get plant data from Sol-Ark Cloud."""
        if not self._token:
            await self.login()
        
        try:
            data = {
                "plantId": self.plant_id,
            }
            
            result = await self._request("POST", "/rest/plant/getPlantData", data)
            
            # Extract data from response
            if isinstance(result, dict):
                if "data" in result:
                    return result["data"]
                return result
            
            return {}
            
        except SolArkCloudAPIError as err:
            # If we get an auth error, try to re-login
            if "401" in str(err) or "auth" in str(err).lower():
                _LOGGER.debug("Token expired, re-authenticating")
                self._token = None
                await self.login()
                return await self.get_plant_data()
            raise

    async def test_connection(self) -> bool:
        """Test the connection to Sol-Ark Cloud."""
        try:
            await self.login()
            await self.get_plant_data()
            return True
        except SolArkCloudAPIError as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False

    def parse_plant_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse plant data into sensor values."""
        sensors = {}
        
        try:
            # These field names may vary - adjust based on actual API response
            sensors["pv_power"] = float(data.get("pvPower", 0))
            sensors["load_power"] = float(data.get("loadPower", 0))
            sensors["grid_import_power"] = float(data.get("gridImportPower", 0))
            sensors["grid_export_power"] = float(data.get("gridExportPower", 0))
            sensors["battery_power"] = float(data.get("battPower", 0))
            sensors["battery_soc"] = float(data.get("battSoc", 0))
            sensors["energy_today"] = float(data.get("energyToday", 0))
            sensors["last_error"] = data.get("lastError", "None")
            
        except (KeyError, ValueError, TypeError) as err:
            _LOGGER.warning("Error parsing plant data: %s", err)
        
        return sensors

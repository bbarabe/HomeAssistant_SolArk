"""Authentication helpers for Sol-Ark Cloud."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import aiohttp

from .solark_errors import SolArkCloudAPIError
from .solark_logging import get_logger

_LOGGER = get_logger(__name__)


class SolArkAuth:
    """Handle Sol-Ark Cloud authentication and token management."""

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str,
        api_url: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self.username = username
        self.password = password
        self.base_url = base_url.rstrip("/")
        self.api_url = api_url.rstrip("/")
        self._session = session

        self._token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def get_headers(self, strict: bool = True) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if strict:
            headers.update(
                {
                    "Origin": self.base_url,
                    "Referer": f"{self.base_url}/",
                }
            )
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def ensure_token(self) -> None:
        if self._token and self._token_expiry and datetime.utcnow() < self._token_expiry:
            return
        _LOGGER.debug("Token missing or expired, logging in again")
        await self.login()

    async def _oauth_login(self) -> None:
        url = f"{self.api_url}/oauth/token"
        headers = self.get_headers(strict=True)
        headers["Content-Type"] = "application/json;charset=UTF-8"

        payload = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
            "client_id": "csp-web",
        }

        _LOGGER.debug("Attempting OAuth login at %s", url)

        try:
            async with self._session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                text = await resp.text()
                _LOGGER.debug(
                    "OAuth login response HTTP %s, body: %s",
                    resp.status,
                    text[:1000],
                )
                try:
                    resp.raise_for_status()
                except aiohttp.ClientResponseError as exc:
                    raise SolArkCloudAPIError(
                        f"OAuth login HTTP {resp.status}: {text[:500]}"
                    ) from exc

                try:
                    result = await resp.json()
                except Exception as exc:  # noqa: BLE001
                    raise SolArkCloudAPIError(
                        f"OAuth login invalid JSON: {text[:200]}"
                    ) from exc

        except asyncio.TimeoutError as exc:  # noqa: BLE001
            raise SolArkCloudAPIError("OAuth login timeout") from exc
        except aiohttp.ClientError as exc:  # noqa: BLE001
            raise SolArkCloudAPIError(f"OAuth login client error: {exc}") from exc

        if not isinstance(result, dict):
            raise SolArkCloudAPIError("OAuth login response not JSON object")

        code = result.get("code")
        if code not in (0, "0"):
            raise SolArkCloudAPIError(
                f"OAuth login failed: {result.get('msg', 'Unknown error')} (code={code})"
            )

        data = result.get("data") or {}
        token = data.get("access_token") or data.get("token")
        if not token:
            raise SolArkCloudAPIError("OAuth login succeeded but no access_token")

        self._token = token
        self._refresh_token = data.get("refresh_token")
        expires_in = int(data.get("expires_in", 3600))
        self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)

        _LOGGER.debug(
            "OAuth login successful, token expires in %s seconds (at %s)",
            expires_in,
            self._token_expiry,
        )

    async def _legacy_login(self) -> None:
        url = "https://api.solarkcloud.com/rest/account/login"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {"username": self.username, "password": self.password}

        _LOGGER.debug("Attempting legacy login at %s", url)

        try:
            async with self._session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                text = await resp.text()
                _LOGGER.debug(
                    "Legacy login response HTTP %s, body: %s",
                    resp.status,
                    text[:1000],
                )
                try:
                    resp.raise_for_status()
                except aiohttp.ClientResponseError as exc:
                    raise SolArkCloudAPIError(
                        f"Legacy login HTTP {resp.status}: {text[:500]}"
                    ) from exc

                try:
                    result = await resp.json()
                except Exception as exc:  # noqa: BLE001
                    raise SolArkCloudAPIError(
                        f"Legacy login invalid JSON: {text[:200]}"
                    ) from exc

        except asyncio.TimeoutError as exc:  # noqa: BLE001
            raise SolArkCloudAPIError("Legacy login timeout") from exc
        except aiohttp.ClientError as exc:  # noqa: BLE001
            raise SolArkCloudAPIError(f"Legacy login client error: {exc}") from exc

        if not isinstance(result, dict):
            raise SolArkCloudAPIError("Legacy login response not JSON object")

        token = (
            result.get("token")
            or result.get("access_token")
            or (result.get("data") or {}).get("token")
            or (result.get("data") or {}).get("access_token")
        )
        if not token:
            raise SolArkCloudAPIError("Legacy login succeeded but no token")

        self._token = token
        self._token_expiry = datetime.utcnow() + timedelta(minutes=30)

        _LOGGER.debug("Legacy login successful, temporary token set")

    async def login(self) -> bool:
        errors: list[str] = []

        try:
            await self._oauth_login()
            return True
        except SolArkCloudAPIError as exc:
            _LOGGER.debug("OAuth login failed: %s", exc)
            errors.append(f"oauth: {exc}")

        try:
            await self._legacy_login()
            return True
        except SolArkCloudAPIError as exc:
            _LOGGER.debug("Legacy login failed: %s", exc)
            errors.append(f"legacy: {exc}")

        raise SolArkCloudAPIError("All login methods failed: " + " | ".join(errors))

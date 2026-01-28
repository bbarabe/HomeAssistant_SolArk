"""Compatibility imports for the SolArk client."""

from .solark_client import SolArkCloudAPI
from .solark_errors import SolArkCloudAPIError

__all__ = ["SolArkCloudAPI", "SolArkCloudAPIError"]

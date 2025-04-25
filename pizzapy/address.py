from enum import Enum
from dataclasses import dataclass


class Country(Enum):
    """Collection of supported countries"""

    UNITED_STATES = "us"
    CANADA = "ca"


@dataclass
class Address:
    """Descriptor of a North American street address."""

    street: str
    city: str
    region: str
    postal_code: int

    @property
    def line_one(self) -> str:
        return self.street

    @property
    def line_two(self) -> str:
        return f"{self.city} {self.region} {self.postal_code}"

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

    # def nearby_stores(self, service="Delivery"):
    #     """Query the API to find nearby stores.
    #
    #     nearby_stores will filter the information we receive from the API
    #     to exclude stores that are not currently online (!['IsOnlineNow']),
    #     and stores that are not currently in service (!['ServiceIsOpen']).
    #     """
    #     data = request_json(
    #         self.urls.find_url(), line1=self.line1, line2=self.line2, type=service
    #     )
    #     return [
    #         Store(x, self.country)
    #         for x in data["Stores"]
    #         if x["IsOnlineNow"] and x["ServiceIsOpen"][service]
    #     ]
    #
    # def closest_store(self, service="Delivery"):
    #     stores = self.nearby_stores(service=service)
    #     if not stores:
    #         raise Exception("No local stores are currently open")
    #     return stores[0]

from collections.abc import Generator
from enum import Enum
from json import JSONDecodeError

import httpx
import structlog

from pizzapy.address import Address
from pizzapy.store import PickupType, Store

logger = structlog.stdlib.get_logger(__name__)


class DominosApiEndpoints(Enum):
    """Collection of valid Dominos API endpoint URLs"""

    FIND_STORE = "https://order.dominos.com/power/store-locator?s=${address_line_one}&c=${address_line_two}&type=${pickup_type}"
    GET_MENU = (
        "https://order.dominos.com/power/store/${store_id}/menu?lang=en&structured=true"
    )


class DominosApiConnector:
    """Interface connections to the Dominos API."""

    def get_nearest_stores(
        self, address: Address, pickup_type: PickupType
    ) -> Generator[Store]:
        endpoint = DominosApiEndpoints.FIND_STORE
        url = endpoint.value.format(
            address_line_one=address.line_one,
            address_line_two=address.line_two,
            pickup_type=pickup_type.value,
        )
        with httpx.Client() as client:
            response = client.get(url)

        try:
            data = response.json()
        except JSONDecodeError:
            logger.error("Failed to parse JSON from Dominos", response=response)
            return

        stores = data.get("Stores", [])
        if not stores:
            logger.warning("No stores found near address", address=address)
            return

        for store in stores:
            store_address = store.get("Address", {})
            if not store_address:
                logger.warning("Could not parse store address", raw_store=store)
                return None

            store_address_street = store_address.get("Street", None)
            store_address_city = store_address.get("City", None)
            store_address_region = store_address.get("Region", None)
            store_address_postal_code = store_address.get("PostalCode", None)

            if not any(
                (
                    store_address_street,
                    store_address_city,
                    store_address_region,
                    store_address_postal_code,
                )
            ):
                logger.warning("Could not parse store address", raw_store=store)
                return None

            try:
                postal_code = int(store_address_postal_code)
                id_ = int(store.get("StoreID", None))
            except ValueError:
                logger.error(
                    "Failed to convert number strings to integers",
                    raw_store=store,
                )
                return None

            is_available = store.get("IsOnlineNow", False) and store.get(
                "ServiceIsOpen", {}
            ).get(pickup_type.value, False)

            yield Store(
                id_=id_,
                address=Address(
                    street=store_address_street,
                    city=store_address_city,
                    region=store_address_region,
                    postal_code=postal_code,
                ),
                is_available=is_available,
            )

    def get_store_closest_to_address(
        self, address: Address, pickup_type: PickupType
    ) -> Store | None:
        for store in self.get_nearest_stores(address, pickup_type):
            if store.is_available:
                return store
        return None

    def get_menu_for_store(self, store: Store) -> None:
        endpoint = DominosApiEndpoints.GET_MENU
        url = endpoint.value.format(store_id=store.id_)
        with httpx.Client() as client:
            response = client.get(url)

        try:
            data = response.json()
        except JSONDecodeError:
            logger.error("Failed to parse JSON from Dominos", response=response)
            return

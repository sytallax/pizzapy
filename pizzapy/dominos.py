from collections.abc import Generator
import re
from enum import Enum
from json import JSONDecodeError
from typing import Any

import httpx
import structlog

from pizzapy.address import Address
from pizzapy.coupon import Coupon
from pizzapy.menu import Menu, MenuCategory, MenuCoupon, MenuLineItem, MenuProduct
from pizzapy.store import PickupType, Store

logger = structlog.stdlib.get_logger(__name__)


class DominosApiEndpoints(Enum):
    """Collection of valid Dominos API endpoint URLs"""

    FIND_STORE = "https://order.dominos.com/power/store-locator?s={address_line_one}&c={address_line_two}&type={pickup_type}"
    GET_MENU = (
        "https://order.dominos.com/power/store/{store_id}/menu?lang=en&structured=true"
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

    def get_menu_for_store(self, store: Store) -> Menu | None:
        endpoint = DominosApiEndpoints.GET_MENU
        url = endpoint.value.format(store_id=store.id_)
        with httpx.Client() as client:
            response = client.get(url)

        try:
            data = response.json()
        except JSONDecodeError:
            logger.error(
                "Failed to parse JSON from Dominos", response=response, url=response.url
            )
            return None

        categories: list[dict[str, Any]] = (
            data.get("Categorization", {}).get("Food", {}).get("Categories", [])
        )
        products: dict[str, dict[str, Any]] = data.get("Products", {})
        variants = data.get("Variants", {})
        coupons = data.get("Coupons", {})

        if not any((categories, products, variants, coupons)):
            logger.error("Could not parse menu", raw_menu=data)
            return None

        parsed_categories = self._parse_categories(categories)
        parsed_products = self._parse_products(products)
        parsed_line_items = self._parse_line_items(variants)
        parsed_coupons = self._parse_coupons(coupons)

        return Menu(
            categories=list(parsed_categories),
            products=list(parsed_products),
            line_items=list(parsed_line_items),
            coupons=list(parsed_coupons),
        )

    def _parse_categories(self, data: list[dict[str, Any]]) -> Generator[MenuCategory]:
        def get_all_product_codes_from_category(data: dict[str, Any]) -> Generator[str]:
            if not {"Categories", "Code", "Name", "Description", "Products"}.issubset(
                data.keys()
            ):
                logger.error("Incorrect menu category format", data=data)
                return

            categories = data.get("Categories", [])
            products = data.get("Products", [])

            if not products:
                for subcategory in categories:
                    yield from get_all_product_codes_from_category(subcategory)

            yield from products

        for category in data:
            if not {"Categories", "Code", "Name", "Description", "Products"}.issubset(
                category.keys()
            ):
                logger.error("Incorrect menu category format", data=category)
                return

            product_codes = set(get_all_product_codes_from_category(category))
            code = category.get("Code", "")
            name = category.get("Name", "")
            description = category.get("Description", "")

            if not any((product_codes, code, name, description)):
                logger.error("Could not parse menu category data", raw_data=data)

            yield MenuCategory(
                code=code, name=name, description=description, products=product_codes
            )

    def _parse_products(
        self, data: dict[str, dict[str, Any]]
    ) -> Generator[MenuProduct]:
        for code, product in data.items():
            if not {"Code", "Name", "ProductType", "Description", "Variants"}.issubset(
                product.keys()
            ):
                logger.error("Incorrect product format", raw_data=product)
                return

            name = product.get("Name", "")
            description = product.get("Description", "")
            variants = product.get("Variants", [])
            yield MenuProduct(
                code=code, name=name, description=description, variants=set(variants)
            )

    def _parse_line_items(self, data: dict[str, Any]) -> Generator[MenuLineItem]:
        for code, variant in data.items():
            if not {"Code", "Name", "Price", "SizeCode", "ProductCode"}.issubset(
                variant.keys()
            ):
                logger.error("Incorrect variant format", data=(code, variant))
                return

            name = variant.get("Name", "")
            product_code = variant.get("ProductCode", "")

            try:
                price = float(variant.get("Price", 0.0))
            except ValueError:
                logger.error(
                    "Failed to parse price for line item", raw_line_item=variant
                )
                return
            yield MenuLineItem(code, name, product_code, price)

    def _parse_coupons(self, data: dict[str, Any]) -> Generator[MenuCoupon]:
        for code, coupon in data.items():
            if not {"Code", "Name", "Price"}.issubset(coupon.keys()):
                logger.error("Incorrect coupon format", data=coupon)
                return
            name = coupon.get("Name", "")
            price = coupon.get("Price", "")
            if price and not re.search(r"\$\d{1,2}\.\d{2}", name):
                name += f" ${price}"

            yield MenuCoupon(code, name)

from collections.abc import Sequence, Set
from dataclasses import dataclass


@dataclass
class MenuCategory:
    code: str
    name: str
    description: str
    products: Set[str]


@dataclass
class MenuProduct:
    code: str
    name: str
    description: str
    variants: Set[str]


@dataclass
class MenuLineItem:
    code: str
    name: str
    product: MenuProduct
    price: float


@dataclass
class MenuCoupon:
    code: str
    name: str


@dataclass
class Menu:
    categories: Sequence[MenuCategory]
    products: Sequence[MenuProduct]
    line_items: Sequence[MenuLineItem]
    coupons: Sequence[MenuCoupon]


# class Menu(object):
#     """The Menu is our primary interface with the API.
#
#     This is far and away the most complicated class - it wraps up most of
#     the logic that parses the information we get from the API.
#
#     Next time I get pizza, there is a lot of work to be done in
#     documenting this class.
#     """
#
#     def __init__(self, data={}, country=COUNTRY_USA):
#         self.variants = data.get("Variants", {})
#         self.menu_by_code = {}
#         self.root_categories = {}
#         self.country = COUNTRY_USA
#
#         if self.variants:
#             self.products = self.parse_items(data["Products"])
#             self.coupons = self.parse_items(data["Coupons"])
#             self.preconfigured = self.parse_items(data["PreconfiguredProducts"])
#             for key, value in data["Categorization"].items():
#                 self.root_categories[key] = self.build_categories(value)
#
#     @classmethod
#     def from_store(cls, store_id, lang="en", country=COUNTRY_USA):
#         response = request_json(Urls(country).menu_url(), store_id=store_id, lang=lang)
#         menu = cls(response)
#         return menu
#
#     # TODO: Reconfigure structure to show that Codes (not ProductCodes) matter
#     def build_categories(self, category_data, parent=None):
#         category = MenuCategory(category_data, parent)
#         for subcategory in category_data["Categories"]:
#             new_subcategory = self.build_categories(subcategory, category)
#             category.subcategories.append(new_subcategory)
#         for product_code in category_data["Products"]:
#             if product_code not in self.menu_by_code:
#                 print("PRODUCT NOT FOUND: %s %s" % (product_code, category.code))
#             else:
#                 product = self.menu_by_code[product_code]
#                 category.items.append(product)
#                 product.categories.append(category)
#         return category
#
#     def parse_items(self, parent_data):
#         items = []
#         for code in parent_data.keys():
#             obj = MenuItem(parent_data[code])
#             self.menu_by_code[obj.code] = obj
#             items.append(obj)
#         return items
#
#     # TODO: Print codes that can actually be used to order items
#     def display(self):
#         def print_category(category, depth=1):
#             indent = "  " * (depth + 1)
#             if len(category.products) + len(category.subcategories) > 0:
#                 print(indent + category.name)
#                 for subcategory in category.subcategories:
#                     print_category(subcategory, depth + 1)
#                 for product in category.products:
#                     print(indent + "  [%s]" % product.code, product.name)
#
#     # TODO: Find more pythonic way to format the menu
#     # TODO: Format the menu after the variants have been filtered
#     # TODO: Return the search results and print in different method
#     # TODO: Import fuzzy search module or allow lists as search conditions
#     def search(self, **conditions):
#         max_len = lambda x: 2 + max(len(v[x]) for v in list(self.variants.values()))
#         for v in self.variants.values():
#             v["Toppings"] = dict(
#                 x.split("=", 1) for x in v["Tags"]["DefaultToppings"].split(",") if x
#             )
#             if all(y in v.get(x, "") for x, y in conditions.items()):
#                 pass
#             return "Hello?"

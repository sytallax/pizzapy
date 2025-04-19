from dataclasses import dataclass
from .address import Address


@dataclass
class Customer:
    """Information about user who orders a pizza."""

    first_name: str
    last_name: str
    email: str
    phone_number: int
    address: Address

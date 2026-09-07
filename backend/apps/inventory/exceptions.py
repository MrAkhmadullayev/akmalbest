"""Inventory domain exceptions."""


class InventoryError(ValueError):
    """Base class for inventory errors.

    Inherits from ValueError so existing views that catch ValueError and turn it
    into a 400 response keep working.
    """


class InsufficientStockError(InventoryError):
    """Raised when a decrease would push stock below zero."""

    def __init__(self, product, requested, available):
        self.product = product
        self.requested = requested
        self.available = available
        super().__init__(
            f"Omborda yetarli mahsulot mavjud emas. "
            f"'{product.name}' - Mavjud: {available}, So'ralgan: {requested}"
        )

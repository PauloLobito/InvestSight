from decimal import Decimal
from typing import Optional

from django.db import models

from apps.apis.services.unified import get_price


class AssetType(models.TextChoices):
    CRYPTO = "crypto", "Cryptocurrency"
    STOCK = "stock", "Stock"


class Asset(models.Model):
    symbol = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=20, choices=AssetType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.symbol = self.symbol.upper()
        super().save(*args, **kwargs)

    @property
    def current_price(self) -> Optional[Decimal]:
        result = get_price(self.symbol)
        if result:
            return result.price
        return None

    def __str__(self):
        return f"{self.symbol} ({self.name})"


class Holding(models.Model):
    portfolio = models.ForeignKey(
        "portfolio.Portfolio", on_delete=models.CASCADE, related_name="holdings"
    )
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="holdings")
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    avg_buy_price = models.DecimalField(max_digits=20, decimal_places=8)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_cost(self) -> Decimal:
        return self.quantity * self.avg_buy_price

    @property
    def current_value(self) -> Optional[Decimal]:
        current_price = self.asset.current_price
        if current_price is None:
            return None
        return self.quantity * current_price

    @property
    def profit_loss(self) -> Optional[Decimal]:
        current = self.current_value
        if current is None:
            return None
        return current - self.total_cost

    @property
    def pnl_pct(self) -> Optional[Decimal]:
        if self.total_cost == 0:
            return None
        pl = self.profit_loss
        if pl is None:
            return None
        return (pl / self.total_cost) * 100

    def __str__(self):
        return f"{self.asset.symbol} x {self.quantity}"

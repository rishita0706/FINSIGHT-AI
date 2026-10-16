"""Disabled integration contract for a future user-authorized financial data source."""

from __future__ import annotations

from typing import Protocol


class FinancialDataProvider(Protocol):
    name: str

    def fetch_transactions(self, account_reference: str) -> list[dict]: ...


def get_provider() -> None:
    """Live financial-data providers are intentionally unavailable in this MVP."""
    return None

import unittest
from datetime import datetime

from src.risk import RiskManager
from src.strategy import MovingAverageCrossStrategy
from src.trader import DayTrader, MARKET_CLOSE, MARKET_OPEN


class FakeClient:
    """Minimal stand-in for KISClient. Returns pre-scripted quotes; never calls the network."""

    is_virtual = True

    def __init__(self):
        self.closes_by_code = {}
        self.price_by_code = {}
        self.balance = {"cash": 10_000_000, "total_equity": 10_000_000, "holdings": []}

    def get_minute_closes(self, code, count=30):
        return self.closes_by_code.get(code, [])[-count:]

    def get_current_price(self, code):
        return self.price_by_code[code]

    def get_balance(self):
        return self.balance

    def place_order(self, *args, **kwargs):
        raise AssertionError("place_order must never be called while dry_run=True")


def make_trader(client, dry_run=True):
    strategy = MovingAverageCrossStrategy(short_period=2, long_period=4)
    risk = RiskManager(
        max_position_pct=10,
        max_concurrent_positions=3,
        stop_loss_pct=2,
        take_profit_pct=3,
        daily_loss_limit_pct=5,
    )
    return DayTrader(
        client=client,
        strategy=strategy,
        risk=risk,
        watchlist=["005930"],
        candle_count=6,
        poll_interval_sec=1,
        request_interval_sec=0,
        force_close_time=MARKET_CLOSE,
        dry_run=dry_run,
        dry_run_starting_cash=10_000_000,
    )


class TestDayTraderDryRunCycle(unittest.TestCase):
    def test_golden_cross_opens_dry_run_position(self):
        client = FakeClient()
        client.closes_by_code["005930"] = [10000, 10000, 10000, 10000, 10000, 20000]
        client.price_by_code["005930"] = 20000

        trader = make_trader(client)
        trader._run_cycle()

        self.assertIn("005930", trader.positions)
        self.assertLess(trader.dry_run_cash, 10_000_000)

    def test_stop_loss_closes_dry_run_position(self):
        client = FakeClient()
        client.closes_by_code["005930"] = [10000, 10000, 10000, 10000, 10000, 20000]
        client.price_by_code["005930"] = 20000
        trader = make_trader(client)
        trader._run_cycle()
        self.assertIn("005930", trader.positions)
        cash_after_buy = trader.dry_run_cash

        client.price_by_code["005930"] = 19000  # -5% from 20000 entry, breaches 2% stop loss
        trader._run_cycle()

        self.assertNotIn("005930", trader.positions)
        self.assertGreater(trader.dry_run_cash, cash_after_buy)

    def test_liquidate_all_clears_positions(self):
        client = FakeClient()
        client.closes_by_code["005930"] = [10000, 10000, 10000, 10000, 10000, 20000]
        client.price_by_code["005930"] = 20000
        trader = make_trader(client)
        trader._run_cycle()
        self.assertIn("005930", trader.positions)

        trader.liquidate_all("test force close")
        self.assertEqual(trader.positions, {})


class TestMarketHours(unittest.TestCase):
    def test_closed_on_weekend(self):
        saturday = datetime(2026, 8, 8, 10, 0)  # 2026-08-08 is a Saturday
        self.assertEqual(saturday.weekday(), 5)
        self.assertFalse(DayTrader.is_market_open(saturday))

    def test_open_during_market_hours_on_weekday(self):
        monday_noon = datetime(2026, 8, 10, 12, 0)
        self.assertEqual(monday_noon.weekday(), 0)
        self.assertTrue(DayTrader.is_market_open(monday_noon))

    def test_closed_before_open(self):
        early = datetime(2026, 8, 10, 8, 59)
        self.assertFalse(DayTrader.is_market_open(early))

    def test_boundaries_are_inclusive(self):
        at_open = datetime(2026, 8, 10, MARKET_OPEN.hour, MARKET_OPEN.minute)
        at_close = datetime(2026, 8, 10, MARKET_CLOSE.hour, MARKET_CLOSE.minute)
        self.assertTrue(DayTrader.is_market_open(at_open))
        self.assertTrue(DayTrader.is_market_open(at_close))


if __name__ == "__main__":
    unittest.main()

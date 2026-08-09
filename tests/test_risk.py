import unittest

from src.risk import RiskManager


def make_risk(**overrides):
    defaults = dict(
        max_position_pct=10,
        max_concurrent_positions=3,
        stop_loss_pct=2,
        take_profit_pct=3,
        daily_loss_limit_pct=5,
    )
    defaults.update(overrides)
    return RiskManager(**defaults)


class TestStopLossTakeProfit(unittest.TestCase):
    def setUp(self):
        self.risk = make_risk()

    def test_stop_loss_triggers_below_threshold(self):
        self.assertTrue(self.risk.should_stop_loss(entry_price=10000, current_price=9790))

    def test_stop_loss_not_triggered_within_threshold(self):
        self.assertFalse(self.risk.should_stop_loss(entry_price=10000, current_price=9850))

    def test_take_profit_triggers_above_threshold(self):
        self.assertTrue(self.risk.should_take_profit(entry_price=10000, current_price=10310))

    def test_take_profit_not_triggered_below_threshold(self):
        self.assertFalse(self.risk.should_take_profit(entry_price=10000, current_price=10200))


class TestPositionSizing(unittest.TestCase):
    def test_qty_capped_by_max_position_pct(self):
        risk = make_risk(max_position_pct=10)
        qty = risk.calculate_order_qty(available_cash=100_000_000, total_equity=10_000_000, price=10_000)
        # 10% of 10,000,000 = 1,000,000 -> 100 shares at 10,000
        self.assertEqual(qty, 100)

    def test_qty_capped_by_available_cash(self):
        risk = make_risk(max_position_pct=50)
        qty = risk.calculate_order_qty(available_cash=5_000, total_equity=10_000_000, price=10_000)
        self.assertEqual(qty, 0)

    def test_zero_price_returns_zero_qty(self):
        risk = make_risk()
        self.assertEqual(risk.calculate_order_qty(1_000_000, 1_000_000, 0), 0)


class TestConcurrentPositionsAndDailyLoss(unittest.TestCase):
    def test_can_open_new_position_respects_max(self):
        risk = make_risk(max_concurrent_positions=2)
        self.assertTrue(risk.can_open_new_position(current_position_count=1))
        self.assertFalse(risk.can_open_new_position(current_position_count=2))

    def test_daily_loss_limit_halts_new_entries(self):
        risk = make_risk(daily_loss_limit_pct=5)
        risk.start_day(10_000_000)
        self.assertFalse(risk.check_daily_loss_limit(9_600_000))  # -4% loss, not halted
        self.assertTrue(risk.can_open_new_position(0))

        self.assertTrue(risk.check_daily_loss_limit(9_400_000))  # -6% loss, halted
        self.assertFalse(risk.can_open_new_position(0))

    def test_new_day_resets_halt(self):
        risk = make_risk(daily_loss_limit_pct=5)
        risk.start_day(10_000_000)
        risk.check_daily_loss_limit(9_000_000)
        self.assertTrue(risk.halted)

        risk.start_day(9_000_000)
        self.assertFalse(risk.halted)
        self.assertTrue(risk.can_open_new_position(0))


if __name__ == "__main__":
    unittest.main()

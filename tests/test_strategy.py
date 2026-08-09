import unittest

from src.strategy import MovingAverageCrossStrategy, sma


class TestSMA(unittest.TestCase):
    def test_sma_insufficient_data(self):
        self.assertIsNone(sma([1, 2], 3))

    def test_sma_basic(self):
        self.assertAlmostEqual(sma([1, 2, 3, 4, 5], 3), 4.0)


class TestMovingAverageCrossStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = MovingAverageCrossStrategy(short_period=2, long_period=4)

    def test_not_enough_data_returns_none(self):
        self.assertIsNone(self.strategy.evaluate([1, 2, 3], holding=False))

    def test_golden_cross_generates_buy(self):
        closes = [10, 10, 10, 10, 10, 20]
        signal = self.strategy.evaluate(closes, holding=False)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, "BUY")

    def test_no_signal_when_flat(self):
        closes = [10] * 8
        self.assertIsNone(self.strategy.evaluate(closes, holding=False))

    def test_dead_cross_generates_sell_only_when_holding(self):
        closes = [10, 10, 10, 10, 10, 0]
        signal_not_holding = self.strategy.evaluate(closes, holding=False)
        self.assertIsNone(signal_not_holding)

        signal_holding = self.strategy.evaluate(closes, holding=True)
        self.assertIsNotNone(signal_holding)
        self.assertEqual(signal_holding.action, "SELL")

    def test_buy_signal_suppressed_when_already_holding(self):
        closes = [10, 10, 10, 10, 10, 20]
        signal = self.strategy.evaluate(closes, holding=True)
        self.assertIsNone(signal)


if __name__ == "__main__":
    unittest.main()

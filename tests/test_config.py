import unittest

from config import Config


def make_config(**overrides):
    base = dict(
        app_key="key",
        app_secret="secret",
        account_no="12345678",
        account_product_code="01",
        is_virtual=True,
        dry_run=True,
        confirm_live_trading=False,
        watchlist=["005930"],
        short_ma=5,
        long_ma=20,
        candle_interval_min=1,
        max_position_pct=10,
        max_concurrent_positions=3,
        stop_loss_pct=2,
        take_profit_pct=3,
        daily_loss_limit_pct=5,
        poll_interval_sec=30,
        request_interval_sec=0.3,
        dry_run_starting_cash=10_000_000,
    )
    base.update(overrides)
    return Config(**base)


class TestConfigValidate(unittest.TestCase):
    def test_valid_config_passes(self):
        make_config().validate()  # should not raise

    def test_missing_app_key_raises(self):
        with self.assertRaises(ValueError):
            make_config(app_key="").validate()

    def test_empty_watchlist_raises(self):
        with self.assertRaises(ValueError):
            make_config(watchlist=[]).validate()

    def test_invalid_stock_code_raises(self):
        with self.assertRaises(ValueError):
            make_config(watchlist=["AAPL"]).validate()

    def test_short_ma_must_be_less_than_long_ma(self):
        with self.assertRaises(ValueError):
            make_config(short_ma=20, long_ma=5).validate()

    def test_stop_loss_pct_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            make_config(stop_loss_pct=150).validate()

    def test_live_trading_without_confirmation_raises(self):
        with self.assertRaises(ValueError):
            make_config(dry_run=False, is_virtual=False, confirm_live_trading=False).validate()

    def test_live_trading_with_confirmation_passes(self):
        make_config(dry_run=False, is_virtual=False, confirm_live_trading=True).validate()

    def test_virtual_live_trading_does_not_require_confirmation(self):
        make_config(dry_run=False, is_virtual=True, confirm_live_trading=False).validate()


if __name__ == "__main__":
    unittest.main()

import logging

logger = logging.getLogger("daytrader")


class RiskManager:
    def __init__(
        self,
        max_position_pct: float,
        max_concurrent_positions: int,
        stop_loss_pct: float,
        take_profit_pct: float,
        daily_loss_limit_pct: float,
    ):
        self.max_position_pct = max_position_pct
        self.max_concurrent_positions = max_concurrent_positions
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.daily_start_equity = None
        self.halted = False

    def start_day(self, equity: float):
        self.daily_start_equity = equity
        self.halted = False

    def check_daily_loss_limit(self, current_equity: float) -> bool:
        if self.daily_start_equity is None or self.daily_start_equity == 0:
            return False
        loss_pct = (self.daily_start_equity - current_equity) / self.daily_start_equity * 100
        if loss_pct >= self.daily_loss_limit_pct and not self.halted:
            self.halted = True
            logger.warning(
                "일일 손실 한도(%.1f%%) 도달 (현재 손실 %.1f%%). 신규 진입을 중단합니다.",
                self.daily_loss_limit_pct,
                loss_pct,
            )
        return self.halted

    def can_open_new_position(self, current_position_count: int) -> bool:
        if self.halted:
            return False
        return current_position_count < self.max_concurrent_positions

    def calculate_order_qty(self, available_cash: float, total_equity: float, price: float) -> int:
        if price <= 0:
            return 0
        budget = min(available_cash, total_equity * self.max_position_pct / 100)
        qty = int(budget // price)
        return max(qty, 0)

    def should_stop_loss(self, entry_price: float, current_price: float) -> bool:
        if entry_price <= 0:
            return False
        change_pct = (current_price - entry_price) / entry_price * 100
        return change_pct <= -self.stop_loss_pct

    def should_take_profit(self, entry_price: float, current_price: float) -> bool:
        if entry_price <= 0:
            return False
        change_pct = (current_price - entry_price) / entry_price * 100
        return change_pct >= self.take_profit_pct

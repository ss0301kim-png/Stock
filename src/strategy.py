from dataclasses import dataclass
from typing import Optional


def sma(values: list, period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


@dataclass
class Signal:
    action: str
    reason: str


class MovingAverageCrossStrategy:
    def __init__(self, short_period: int, long_period: int):
        self.short_period = short_period
        self.long_period = long_period

    def evaluate(self, closes: list, holding: bool) -> Optional[Signal]:
        needed = self.long_period + 1
        if len(closes) < needed:
            return None

        prev_short = sma(closes[:-1], self.short_period)
        prev_long = sma(closes[:-1], self.long_period)
        cur_short = sma(closes, self.short_period)
        cur_long = sma(closes, self.long_period)
        if None in (prev_short, prev_long, cur_short, cur_long):
            return None

        golden_cross = prev_short <= prev_long and cur_short > cur_long
        dead_cross = prev_short >= prev_long and cur_short < cur_long

        if not holding and golden_cross:
            return Signal("BUY", f"골든크로스 (MA{self.short_period}={cur_short:.1f} > MA{self.long_period}={cur_long:.1f})")
        if holding and dead_cross:
            return Signal("SELL", f"데드크로스 (MA{self.short_period}={cur_short:.1f} < MA{self.long_period}={cur_long:.1f})")
        return None

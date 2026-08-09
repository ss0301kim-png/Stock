import logging
import time as time_module
from dataclasses import dataclass
from datetime import datetime, time

from src.kis_client import KISClient
from src.risk import RiskManager
from src.strategy import MovingAverageCrossStrategy

logger = logging.getLogger("daytrader")

MARKET_OPEN = time(9, 0)
MARKET_CLOSE = time(15, 30)


@dataclass
class Position:
    entry_price: float
    qty: int


class DayTrader:
    def __init__(
        self,
        client: KISClient,
        strategy: MovingAverageCrossStrategy,
        risk: RiskManager,
        watchlist: list,
        candle_count: int,
        poll_interval_sec: int,
        request_interval_sec: float,
        force_close_time: time,
        dry_run: bool,
        dry_run_starting_cash: float = 10_000_000.0,
    ):
        self.client = client
        self.strategy = strategy
        self.risk = risk
        self.watchlist = watchlist
        self.candle_count = candle_count
        self.poll_interval_sec = poll_interval_sec
        self.request_interval_sec = request_interval_sec
        self.force_close_time = force_close_time
        self.dry_run = dry_run
        self.dry_run_cash = dry_run_starting_cash
        self.positions: dict = {}
        self._forced_close_done = False
        self._trading_date = None

    @staticmethod
    def is_market_open(now: datetime) -> bool:
        if now.weekday() >= 5:
            return False
        return MARKET_OPEN <= now.time() <= MARKET_CLOSE

    def _safe_current_price(self, code: str) -> float:
        try:
            return self.client.get_current_price(code)
        except Exception:
            pos = self.positions.get(code)
            return pos.entry_price if pos else 0.0

    def _sync_positions_from_balance(self, balance: dict):
        broker_holdings = {h["code"]: h for h in balance["holdings"]}
        for code in list(self.positions.keys()):
            if code in self.watchlist and code not in broker_holdings:
                logger.warning("포지션 동기화: %s가 계좌에 없어 내부 상태에서 제거합니다.", code)
                del self.positions[code]
        for code, h in broker_holdings.items():
            if code in self.watchlist:
                prev = self.positions.get(code)
                if prev is None or prev.qty != h["qty"] or prev.entry_price != h["avg_price"]:
                    self.positions[code] = Position(entry_price=h["avg_price"], qty=h["qty"])

    def _execute_buy(self, code: str, qty: int, price: float):
        logger.info("[%s매수] %s %d주 (예상단가 %.0f)", "모의 " if self.dry_run else "", code, qty, price)
        if self.dry_run:
            self.positions[code] = Position(entry_price=price, qty=qty)
            self.dry_run_cash -= qty * price
            return
        result = self.client.place_order(code, "buy", qty, order_type="market")
        if result.get("rt_cd") == "0":
            self.positions[code] = Position(entry_price=price, qty=qty)

    def _execute_sell(self, code: str, current_price: float, reason: str):
        pos = self.positions.get(code)
        if not pos:
            return
        pnl_pct = (current_price - pos.entry_price) / pos.entry_price * 100 if pos.entry_price else 0.0
        logger.info(
            "[%s매도] %s %d주 - %s (손익 %.2f%%)",
            "모의 " if self.dry_run else "",
            code,
            pos.qty,
            reason,
            pnl_pct,
        )
        if self.dry_run:
            self.dry_run_cash += pos.qty * current_price
            del self.positions[code]
            return
        result = self.client.place_order(code, "sell", pos.qty, order_type="market")
        if result.get("rt_cd") == "0":
            del self.positions[code]

    def liquidate_all(self, reason: str):
        for code in list(self.positions.keys()):
            price = self._safe_current_price(code)
            self._execute_sell(code, price, reason)

    def _run_cycle(self):
        if not self.dry_run:
            balance = self.client.get_balance()
            self._sync_positions_from_balance(balance)
            cash = balance["cash"]
            equity = balance["total_equity"]
        else:
            cash = self.dry_run_cash
            equity = self.dry_run_cash + sum(
                pos.qty * self._safe_current_price(code) for code, pos in self.positions.items()
            )

        today = datetime.now().date()
        if self._trading_date != today:
            self._trading_date = today
            self.risk.start_day(equity)
            logger.info("신규 거래일 시작 (%s), 기준자산 %.0f원", today, equity)

        for i, code in enumerate(self.watchlist):
            if i > 0 and self.request_interval_sec > 0:
                time_module.sleep(self.request_interval_sec)
            try:
                closes = self.client.get_minute_closes(code, count=self.candle_count)
                if not closes:
                    continue
                current_price = self.client.get_current_price(code)
                holding = code in self.positions

                if holding:
                    pos = self.positions[code]
                    if self.risk.should_stop_loss(pos.entry_price, current_price):
                        self._execute_sell(
                            code, current_price, f"손절 (진입 {pos.entry_price:.0f} -> 현재 {current_price:.0f})"
                        )
                        continue
                    if self.risk.should_take_profit(pos.entry_price, current_price):
                        self._execute_sell(
                            code, current_price, f"익절 (진입 {pos.entry_price:.0f} -> 현재 {current_price:.0f})"
                        )
                        continue

                signal = self.strategy.evaluate(closes, holding)
                if signal is None:
                    continue

                if signal.action == "SELL" and holding:
                    self._execute_sell(code, current_price, signal.reason)
                elif signal.action == "BUY" and not holding:
                    if not self.risk.can_open_new_position(len(self.positions)):
                        continue
                    qty = self.risk.calculate_order_qty(cash, equity, current_price)
                    if qty > 0:
                        self._execute_buy(code, qty, current_price)
                        cash -= qty * current_price
            except Exception:
                logger.exception("종목 %s 처리 중 오류", code)

        self.risk.check_daily_loss_limit(equity)

    def run(self):
        logger.info(
            "데이트레이딩 봇 시작 (dry_run=%s, is_virtual=%s, watchlist=%s)",
            self.dry_run,
            self.client.is_virtual,
            ",".join(self.watchlist),
        )

        while True:
            now = datetime.now()
            if not self.is_market_open(now):
                logger.info("장 시간이 아닙니다 (%s). 대기합니다.", now.strftime("%H:%M:%S"))
                self._forced_close_done = False
                time_module.sleep(self.poll_interval_sec)
                continue

            if now.time() >= self.force_close_time:
                if not self._forced_close_done:
                    logger.info("장마감 강제 청산 시각 도달 (%s). 보유 포지션을 정리합니다.", self.force_close_time)
                    try:
                        self.liquidate_all("장마감 강제 청산")
                    except Exception:
                        logger.exception("장마감 강제 청산 중 오류 발생")
                    self._forced_close_done = True
                time_module.sleep(self.poll_interval_sec)
                continue

            try:
                self._run_cycle()
            except Exception:
                logger.exception("매매 사이클 처리 중 오류가 발생했습니다. 다음 주기에 재시도합니다.")

            time_module.sleep(self.poll_interval_sec)

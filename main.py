import sys

from config import config
from src.kis_client import KISClient
from src.logger_setup import setup_logger
from src.risk import RiskManager
from src.strategy import MovingAverageCrossStrategy
from src.trader import DayTrader

logger = setup_logger()


def confirm_live_trading():
    print("=" * 60)
    print("경고: 실전투자 계좌로 실제 자동매매 주문을 실행합니다.")
    print("실제 자금 손실이 발생할 수 있습니다.")
    print("=" * 60)
    answer = input("계속하려면 'START'를 입력하세요: ")
    if answer.strip() != "START":
        print("취소되었습니다.")
        sys.exit(0)


def main():
    try:
        config.validate()
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)

    if not config.dry_run and not config.is_virtual:
        confirm_live_trading()

    client = KISClient(
        app_key=config.app_key,
        app_secret=config.app_secret,
        account_no=config.account_no,
        account_product_code=config.account_product_code,
        is_virtual=config.is_virtual,
    )
    strategy = MovingAverageCrossStrategy(config.short_ma, config.long_ma)
    risk = RiskManager(
        max_position_pct=config.max_position_pct,
        max_concurrent_positions=config.max_concurrent_positions,
        stop_loss_pct=config.stop_loss_pct,
        take_profit_pct=config.take_profit_pct,
        daily_loss_limit_pct=config.daily_loss_limit_pct,
    )
    trader = DayTrader(
        client=client,
        strategy=strategy,
        risk=risk,
        watchlist=config.watchlist,
        candle_count=config.long_ma + 5,
        poll_interval_sec=config.poll_interval_sec,
        request_interval_sec=config.request_interval_sec,
        force_close_time=config.force_close_time,
        dry_run=config.dry_run,
        dry_run_starting_cash=config.dry_run_starting_cash,
    )

    try:
        trader.run()
    except KeyboardInterrupt:
        logger.info("종료 요청 수신. 보유 포지션은 유지된 채 프로그램을 종료합니다.")


if __name__ == "__main__":
    main()

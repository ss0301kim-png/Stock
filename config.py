import os
from dataclasses import dataclass, field
from datetime import time

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "y")


def _float(name: str, default: float) -> float:
    val = os.getenv(name)
    return float(val) if val else default


def _int(name: str, default: int) -> int:
    val = os.getenv(name)
    return int(val) if val else default


@dataclass
class Config:
    app_key: str = field(default_factory=lambda: os.getenv("KIS_APP_KEY", ""))
    app_secret: str = field(default_factory=lambda: os.getenv("KIS_APP_SECRET", ""))
    account_no: str = field(default_factory=lambda: os.getenv("KIS_ACCOUNT_NO", ""))
    account_product_code: str = field(default_factory=lambda: os.getenv("KIS_ACCOUNT_PRODUCT_CODE", "01"))

    is_virtual: bool = field(default_factory=lambda: _bool("IS_VIRTUAL", True))
    dry_run: bool = field(default_factory=lambda: _bool("DRY_RUN", True))
    confirm_live_trading: bool = field(
        default_factory=lambda: os.getenv("CONFIRM_LIVE_TRADING", "NO").strip().upper() == "YES"
    )

    watchlist: list = field(
        default_factory=lambda: [c.strip() for c in os.getenv("WATCHLIST", "").split(",") if c.strip()]
    )

    short_ma: int = field(default_factory=lambda: _int("SHORT_MA", 5))
    long_ma: int = field(default_factory=lambda: _int("LONG_MA", 20))
    candle_interval_min: int = field(default_factory=lambda: _int("CANDLE_INTERVAL_MIN", 1))

    max_position_pct: float = field(default_factory=lambda: _float("MAX_POSITION_PCT", 10))
    max_concurrent_positions: int = field(default_factory=lambda: _int("MAX_CONCURRENT_POSITIONS", 3))
    stop_loss_pct: float = field(default_factory=lambda: _float("STOP_LOSS_PCT", 2))
    take_profit_pct: float = field(default_factory=lambda: _float("TAKE_PROFIT_PCT", 3))
    daily_loss_limit_pct: float = field(default_factory=lambda: _float("DAILY_LOSS_LIMIT_PCT", 5))

    poll_interval_sec: int = field(default_factory=lambda: _int("POLL_INTERVAL_SEC", 30))
    request_interval_sec: float = field(default_factory=lambda: _float("REQUEST_INTERVAL_SEC", 0.3))
    dry_run_starting_cash: float = field(default_factory=lambda: _float("DRY_RUN_STARTING_CASH", 10_000_000))

    force_close_time: time = field(init=False)

    def __post_init__(self):
        hh, mm = os.getenv("FORCE_CLOSE_TIME", "15:20").split(":")
        self.force_close_time = time(int(hh), int(mm))

    def validate(self):
        missing = [
            name
            for name, val in (
                ("KIS_APP_KEY", self.app_key),
                ("KIS_APP_SECRET", self.app_secret),
                ("KIS_ACCOUNT_NO", self.account_no),
            )
            if not val
        ]
        if missing:
            raise ValueError(f"필수 환경변수가 비어 있습니다: {', '.join(missing)}. .env를 확인하세요.")

        if not self.watchlist:
            raise ValueError("WATCHLIST가 비어 있습니다. 최소 한 종목을 지정하세요.")
        for code in self.watchlist:
            if not (code.isdigit() and len(code) == 6):
                raise ValueError(f"종목코드 형식이 올바르지 않습니다: '{code}' (6자리 숫자여야 합니다)")

        if self.short_ma <= 0 or self.long_ma <= 0:
            raise ValueError("SHORT_MA와 LONG_MA는 1 이상이어야 합니다.")
        if self.short_ma >= self.long_ma:
            raise ValueError("SHORT_MA는 LONG_MA보다 작아야 합니다.")

        if not (0 < self.stop_loss_pct < 100):
            raise ValueError("STOP_LOSS_PCT는 0~100 사이여야 합니다.")
        if not (0 < self.take_profit_pct < 100):
            raise ValueError("TAKE_PROFIT_PCT는 0~100 사이여야 합니다.")
        if not (0 < self.daily_loss_limit_pct <= 100):
            raise ValueError("DAILY_LOSS_LIMIT_PCT는 0~100 사이여야 합니다.")
        if not (0 < self.max_position_pct <= 100):
            raise ValueError("MAX_POSITION_PCT는 0~100 사이여야 합니다.")
        if self.max_concurrent_positions <= 0:
            raise ValueError("MAX_CONCURRENT_POSITIONS는 1 이상이어야 합니다.")

        if self.poll_interval_sec < 5:
            raise ValueError("POLL_INTERVAL_SEC는 KIS API 요청 제한을 고려해 5초 이상으로 설정하세요.")
        if self.request_interval_sec < 0:
            raise ValueError("REQUEST_INTERVAL_SEC는 0 이상이어야 합니다.")
        if self.dry_run_starting_cash <= 0:
            raise ValueError("DRY_RUN_STARTING_CASH는 0보다 커야 합니다.")

        if not self.dry_run and not self.is_virtual and not self.confirm_live_trading:
            raise ValueError(
                "실계좌 자동매매를 시작하려면 .env에서 CONFIRM_LIVE_TRADING=YES로 설정해야 합니다. "
                "(DRY_RUN=false, IS_VIRTUAL=false 상태에서의 추가 안전 확인)"
            )


config = Config()

# kis-daytrading-bot

한국투자증권(KIS Developers) Open API를 이용한 국내 주식 단타(데이트레이딩) 자동매매 프로그램입니다.
관심 종목의 분봉 이동평균 크로스 신호로 매수/매도를 반복하고, 손절/익절/일일 손실 한도로 리스크를 관리하며,
장 마감 전 보유 포지션을 자동 청산해 당일 매매를 원칙으로 합니다.

## ⚠️ 투자 위험 고지

- 이 프로그램은 **실제 자금으로 실제 주문을 실행**할 수 있습니다. 매매 손실이 발생할 수 있으며, 수익을 보장하지 않습니다.
- 반드시 `IS_VIRTUAL=true`(모의투자)로 먼저 충분히 검증한 뒤, 소액으로 실전 전환하세요.
- 전략/파라미터는 예시 수준입니다. 실전 투입 전 백테스트와 파라미터 튜닝을 권장합니다.
- 이 코드는 투자 자문이 아니며, 사용에 따른 모든 손익 책임은 사용자 본인에게 있습니다.

## 사전 준비

1. [한국투자증권 KIS Developers](https://apiportal.koreainvestment.com)에서 API 신청 후 `앱키(App Key)`, `앱시크릿(App Secret)` 발급
2. 실전투자 계좌 또는 모의투자 계좌의 계좌번호(8자리-2자리) 확인
3. Python 3.10+ 설치

## 설치

### 공통 (수동 설치, macOS/Linux/Windows 어디서나)

```bash
pip install -r requirements.txt
cp .env.example .env
# .env 파일을 열어 앱키/시크릿/계좌번호/전략 파라미터를 채워넣으세요
```

### Windows 바탕화면에 설치

1. 이 저장소를 다운로드하거나 클론합니다.
   ```powershell
   git clone https://github.com/ss0301kim-png/Stock.git
   cd Stock
   ```
2. PowerShell을 열고 설치 스크립트를 실행합니다.
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\windows\install.ps1
   ```
   Python 3.10+ 자동 감지, 가상환경(`.venv`) 생성, 의존성 설치, `.env` 생성, **바탕화면에 'KIS 단타봇' 바로가기**를 만들어줍니다.
3. `.env` 파일(메모장으로 열기)에 앱키/시크릿/계좌번호/관심종목을 채워넣습니다.
4. 바탕화면의 **'KIS 단타봇'** 아이콘을 더블클릭하면 콘솔 창이 열리며 실행됩니다. 끄려면 창에서 `Ctrl+C`.
5. Python이 없다는 오류가 나오면 [python.org](https://www.python.org/downloads/)에서 설치 시 "Add python.exe to PATH"를 체크한 뒤 스크립트를 다시 실행하세요.

### OCI(Oracle Cloud) 기존 Compute 인스턴스에 설치

1. SSH로 인스턴스에 접속합니다.
   ```bash
   ssh <user>@<oci-instance-public-ip>
   ```
2. 저장소를 배포 경로로 바로 클론합니다(권장).
   ```bash
   sudo git clone https://github.com/ss0301kim-png/Stock.git /opt/kis-daytrading-bot
   cd /opt/kis-daytrading-bot
   ```
3. 설치 스크립트 실행 (Oracle Linux/dnf, Ubuntu/apt 자동 감지):
   ```bash
   sudo bash scripts/oci/setup.sh
   ```
   Python/가상환경/의존성 설치, 전용 서비스 계정(`kisbot`) 생성, `.env` 생성, systemd 서비스(`kis-daytrader`) 등록까지 자동으로 처리합니다.
4. `/opt/kis-daytrading-bot/.env`를 열어 앱키/시크릿/계좌번호/관심종목을 채워넣습니다. 처음엔 `IS_VIRTUAL=true`, `DRY_RUN=true`로 검증하세요.
5. 서비스 시작 및 부팅 시 자동 시작 등록:
   ```bash
   sudo systemctl enable --now kis-daytrader
   ```
6. 상태/로그 확인:
   ```bash
   systemctl status kis-daytrader
   journalctl -u kis-daytrader -f
   ```
7. `.env`를 수정한 뒤에는 반드시 재시작해야 반영됩니다: `sudo systemctl restart kis-daytrader`
8. 봇은 KIS 서버로 나가는 요청(아웃바운드)만 하므로 OCI 보안 목록/방화벽에서 별도 인바운드 포트를 열 필요가 없습니다.
9. 실전투자(`IS_VIRTUAL=false`, `DRY_RUN=false`)로 systemd에서 무인 실행할 경우, 콘솔이 없는 서비스 환경에서는 `main.py`의 대화형 확인(`START` 입력)을 자동으로 건너뛰고 `.env`의 `CONFIRM_LIVE_TRADING=YES`만으로 확인을 대체합니다. 즉, 서버에 이 값을 켜는 순간이 실질적인 "실행 확인"이므로 신중하게 설정하세요.

## 안전장치

- `DRY_RUN=true` (기본값): 실제 주문을 넣지 않고 신호와 판단 로직만 로그로 확인
- `IS_VIRTUAL=true`: KIS 모의투자 도메인 사용 (실제 자금 영향 없음)
- `CONFIRM_LIVE_TRADING=YES`: `DRY_RUN=false` **그리고** `IS_VIRTUAL=false`(실전투자) 상태에서 실제 주문을 넣으려면 이 값도 명시적으로 `YES`로 설정해야 합니다. 이 값이 없으면 프로그램이 아예 시작되지 않습니다(`config.validate()`에서 차단).
- 위 조건을 모두 만족해도, 실행 시점에 콘솔에서 `START`를 직접 입력해야 매매 루프가 시작됩니다(`main.py`). 실수로 실계좌 매매가 시작되는 것을 막기 위한 이중 안전장치입니다.
- 손절(`STOP_LOSS_PCT`) / 익절(`TAKE_PROFIT_PCT`) / 일일 손실 한도(`DAILY_LOSS_LIMIT_PCT`) 도달 시 자동 매도 및 신규 진입 중단
- 장 마감(`FORCE_CLOSE_TIME`, 기본 15:20) 전 보유 포지션 전량 자동 청산 (오버나잇 보유 금지)

## 실행

```bash
python main.py
```

실행 시 `DRY_RUN=false`이고 `IS_VIRTUAL=false`이면 실계좌 매매임을 알리는 경고와 함께 콘솔에서 `START`를 직접 입력해야 시작됩니다.

## 테스트

네트워크·API 키 없이 전략/리스크/매매 루프 로직만 검증하는 단위 테스트가 포함되어 있습니다.

```bash
python -m unittest discover -s tests -v
```

## 동작 방식 (안정성 관련 세부사항)

- **포지션 동기화**: 실계좌 모드에서는 매 사이클마다 실제 잔고를 조회해 내부 포지션 상태를 동기화합니다. 수동 매매, 부분 체결 등으로 실제 보유 수량/평균단가가 바뀌어도 봇 상태가 어긋나지 않습니다.
- **API 오류 격리**: 한 종목 처리 중 오류가 나도 다른 종목 처리와 다음 매매 사이클에는 영향을 주지 않습니다. 사이클 전체가 실패해도 프로그램은 종료되지 않고 다음 주기에 재시도합니다.
- **요청 속도 제한 대응**: `REQUEST_INTERVAL_SEC`만큼 종목별 API 호출 사이에 대기하여 KIS의 초당 요청 제한(특히 모의투자 도메인)을 피합니다.
- **일별 손실 한도 리셋**: 봇을 여러 날 연속 실행해도 매 거래일 시작 시점의 자산을 기준으로 `DAILY_LOSS_LIMIT_PCT`를 새로 계산합니다.
- **모의매매 자금 시뮬레이션**: `DRY_RUN=true`일 때는 `DRY_RUN_STARTING_CASH`로 시작하는 가상 계좌로 매수/매도 시 현금이 실제로 증감하여, 리스크 한도(포지션 사이징 등)가 실전과 동일하게 동작하는지 확인할 수 있습니다. 시세 조회 자체는 실제 KIS 시세를 사용하므로 실시간에 가까운 모의매매가 가능합니다.

## 전략 개요

- 관심 종목(`WATCHLIST`)별로 KIS 분봉 API에서 최근 N개 종가를 조회
- 단기 이동평균(`SHORT_MA`)이 장기 이동평균(`LONG_MA`)을 상향 돌파(골든크로스) → 매수 신호
- 단기 이동평균이 장기 이동평균을 하향 돌파(데드크로스) → 매도 신호
- 보유 중에는 매 루프마다 현재가 대비 손절/익절 라인 체크
- `POLL_INTERVAL_SEC` 주기로 반복

`src/strategy.py`의 `MovingAverageCrossStrategy`를 교체하거나 확장해 원하는 전략으로 바꿀 수 있습니다.

## 리스크 관리 파라미터 (.env)

| 변수 | 설명 | 기본값 |
|---|---|---|
| `MAX_POSITION_PCT` | 종목당 최대 투입 비중 (총자산 대비 %) | 10 |
| `MAX_CONCURRENT_POSITIONS` | 동시 보유 가능 종목 수 | 3 |
| `STOP_LOSS_PCT` | 손절 기준 (매입가 대비 %) | 2 |
| `TAKE_PROFIT_PCT` | 익절 기준 (매입가 대비 %) | 3 |
| `DAILY_LOSS_LIMIT_PCT` | 일일 손실 한도 (당일 시작 자산 대비 %) 도달 시 신규 진입 중단 | 5 |

## 프로젝트 구조

```
main.py               진입점, 안전 확인 후 트레이더 실행
config.py              환경변수 로드 및 설정 객체
src/auth.py            KIS OAuth 토큰 발급/캐시, 해시키
src/kis_client.py       KIS REST API 래퍼 (시세/잔고/주문)
src/strategy.py         이동평균 크로스 전략
src/risk.py             포지션 사이징, 손절/익절, 일일 손실 한도
src/trader.py           메인 매매 루프, 장마감 강제 청산
src/logger_setup.py     로깅 설정
tests/                  단위 테스트
scripts/windows/         Windows 설치 스크립트 및 바탕화면 실행 런처
scripts/oci/             OCI Compute 인스턴스 설치 스크립트 및 systemd 서비스 템플릿
```

## 참고

- KIS Open API는 사양이 수시로 변경될 수 있습니다. 실행 전 [공식 문서](https://apiportal.koreainvestment.com)로 TR ID·엔드포인트를 확인하세요.
- 분봉/시세 조회는 API 호출 제한(초당 요청 수)이 있으니 `POLL_INTERVAL_SEC`을 너무 짧게 설정하지 마세요.

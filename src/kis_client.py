import logging
from datetime import datetime

import requests

from src.auth import KISAuth

logger = logging.getLogger("daytrader")

REAL_DOMAIN = "https://openapi.koreainvestment.com:9443"
VIRTUAL_DOMAIN = "https://openapivts.koreainvestment.com:29443"


class KISAPIError(Exception):
    pass


class KISClient:
    def __init__(self, app_key: str, app_secret: str, account_no: str, account_product_code: str, is_virtual: bool):
        self.base_url = VIRTUAL_DOMAIN if is_virtual else REAL_DOMAIN
        self.is_virtual = is_virtual
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.account_product_code = account_product_code
        self.auth = KISAuth(self.base_url, app_key, app_secret)

    def _headers(self, tr_id: str, extra: dict = None) -> dict:
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.auth.get_access_token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }
        if extra:
            headers.update(extra)
        return headers

    @staticmethod
    def _check_ok(data: dict, context: str) -> dict:
        rt_cd = data.get("rt_cd")
        if rt_cd is not None and rt_cd != "0":
            raise KISAPIError(f"{context} 실패 (rt_cd={rt_cd}): {data.get('msg1')}")
        return data

    def get_current_price(self, stock_code: str) -> float:
        resp = requests.get(
            f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price",
            headers=self._headers("FHKST01010100"),
            params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code},
            timeout=10,
        )
        resp.raise_for_status()
        data = self._check_ok(resp.json(), f"{stock_code} 현재가 조회")
        return float(data["output"]["stck_prpr"])

    def get_minute_closes(self, stock_code: str, count: int = 30) -> list:
        resp = requests.get(
            f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
            headers=self._headers("FHKST03010200"),
            params={
                "FID_ETC_CLS_CODE": "",
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": stock_code,
                "FID_INPUT_HOUR_1": datetime.now().strftime("%H%M%S"),
                "FID_PW_DATA_INCU_YN": "N",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = self._check_ok(resp.json(), f"{stock_code} 분봉 조회")
        rows = [r for r in data.get("output2", []) if r.get("stck_prpr") and r.get("stck_cntg_hour")]
        rows.sort(key=lambda r: r["stck_cntg_hour"])
        closes = [float(r["stck_prpr"]) for r in rows]
        return closes[-count:]

    def get_balance(self) -> dict:
        tr_id = "VTTC8434R" if self.is_virtual else "TTTC8434R"
        resp = requests.get(
            f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance",
            headers=self._headers(tr_id),
            params={
                "CANO": self.account_no,
                "ACNT_PRDT_CD": self.account_product_code,
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "",
                "INQR_DVSN": "02",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "01",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": "",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = self._check_ok(resp.json(), "잔고 조회")

        summary_rows = data.get("output2") or []
        summary = summary_rows[0] if summary_rows else {}

        holdings = [
            {
                "code": h["pdno"],
                "name": h.get("prdt_name", ""),
                "qty": int(h["hldg_qty"]),
                "avg_price": float(h["pchs_avg_pric"]),
                "current_price": float(h["prpr"]),
            }
            for h in data.get("output1") or []
            if int(h.get("hldg_qty", 0)) > 0
        ]
        return {
            "cash": float(summary.get("dnca_tot_amt", 0)),
            "total_equity": float(summary.get("tot_evlu_amt", 0)),
            "holdings": holdings,
        }

    def place_order(self, stock_code: str, side: str, qty: int, price: int = 0, order_type: str = "market") -> dict:
        if side not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        if qty <= 0:
            raise ValueError("qty must be positive")

        if side == "buy":
            tr_id = "VTTC0802U" if self.is_virtual else "TTTC0802U"
        else:
            tr_id = "VTTC0801U" if self.is_virtual else "TTTC0801U"

        ord_dvsn = "01" if order_type == "market" else "00"
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_product_code,
            "PDNO": stock_code,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price if order_type == "limit" else 0),
        }
        hashkey = self.auth.get_hashkey(body)
        resp = requests.post(
            f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash",
            headers=self._headers(tr_id, {"hashkey": hashkey}),
            json=body,
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("rt_cd") != "0":
            logger.error("주문 실패 [%s %s %s주]: %s", side, stock_code, qty, result.get("msg1"))
        else:
            logger.info("주문 성공 [%s %s %s주]: %s", side, stock_code, qty, result.get("msg1"))
        return result

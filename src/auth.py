import json
import os
import time as time_module
from datetime import datetime, timedelta

import requests

TOKEN_CACHE_PATH = ".token_cache.json"


class KISAuth:
    def __init__(self, base_url: str, app_key: str, app_secret: str):
        self.base_url = base_url
        self.app_key = app_key
        self.app_secret = app_secret
        self._access_token = None
        self._expires_at = None
        self._load_cached_token()

    def _load_cached_token(self):
        if not os.path.exists(TOKEN_CACHE_PATH):
            return
        try:
            with open(TOKEN_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("app_key") != self.app_key or data.get("base_url") != self.base_url:
                return
            expires_at = datetime.fromisoformat(data["expires_at"])
            if expires_at > datetime.now() + timedelta(minutes=5):
                self._access_token = data["access_token"]
                self._expires_at = expires_at
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    def _save_cached_token(self):
        with open(TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "app_key": self.app_key,
                    "base_url": self.base_url,
                    "access_token": self._access_token,
                    "expires_at": self._expires_at.isoformat(),
                },
                f,
            )

    def get_access_token(self, retries: int = 3) -> str:
        if self._access_token and self._expires_at and self._expires_at > datetime.now() + timedelta(minutes=5):
            return self._access_token

        last_error = None
        for attempt in range(retries):
            try:
                resp = requests.post(
                    f"{self.base_url}/oauth2/tokenP",
                    headers={"content-type": "application/json"},
                    json={
                        "grant_type": "client_credentials",
                        "appkey": self.app_key,
                        "appsecret": self.app_secret,
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                self._access_token = data["access_token"]
                self._expires_at = datetime.now() + timedelta(seconds=int(data.get("expires_in", 86400)))
                self._save_cached_token()
                return self._access_token
            except (requests.RequestException, KeyError, ValueError) as exc:
                last_error = exc
                time_module.sleep(2**attempt)

        raise RuntimeError(f"KIS access token 발급 실패: {last_error}")

    def get_hashkey(self, body: dict) -> str:
        resp = requests.post(
            f"{self.base_url}/uapi/hashkey",
            headers={
                "content-type": "application/json",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
            },
            json=body,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["HASH"]

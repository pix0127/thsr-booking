"""
TDX API Client for THSR Timetable
台灣高鐵時刻表 TDX API 客戶端
"""
import time
import os
from typing import Optional, Dict, List, Any, Union

import requests


class TDXClient:
    """TDX API 客戶端，處理 OAuth 認證與 API 呼叫"""

    # TDX API endpoints
    TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    BASE_URL = "https://tdx.transportdata.tw/api/basic/v2"

    # TDX station codes for THSR
    STATION_IDS = {
        1: "0990", 2: "1000", 3: "1010", 4: "1020",
        5: "1030", 6: "1035", 7: "1040", 8: "1043",
        9: "1047", 10: "1050", 11: "1060", 12: "1070",
    }

    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or os.environ.get("TDX_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("TDX_CLIENT_SECRET")
        self._token: Optional[str] = None
        self._token_expires: float = 0

        if not self.client_id or not self.client_secret:
            print("[TDX] 警告: 未設定 TDX_CLIENT_ID / TDX_CLIENT_SECRET 環境變數")
            print("[TDX] 請至 https://tdx.transportdata.tw 申請，並設定環境變數")
            print("[TDX] 時刻表資料將無法取得，請確認 TDX_CLIENT_ID 和 TDX_CLIENT_SECRET 已設定")

    def _get_token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "TDX Client ID 和 Client Secret 未設定。"
                "請至 https://tdx.transportdata.tw 申請，或設定環境變數 TDX_CLIENT_ID 和 TDX_CLIENT_SECRET"
            )
        if self._token and time.time() < self._token_expires - 60:
            return self._token

        resp = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        self._token = data["access_token"]
        self._token_expires = time.time() + data["expires_in"]
        return self._token

    def _request(self, endpoint: str, params: Dict = None) -> Any:
        """發送 API 請求"""
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Accept-Encoding": "gzip",
        }

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_daily_timetable(self, date: str) -> List[Dict]:
        """取得指定日期的所有高鐵班次

        Args:
            date: 日期 (yyyy-MM-dd 格式，例如 "2026-04-10")

        Returns:
            班次列表
        """
        endpoint = f"/Rail/THSR/DailyTimetable/TrainDate/{date}"
        return self._request(endpoint, {"$format": "JSON"})

    def get_od_timetable(
        self,
        origin_station_id: int,
        dest_station_id: int,
        date: str,
    ) -> List[Dict]:
        """取得特定起訖站與日期的高鐵班次

        Args:
            origin_station_id: 起站 ID (1-12)
            dest_station_id: 迄站 ID (1-12)
            date: 日期 (yyyy-MM-dd 格式)

        Returns:
            班次列表
        """
        origin_code = self.STATION_IDS.get(origin_station_id)
        dest_code = self.STATION_IDS.get(dest_station_id)

        if not origin_code or not dest_code:
            raise ValueError(
                f"無效的車站 ID: origin={origin_station_id}, dest={dest_station_id}"
            )

        endpoint = f"/Rail/THSR/DailyTimetable/OD/{origin_code}/to/{dest_code}/{date}"
        return self._request(endpoint, {"$format": "JSON"})

    def get_stations(self) -> List[Dict]:
        """取得高鐵車站列表"""
        endpoint = "/Rail/THSR/Station"
        return self._request(endpoint, {"$format": "JSON"})


def get_tdx_client() -> TDXClient:
    """取得 TDXClient 實例（工廠函式）"""
    return TDXClient()

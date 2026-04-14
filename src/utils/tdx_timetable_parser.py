"""
TDX Timetable Parser for THSR
從 TDX API 取得高鐵時刻表數據
"""
import os
from datetime import datetime
from typing import List, Dict, Optional

from controller.models import TrainCache
from remote.tdx_client import TDXClient


class TDXTimetableParser:

    STATION_NAME_TO_ID = {
        "南港": 1, "Nangang": 1,
        "台北": 2, "Taipei": 2,
        "板橋": 3, "Banqiao": 3,
        "桃園": 4, "Taoyuan": 4,
        "新竹": 5, "Hsinchu": 5,
        "苗栗": 6, "Miaoli": 6,
        "台中": 7, "Taichung": 7,
        "彰化": 8, "Changhua": 8,
        "雲林": 9, "Yunlin": 9,
        "嘉義": 10, "Chiayi": 10,
        "台南": 11, "Tainan": 11,
        "左營": 12, "Zuoying": 12,
    }

    def __init__(self):
        self.cache = TrainCache()
        self.tdx_client = TDXClient()

    def _transform_od_response(self, origin_station: str, dest_station: str, weekday: str) -> List[Dict]:
        date = self._weekday_to_date(weekday) if weekday else datetime.now().strftime("%Y-%m-%d")

        cache_key = f"tdx:od:{origin_station}:{dest_station}:{date}"
        cached = self.cache.get_cached_trains(cache_key)
        if cached:
            print(f"[TDX] 使用快取 ({origin_station}->{dest_station}, {date}), {len(cached)} 班次")
            return cached

        print(f"[TDX] 向 TDX API 請求 {origin_station}->{dest_station} ({date})...")
        origin_id = self.STATION_NAME_TO_ID.get(origin_station)
        dest_id = self.STATION_NAME_TO_ID.get(dest_station)

        raw_trains = self.tdx_client.get_od_timetable(origin_id, dest_id, date)
        print(f"[TDX] 收到 {len(raw_trains)} 班次")

        trains = []
        for raw in raw_trains:
            parsed = self._parse_od_train(raw, origin_station, dest_station)
            if parsed:
                trains.append(parsed)

        trains.sort(key=lambda x: x["departure_time"])

        if trains:
            self.cache.cache_trains(cache_key, trains, tdx_date=date)

        return trains

    def _parse_od_train(self, raw: Dict, origin_station: str, dest_station: str) -> Optional[Dict]:
        try:
            info = raw.get("DailyTrainInfo", {})
            train_no = str(info.get("TrainNo", "")).strip()
            if not train_no:
                return None

            direction = info.get("Direction", 0)
            direction_str = "southbound" if direction == 0 else "northbound"

            origin_stop = raw.get("OriginStopTime", {})
            dest_stop = raw.get("DestinationStopTime", {})

            departure_time = origin_stop.get("DepartureTime", "")
            arrival_time = dest_stop.get("ArrivalTime", "")

            if not departure_time or not arrival_time:
                return None

            return {
                "train_no": train_no,
                "departure_time": departure_time,
                "arrival_time": arrival_time,
                "origin_station": origin_station,
                "destination_station": dest_station,
                "direction": direction_str,
                "operating_days": {"daily": True},
                "operating_info": "每日",
            }
        except Exception as e:
            print(f"[TDX] 解析班次失敗: {e}")
            return None

    def get_route_timetable(
        self,
        origin_station: str,
        dest_station: str,
        weekday: str = None,
    ) -> List[Dict]:
        origin_id = self.STATION_NAME_TO_ID.get(origin_station)
        dest_id = self.STATION_NAME_TO_ID.get(dest_station)

        if not origin_id or not dest_id:
            print(f"[TDX] 無效的站名: origin={origin_station}, dest={dest_station}")
            return []

        trains = self._transform_od_response(origin_station, dest_station, weekday or "")
        print(f"[TDX] {origin_station} -> {dest_station} ({weekday or 'today'}): {len(trains)} 班次")
        return trains

    def _weekday_to_date(self, weekday: str) -> str:
        weekday_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
        target_weekday = weekday_map.get(weekday)
        if target_weekday is None:
            return datetime.now().strftime("%Y-%m-%d")

        today = datetime.now()
        days_ahead = target_weekday - today.weekday()
        if days_ahead < 0:
            days_ahead += 7
        target = today.replace(hour=0, minute=0, second=0, microsecond=0)
        target = target.replace(day=today.day + days_ahead)
        return target.strftime("%Y-%m-%d")

    def _calculate_duration(self, start_time: str, end_time: str) -> str:
        try:
            start_dt = datetime.strptime(start_time, "%H:%M")
            end_dt = datetime.strptime(end_time, "%H:%M")
            if end_dt < start_dt:
                end_dt = end_dt.replace(day=end_dt.day + 1)
            duration = end_dt - start_dt
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            if hours > 0:
                return f"{hours}h{minutes:02d}m"
            return f"{minutes}m"
        except Exception:
            return "N/A"

    def show_popular_routes(self, weekday: str = None):
        popular_routes = [
            ("台北", "左營"),
            ("台北", "台中"),
            ("台中", "左營"),
            ("台北", "台南"),
        ]
        print("=== 高鐵熱門路線時刻表 (TDX API 數據) ===")
        print()
        for origin, dest in popular_routes:
            formatted = self.format_route_timetable(origin, dest, weekday)
            print(formatted)
            print()

    def format_route_timetable(self, origin_station: str, dest_station: str, weekday: str = None) -> str:
        trains = self.get_route_timetable(origin_station, dest_station, weekday)
        if not trains:
            weekday_info = f" ({weekday})" if weekday else ""
            return f"沒有找到 {origin_station} -> {dest_station}{weekday_info} 的班次"

        result = []
        weekday_info = f" ({weekday})" if weekday else ""
        result.append(f"\n{origin_station} -> {dest_station}{weekday_info} 時刻表 (來源: TDX API)")
        result.append("=" * 80)
        result.append(f"{'班次':>6} {'發車時間':>10} {'到達時間':>10} {'行駛時間':>10} {'運行日':>12}")
        result.append("-" * 80)

        for train in trains:
            duration = self._calculate_duration(train["departure_time"], train["arrival_time"])
            result.append(
                f"{train['train_no']:>6} {train['departure_time']:>10} "
                f"{train['arrival_time']:>10} {duration:>10} {train['operating_info']:>12}"
            )
        return "\n".join(result)


def main():
    parser = TDXTimetableParser()
    parser.show_popular_routes()


if __name__ == "__main__":
    main()

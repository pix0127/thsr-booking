"""
Booking Date Validator with Timetable Integration
訂票日期驗證器，整合時刻表顯示功能
"""
from datetime import datetime, date, timedelta
from typing import Optional, Tuple, List
from controller.schemas import DAYS_BEFORE_BOOKING_AVAILABLE
from utils.tdx_timetable_parser import TDXTimetableParser


class BookingDateValidator:
    """訂票日期驗證器，包含時刻表查詢功能"""

    def __init__(self):
        self.max_advance_days = DAYS_BEFORE_BOOKING_AVAILABLE
        self.timetable_parser = TDXTimetableParser()  # TDX 時刻表解析器

        # 車站名稱映射 (ID -> 中文名稱) - 仍被 booking_controller 使用
        self.station_id_to_name = {
            1: "南港", 2: "台北", 3: "板橋", 4: "桃園",
            5: "新竹", 6: "苗栗", 7: "台中", 8: "彰化",
            9: "雲林", 10: "嘉義", 11: "台南", 12: "左營"
        }

    def validate_booking_date(self, target_date_str: str,
                              start_station_id: int = None,
                              dest_station_id: int = None) -> Tuple[bool, str]:
        """
        驗證訂票日期

        Args:
            target_date_str: 目標日期字串 (YYYY/MM/DD 或 YYYY-MM-DD)
            start_station_id: 起站ID (保留參數以維持向後兼容)
            dest_station_id: 迄站ID (保留參數以維持向後兼容)

        Returns:
            Tuple[bool, str]: (是否有效, 訊息)
        """
        try:
            # 解析日期
            target_date = self._parse_date(target_date_str)
            if not target_date:
                return False, "日期格式錯誤，請使用 YYYY/MM/DD 或 YYYY-MM-DD 格式"

            today = date.today()

            # 檢查是否為過去日期
            if target_date < today:
                return False, f"不能選擇過去的日期：{target_date}"

            # 計算可預訂的最晚日期

            return True, f"日期有效，{target_date} 可預訂"

        except Exception as e:
            return False, f"日期驗證時發生錯誤：{e}"

    def _parse_date(self, date_str: str) -> Optional[date]:
        """解析日期字串"""
        date_str = date_str.strip()

        # 嘗試不同的日期格式
        formats = [
            "%Y/%m/%d",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y.%m.%d"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def get_available_booking_range(self) -> Tuple[date, date]:
        """獲取可預訂的日期範圍"""
        today = date.today()
        max_date = today + timedelta(days=self.max_advance_days)
        return today, max_date

    def suggest_alternative_dates(self, target_date: date) -> List[str]:
        """建議替代日期"""
        today = date.today()
        max_booking_date = today + timedelta(days=self.max_advance_days)

        suggestions = []

        # 建議1：最接近的可預訂日期
        if target_date > max_booking_date:
            suggestions.append(f"最晚可預訂：{max_booking_date}")

        # 建議2：同一星期幾的最近日期
        target_weekday = target_date.weekday()
        current_date = today

        while current_date <= max_booking_date:
            if current_date.weekday() == target_weekday and current_date != today:
                weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
                suggestions.append(f"同星期{weekday_names[target_weekday]}：{current_date}")
                break
            current_date += timedelta(days=1)

        # 建議3：下週同一天
        next_week_date = target_date - timedelta(days=7)
        if next_week_date >= today and next_week_date <= max_booking_date:
            suggestions.append(f"提前一週：{next_week_date}")

        return suggestions

    def _calculate_duration(self, start_time: str, end_time: str) -> str:
        """計算行程時間 - 仍被 booking_controller 使用"""
        try:
            start_dt = datetime.strptime(start_time, '%H:%M')
            end_dt = datetime.strptime(end_time, '%H:%M')

            # 處理跨日情況
            if end_dt < start_dt:
                end_dt = end_dt.replace(day=end_dt.day + 1)

            duration = end_dt - start_dt
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)

            if hours > 0:
                return f"{hours}h{minutes:02d}m"
            else:
                return f"{minutes}m"
        except Exception:
            return "N/A"


def main():
    """測試函數"""
    validator = BookingDateValidator()

    # 測試案例
    test_cases = [
        ("2024/12/25", 2, 12),  # 台北 -> 左營
        ("2025/01/15", 2, 7),   # 台北 -> 台中
        ("2024/11/30", 7, 12),  # 台中 -> 左營
    ]

    for date_str, start_id, dest_id in test_cases:
        print(f"\n測試日期：{date_str}")
        is_valid, message = validator.validate_booking_date(
            date_str, start_id, dest_id
        )

        print(f"結果：{'✅ 有效' if is_valid else '❌ 無效'}")
        print(f"訊息：{message}")


if __name__ == "__main__":
    main()

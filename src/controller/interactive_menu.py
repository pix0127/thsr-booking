# -*- coding: utf-8 -*-
"""
Interactive CLI Controller
互動式命令列控制器 - 統一的 CLI 介面
"""
import sys
from typing import Any, Dict, List
from controller.reservation_manager import ReservationManager


class InteractiveCLIController:
    """互動式命令列控制器 - 統一 CLI 和互動選單功能"""

    def __init__(self):
        self.reservation_manager = ReservationManager()

    def execute(self, command_data: Dict = None) -> Any:
        """執行 CLI 控制器 - 支援命令模式和互動模式"""
        if command_data:
            # 命令列模式
            return self._execute_command_mode(command_data)
        else:
            # 互動模式
            return self._execute_interactive_mode()

    def parse_args(self, args: List[str]) -> Dict:
        """解析命令列參數"""
        if not args:
            return {}

        command_map = {
            "create": {
                "command": "create_reservation"
            },
            "execute": {
                "command": "execute_reservations"
            },
            "list": {
                "command": "list_reservations"
            },
            "delete": {
                "command": "delete_reservation"
            },
            "help": {
                "command": "help"
            }
        }

        command = args[0] if args else "interactive"
        return command_map.get(command, {"command": "interactive"})

    def show_output(self, data: Any):
        """顯示輸出結果"""
        if isinstance(data, dict):
            if "error" in data:
                print(f"❌ 錯誤: {data['error']}")
            elif "success" in data:
                print(f"✅ 成功: {data['success']}")
            elif "message" in data:
                print(f"💡 {data['message']}")
        else:
            print(data)

    def _execute_command_mode(self, command_data: Dict) -> Dict:
        """執行命令列模式"""
        command = command_data.get("command", "")

        try:
            if command == "create_reservation":
                reservation_id = self.reservation_manager.create_new_reservation()
                return {"success": f"預約 {reservation_id} 建立成功"}

            elif command == "execute_reservations":
                results = self.reservation_manager.execute_all_reservations()
                return {"success": f"執行完成，共處理 {len(results)} 個預約"}

            elif command == "list_reservations":
                self.reservation_manager.list_all_reservations()
                return {"message": "預約列表已顯示"}

            elif command == "delete_reservation":
                # 需要額外的 ID 參數
                return {"error": "需要指定預約 ID"}

            elif command == "help":
                self._show_help()
                return {"message": "說明已顯示"}

            else:
                return {"error": f"未知命令: {command}"}

        except Exception as e:
            return {"error": str(e)}

    def _execute_interactive_mode(self):
        """執行互動模式"""
        print("=== 台灣高鐵訂票系統 ===")
        print("Taiwan High Speed Railway Booking System")

        while True:
            self._show_main_menu()
            choice = input("請選擇功能 (輸入數字): ").strip()

            if choice == "1":
                self._handle_booking()
            elif choice == "2":
                self._handle_execute_reservations()
            elif choice == "3":
                self._handle_reservation_management()
            elif choice == "4":
                self._show_help()
            elif choice == "5":
                print("感謝使用！")
                sys.exit(0)
            else:
                print("無效的選擇，請重新輸入\n")

    def _show_main_menu(self):
        """顯示主選單"""
        print("\n" + "=" * 50)
        print("主選單:")
        print("1. 建立新預約")
        print("2. 執行所有預約")
        print("3. 預約管理")
        print("4. 說明")
        print("5. 離開")
        print("=" * 50)

    def _handle_booking(self):
        """處理建立新預約功能 - 使用 ReservationManager"""
        print("\n" + "=" * 60)
        print("🚄 建立新預約 - 完整互動式流程")
        print("=" * 60)

        try:
            # 直接使用 ReservationManager 的功能
            print("🔄 啟動預約建立流程...")
            reservation_id = self.reservation_manager.create_new_reservation()
            print(f"✅ 預約 {reservation_id} 建立成功！")

        except KeyboardInterrupt:
            print("\n⛔ 用戶取消操作")
        except Exception as e:
            print(f"❌ 預約建立過程發生錯誤: {str(e)}")
            print("💡 請檢查網路連線或稍後重試")

    def _handle_execute_reservations(self):
        """處理執行預約功能"""
        print("\n🚀 === 執行預約 ===")

        try:
            print("選擇執行模式:")
            print("1. 執行所有預約")
            print("2. 執行特定預約")
            print("3. 返回主選單")

            choice = input("選擇操作 (1-3): ").strip()

            if choice == "1":
                print("🔄 執行所有預約...")
                results = self.reservation_manager.execute_all_reservations()
                print(f"執行完成，共處理 {len(results)} 個預約")

            elif choice == "2":
                reservation_id = input("輸入要執行的預約 ID: ").strip()
                if reservation_id:
                    try:
                        reservation_id = int(reservation_id)
                        print(f"🔄 執行預約 {reservation_id}...")
                        success = self.reservation_manager.execute_specific_reservation(
                            reservation_id)
                        if success:
                            print("✅ 預約執行成功")
                        else:
                            print("❌ 預約執行失敗")
                    except ValueError:
                        print("❌ 請輸入有效的數字 ID")

            elif choice == "3":
                return
            else:
                print("❌ 無效選擇")

        except KeyboardInterrupt:
            print("\n⛔ 操作已取消")
        except Exception as e:
            print(f"❌ 執行失敗: {str(e)}")

    def _handle_train_query(self):
        """處理車次查詢 - 使用 ReservationManager"""
        print("\n🔍 === 查詢車次 ===")

        try:
            # 使用 ReservationManager 的查詢功能
            print("🔄 啟動車次查詢...")
            print("💡 此功能需要先建立預約配置")
            print("請先使用 '1. 預訂車票' 建立預約，然後查看可用車次")

        except KeyboardInterrupt:
            print("\n⛔ 查詢已取消")
        except Exception as e:
            print(f"❌ 查詢失敗: {str(e)}")
            print("💡 請檢查網路連線或稍後重試")

    def _handle_reservation_management(self):
        """處理預約管理"""
        print("\n� === 預約管理 ===")

        while True:
            print("\n管理選項:")
            print("1. 查看預約歷史")
            print("2. 取消預約")
            print("3. 查看用戶資料")
            print("4. 返回主選單")

            choice = input("選擇操作 (1-4): ").strip()

            if choice == "1":
                self.reservation_manager.list_all_reservations()

            elif choice == "2":
                reservation_id = input("輸入要取消的預約 ID: ").strip()
                if reservation_id:
                    self.reservation_manager.delete_reservation(reservation_id)

            elif choice == "3":
                print("� 載入用戶資料...")
                # ReservationManager 應該有處理用戶資料的功能
                print("👤 用戶資料管理功能")
                print("� 提示: 此功能由 ReservationManager 內建的 ProfileManager 處理")

            elif choice == "4":
                break
            else:
                print("❌ 無效選擇")

    def _show_help(self):
        """顯示說明"""
        help_text = """
📖 === 使用說明 ===

🚄 1. 建立新預約：
   • 互動式收集預訂資訊 (車站、日期、時間、票數)
   • 自動處理驗證碼和車次選擇
   • 收集乘客個人資訊 (身分證、電話、信箱)
   • 將預約儲存到資料庫

� 2. 執行預約：
   • 執行所有已建立的預約
   • 執行特定預約 ID
   • 自動完成完整訂票流程
   • 成功後自動清理預約

📋 3. 預約管理：
   • 查看所有預約歷史
   • 刪除特定預約
   • 管理用戶資料

⚠️  注意事項：
   • 建立預約時請確保資訊正確
   • 執行預約需要網路連線
   • 請在非尖峰時間執行以獲得更好成功率

🚉 常見車站：
   台北(2)、板橋(3)、桃園(4)、新竹(5)、苗栗(6)
   台中(7)、彰化(8)、雲林(9)、嘉義(10)、台南(11)、左營(12)

💡 使用流程：
   1️⃣ 先建立新預約 (輸入所有訂票資訊)
   2️⃣ 再執行預約 (實際進行訂票)
   3️⃣ 查看結果或管理預約
        """
        print(help_text)


if __name__ == "__main__":
    controller = InteractiveCLIController()
    controller.execute()  # 不傳參數即為互動模式

import argparse
from controller.interactive_menu import InteractiveCLIController
from controller.reservation_manager import ReservationManager


def handle_args():
    parser = argparse.ArgumentParser(
        description="Taiwan High Speed Railway Booking System - Simplified Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  %(prog)s -n              # Create new reservation
  %(prog)s -r              # Execute all reservations
  %(prog)s -i              # Start interactive management (Recommended)
  %(prog)s --list          # List all reservations
  %(prog)s --execute ID    # Execute specific reservation
  %(prog)s --delete ID     # Delete specific reservation
        """)

    parser.add_argument("-n", "--new", help="Create new reservation", action="store_true")
    parser.add_argument("-r", "--run", help="Execute all reservations", action="store_true")
    parser.add_argument("-i",
                        "--interactive",
                        help="Start interactive management",
                        action="store_true")
    parser.add_argument("--list", help="List all reservations", action="store_true")
    parser.add_argument("--execute",
                        type=int,
                        metavar="ID",
                        help="Execute specific reservation by ID")
    parser.add_argument("--delete",
                        type=int,
                        metavar="ID",
                        help="Delete specific reservation by ID")

    return parser.parse_args()


def main():
    args = handle_args()

    # 如果沒有指定參數，啟動互動式介面
    if not any([args.new, args.run, args.interactive, args.list, args.execute, args.delete]):
        print("Welcome to Taiwan High Speed Railway Booking System!")
        print("Tip: Use -h to see all available options")
        print("Starting interactive management interface...")
        menu = InteractiveCLIController()
        menu.execute()
        return

    # 處理不同的命令
    try:
        if args.interactive:
            # 啟動互動式選單
            menu = InteractiveCLIController()
            menu.execute()
        elif args.new:
            # 創建新預約 - 使用 CLI 控制器
            cli_controller = InteractiveCLIController()
            print("Creating new reservation...")
            print("Please provide the following information:")

            # 收集使用者輸入
            from_station = input("From station: ")
            to_station = input("To station: ")
            date = input("Travel date (YYYY-MM-DD): ")
            time = input("Travel time (HH:MM): ")
            adult_num = int(input("Number of adult tickets: ") or "1")

            command_data = {
                "command": "book",
                "from": from_station,
                "to": to_station,
                "date": date,
                "time": time,
                "adult_num": adult_num
            }

            result = cli_controller.execute(command_data)
            if "error" in result:
                print(f"Reservation failed: {result['error']}")
            else:
                print("Reservation created successfully!")

        elif args.run:
            # 執行所有預約
            reservation_manager = ReservationManager()
            print("Executing all reservations...")
            # 這裡可以實現批量執行邏輯
            reservation_manager = ReservationManager()
            print(reservation_manager.execute_all_reservations())

        elif args.list:
            # 列出所有預約
            reservation_manager = ReservationManager()
            history = reservation_manager.get_all_reservations()
            if history:
                print("Reservation History:")
                for i, reservation in enumerate(history, 1):
                    print(f"{i}. {reservation}")
            else:
                print("No reservations found")

        elif args.execute:
            # 執行特定預約
            print(f"Executing reservation {args.execute}...")

        elif args.delete:
            # 刪除特定預約
            reservation_manager = ReservationManager()
            result = reservation_manager.delete_reservation(args.delete)
            if result:
                print(f"Reservation {args.delete} deleted successfully")
            else:
                print(f"Failed to delete reservation {args.delete}")

    except Exception as e:
        print(f"Operation failed: {e}")
    except KeyboardInterrupt:
        print("\nUser cancelled operation")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nUser cancelled operation, exiting program")
    except Exception as e:
        print(f"Program execution error: {e}")
        print("For help, use -h parameter to see usage instructions")

# -*- coding: utf-8 -*-
from datetime import date, datetime
from controller.models import RecordFirstPage, RecordTrainPage, RecordTicketPage, ReservationDB, UserProfileManager, UserProfile
from controller.schemas import AVAILABLE_TIME_TABLE, MAX_TICKET_NUM, StationMapping, TicketType
from controller.parsers import TrainListParser, BookingResultParser, PrintBookingResult, print_reservations
from controller.booking_service import BookingService
from utils.booking_date_validator import BookingDateValidator


MAX_RETRIES = 5


class ReservationManager:
    def __init__(self):
        self.db = ReservationDB()
        self.profile_mgr = UserProfileManager()
        self.date_validator = BookingDateValidator()

    def create_new_reservation(self):
        """Create new reservation via interactive CLI"""
        print("=== Creating New Reservation ===")
        first_data = self._collect_basic_info()
        train_data = self._collect_train_info(first_data)
        ticket_data = self._collect_passenger_info(first_data)
        self.db.save(first_data, ticket_data, train_data)
        print("SUCCESS: Reservation created!")
        return max(r[0] for r in self.db.get_history()) if self.db.get_history() else 1

    def list_all_reservations(self):
        for res_id, record in self.db.get_history():
            print(f"ID: {res_id} | {StationMapping(record.start_station).name} -> {StationMapping(record.dest_station).name} | {record.outbound_date} {record.outbound_time}")

    def delete_reservation(self, reservation_id):
        self.db.remove(reservation_id)
        print(f"Reservation {reservation_id} deleted")

    def execute_all_reservations(self):
        """Execute all reservations"""
        reservations = self.db.get_history()
        if not reservations:
            print("No reservations found")
            return []

        results = []
        for reservation_id, record in reservations:
            if self._is_expired(record):
                print(f"EXPIRED: Reservation {reservation_id} ({record.outbound_date})")
                self.delete_reservation(reservation_id)
                results.append((reservation_id, False))
                continue

            success = self._execute_single_booking(record, reservation_id)
            results.append((reservation_id, success))
            if success:
                self.delete_reservation(reservation_id)

        self._show_summary(results)
        return results

    def execute_specific_reservation(self, reservation_id):
        """Execute specific reservation"""
        record = None
        for res_id, rec in self.db.get_history():
            if res_id == reservation_id:
                record = rec
                break
        if not record:
            print(f"Reservation {reservation_id} not found")
            return False

        if self._is_expired(record):
            print(f"EXPIRED: Reservation {reservation_id}")
            self.delete_reservation(reservation_id)
            return False

        success = self._execute_single_booking(record, reservation_id)
        if success:
            self.delete_reservation(reservation_id)
        return success

    # =========================================================================
    # Private collection methods
    # =========================================================================

    def _collect_basic_info(self):
        """Collect basic booking info"""
        data = RecordFirstPage()
        print("\n=== Station Selection ===")
        for s in StationMapping:
            print(f"{s.value}. {s.name}")
        data.start_station = int(input("\nDeparture (default: 2): ") or "2")
        data.dest_station = int(input("Destination (default: 12): ") or "12")

        print(f"\n=== Date Selection ===")
        today = date.today()
        while True:
            date_input = input(f"Travel date (YYYY/MM/DD, default: {today}): ").strip() or str(today)
            is_valid, _ = self.date_validator.validate_booking_date(date_input, data.start_station, data.dest_station)
            if is_valid:
                data.outbound_date = date_input
                break
            print("Invalid date, try again")

        print("\n=== Time Selection ===")
        for idx, time_str in enumerate(AVAILABLE_TIME_TABLE, 1):
            readable = self._format_time(time_str)
            print(f"{idx:2d}. {readable} ({time_str})")
        time_choice = int(input("\nTime choice (default: 10): ") or "10") - 1
        data.outbound_time = AVAILABLE_TIME_TABLE[time_choice]

        print("\n=== Ticket Selection ===")
        mode = input("1. Quick (total passengers)  2. Detailed  3. Common combos (default: 1): ").strip() or "1"

        if mode == "2":
            counts = {t: int(input(f"{t.name} tickets (default: {'1' if t == TicketType.ADULT else '0'}): ") or ("1" if t == TicketType.ADULT else "0")) for t in TicketType}
        elif mode == "3":
            combo_map = {"1": (1,0,0,0,0,0), "2": (2,0,0,0,0,0), "3": (1,1,0,0,0,0), "4": (2,1,0,0,0,0), "5": (2,2,0,0,0,0), "6": (1,0,0,1,0,0)}
            combo = combo_map.get(input("Combo (1-6): ").strip(), (1,0,0,0,0,0))
            counts = dict(zip(TicketType, combo))
        else:
            total = int(input("Total passengers (default: 1): ") or "1")
            counts = {TicketType.ADULT: total}
            for t in TicketType:
                if t != TicketType.ADULT:
                    counts[t] = 0

        data.adult_num = counts[TicketType.ADULT]
        data.child_num = counts[TicketType.CHILD]
        data.disabled_num = counts[TicketType.DISABELD]
        data.elder_num = counts[TicketType.ELDER]
        data.college_num = counts[TicketType.COLLEGE]
        return data

    def _collect_train_info(self, first_data):
        """Collect train selection from timetable"""
        data = RecordTrainPage()
        try:
            start_name = self.date_validator.station_id_to_name.get(first_data.start_station)
            dest_name = self.date_validator.station_id_to_name.get(first_data.dest_station)
            target_date = self.date_validator._parse_date(first_data.outbound_date)
            weekday = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][target_date.weekday()] if target_date else None

            trains = self.date_validator.timetable_parser.get_route_timetable(start_name, dest_name, weekday)
            if not trains:
                print("No trains found")
                return data

            filtered = self._filter_trains(trains, first_data.outbound_time)
            print(f"\n=== Found {len(filtered)} trains ===")
            for idx, t in enumerate(filtered[:20], 1):
                dur = self.date_validator._calculate_duration(t["departure_time"], t["arrival_time"])
                print(f"{idx:2d}. Train {t['train_no']:>4} | {t['departure_time']} -> {t['arrival_time']} | {dur}")

            selection = input("\nSelect trains (e.g., 1,3,5) or Enter to skip: ").strip()
            if selection:
                data.selection_time = [filtered[int(s.strip())-1]["departure_time"] for s in selection.split(",") if s.strip().isdigit()]
        except Exception as e:
            print(f"Error: {e}")
        return data

    def _collect_passenger_info(self, first_data):
        """Collect passenger info with profile support"""
        data = RecordTicketPage()
        expected = sum(getattr(first_data, f"{t.name.lower()}_num", 0) or 0 for t in TicketType) or 1

        profiles = self.profile_mgr.list_profiles()
        if profiles:
            print("\n=== Saved Profiles ===")
            for idx, name in enumerate(profiles, 1):
                p = self.profile_mgr.get_profile(name)
                print(f"{idx}. {name} ({', '.join(p.personal_ids[:2])})")
            choice = input("Select profile or 0 for manual: ").strip()
            if choice and int(choice) > 0:
                profile = self.profile_mgr.get_profile(profiles[int(choice)-1])
                data.personal_id = profile.personal_ids[:expected]
                data.phone = profile.phone
                data.email = profile.email
                self.profile_mgr.update_last_used(profile.profile_name)
                return data

        while True:
            ids = input(f"ID numbers ({expected}, comma separated): ").strip().upper()
            if ids:
                data.personal_id = [i.strip() for i in ids.split(",")][:expected]
                if len(data.personal_id) >= expected:
                    break
        while True:
            data.phone = input("Phone: ").strip()
            if data.phone and len(data.phone.replace('-','').replace(' ','')) >= 10:
                break
        while True:
            data.email = input("Email: ").strip().lower()
            if data.email and '@' in data.email:
                break

        if input("Save as profile? (y/n): ").strip().lower() in ['y', 'yes']:
            name = input("Profile name: ").strip()
            self.profile_mgr.save_profile(UserProfile(profile_name=name, personal_ids=data.personal_id, phone=data.phone, email=data.email))
            print("Profile saved")
        return data

    def _filter_trains(self, trains, outbound_time):
        """Filter trains by time preference"""
        if not outbound_time or not trains:
            return trains
        try:
            pref = self._time_to_minutes(outbound_time)
            filtered = []
            for t in trains:
                diff = self._time_to_minutes(t["departure_time"]) - pref
                if -30 <= diff <= 180:
                    filtered.append(t)
            return filtered if filtered else trains
        except:
            return trains

    def _time_to_minutes(self, time_str):
        """Convert time string to minutes"""
        if not time_str or str(time_str).strip() in ('', 'None'):
            return 0
        s = str(time_str).strip()
        suffix = s[-1] if s and s[-1] in ('A', 'P', 'N') else None
        digits = ''.join(c for c in s if c.isdigit() or c == ':')
        if ':' in digits:
            h, m = map(int, digits.split(':'))
        elif len(digits) >= 3:
            h, m = int(digits[:-2]), int(digits[-2:])
        else:
            h, m = int(digits[:1]), int(digits[1:])
        if suffix == 'A' and h == 12: h = 0
        elif suffix == 'P' and h != 12: h += 12
        return h * 60 + m

    def _format_time(self, time_str):
        """Format time string for display"""
        t_int = int(time_str[:-1])
        if time_str[-1] == 'A' and t_int // 100 == 12: t_int = 0
        elif time_str[-1] == 'P': t_int += 1200
        elif time_str[-1] == 'N': t_int = 1200
        return f"{str(t_int).zfill(4)[:-2]}:{time_str[-3 if time_str[-1] != 'N' else -2:][-2:]}"

    def _is_expired(self, record):
        try:
            d = self.date_validator._parse_date(record.outbound_date)
            return d and d < date.today()
        except:
            return False

    def _execute_single_booking(self, record, reservation_id):
        for attempt in range(1, MAX_RETRIES + 1):
            print(f"Attempt {attempt}/{MAX_RETRIES}")
            try:
                booking_service = BookingService()
                success, result = booking_service.execute_full_booking(record)
                if success:
                    if 'final_response' in result:
                        result_model = BookingResultParser().parse(result['final_response'].content)
                        PrintBookingResult().print_result(result_model)
                    print("SUCCESS: Please complete payment via official channels!")
                    return True
                else:
                    print(f"Failed: {result.get('error', 'Unknown')}")
            except Exception as e:
                print(f"Error: {e}")
        return False

    def _show_summary(self, results):
        success = sum(1 for _, s in results if s)
        print(f"\n{'='*40}\nSUMMARY: {success}/{len(results)} successful\n{'='*40}")

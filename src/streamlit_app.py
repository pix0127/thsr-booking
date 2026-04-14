# -*- coding: utf-8 -*-
import streamlit as st
from datetime import date, datetime, timedelta

from controller.models import RecordFirstPage, RecordTrainPage, RecordTicketPage, ParamDB, UserProfile, UserProfileManager
from controller.schemas import StationMapping, TicketType, AVAILABLE_TIME_TABLE, MAX_TICKET_NUM
from utils.booking_date_validator import BookingDateValidator

date_validator = BookingDateValidator()


def get_station_options():
    """取得站點選項"""
    return {f"{s.name} ({s.value})": s.value for s in StationMapping}


def get_time_options():
    """取得時間選項（轉換成可讀格式）"""
    options = {}
    for time_str in AVAILABLE_TIME_TABLE:
        t_int = int(time_str[:-1])
        if time_str[-1] == "A" and (t_int // 100) == 12:
            t_int = t_int % 1200
        elif t_int != 1230 and time_str[-1] == "P":
            t_int += 1200
        elif time_str[-1] == "N":
            t_int = 1200
        t_str = str(t_int).zfill(4)
        readable_time = f"{t_str[:-2]}:{t_str[-2:]}"
        options[f"{readable_time} ({time_str})"] = time_str
    return options


def get_available_date_range():
    """取得可預訂日期範圍"""
    today = date.today()
    max_date = today + timedelta(days=DAYS_BEFORE_BOOKING_AVAILABLE)
    return today, max_date


# 取得日期範圍常數
DAYS_BEFORE_BOOKING_AVAILABLE = 90


def filter_trains_by_time(route_trains, outbound_time):
    """根據時間偏好篩選火車"""
    if not outbound_time or not route_trains:
        return route_trains

    try:
        time_str = outbound_time
        if time_str.endswith('A') or time_str.endswith('P') or time_str.endswith('N'):
            t_int = int(time_str[:-1])
            if time_str[-1] == "A" and (t_int // 100) == 12:
                t_int = t_int % 1200
            elif t_int != 1230 and time_str[-1] == "P":
                t_int += 1200
            elif time_str[-1] == "N":
                t_int = 1200
            preferred_time = f"{t_int//100:02d}:{t_int%100:02d}"
        else:
            preferred_time = time_str

        filtered = []
        for train in route_trains:
            train_time = train["departure_time"]
            try:
                pref_dt = datetime.strptime(preferred_time, "%H:%M")
                train_dt = datetime.strptime(train_time, "%H:%M")
                time_diff = (train_dt - pref_dt).total_seconds() / 60
                if -30 <= time_diff <= 180:
                    filtered.append(train)
            except Exception:
                filtered.append(train)
        return filtered if filtered else route_trains
    except Exception:
        return route_trains


def main():
    st.set_page_config(
        page_title="THSR 預約訂票",
        page_icon="🚄",
        layout="centered"
    )

    st.title("🚄 台灣高鐵預約訂票")

    menu = st.sidebar.radio("功能", ["📝 新增預約", "📋 預約列表", "👤 個人資料"])

    if menu == "📝 新增預約":
        show_booking_flow()
    elif menu == "📋 預約列表":
        show_reservation_list()
    elif menu == "👤 個人資料":
        show_profile_management()


def show_booking_flow():
    st.markdown("**注意：** 此網頁僅建立預約，實際訂票由週期系統執行")

    if 'step' not in st.session_state:
        st.session_state.step = 1
        st.session_state.first_data = None
        st.session_state.train_data = None
        st.session_state.ticket_data = None
        st.session_state.available_trains = []

    if st.session_state.step == 1:
        show_step1()
    elif st.session_state.step == 2:
        show_step2()
    elif st.session_state.step == 3:
        show_step3()
    elif st.session_state.step == 4:
        show_complete()


def show_step1():
    """Step 1: 收集基本訂票資訊"""
    st.header("Step 1: 選擇車站與時間")

    with st.form("basic_info_form"):
        # 站點選擇
        station_options = list(StationMapping)
        start_station = st.selectbox(
            "起點站",
            options=station_options,
            format_func=lambda s: f"{s.name} ({s.value})",
            index=1  # default: Taipei
        )

        dest_station = st.selectbox(
            "終點站",
            options=station_options,
            format_func=lambda s: f"{s.name} ({s.value})",
            index=11  # default: Zuoying
        )

        # 日期選擇
        today = date.today()
        max_date = today + timedelta(days=DAYS_BEFORE_BOOKING_AVAILABLE)
        travel_date = st.date_input(
            "出發日期",
            min_value=today,
            max_value=max_date,
            value=today + timedelta(days=1)
        )

        # 時間選擇
        time_options = get_time_options()
        time_display = st.selectbox(
            "出發時間",
            options=list(time_options.keys()),
            index=8  # default: 09:00
        )
        outbound_time = time_options[time_display]

        # 票數選擇
        st.subheader("票數")
        col1, col2, col3 = st.columns(3)
        with col1:
            adult_num = st.number_input("大人", min_value=1, max_value=10, value=1)
        with col2:
            child_num = st.number_input("孩童", min_value=0, max_value=10, value=0)
        with col3:
            elder_num = st.number_input("敬老", min_value=0, max_value=10, value=0)

        col4, col5 = st.columns(2)
        with col4:
            disabled_num = st.number_input("愛心", min_value=0, max_value=10, value=0)
        with col5:
            college_num = st.number_input("學生", min_value=0, max_value=10, value=0)

        submitted = st.form_submit_button("下一步 →")

        if submitted:
            # 驗證
            if start_station.value == dest_station.value:
                st.error("起點站和終點站不能相同")
                return

            total_tickets = adult_num + child_num + disabled_num + elder_num + college_num
            if total_tickets == 0:
                st.error("請至少選擇一張票")
                return

            # 建立 RecordFirstPage
            first_data = RecordFirstPage()
            first_data.start_station = start_station.value
            first_data.dest_station = dest_station.value
            first_data.outbound_date = travel_date.strftime("%Y/%m/%d")
            first_data.outbound_time = outbound_time
            first_data.adult_num = adult_num
            first_data.child_num = child_num
            first_data.disabled_num = disabled_num
            first_data.elder_num = elder_num
            first_data.college_num = college_num

            st.session_state.first_data = first_data

            # 取得火車清單（從 TDX 時刻表）
            trains = get_trains_from_timetable(first_data)
            st.session_state.available_trains = trains

            st.session_state.step = 2
            st.rerun()


def get_trains_from_timetable(first_data):
    """從 TDX 時刻表取得火車清單"""
    try:
        # 取得站點名稱
        start_name = date_validator.station_id_to_name.get(
            first_data.start_station, f"Station {first_data.start_station}")
        dest_name = date_validator.station_id_to_name.get(
            first_data.dest_station, f"Station {first_data.dest_station}")

        # 解析日期取得星期
        target_date = date_validator._parse_date(first_data.outbound_date)
        if target_date:
            weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            target_weekday = weekday_names[target_date.weekday()]

        # 取得時刻表
        route_trains = date_validator.timetable_parser.get_route_timetable(
            start_name, dest_name, target_weekday)

        if not route_trains:
            return []

        # 根據時間偏好篩選
        filtered_trains = filter_trains_by_time(route_trains, first_data.outbound_time)
        return filtered_trains

    except Exception as e:
        st.error(f"取得火車時刻表失敗: {e}")
        return []


def show_step2():
    """Step 2: 選擇火車"""
    st.header("Step 2: 選擇車次")

    trains = st.session_state.available_trains

    if not trains:
        st.warning("找不到符合的火車，您可以在下一步輸入乘客資料，系統會在執行時自動選取火車")
        st.session_state.train_data = RecordTrainPage()
        st.session_state.train_data.selection_time = []
    else:
        st.markdown(f"**找到 {len(trains)} 班火車**（依時間排序）")
        st.markdown("可選擇多班火車，系統會依序嘗試直到成功")

        # 火車選擇
        selected_times = []
        for idx, train in enumerate(trains[:20]):  # 最多顯示20班
            duration = date_validator._calculate_duration(
                train["departure_time"], train["arrival_time"])
            checkbox_label = f"🚄 {train['train_no']} | {train['departure_time']} → {train['arrival_time']} | 約{duration}分鐘"
            
            if st.checkbox(checkbox_label, key=f"train_{idx}"):
                selected_times.append(train["departure_time"])

        st.session_state.train_data = RecordTrainPage()
        st.session_state.train_data.selection_time = selected_times

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 上一步"):
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("下一步 →"):
            st.session_state.step = 3
            st.rerun()


def show_step3():
    st.header("Step 3: 乘客資訊")

    first_data = st.session_state.first_data
    total_passengers = (
        first_data.adult_num + 
        first_data.child_num + 
        first_data.disabled_num + 
        first_data.elder_num + 
        first_data.college_num
    )

    profile_mgr = UserProfileManager()
    profiles = profile_mgr.list_profiles()

    if 'pid_0' not in st.session_state:
        for i in range(10):
            st.session_state[f"pid_{i}"] = ""
        st.session_state.phone_input = ""
        st.session_state.email_input = ""

    if profiles:
        def on_profile_select():
            selected = st.session_state.profile_select
            if selected == "（手動輸入）":
                return
            applied_profile = profile_mgr.get_profile(selected)
            for i, pid in enumerate(applied_profile.personal_ids):
                if i < 10:
                    st.session_state[f"pid_{i}"] = pid
            st.session_state.phone_input = applied_profile.phone
            st.session_state.email_input = applied_profile.email
            st.session_state.profile_select = "（手動輸入）"

        profile_options = ["（手動輸入）"] + profiles
        st.selectbox("👤 選擇已儲存的個人資料", profile_options, key="profile_select", on_change=on_profile_select)
    else:
        st.info("尚無儲存的個人資料，請手動輸入")

    st.subheader(f"請輸入 {total_passengers} 位乘客的身份證字號")

    personal_ids = []
    for i in range(total_passengers):
        pid = st.text_input(f"乘客 {i+1} 身份證字號", max_chars=20, key=f"pid_{i}").upper()
        if pid:
            personal_ids.append(pid)

    phone = st.text_input("電話", max_chars=20, key="phone_input")
    email = st.text_input("Email", max_chars=100, key="email_input")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 上一步"):
            st.session_state.step = 2
            st.rerun()
    with col2:
        submitted = st.button("✅ 建立預約")

    if submitted:
        if len(personal_ids) != total_passengers:
            st.error(f"請輸入所有 {total_passengers} 位乘客的身份證字號")
        elif not phone or len(phone.replace('-', '').replace(' ', '')) < 10:
            st.error("請輸入有效的電話號碼")
        elif not email or '@' not in email:
            st.error("請輸入有效的 Email")
        else:
            ticket_data = RecordTicketPage()
            ticket_data.personal_id = personal_ids
            ticket_data.phone = phone
            ticket_data.email = email
            st.session_state.ticket_data = ticket_data
            try:
                db = ParamDB()
                db.save(
                    st.session_state.first_data,
                    st.session_state.ticket_data,
                    st.session_state.train_data
                )
                st.session_state.step = 4
                st.rerun()
            except Exception as e:
                st.error(f"儲存失敗: {e}")


def show_complete():
    """Step 4: 完成"""
    st.success("✅ 預約建立成功！")

    first_data = st.session_state.first_data
    ticket_data = st.session_state.ticket_data

    st.markdown("### 預約摘要")
    st.markdown(f"""
    | 項目 | 內容 |
    |------|------|
    | 起點站 | {StationMapping(first_data.start_station).name} |
    | 終點站 | {StationMapping(first_data.dest_station).name} |
    | 出發日期 | {first_data.outbound_date} |
    | 出發時間 | {first_data.outbound_time} |
    | 票數 | 大人{first_data.adult_num}、孩童{first_data.child_num}、敬老{first_data.elder_num}、愛心{first_data.disabled_num}、學生{first_data.college_num} |
    | 乘客數 | {len(ticket_data.personal_id)} 人 |
    | 電話 | {ticket_data.phone} |
    | Email | {ticket_data.email} |
    """)

    if st.session_state.train_data and st.session_state.train_data.selection_time:
        st.markdown(f"**已選擇的火車時間:** {', '.join(st.session_state.train_data.selection_time)}")
    else:
        st.markdown("**火車時間:** 將在執行時自動選取")

    st.info("💡 此預約已儲存，將由週期系統在適當時間自動執行訂票")

    if st.button("🔄 建立新預約"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        if "apply_profile" in st.session_state:
            del st.session_state.apply_profile
        st.rerun()


def show_reservation_list():
    st.header("📋 預約列表")

    db = ParamDB()
    reservations = db.get_history()

    if not reservations:
        st.info("目前沒有預約記錄")
        return

    for doc_id, record in reversed(reservations):
        with st.expander(f"🚄 {record.start_station} → {record.dest_station} | {record.outbound_date}"):
            st.markdown(f"""
            | 項目 | 內容 |
            |------|------|
            | ID | {doc_id} |
            | 起點站 | {StationMapping(record.start_station).name} |
            | 終點站 | {StationMapping(record.dest_station).name} |
            | 出發日期 | {record.outbound_date} |
            | 出發時間 | {record.outbound_time} |
            | 大人票 | {record.adult_num} |
            | 孩童票 | {record.child_num} |
            | 敬老票 | {record.elder_num} |
            | 愛心票 | {record.disabled_num} |
            | 學生票 | {record.college_num} |
            | 乘客 ID | {record.personal_id} |
            | 電話 | {record.phone} |
            | Email | {record.email} |
            """)

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"🗑️ 刪除", key=f"del_{doc_id}"):
                    db.remove(doc_id)
                    st.success("已刪除")
                    st.rerun()
            with col2:
                st.markdown("")  # placeholder


def show_profile_management():
    st.header("👤 個人資料管理")

    profile_mgr = UserProfileManager()
    profiles = profile_mgr.list_profiles()

    tab1, tab2 = st.tabs(["📂 現有資料", "➕ 新增資料"])

    with tab1:
        if not profiles:
            st.info("目前沒有儲存的個人資料")
        else:
            for name in profiles:
                profile = profile_mgr.get_profile(name)
                with st.expander(f"👤 {name}"):
                    st.markdown(f"""
                    | 項目 | 內容 |
                    |------|------|
                    | 姓名 | {profile.profile_name} |
                    | 身份證字號 | {', '.join(profile.personal_ids)} |
                    | 電話 | {profile.phone} |
                    | Email | {profile.email} |
                    """)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"✅ 套用", key=f"apply_{name}"):
                            st.session_state.apply_profile = profile
                            st.success(f"已套用 {name} 的資料到新預約表單")
                            st.rerun()
                    with col2:
                        if st.button(f"🗑️ 刪除", key=f"del_profile_{name}"):
                            profile_mgr.delete_profile(name)
                            st.success("已刪除")
                            st.rerun()

    with tab2:
        with st.form("new_profile"):
            st.subheader("新增個人資料")

            profile_name = st.text_input("資料名稱（方便識別）", placeholder="例如：我的資料")
            adult_count = st.number_input("人數", min_value=1, max_value=10, value=1)

            ids = []
            for i in range(adult_count):
                pid = st.text_input(f"身份證字號 {i+1}", placeholder="例：A123456789").upper()
                if pid:
                    ids.append(pid)

            phone = st.text_input("電話", placeholder="例：0912345678")
            email = st.text_input("Email", placeholder="例：test@example.com")

            submitted = st.form_submit_button("💾 儲存資料")

            if submitted:
                if not profile_name:
                    st.error("請輸入資料名稱")
                elif not ids:
                    st.error("請輸入身份證字號")
                elif not phone or len(phone.replace('-', '').replace(' ', '')) < 10:
                    st.error("請輸入有效的電話號碼")
                elif not email or '@' not in email:
                    st.error("請輸入有效的 Email")
                else:
                    profile = UserProfile(
                        profile_name=profile_name,
                        personal_ids=ids,
                        phone=phone,
                        email=email
                    )
                    profile_mgr.save_profile(profile)
                    st.success("✅ 資料已儲存！")
                    st.rerun()


if __name__ == "__main__":
    main()

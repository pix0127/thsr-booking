# -*- coding: utf-8 -*-
"""
Booking Service
簡化的預訂服務，整合所有預訂邏輯
"""
import io
import json
import contextlib
from typing import Tuple, List

import numpy as np
import ddddocr
from PIL import Image
from bs4 import BeautifulSoup
from requests.models import Response

from remote.http_request import HTTPRequest
from controller.models import Record
from controller.parsers import ErrorParser, ErrorType, TrainListParser
from controller.schemas import BookingModel, ConfirmTrainModel, ConfirmTicketModel, BOOKING_PAGE
from utils.image_process import clean_img


MAX_CAPTCHA_RETRIES = 3


class BookingService:
    """簡化的預訂服務"""

    def __init__(self, client: HTTPRequest = None):
        self.client = client or HTTPRequest()
        self._personal_id = None

    def execute_full_booking(self, record: Record) -> Tuple[bool, dict]:
        """執行完整預訂流程"""
        try:
            book_resp, book_model = self._submit_first_page_with_retry(record)
            train_resp, train_model = self._confirm_train(book_resp, record)
            ticket_resp, ticket_model = self._confirm_ticket(train_resp, record)

            return True, {
                'book_model': book_model,
                'train_model': train_model,
                'ticket_model': ticket_model,
                'final_response': ticket_resp
            }
        except Exception as e:
            return False, {'error': str(e)}

    def get_available_trains(self, record: Record) -> list:
        """獲取可用車次"""
        try:
            book_resp, _ = self._submit_first_page(record)
            return AvailTrains().parse(book_resp.content)
        except Exception as e:
            print(f"Failed to get available trains: {e}")
            return []

    def validate_record(self, record: Record) -> bool:
        """驗證預訂記錄"""
        if not record:
            return False
        required_fields = ['start_station', 'dest_station', 'outbound_date']
        for field in required_fields:
            if not getattr(record, field, None):
                return False
        return True

    # =========================================================================
    # Internal booking steps
    # =========================================================================

    def _submit_first_page_with_retry(self, record: Record) -> Tuple[Response, BookingModel]:
        """提交第一頁並處理驗證碼重試"""
        error_checker = ErrorFeedback()

        for attempt in range(1, MAX_CAPTCHA_RETRIES + 1):
            book_resp, book_model = self._submit_first_page(record)

            error_type = error_checker.parse(book_resp.content)
            if error_type == ErrorType.NO_ERROR:
                return book_resp, book_model

            if error_type == ErrorType.CAPTCHA_ERROR:
                print(f"Captcha error (attempt {attempt}/{MAX_CAPTCHA_RETRIES}), retrying...")
                continue

            if error_type == ErrorType.DATE_OUT_OF_RANGE:
                raise ValueError("Date out of range — not yet open for booking")

            raise ValueError(f"Booking form rejected: {error_type.value}")

        raise ValueError(f"Captcha failed after {MAX_CAPTCHA_RETRIES} attempts")

    def _submit_first_page(self, record: Record) -> Tuple[Response, BookingModel]:
        """提交第一頁表單"""
        print("    Step: Submitting booking form")

        book_page = self.client.request_booking_page().content
        img_resp = self.client.request_security_code_img(book_page).content
        page = BeautifulSoup(book_page, features="html.parser")

        data_dict = {
            "selectStartStation": record.start_station,
            "selectDestinationStation": record.dest_station,
            "toTimeInputField": record.outbound_date,
            "toTimeTable": record.outbound_time,
            "seatCon:seatRadioGroup": self._parse_seat_prefer_value(page),
            "tripCon:typesoftrip": self._parse_types_of_trip_value(page),
            "bookingMethod": self._parse_search_by(page),
            "homeCaptcha:securityCode": self._input_security_code(img_resp),
            "BookingS1Form:hf:0": "",
            "trainCon:trainRadioGroup": 0,
            "ticketPanel:rows:0:ticketAmount": f"{record.adult_num}F",
            "ticketPanel:rows:1:ticketAmount": f"{getattr(record, 'child_num', 0)}H",
            "ticketPanel:rows:2:ticketAmount": f"{getattr(record, 'disabled_num', 0)}W",
            "ticketPanel:rows:3:ticketAmount": f"{getattr(record, 'elder_num', 0)}E",
            "ticketPanel:rows:4:ticketAmount": f"{getattr(record, 'college_num', 0)}P",
        }
        book_model = BookingModel.model_validate(data_dict)

        json_params = book_model.json(by_alias=True)
        dict_params = json.loads(json_params)
        resp = self.client.submit_booking_form(dict_params)
        return resp, book_model

    def _confirm_train(self, book_resp: Response, record: Record) -> Tuple[Response, ConfirmTrainModel]:
        """確認車次"""
        print("    Step: Confirming train selection")

        trains = AvailTrains().parse(book_resp.content)
        if not trains:
            raise ValueError("No available trains!")

        selected_train = self._select_available_train(trains, getattr(record, 'selection_time', None))
        if selected_train is None:
            raise ValueError("找不到指定班次,被買光了QQ")

        confirm_model = ConfirmTrainModel(selected_train=selected_train)
        json_params = confirm_model.json(by_alias=True)
        dict_params = json.loads(json_params)
        resp = self.client.submit_train(dict_params)
        return resp, confirm_model

    def _confirm_ticket(self, train_resp: Response, record: Record) -> Tuple[Response, ConfirmTicketModel]:
        """確認票種資訊"""
        print("    Step: Confirming ticket details")

        page = BeautifulSoup(train_resp.content, features="html.parser")
        ticket_model = ConfirmTicketModel(
            personal_id=self._get_personal_id(record),
            phone_num=self._get_phone_num(record),
            email=self._get_email(record),
            member_radio=_parse_member_radio(page),
            member_id=self._get_member_id(record),
            early_member0_id=self._get_early_member_id(0, record, page),
            early_member1_id=self._get_early_member_id(1, record, page),
            early_member2_id=self._get_early_member_id(2, record, page),
        )

        json_params = ticket_model.json(by_alias=True)
        dict_params = json.loads(json_params)
        dict_params = {k: v for k, v in dict_params.items() if v is not None}
        resp = self.client.submit_ticket(dict_params)
        return resp, ticket_model

    # =========================================================================
    # Helper methods
    # =========================================================================

    def _parse_seat_prefer_value(self, page: BeautifulSoup) -> str:
        options = page.find(**BOOKING_PAGE["seat_prefer_radio"])
        preferred_seat = options.find_next(selected="selected")
        return preferred_seat.attrs["value"]

    def _parse_types_of_trip_value(self, page: BeautifulSoup) -> int:
        options = page.find(**BOOKING_PAGE["types_of_trip"])
        tag = options.find_next(selected="selected")
        return int(tag.attrs["value"])

    def _parse_search_by(self, page: BeautifulSoup) -> str:
        candidates = page.find_all("input", {"name": "bookingMethod"})
        tag = next((cand for cand in candidates if "checked" in cand.attrs))
        return tag.attrs["value"]

    def _input_security_code(self, img_resp: bytes) -> str:
        print("Processing security code...")
        image = Image.open(io.BytesIO(img_resp))
        io_buf = io.BytesIO(clean_img(np.array(image)))

        with contextlib.redirect_stdout(io.StringIO()):
            ocr = ddddocr.DdddOcr()
            res = ocr.classification(io_buf.getvalue())

        print(f"Security code detected: {res.upper()}")
        return res.upper()

    def _select_available_train(self, trains: List, trains_departtime) -> str:
        """選擇可用車次"""
        if isinstance(trains_departtime, str):
            selection_times = [trains_departtime]
        elif isinstance(trains_departtime, list):
            selection_times = trains_departtime
        else:
            selection_times = []

        if not selection_times or selection_times == [None] or selection_times == ['']:
            return trains[0].form_value if trains else None

        selection_minutes = [_time_to_minutes(t) for t in selection_times]

        for time_min in selection_minutes:
            for train in trains:
                if _time_to_minutes(train.depart) == time_min:
                    return train.form_value

        return None

    def _get_personal_id(self, record: Record) -> str:
        if record and hasattr(record, 'personal_id') and record.personal_id:
            pid = record.personal_id
            self._personal_id = pid
            if isinstance(pid, list):
                return pid[0] if pid else ""
            return str(pid)
        self._personal_id = input("輸入身分證字號：\n")
        return self._personal_id

    def _get_phone_num(self, record: Record) -> str:
        if record and record.phone:
            return record.phone
        return input('輸入手機號碼:\n')

    def _get_email(self, record: Record) -> str:
        if record and record.email:
            return record.email
        return input('輸入email:\n')

    def _get_member_id(self, record: Record):
        if not self._personal_id or not record:
            return None
        pid = record.personal_id
        if isinstance(pid, list) and pid:
            return pid[0]
        if isinstance(pid, str) and pid:
            return pid
        return None

    def _get_early_member_id(self, num: int, record: Record, page: BeautifulSoup):
        if not isinstance(self._personal_id, list) or len(self._personal_id) <= num:
            return None
        if len(page.find_all(attrs={"class": "uk-input passengerDataIdNumber"})) > num:
            return self._personal_id[num]
        return None


def _time_to_minutes(time_str: str) -> int:
    """Convert time string to minutes since midnight."""
    if not time_str or str(time_str).strip() in ('', 'None'):
        return 0

    s = str(time_str).strip()
    suffix = s[-1] if s and s[-1] in ('A', 'P', 'N') else None
    digits = ''.join(c for c in s if c.isdigit() or c == ':')

    if ':' in digits:
        hour_str, min_str = digits.split(':')
        hours, minutes = int(hour_str), int(min_str)
    elif len(digits) >= 3:
        hours, minutes = int(digits[:-2]), int(digits[-2:])
    elif len(digits) >= 1:
        hours, minutes = int(digits[:1]), int(digits[1:])
    else:
        return 0

    if suffix == 'A':
        if hours == 12:
            hours = 0
    elif suffix == 'N':
        if hours == 12:
            pass
    elif suffix == 'P':
        if hours != 12:
            hours += 12

    return hours * 60 + minutes


def _parse_member_radio(page: BeautifulSoup) -> str:
    """解析會員選項"""
    candidates = page.find_all(
        "input",
        attrs={
            "name": "TicketMemberSystemInputPanel:TakerMemberSystemDataView:memberSystemRadioGroup"
        },
    )
    tag = next((cand for cand in candidates if cand.get('id') == "memberSystemRadio1"))
    return tag.attrs["value"]

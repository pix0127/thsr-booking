# -*- coding: utf-8 -*-
import re
from datetime import date, datetime
from enum import Enum
from typing import Mapping, Any, Optional

from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field, field_validator


DAYS_BEFORE_BOOKING_AVAILABLE = 90

AVAILABLE_TIME_TABLE = [
    '1201A', '1230A', '600A', '630A', '700A', '730A', '800A', '830A', '900A', '930A',
    '1000A', '1030A', '1100A', '1130A', '1200N', '1230P', '100P', '130P', '200P', '230P',
    '300P', '330P', '400P', '430P', '500P', '530P', '600P', '630P', '700P', '730P',
    '800P', '830P', '900P', '930P', '1000P', '1030P', '1100P', '1130P',
]

MAX_TICKET_NUM = 10


class StationMapping(Enum):
    Nangang = 1
    Taipei = 2
    Banqiao = 3
    Taoyuan = 4
    Hsinchu = 5
    Miaoli = 6
    Taichung = 7
    Changhua = 8
    Yunlin = 9
    Chiayi = 10
    Tainan = 11
    Zuoying = 12


class TicketType(Enum):
    ADULT = 'F'
    CHILD = 'H'
    DISABELD = 'W'
    ELDER = 'E'
    COLLEGE = 'P'


BOOKING_PAGE: Mapping[str, Any] = {
    "security_code_img": {"id": "BookingS1Form_homeCaptcha_passCode"},
    "seat_prefer_radio": {"id": "BookingS1Form_seatCon_seatRadioGroup"},
    "types_of_trip": {"id": "BookingS1Form_tripCon_typesoftrip"}
}

ERROR_FEEDBACK: Mapping[str, Any] = {
    "name": "span",
    "attrs": {"class": "feedbackPanelERROR"}
}

TICKET_CONFIRMATION: Mapping[str, Any] = {
    "id_input_radio": {"id": "idInputRadio1"},
    "mobile_input_radio": {"id": "mobileInputRadio"}
}

BOOKING_RESULT: Mapping[str, Any] = {
    "ticket_id": {"name": "p", "attrs": {"class": "pnr-code"}},
    "payment_deadline": {"name": "p", "attrs": {"class": "payment-status"}},
    "phone": {"text": "行動電話"},
    "info": {"name": "table", "attrs": {"class": "table_simple"}},
    "outbound_info": {"text": "去程"},
    "seat_class": {"text": "車廂"},
    "ticket_num": {"name": "p", "text": "票數"},
    "total_price": {"id": "setTrainTotalPriceValue"},
    "train_id": {"id": "setTrainCode0"},
    "depart_time": {"id": "setTrainDeparture0"},
    "arrival_time": {"id": "setTrainArrival0"},
    "seat_num": {"name": "div", "attrs": {"class": "seat-label"}},
    "depart_station": {"name": "p", "attrs": {"class": "departure-stn"}},
    "arrival_station": {"name": "p", "attrs": {"class": "arrival-stn"}},
    "date": {"name": "span", "attrs": {"class": "date"}}
}


class ParseAvailTrain:
    from_html = {"attrs": {"class": "result-item"}}
    train_id = {"id": "QueryCode"}
    depart = {"id": "QueryDeparture"}
    arrival = {"id": "QueryArrival"}
    duration = {"attrs": {"class": "duration"}}
    early_bird_discount = {'name': 'p', 'attrs': {'class': 'early-bird'}}
    college_student_discount = {'name': 'p', 'attrs': {'class': 'student'}}
    form_value = {"name": "input", "attrs": {"name": "TrainQueryDataViewPanel:TrainGroup"}}


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
    )


class BookingModel(BaseModel):
    start_station: int = Field(..., alias="selectStartStation")
    dest_station: int = Field(..., alias="selectDestinationStation")
    search_by: str = Field(..., alias="bookingMethod")
    types_of_trip: int = Field(..., alias="tripCon:typesoftrip")
    outbound_date: str = Field(..., alias="toTimeInputField")
    outbound_time: str = Field(..., alias="toTimeTable")
    security_code: str = Field(..., alias="homeCaptcha:securityCode")
    seat_prefer: str = Field(..., alias="seatCon:seatRadioGroup")
    form_mark: str = Field("", alias="BookingS1Form:hf:0")
    class_type: int = Field(0, alias="trainCon:trainRadioGroup")
    inbound_date: str = Field(None, alias="backTimeInputField")
    inbound_time: str = Field(None, alias="backTimeTable")
    to_train_id: int = Field(None, alias="toTrainIDInputField")
    back_train_id: int = Field(None, alias="backTrainIDInputField")
    adult_ticket_num: str = Field("1F", alias="ticketPanel:rows:0:ticketAmount")
    child_ticket_num: str = Field("0H", alias="ticketPanel:rows:1:ticketAmount")
    disabled_ticket_num: str = Field("0W", alias="ticketPanel:rows:2:ticketAmount")
    elder_ticket_num: str = Field("0E", alias="ticketPanel:rows:3:ticketAmount")
    college_ticket_num: str = Field("0P", alias="ticketPanel:rows:4:ticketAmount")

    @field_validator("start_station", "dest_station")
    @classmethod
    def check_station(cls, station):
        if station not in range(1, 13):
            raise ValueError(f"Unknown station number: {station}")
        return station

    @field_validator("search_by")
    @classmethod
    def check_search_by(cls, value):
        if not re.match(r"radio\d+", value):
            raise ValueError(f"Invalid search_by format: {value}")
        return value

    @field_validator("types_of_trip")
    @classmethod
    def check_types_of_trip(cls, value):
        if value not in [0, 1]:
            raise ValueError(f"Invalid type of trip: {value}")
        return value

    @field_validator("outbound_date", "inbound_date")
    @classmethod
    def check_date(cls, value):
        if value is None:
            return date.today().strftime("%Y/%m/%d")
        if matched := re.match(r"\d{8}", value):
            target_date = datetime.strptime(matched.string, "%Y%m%d").date()
        elif matched := re.match(r"\d{4}-[0]?\d+-[0]?\d+", value):
            target_date = datetime.strptime(matched.string, "%Y-%m-%d").date()
        elif matched := re.match(r"\d{4}/[0]?\d+/[0]?\d+", value):
            target_date = datetime.strptime(matched.string, "%Y/%m/%d").date()
        else:
            raise ValueError(f"Failed to parse the date string: {value}")
        if target_date < date.today():
            raise ValueError(f"Target date should not be ealier than today: {target_date}")
        return target_date.strftime("%Y/%m/%d")

    @field_validator("inbound_time", "outbound_time")
    @classmethod
    def check_time(cls, value):
        if value not in AVAILABLE_TIME_TABLE:
            raise ValueError(f"Unknown time string: {value}")
        return value

    @field_validator("adult_ticket_num")
    @classmethod
    def check_adult_ticket_num(cls, value):
        if not re.match(r"\d+F", value):
            raise ValueError(f"Invalid adult ticket num format: {value}")
        return value

    @field_validator("child_ticket_num")
    @classmethod
    def check_child_ticket_num(cls, value):
        if not re.match(r"\d+H", value):
            raise ValueError(f"Invalid child ticket num format: {value}")
        return value

    @field_validator("disabled_ticket_num")
    @classmethod
    def check_disabled_ticket_num(cls, value):
        if not re.match(r"\d+W", value):
            raise ValueError(f"Invalid disabled ticket num format: {value}")
        return value

    @field_validator("elder_ticket_num")
    @classmethod
    def check_elder_ticket_num(cls, value):
        if not re.match(r"\d+E", value):
            raise ValueError(f"Invalid elder ticket num format: {value}")
        return value

    @field_validator("college_ticket_num")
    @classmethod
    def check_college_ticket_num(cls, value):
        if not re.match(r"\d+P", value):
            raise ValueError(f"Invalid college ticket num format: {value}")
        return value


class Train(BaseModel):
    id: int
    depart: str
    arrive: str
    travel_time: str
    discount_str: Optional[str] = ""
    form_value: str


class ConfirmTrainModel(BaseModel):
    selected_train: str = Field(..., alias="TrainQueryDataViewPanel:TrainGroup")
    form_mark: str = Field("", alias="BookingS2Form:hf:0")


class ConfirmTicketModel(BaseModel):
    personal_id: str = Field(..., alias="dummyId")
    phone_num: str = Field(..., alias="dummyPhone")
    member_radio: str = Field(
        ...,
        alias="TicketMemberSystemInputPanel:TakerMemberSystemDataView:memberSystemRadioGroup",
    )
    member_id: Optional[str] = Field(
        None,
        alias="TicketMemberSystemInputPanel:TakerMemberSystemDataView:memberSystemRadioGroup:memberShipNumber",
    )
    form_mark: str = Field("", alias="BookingS3FormSP:hf:0")
    id_input_radio: int = Field(0, alias="idInputRadio")
    diff_over: int = Field(1, alias="diffOver")
    email: str = Field("", alias="email")
    agree: str = Field("on", alias="agree")
    go_back_m: str = Field("", alias="isGoBackM")
    back_home: str = Field("", alias="backHome")
    tgo_error: int = Field(1, alias="TgoError")
    early_member0_id: Optional[str] = Field(
        "",
        alias="TicketPassengerInfoInputPanel:passengerDataView:0:passengerDataView2:passengerDataIdNumber",
    )
    early_member1_id: Optional[str] = Field(
        "",
        alias="TicketPassengerInfoInputPanel:passengerDataView:1:passengerDataView2:passengerDataIdNumber",
    )
    early_member2_id: Optional[str] = Field(
        "",
        alias="TicketPassengerInfoInputPanel:passengerDataView:2:passengerDataView2:passengerDataIdNumber",
    )


class HTTPConfig:
    BASE_URL = "https://irs.thsrc.com.tw"
    BOOKING_PAGE_URL = "https://irs.thsrc.com.tw/IMINT/?locale=tw"
    SUBMIT_FORM_URL = "https://irs.thsrc.com.tw/IMINT/;jsessionid={}?wicket:interface=:0:BookingS1Form::IFormSubmitListener"
    CONFIRM_TRAIN_URL = "https://irs.thsrc.com.tw/IMINT/?wicket:interface=:1:BookingS2Form::IFormSubmitListener"
    CONFIRM_TICKET_URL = "https://irs.thsrc.com.tw/IMINT/?wicket:interface=:2:BookingS3Form::IFormSubmitListener"

    class HTTPHeader:
        ACCEPT_HTML = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        ACCEPT_IMG = "image/webp,*/*"
        ACCEPT_LANGUAGE = "zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3"
        ACCEPT_ENCODING = "deflate, br"
        REFERER = "https://irs.thsrc.com.tw/IMINT/"
        BOOKING_PAGE_HOST = "irs.thsrc.com.tw"

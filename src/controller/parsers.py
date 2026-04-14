# -*- coding: utf-8 -*-
from typing import List, Any
from collections import namedtuple
from enum import Enum

from bs4 import BeautifulSoup
from bs4.element import Tag

from controller.schemas import (
    BOOKING_RESULT,
    ERROR_FEEDBACK,
    ParseAvailTrain,
    Train,
)


class BaseParser:
    def parse(self, html: bytes) -> List[Any]:
        raise NotImplementedError

    def _parse_html(self, html: bytes) -> BeautifulSoup:
        return BeautifulSoup(html, features="html.parser")


class ErrorType(Enum):
    NO_ERROR = "no_error"
    DATE_OUT_OF_RANGE = "date_out_of_range"
    CAPTCHA_ERROR = "captcha_error"
    OTHER = "other"


class ErrorParser(BaseParser):
    def parse(self, html: bytes) -> ErrorType:
        page = self._parse_html(html)
        items = page.find_all(**ERROR_FEEDBACK)

        for it in items:
            error_msg = it.text
            if "去程您所選擇的日期超過目前開放預訂之日期" in error_msg:
                return ErrorType.DATE_OUT_OF_RANGE
            if "檢測碼輸入錯誤" in error_msg:
                return ErrorType.CAPTCHA_ERROR
        if items:
            return ErrorType.OTHER
        return ErrorType.NO_ERROR


Ticket = namedtuple("Ticket", [
    "id", "price", "start_station", "dest_station", "train_id", "depart_time", "arrival_time",
    "date", "seat", "seat_class", "payment_deadline", "ticket_num_info"
])


class BookingResultParser(BaseParser):
    def parse(self, html: bytes) -> List[Ticket]:
        page = self._parse_html(html)
        booking_id = page.find(**BOOKING_RESULT["ticket_id"]).find("span").text
        deadline = page.find(**BOOKING_RESULT["payment_deadline"]).find_next(text='（付款期限：').find_next().text
        total_price = page.find(**BOOKING_RESULT["total_price"]).text
        train_id = page.find(**BOOKING_RESULT["train_id"]).text
        depart_time = page.find(**BOOKING_RESULT["depart_time"]).text
        arrival_time = page.find(**BOOKING_RESULT["arrival_time"]).text
        seat_num = page.find(**BOOKING_RESULT["seat_num"]).find_next().text
        seat_class = page.find(**BOOKING_RESULT["seat_class"]).find_next().text
        depart_station = page.find(**BOOKING_RESULT["depart_station"]).find_next().text
        arrival_station = page.find(**BOOKING_RESULT["arrival_station"]).find_next().text
        ticket_num_info = page.find(**BOOKING_RESULT["ticket_num"]).find_next().text
        ticket_num_info = ticket_num_info.strip().replace('\xa0', ' ')
        date = page.find(**BOOKING_RESULT["date"]).find_next().text
        return [Ticket(
            id=booking_id,
            payment_deadline=deadline,
            seat_class=seat_class,
            ticket_num_info=ticket_num_info,
            price=total_price,
            train_id=train_id,
            depart_time=depart_time,
            arrival_time=arrival_time,
            seat=seat_num,
            start_station=depart_station,
            dest_station=arrival_station,
            date=date,
        )]


class TrainListParser(BaseParser):
    def __init__(self) -> None:
        super().__init__()
        self.trains: List[Train] = []
        self.selector = ParseAvailTrain()

    def parse(self, html: bytes) -> List[Train]:
        page = self._parse_html(html)
        avail = page.find_all('label', **self.selector.from_html)
        return self._parse_train(avail)

    def _parse_train(self, avail: List[Tag]) -> List[Train]:
        self.trains = []
        for item in avail:
            try:
                train_id = int(item.find(**self.selector.train_id).text)
                depart_time = item.find(**self.selector.depart).text
                arrival_time = item.find(**self.selector.arrival).text
                travel_time = item.find(**self.selector.duration).find_next(
                    'span', {'class': 'material-icons'}
                ).fetchNextSiblings()[0].text
                discount_str = self._parse_discount(item)
                form_value = item.find(**self.selector.form_value).attrs['value']
                self.trains.append(Train(
                    id=train_id,
                    depart=depart_time,
                    arrive=arrival_time,
                    travel_time=travel_time,
                    discount_str=discount_str,
                    form_value=form_value,
                ))
            except Exception:
                continue
        return self.trains

    def _parse_discount(self, item: Tag) -> str:
        discounts = []
        if tag := item.find(**self.selector.early_bird_discount):
            discounts.append(tag.find_next().text)
        if tag := item.find(**self.selector.college_student_discount):
            discounts.append(tag.find_next().text)
        if discounts:
            return f'({", ".join(discounts)})'
        return ''


class PrintBookingResult:
    def print_result(self, tickets: List[Ticket], select: bool = False) -> int:
        ticket = tickets[0]
        print("\n\n----------- 訂位結果 -----------")
        print("訂位代號: " + ticket.id)
        print("繳費期限: " + ticket.payment_deadline)
        print("票數：" + ticket.ticket_num_info)
        print("總價: " + ticket.price)
        print("-" * 32)
        hint = ["日期", "起程站", "到達站", "出發時間", "到達時間", "車次"]
        fmt = "{:>6}" * len(hint)
        print(fmt.format(*hint))
        info = [
            ticket.date, ticket.start_station, ticket.dest_station, ticket.depart_time,
            ticket.arrival_time, ticket.train_id
        ]
        print("    {}   {}     {}     {}    {}      {}".format(*info))
        print("    {} {}".format(ticket.seat_class, ticket.seat))
        return 0


def print_reservations(hists, select: bool = True) -> int:
    from controller.models import Record
    from controller.schemas import StationMapping
    for idx, r in enumerate(hists, 1):
        print("第{}筆紀錄".format(idx))
        print("  身分證字號: " + r.personal_id)
        print("  手機號碼: " + r.phone)
        print("  起程站: " + StationMapping(r.start_station).name)
        print("  到達站: " + StationMapping(r.dest_station).name)
        t_str = r.outbound_time
        print("  出發時間: {}:{} (A: 早上, P: 下午, N: 中午)".format(t_str[:-3], t_str[-3:]))
        print("  大人票數: " + str(r.adult_num))
    if select:
        sel = input("請選擇紀錄或是Enter跳過: ")
        return int(sel) - 1 if sel != "" else None
    return None

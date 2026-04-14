import random
import time
from typing import Mapping, Any

import requests
from requests.adapters import HTTPAdapter
from requests.models import Response
from requests.exceptions import ReadTimeout
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from controller.schemas import HTTPConfig
from controller.schemas import BOOKING_PAGE


def _retry_with_backoff(total: int = 3, backoff_factor: float = 1.0):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(total):
                try:
                    return func(*args, **kwargs)
                except ReadTimeout as e:
                    last_err = e
                    if attempt < total - 1:
                        time.sleep(backoff_factor * (2 ** attempt))
                    else:
                        raise
            if last_err:
                raise last_err
        return wrapper
    return decorator


def _generate_headers() -> dict:
    """Generate randomized browser headers to avoid bot detection.

    Modelled after THSR-Sniper ``_headers()`` which rotates Firefox UA
    strings with varying Windows / Firefox versions plus standard
    Sec-Fetch-* headers that a real browser would send.
    """
    windows_ver = random.choice(["10.0", "11.0"])
    firefox_ver = f"{random.choice([136, 137, 138])}.{random.randint(0, 9)}"

    return {
        "Host": HTTPConfig.HTTPHeader.BOOKING_PAGE_HOST,
        "User-Agent": (
            f"Mozilla/5.0 (Windows NT {windows_ver}; Win64; x64; "
            f"rv:{firefox_ver}) Gecko/20100101 Firefox/{firefox_ver}"
        ),
        "Accept": HTTPConfig.HTTPHeader.ACCEPT_HTML,
        "Accept-Language": HTTPConfig.HTTPHeader.ACCEPT_LANGUAGE,
        "Accept-Encoding": HTTPConfig.HTTPHeader.ACCEPT_ENCODING,
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": HTTPConfig.HTTPHeader.REFERER,
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "no-cors",
    }


class HTTPRequest:

    DEFAULT_TIMEOUT = 60

    def __init__(self, max_retries: int = 3) -> None:
        self.sess = requests.Session()
        retry = Retry(total=0)
        self.sess.mount("https://", HTTPAdapter(max_retries=retry))

    def _headers(self) -> dict:
        return _generate_headers()

    @_retry_with_backoff(total=3, backoff_factor=1.0)
    def request_booking_page(self) -> Response:
        return self.sess.get(HTTPConfig.BOOKING_PAGE_URL, headers=self._headers(),
                             allow_redirects=True, timeout=self.DEFAULT_TIMEOUT)

    @_retry_with_backoff(total=3, backoff_factor=1.0)
    def request_security_code_img(self, book_page: bytes) -> Response:
        img_url = parse_security_img_url(book_page)
        return self.sess.get(img_url, headers=self._headers(), timeout=self.DEFAULT_TIMEOUT)

    @_retry_with_backoff(total=3, backoff_factor=1.0)
    def submit_booking_form(self, params: Mapping[str, Any]) -> Response:
        url = HTTPConfig.SUBMIT_FORM_URL.format(self.sess.cookies["JSESSIONID"])
        headers = self._headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        return self.sess.post(url, headers=headers, data=params,
                              allow_redirects=True, timeout=self.DEFAULT_TIMEOUT)

    @_retry_with_backoff(total=3, backoff_factor=1.0)
    def submit_train(self, params: Mapping[str, Any]) -> Response:
        headers = self._headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        return self.sess.post(HTTPConfig.CONFIRM_TRAIN_URL, headers=headers,
                              data=params, allow_redirects=True, timeout=self.DEFAULT_TIMEOUT)

    @_retry_with_backoff(total=3, backoff_factor=1.0)
    def submit_ticket(self, params: Mapping[str, Any]) -> Response:
        headers = self._headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        return self.sess.post(HTTPConfig.CONFIRM_TICKET_URL, headers=headers,
                              data=params, allow_redirects=True, timeout=self.DEFAULT_TIMEOUT)


def parse_security_img_url(html: bytes) -> str:
    page = BeautifulSoup(html, features="html.parser")
    element = page.find(**BOOKING_PAGE["security_code_img"])
    return HTTPConfig.BASE_URL + element["src"]

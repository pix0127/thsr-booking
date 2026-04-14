# -*- coding: utf-8 -*-
"""
Streamlit 預約訂票 E2E 測試

測試流程：新增預約 → 使用已儲存的 profile → 提交 → 刪除預約
執行方式：python -m pytest tests/test_booking_flow.py -v
"""
import subprocess
import time
import signal
import os
import sys

import pytest
from playwright.sync_api import sync_playwright, Page, expect


# 測試用 profile 名稱（需與 .db/user_profiles.json 中的現有資料一致）
PROFILE_NAME = "cy"

# Streamlit 伺服器設定
APP_PATH = os.path.join(os.path.dirname(__file__), "..", "streamlit_app.py")
PORT = 8506
BASE_URL = f"http://localhost:{PORT}"


class StreamlitServer:
    """啟動/停止 Streamlit 測試伺服器"""

    def __init__(self, port: int):
        self.port = port
        self.process: subprocess.Popen | None = None

    def start(self):
        self.process = subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run", APP_PATH,
                "--server.headless", "true",
                "--server.port", str(self.port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # 等待伺服器就緒
        for _ in range(30):
            try:
                import urllib.request
                urllib.request.urlopen(BASE_URL, timeout=1)
                return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError(f"Streamlit server failed to start on port {self.port}")

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)


@pytest.fixture(scope="module")
def server():
    srv = StreamlitServer(PORT)
    srv.start()
    yield srv
    srv.stop()


@pytest.fixture
def browser_page(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(BASE_URL)
        yield page
        context.close()
        browser.close()


# ---------------------------------------------------------------------------
#  Helper functions
# ---------------------------------------------------------------------------

def click_radio(page: Page, label: str):
    page.get_by_role("radiogroup").get_by_label(label).click()


def submit_form_button(page: Page, label: str = "下一步 →"):
    page.get_by_role("button", name=label).click()


def select_profile_in_step3(page: Page, profile_name: str):
    """在 Step 3 選擇已儲存的 profile"""
    combobox = page.get_by_role("combobox", label="選擇已儲存的個人資料")
    combobox.click()
    page.get_by_role("option", name=profile_name, exact=True).click()


def expand_reservation(page: Page):
    """展開預約列表中的第一筆預約"""
    page.get_by_role("group").get_by_label("🚄").click()


# ---------------------------------------------------------------------------
#  Test cases
# ---------------------------------------------------------------------------

def test_create_reservation_with_saved_profile(browser_page: Page):
    """
    測試：使用已儲存的 profile 完成預約流程
    1. Step 1 → Step 2（使用預設值）
    2. Step 2 → Step 3（跳過火車選擇）
    3. Step 3：選擇已儲存的 profile，驗證欄位自動填入
    4. 提交 → Step 4 成功
    """
    page = browser_page

    # Step 1：使用預設值直接提交
    expect(page.get_by_role("heading", name="Step 1: 選擇車站與時間")).to_be_visible()
    submit_form_button(page)

    # Step 2：跳過火車選擇，直接下一步
    expect(page.get_by_role("heading", name="Step 2: 選擇車次")).to_be_visible()
    submit_form_button(page)

    # Step 3：選擇已儲存的 profile
    expect(page.get_by_role("heading", name="Step 3: 乘客資訊")).to_be_visible()
    select_profile_in_step3(page, PROFILE_NAME)

    # 驗證 profile 資料已填入（身份證、姓名、Email）
    pid_input = page.get_by_label("乘客 1 身份證字號")
    expect(pid_input).to_have_value("E124467600", timeout=5000)

    phone_input = page.get_by_label("電話")
    expect(phone_input).to_have_value("0937308556", timeout=2000)

    email_input = page.get_by_label("Email")
    expect(email_input).to_have_value("shanashana000@gmail.com", timeout=2000)

    # 提交預約
    page.get_by_role("button", name="✅ 建立預約").click()

    # Step 4：驗證成功
    expect(page.get_by_role("heading", name="預約摘要")).to_be_visible()
    expect(page.locator("text=預約建立成功")).to_be_visible()


def test_delete_reservation(browser_page: Page):
    """
    測試：刪除預約
    1. 來到預約列表
    2. 展開預約
    3. 點擊刪除
    4. 驗證列表為空
    """
    page = browser_page

    # 切到預約列表
    click_radio(page, "📋 預約列表")
    expect(page.get_by_role("heading", name="📋 預約列表")).to_be_visible()

    # 展開預約
    expand_reservation(page)

    # 刪除
    page.get_by_role("button", name="🗑️ 刪除").click()

    # 驗證已刪除
    expect(page.locator("text=目前沒有預約記錄")).to_be_visible()


def test_profile_autofill_and_button_navigation(browser_page: Page):
    """
    測試：選擇 profile 後，上一步 / 建立預約 按鈕可正常運作
    （迴歸測試：確認 profile callback 不會破壞按鈕）
    """
    page = browser_page

    # 前進到 Step 3
    expect(page.get_by_role("heading", name="Step 1: 選擇車站與時間")).to_be_visible()
    submit_form_button(page)
    expect(page.get_by_role("heading", name="Step 2: 選擇車次")).to_be_visible()
    submit_form_button(page)
    expect(page.get_by_role("heading", name="Step 3: 乘客資訊")).to_be_visible()

    # 選擇 profile
    select_profile_in_step3(page, PROFILE_NAME)

    # 驗證欄位已填入
    expect(page.get_by_label("乘客 1 身份證字號")).to_have_value("E124467600", timeout=5000)

    # 測試「← 上一步」按鈕
    page.get_by_role("button", name="← 上一步").click()
    expect(page.get_by_role("heading", name="Step 2: 選擇車次")).to_be_visible()

    # 回到 Step 3
    submit_form_button(page)
    expect(page.get_by_role("heading", name="Step 3: 乘客資訊")).to_be_visible()

    # 再次選擇 profile 並提交
    select_profile_in_step3(page, PROFILE_NAME)
    expect(page.get_by_label("乘客 1 身份證字號")).to_have_value("E124467600", timeout=5000)
    page.get_by_role("button", name="✅ 建立預約").click()

    # 驗證成功
    expect(page.get_by_role("heading", name="預約摘要")).to_be_visible()

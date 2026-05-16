# 文件: .github/scripts/keepalive.py
# 更新日期: 2026-05-16
# 用途: 用 Playwright 无头浏览器访问 Streamlit demo，建立 WebSocket，必要时点击"唤醒"按钮
# 主要改动: 初始版本

import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL = os.environ.get("DEMO_URL", "").strip()
if not URL:
    print("ERROR: DEMO_URL env var is empty", file=sys.stderr)
    sys.exit(1)

WAKE_BUTTON_TEXTS = [
    "Yes, get this app back up!",
    "get this app back up",
]

def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print(f"Visiting {URL}")
        page.goto(URL, timeout=60_000, wait_until="domcontentloaded")

        # 如果应用处于休眠状态，页面会显示一个"唤醒"按钮，点击它
        for label in WAKE_BUTTON_TEXTS:
            try:
                btn = page.get_by_role("button", name=label)
                if btn.count() > 0 and btn.first.is_visible(timeout=2_000):
                    print(f"Sleep page detected, clicking '{label}'")
                    btn.first.click()
                    break
            except PWTimeout:
                continue
            except Exception as e:
                print(f"Wake-button check skipped: {e}")

        # 等待 Streamlit 主容器渲染（说明 WebSocket 已建立、应用进入活跃状态）
        try:
            page.wait_for_selector('[data-testid="stApp"]', timeout=180_000)
            print("Streamlit app container loaded")
        except PWTimeout:
            print("WARN: stApp selector did not appear within 3 min", file=sys.stderr)

        # 保持会话 30 秒，确保被 Streamlit 服务器计为有效活跃访问
        page.wait_for_timeout(30_000)

        title = page.title()
        print(f"Done. Page title: {title!r}")

        context.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

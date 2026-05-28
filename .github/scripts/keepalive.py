# 文件: .github/scripts/keepalive.py
# 更新日期: 2026-05-28
# 用途: 用 Playwright 无头浏览器访问 Streamlit demo，建立 WebSocket，必要时唤醒睡眠应用
# 主要改动:
#   - 2026-05-16: 初始版本（role 按钮匹配 + 30s 停留）
#   - 2026-05-28: 加 stealth 伪装（去 webdriver 旗、真实 UA/viewport/locale）；
#                 多策略检测+点击唤醒按钮（role / text 子串 / 单按钮兜底 / Enter 键）；
#                 等不到 stApp 改为 sys.exit(1)，让 Actions 真的标红，不再静默"成功"；
#                 唤醒后加鼠标移动模拟真实交互，提高被 Streamlit 计为活跃用户的概率

import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL = os.environ.get("DEMO_URL", "").strip()
if not URL:
    print("ERROR: DEMO_URL env var is empty", file=sys.stderr)
    sys.exit(1)

# 历次 Streamlit 睡眠页用过的按钮文案，按优先级匹配
WAKE_BUTTON_PATTERNS = [
    "Yes, get this app back up!",
    "get this app back up",
    "Wake up",
    "wake up",
    "Yes",
]

# 判断当前是否落在睡眠占位页（不区分大小写）
SLEEP_KEYWORDS = ["zzz", "asleep", "inactivity", "wake it back up", "get this app back up"]

# Stealth 注入：盖掉 Playwright 默认指纹中最显眼的几项
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
window.chrome = { runtime: {} };
"""

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def looks_asleep(page) -> bool:
    """通过 title/body 文本判断当前页是否是 Streamlit 睡眠占位页。"""
    try:
        title = (page.title() or "").lower()
    except Exception as e:
        print(f"[detect] title probe failed: {e}")
        title = ""
    try:
        body = (page.locator("body").inner_text(timeout=3_000) or "").lower()
    except Exception as e:
        print(f"[detect] body probe failed: {e}")
        body = ""
    for kw in SLEEP_KEYWORDS:
        if kw in title or kw in body:
            print(f"[detect] hit sleep keyword: {kw!r}")
            return True
    return False


def try_wake(page) -> bool:
    """页面看起来是睡眠状态时尝试唤醒。返回是否点到/触发了任何唤醒动作。"""

    # 策略 1: 按文本匹配 button role
    for label in WAKE_BUTTON_PATTERNS:
        try:
            btn = page.get_by_role("button", name=label)
            if btn.count() > 0 and btn.first.is_visible(timeout=1_500):
                print(f"[wake] strategy=role button name={label!r}")
                btn.first.click()
                return True
        except PWTimeout:
            continue
        except Exception as e:
            print(f"[wake] role strategy ({label!r}) skipped: {e}")

    # 策略 2: 任意可见文本包含 "get this app back up"
    try:
        loc = page.get_by_text("get this app back up", exact=False)
        if loc.count() > 0 and loc.first.is_visible(timeout=1_500):
            print("[wake] strategy=text contains 'get this app back up'")
            loc.first.click()
            return True
    except Exception as e:
        print(f"[wake] text strategy skipped: {e}")

    # 策略 3: 页面上只有一个可见 button，盲点
    try:
        buttons = page.locator("button:visible")
        cnt = buttons.count()
        if cnt == 1:
            print("[wake] strategy=single visible button fallback")
            buttons.first.click()
            return True
        else:
            print(f"[wake] visible button count={cnt}, skip single-button fallback")
    except Exception as e:
        print(f"[wake] single-button fallback skipped: {e}")

    # 策略 4: 按 Enter 提交默认按钮
    try:
        page.keyboard.press("Enter")
        print("[wake] strategy=Enter key as last resort")
        return True
    except Exception as e:
        print(f"[wake] Enter strategy skipped: {e}")

    return False


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=UA,
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Asia/Shanghai",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        context.add_init_script(STEALTH_SCRIPT)
        page = context.new_page()

        print(f"Visiting {URL}")
        page.goto(URL, timeout=60_000, wait_until="domcontentloaded")

        # 给页面 5s 初步渲染，再判断是不是睡眠页
        page.wait_for_timeout(5_000)

        if looks_asleep(page):
            print("[detect] sleep page detected, attempting wake")
            woke = try_wake(page)
            if woke:
                # 唤醒按钮点了之后，Streamlit 通常 10-90s 内重建容器；先等 10s 再交给 stApp 等待
                page.wait_for_timeout(10_000)
            else:
                print("ERROR: detected sleep page but no wake strategy succeeded", file=sys.stderr)
                # 不立刻退出，继续等 stApp，下面统一判定 + 错误信息更全
        else:
            print("[detect] no sleep markers in title/body, app likely already awake")

        # 等 Streamlit 主容器
        try:
            page.wait_for_selector('[data-testid="stApp"]', timeout=180_000)
            print("OK: Streamlit app container loaded")
        except PWTimeout:
            try:
                snippet = page.locator("body").inner_text(timeout=2_000)[:400]
            except Exception:
                snippet = "<inner_text failed>"
            print(
                "FAIL: stApp selector did not appear within 3 min\n"
                f"  url={page.url}\n"
                f"  title={page.title()!r}\n"
                f"  body[:400]={snippet!r}",
                file=sys.stderr,
            )
            context.close()
            browser.close()
            return 1

        # 保持 30s 真实活跃（鼠标小幅移动，模拟交互）
        for i in range(6):
            page.mouse.move(200 + i * 30, 200 + i * 20)
            page.wait_for_timeout(5_000)

        print(f"Done. Page title: {page.title()!r}")
        context.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

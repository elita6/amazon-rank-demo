# 文件: .github/scripts/keepalive.py
# 更新日期: 2026-05-28
# 用途: 用 Playwright 无头浏览器访问 Streamlit demo，建立 WebSocket，必要时唤醒睡眠应用
# 主要改动:
#   - 2026-05-16: 初始版本
#   - 2026-05-28 v2: 加 stealth、多策略唤醒、真错误退出、鼠标移动
#   - 2026-05-28 v3: stApp 单选择器误报（v2 实测 title 已是 app 名但 stApp 取不到），改为多就绪信号 race
#                    （候选 6 个 test-id / class + body 非空文本兜底），主 frame + 所有 iframe 都扫；
#                    失败时 dump 当时的 HTML 到 keepalive_page.html、全页截图到 keepalive_failure.png，
#                    由 workflow 的 upload-artifact 步骤挂到 run 页面，便于离线诊断；
#                    睡眠关键字检测也扩到所有 iframe 内容

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL = os.environ.get("DEMO_URL", "").strip()
if not URL:
    print("ERROR: DEMO_URL env var is empty", file=sys.stderr)
    sys.exit(1)

WAKE_BUTTON_PATTERNS = [
    "Yes, get this app back up!",
    "get this app back up",
    "Wake up",
    "wake up",
    "Yes",
]

SLEEP_KEYWORDS = ["zzz", "asleep", "inactivity", "wake it back up", "get this app back up"]

# 多个候选就绪信号；任一命中就视为应用真正活跃
READY_SELECTORS = [
    '[data-testid="stApp"]',
    '[data-testid="stAppViewContainer"]',
    '[data-testid="stMain"]',
    '[data-testid="stMainBlockContainer"]',
    'div.stApp',
    '#root .stApp',
]

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { runtime: {} };
"""

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

FAILURE_HTML = Path("keepalive_page.html")
FAILURE_PNG = Path("keepalive_failure.png")


def get_all_text(page) -> str:
    """主 frame body + 所有 iframe body 的 inner_text 拼接，用于睡眠关键字检测。"""
    parts = []
    try:
        parts.append(page.locator("body").inner_text(timeout=3_000) or "")
    except Exception as e:
        print(f"[detect] main body inner_text failed: {e}")
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            parts.append(frame.locator("body").inner_text(timeout=2_000) or "")
        except Exception:
            pass
    return "\n".join(parts).lower()


def looks_asleep(page) -> bool:
    text = get_all_text(page)
    if not text.strip():
        print("[detect] empty page text, cannot determine sleep state from text")
        return False
    for kw in SLEEP_KEYWORDS:
        if kw in text:
            print(f"[detect] hit sleep keyword: {kw!r}")
            return True
    return False


def try_wake(page) -> bool:
    """页面看起来是睡眠状态时尝试唤醒。返回是否点到/触发了任何唤醒动作。"""

    # 策略 1: role 按钮匹配
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

    # 策略 2: 文本子串
    try:
        loc = page.get_by_text("get this app back up", exact=False)
        if loc.count() > 0 and loc.first.is_visible(timeout=1_500):
            print("[wake] strategy=text contains 'get this app back up'")
            loc.first.click()
            return True
    except Exception as e:
        print(f"[wake] text strategy skipped: {e}")

    # 策略 3: 唯一可见按钮兜底
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

    # 策略 4: Enter 键
    try:
        page.keyboard.press("Enter")
        print("[wake] strategy=Enter key as last resort")
        return True
    except Exception as e:
        print(f"[wake] Enter strategy skipped: {e}")

    return False


def _check_selectors(scope, label: str):
    """在某个 scope（page 或 frame）上扫所有候选 ready 选择器。命中返回 (sel, label)，否则 None。"""
    for sel in READY_SELECTORS:
        try:
            if scope.locator(sel).count() > 0:
                return sel, label
        except Exception:
            pass
    return None


def _check_body_nonempty(scope, label: str):
    try:
        txt = (scope.locator("body").inner_text(timeout=500) or "").strip()
        if txt:
            return "body-nonempty", label
    except Exception:
        pass
    return None


def wait_ready(page, timeout_ms: int = 180_000) -> str | None:
    """轮询多个就绪信号；任一命中即返回信号描述，超时返回 None。"""
    step_ms = 2_000
    elapsed = 0
    last_progress_bucket = -1
    while elapsed < timeout_ms:
        # 主 frame: 选择器优先
        hit = _check_selectors(page, "main")
        if hit:
            return f"{hit[1]}:selector:{hit[0]}"
        # iframe: 选择器
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            hit = _check_selectors(frame, f"frame[{frame.url[:60]}]")
            if hit:
                return f"{hit[1]}:selector:{hit[0]}"
        # 主 frame: body 非空兜底
        hit = _check_body_nonempty(page, "main")
        if hit:
            return f"{hit[1]}:{hit[0]}"
        # iframe: body 非空兜底
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            hit = _check_body_nonempty(frame, f"frame[{frame.url[:60]}]")
            if hit:
                return f"{hit[1]}:{hit[0]}"

        # 每 30s 打一次进度（包含 frame url 列表，便于诊断是否真有 iframe）
        bucket = elapsed // 30_000
        if bucket != last_progress_bucket:
            frame_urls = [f.url for f in page.frames]
            print(f"[ready] waiting... elapsed={elapsed // 1000}s, frames={frame_urls}")
            last_progress_bucket = bucket

        page.wait_for_timeout(step_ms)
        elapsed += step_ms
    return None


def dump_failure(page) -> None:
    """失败时把 HTML 和截图落盘，由 workflow upload-artifact 步骤上传。"""
    try:
        FAILURE_HTML.write_text(page.content(), encoding="utf-8")
        print(f"[dump] wrote {FAILURE_HTML} ({FAILURE_HTML.stat().st_size} bytes)")
    except Exception as e:
        print(f"[dump] HTML dump failed: {e}", file=sys.stderr)
    try:
        page.screenshot(path=str(FAILURE_PNG), full_page=True)
        print(f"[dump] wrote {FAILURE_PNG}")
    except Exception as e:
        print(f"[dump] screenshot failed: {e}", file=sys.stderr)


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
        page.wait_for_timeout(5_000)

        if looks_asleep(page):
            print("[detect] sleep page detected, attempting wake")
            if try_wake(page):
                page.wait_for_timeout(10_000)
            else:
                print("ERROR: detected sleep page but no wake strategy succeeded", file=sys.stderr)
        else:
            print("[detect] no sleep markers found")

        signal = wait_ready(page, timeout_ms=180_000)
        if signal is None:
            try:
                snippet = page.locator("body").inner_text(timeout=2_000)[:400]
            except Exception:
                snippet = "<inner_text failed>"
            frame_urls = [f.url for f in page.frames]
            print(
                "FAIL: no ready signal within 3 min\n"
                f"  url={page.url}\n"
                f"  title={page.title()!r}\n"
                f"  frames={frame_urls}\n"
                f"  body[:400]={snippet!r}",
                file=sys.stderr,
            )
            dump_failure(page)
            context.close()
            browser.close()
            return 1

        print(f"OK: ready signal = {signal}")

        # 真实活跃 30s（鼠标小幅移动）
        for i in range(6):
            page.mouse.move(200 + i * 30, 200 + i * 20)
            page.wait_for_timeout(5_000)

        print(f"Done. Page title: {page.title()!r}")
        context.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

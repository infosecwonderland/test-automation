"""
Self-healing selector utility.

Public API
----------
heal_selector(page_path, element_purpose, broken_selector, headless) -> HealResult
    Uses a browser-use Agent to find the real CSS selector for an element
    described by element_purpose on the SUT page at page_path.

patch_page_object(page_name, broken_selector, healed_selector) -> str | None
    Replaces broken_selector with healed_selector in the matching
    TypeScript page object file under ../playwright/pages/.
    Returns the patched file path, or None if nothing was changed.

heal_and_patch(page_name, page_path, element_purpose, broken_selector, headless)
    Convenience wrapper: runs heal_selector then patch_page_object.
    Returns a dict with keys: healed_selector, confidence, reason, patched_file.
"""
from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

from browser_use import Agent, BrowserSession, BrowserProfile
from dotenv import load_dotenv, find_dotenv
from browser_use.llm.anthropic.chat import ChatAnthropic
from pydantic import BaseModel

load_dotenv(find_dotenv(usecwd=True))

BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")
_PAGES_DIR = Path(__file__).parent / "pages"

# ---------------------------------------------------------------------------
# Page-object file mapping
# ---------------------------------------------------------------------------

PAGE_FILE_MAP: dict[str, str] = {
    "login":        "LoginPage.ts",
    "products":     "ProductsPage.ts",
    "cart":         "CartPage.ts",
    "checkout":     "CheckoutPage.ts",
    "payment":      "PaymentPage.ts",
    "confirmation": "ConfirmationPage.ts",
}

# ---------------------------------------------------------------------------
# Known selectors (sourced from page objects)
# ---------------------------------------------------------------------------

KNOWN_SELECTORS: dict[str, list[dict]] = {
    "login": [
        {"purpose": "email input",       "selector": "#email",                      "page_path": "/login"},
        {"purpose": "password input",    "selector": "#password",                   "page_path": "/login"},
        {"purpose": "submit button",     "selector": "#submit",                     "page_path": "/login"},
        {"purpose": "login error",       "selector": "[data-testid='login-error']", "page_path": "/login"},
    ],
    "products": [
        {"purpose": "search input",         "selector": "#search",                             "page_path": "/products-page"},
        {"purpose": "product item",         "selector": "[data-testid='product-item']",        "page_path": "/products-page"},
        {"purpose": "add to cart button",   "selector": "[data-testid='add-to-cart-button']",  "page_path": "/products-page"},
    ],
    "cart": [
        {"purpose": "cart item",               "selector": "[data-testid='cart-item']",              "page_path": "/cart"},
        {"purpose": "remove from cart button", "selector": "[data-testid='remove-from-cart-button']","page_path": "/cart"},
    ],
    "checkout": [
        {"purpose": "continue to payment link", "selector": "a:has-text('Continue to Payment')", "page_path": "/checkout"},
    ],
    "payment": [
        {"purpose": "order id input",  "selector": "input[name='orderId']",              "page_path": "/payment"},
        {"purpose": "card number input","selector": "input[name='cardNumber']",           "page_path": "/payment"},
        {"purpose": "payment error",   "selector": "[data-testid='payment-error']",      "page_path": "/payment"},
    ],
    "confirmation": [
        {"purpose": "order details",      "selector": "[data-testid='order-details']",     "page_path": "/order-confirmation"},
        {"purpose": "order id",           "selector": "[data-testid='order-id']",          "page_path": "/order-confirmation"},
        {"purpose": "order total",        "selector": "[data-testid='order-total']",       "page_path": "/order-confirmation"},
        {"purpose": "back to products",   "selector": "[data-testid='back-to-products']",  "page_path": "/order-confirmation"},
    ],
}

# ---------------------------------------------------------------------------
# Pydantic result model
# ---------------------------------------------------------------------------


class HealResult(BaseModel):
    broken_selector: str
    healed_selector: str
    confidence: str       # high | medium | low | unknown
    reason: str
    raw_output: str


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------


def _make_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


# ---------------------------------------------------------------------------
# heal_selector
# ---------------------------------------------------------------------------


async def heal_selector(
    page_path: str,
    element_purpose: str,
    broken_selector: str,
    headless: bool = True,
) -> HealResult:
    """
    Launch a browser-use Agent on BASE_URL+page_path.
    The agent navigates visually, finds the element matching element_purpose,
    and returns a working CSS selector.

    Expected agent output includes lines like:
        SELECTOR: <css>
        CONFIDENCE: high|medium|low
        REASON: <text>
    """
    url = BASE_URL.rstrip("/") + page_path
    task = (
        f"Navigate to {url}. "
        f"The CSS selector '{broken_selector}' is broken and no longer matches any element. "
        f"Your task: find the element on the page whose purpose is '{element_purpose}'. "
        "Use visual inspection and the page structure to locate it. "
        "Once found, respond with EXACTLY these three lines (no other text):\n"
        "SELECTOR: <the working CSS selector>\n"
        "CONFIDENCE: high   (or medium or low)\n"
        "REASON: <one sentence explaining how you identified it>\n"
        "If you cannot find the element, use SELECTOR: NOT_FOUND and CONFIDENCE: low."
    )

    llm = _make_llm()
    profile = BrowserProfile(headless=headless)
    session = BrowserSession(browser_profile=profile)

    try:
        agent = Agent(task=task, llm=llm, browser_session=session, use_vision=True)
        history = await agent.run()
        raw = history.final_result() or ""
    except Exception as exc:
        raw = f"ERROR: {exc}"

    return _parse_heal_result(broken_selector, raw)


def _parse_heal_result(broken_selector: str, raw: str) -> HealResult:
    selector = "NOT_FOUND"
    confidence = "unknown"
    reason = ""

    for line in raw.splitlines():
        line = line.strip()
        m = re.match(r"SELECTOR:\s*(.+)", line, re.IGNORECASE)
        if m:
            selector = m.group(1).strip()
        m = re.match(r"CONFIDENCE:\s*(\w+)", line, re.IGNORECASE)
        if m:
            confidence = m.group(1).strip().lower()
        m = re.match(r"REASON:\s*(.+)", line, re.IGNORECASE)
        if m:
            reason = m.group(1).strip()

    return HealResult(
        broken_selector=broken_selector,
        healed_selector=selector,
        confidence=confidence,
        reason=reason,
        raw_output=raw,
    )


# ---------------------------------------------------------------------------
# patch_page_object
# ---------------------------------------------------------------------------


def patch_page_object(
    page_name: str,
    broken_selector: str,
    healed_selector: str,
) -> str | None:
    """
    Replace broken_selector with healed_selector in the TypeScript page object
    file for page_name.  Returns the file path if patched, else None.
    """
    filename = PAGE_FILE_MAP.get(page_name.lower())
    if not filename:
        return None

    ts_path = _PAGES_DIR / filename
    if not ts_path.exists():
        return None

    content = ts_path.read_text(encoding="utf-8")
    if broken_selector not in content:
        return None

    patched = content.replace(broken_selector, healed_selector)
    ts_path.write_text(patched, encoding="utf-8")
    return str(ts_path)


# ---------------------------------------------------------------------------
# heal_and_patch  (convenience wrapper)
# ---------------------------------------------------------------------------


async def heal_and_patch(
    page_name: str,
    page_path: str,
    element_purpose: str,
    broken_selector: str,
    headless: bool = True,
) -> dict:
    """
    1. Run heal_selector to find the working CSS selector.
    2. If found, call patch_page_object to update the TypeScript file.

    Returns a dict:
        healed_selector  – the CSS selector the agent found
        confidence       – high | medium | low | unknown
        reason           – agent explanation
        patched_file     – absolute path to the .ts file, or None
    """
    result = await heal_selector(page_path, element_purpose, broken_selector, headless)

    patched_file: str | None = None
    if result.healed_selector not in ("NOT_FOUND", ""):
        patched_file = patch_page_object(page_name, broken_selector, result.healed_selector)

    return {
        "healed_selector": result.healed_selector,
        "confidence":      result.confidence,
        "reason":          result.reason,
        "patched_file":    patched_file,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    page_path_arg     = sys.argv[1] if len(sys.argv) > 1 else "/login"
    purpose_arg       = sys.argv[2] if len(sys.argv) > 2 else "email input"
    broken_arg        = sys.argv[3] if len(sys.argv) > 3 else "#broken"

    result = asyncio.run(heal_selector(page_path_arg, purpose_arg, broken_arg))
    print(result.model_dump_json(indent=2))

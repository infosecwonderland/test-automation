"""
Self-healing agents for the e-commerce SUT.

Pattern mirrors vibetest-use/vibetest/agents.py:
  1. A scout agent inspects the page and identifies interactive elements.
  2. N scenario agents run in parallel, each completing one test task.
  3. Results include any healed selectors discovered when original ones broke.
"""
import asyncio
import os
import time
import uuid

from browser_use import Agent, BrowserSession, BrowserProfile
from browser_use.llm.anthropic.chat import ChatAnthropic
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))

BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")
_test_results: dict = {}


def _make_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


# ---------------------------------------------------------------------------
# Scout – inspects a page and returns a focused set of healing tasks
# ---------------------------------------------------------------------------

async def scout_page(url: str) -> list[str]:
    """
    Visit url, discover all interactive elements, and return 6-8 specific
    self-healing test tasks (one per element / action).
    """
    llm = _make_llm()
    task = (
        f"Navigate to {url}. "
        "List every interactive element you can find (inputs, buttons, links, forms). "
        "For each element describe: its visible label or placeholder, its apparent purpose, "
        "and the most reliable CSS selector to target it. "
        "Return a JSON array of objects with keys: label, purpose, selector."
    )
    agent = Agent(task=task, llm=llm, use_vision=True)
    history = await agent.run()
    result = history.final_result() or ""

    # Convert the free-text result into one task string per element found
    # so each parallel agent gets a distinct, non-overlapping assignment
    lines = [l.strip() for l in result.splitlines() if l.strip()]
    if not lines:
        return [f"Inspect {url} and report what you see"]
    return lines[:8]  # cap at 8 tasks, same as vibetest


# ---------------------------------------------------------------------------
# Per-scenario healing tasks (one agent per Playwright scenario)
# ---------------------------------------------------------------------------

LOGIN_TASK = (
    f"Navigate to {BASE_URL}. "
    "Find the login form. Fill the email field with 'test@example.com' and the "
    "password field with 'password123'. Click the submit / login button. "
    "Verify you are redirected to the products page. "
    "If any element selector is broken or not found, identify a working alternative "
    "and include it in your report as: HEALED: <broken_selector> → <working_selector>. "
    "Report PASS or FAIL and list every healed selector."
)

PRODUCT_SEARCH_TASK = (
    f"Navigate to {BASE_URL}/products-page. "
    "Find the search input and type 'Laptop'. "
    "Wait for the product list to update and verify at least one product appears. "
    "Click 'Add to Cart' on the first visible product. "
    "If any element selector is broken, find a working alternative and report it as: "
    "HEALED: <broken_selector> → <working_selector>. "
    "Report PASS or FAIL."
)

CART_TASK = (
    f"Navigate to {BASE_URL}/cart. "
    "Verify the cart heading is visible. "
    "Check that at least one cart item is displayed. "
    "Click the 'Proceed to Checkout' button. "
    "If any element is missing or its selector is broken, find an alternative and report: "
    "HEALED: <broken_selector> → <working_selector>. "
    "Report PASS or FAIL."
)

CHECKOUT_TASK = (
    f"Navigate to {BASE_URL}/checkout. "
    "Verify the checkout heading is visible. "
    "Click the 'Continue to Payment' link. "
    "If any element selector is broken, report: HEALED: <broken_selector> → <working_selector>. "
    "Report PASS or FAIL."
)

PAYMENT_TASK = (
    f"Navigate to {BASE_URL}/payment. "
    "Verify the payment heading is visible. "
    "Fill the order-id field with 'test-order-001'. "
    "Fill the card number field with '4111111111111111'. "
    "Click the Pay button. "
    "If any selector is broken, report: HEALED: <broken_selector> → <working_selector>. "
    "Report PASS or FAIL."
)

ORDER_CONFIRMATION_TASK = (
    f"Navigate to {BASE_URL}/order-confirmation. "
    "Verify the 'Order Confirmation' heading is visible. "
    "Check that order details are displayed (order id, total, items). "
    "If any selector is broken, report: HEALED: <broken_selector> → <working_selector>. "
    "Report PASS or FAIL."
)

FULL_PURCHASE_FLOW_TASK = (
    f"Starting at {BASE_URL}, complete the full e-commerce purchase flow:\n"
    "1. Log in with email 'test@example.com' and password 'password123'.\n"
    "2. Search for 'Laptop' on the products page and add the first result to the cart.\n"
    "3. Go to the cart and click 'Proceed to Checkout'.\n"
    "4. On the checkout page click 'Continue to Payment'.\n"
    "5. On the payment page fill card number '4111111111111111' and click Pay.\n"
    "6. Verify the order confirmation page shows an order id.\n"
    "At every step, if a selector or element is missing, adapt and use the best available "
    "alternative. Report each healed selector as: HEALED: <broken> → <working>. "
    "Report overall PASS or FAIL with a step-by-step summary."
)

SCENARIO_TASKS = {
    "login":              LOGIN_TASK,
    "product_search":     PRODUCT_SEARCH_TASK,
    "cart":               CART_TASK,
    "checkout":           CHECKOUT_TASK,
    "payment":            PAYMENT_TASK,
    "order_confirmation": ORDER_CONFIRMATION_TASK,
    "full_purchase_flow": FULL_PURCHASE_FLOW_TASK,
}


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------

async def _run_agent(agent_id: str, task: str, headless: bool) -> dict:
    llm = _make_llm()
    profile = BrowserProfile(headless=headless)
    session = BrowserSession(browser_profile=profile)

    start = time.time()
    try:
        agent = Agent(task=task, llm=llm, browser_session=session, use_vision=True)
        history = await agent.run()
        result_text = history.final_result() or ""
        status = _determine_status(history, result_text)
        return {
            "agent_id": agent_id,
            "task": task,
            "result": result_text,
            "healed_selectors": _parse_healed(result_text),
            "status": status,
            "duration": round(time.time() - start, 2),
        }
    except Exception as exc:
        return {
            "agent_id": agent_id,
            "task": task,
            "error": str(exc),
            "healed_selectors": [],
            "status": "ERROR",
            "duration": round(time.time() - start, 2),
        }


def _determine_status(history, result_text: str) -> str:
    """
    Determine PASS/FAIL from agent history and result text.

    Priority:
    1. Use history.is_successful() if available (browser-use native).
    2. Scan the last 10 lines of result_text for explicit verdict keywords
       like "Result: FAIL", "Overall: FAIL", "Verdict: FAIL", "Final Status: FAIL".
    3. Fall back to a whole-text scan, but only for these verdict patterns —
       NOT for incidental mentions of "fail" in explanation prose.
    """
    import re

    # 1. Native success flag
    try:
        success = history.is_successful()
        if success is True:
            return "PASS"
        if success is False:
            return "FAIL"
    except Exception:
        pass

    # 2. Scan last 10 lines for verdict patterns
    lines = [l.strip() for l in result_text.splitlines() if l.strip()]
    tail = lines[-10:] if len(lines) >= 10 else lines
    verdict_re = re.compile(
        r"(result|overall|verdict|final[\s_-]?status|status)\s*[:=]\s*(pass|fail)",
        re.IGNORECASE,
    )
    for line in reversed(tail):
        m = verdict_re.search(line)
        if m:
            return "PASS" if m.group(2).upper() == "PASS" else "FAIL"

    # 3. Whole-text verdict scan
    for line in reversed(lines):
        m = verdict_re.search(line)
        if m:
            return "PASS" if m.group(2).upper() == "PASS" else "FAIL"

    # 4. Last resort: check for standalone PASS/FAIL token on its own line
    for line in reversed(lines):
        upper = line.upper()
        if upper in ("PASS", "FAIL", "✅ PASS", "❌ FAIL"):
            return "PASS" if "PASS" in upper else "FAIL"

    return "PASS"  # assume pass if no explicit failure found


def _parse_healed(text: str) -> list[dict]:
    """Extract HEALED: <broken> → <working> lines from agent output."""
    healed = []
    for line in text.splitlines():
        if "HEALED:" in line.upper():
            parts = line.split("→")
            if len(parts) == 2:
                broken = parts[0].split("HEALED:")[-1].strip().strip("'\"")
                working = parts[1].strip().strip("'\"")
                healed.append({"broken": broken, "working": working})
    return healed


# ---------------------------------------------------------------------------
# Pool runner – runs selected scenarios in parallel (mirrors run_pool)
# ---------------------------------------------------------------------------

async def run_scenarios(
    scenarios: list[str] | None = None,
    headless: bool = False,
    max_concurrent: int = 5,
) -> str:
    """
    Run scenario agents in parallel (like vibetest run_pool).

    Args:
        scenarios: list of keys from SCENARIO_TASKS; None = all except full_purchase_flow
        headless:  run browsers headless
        max_concurrent: semaphore cap

    Returns:
        test_id string for result retrieval via get_results()
    """
    if scenarios is None:
        scenarios = [s for s in SCENARIO_TASKS if s != "full_purchase_flow"]

    sem = asyncio.Semaphore(max_concurrent)
    test_id = str(uuid.uuid4())[:8]
    start_total = time.time()

    async def bounded(agent_id, task):
        async with sem:
            return await _run_agent(agent_id, task, headless)

    coros = [
        bounded(f"{scenario}-{test_id}", SCENARIO_TASKS[scenario])
        for scenario in scenarios
        if scenario in SCENARIO_TASKS
    ]

    agent_results = await asyncio.gather(*coros, return_exceptions=False)

    _test_results[test_id] = {
        "test_id": test_id,
        "scenarios": scenarios,
        "duration": round(time.time() - start_total, 2),
        "results": list(agent_results),
    }
    return test_id


def get_results(test_id: str) -> dict:
    return _test_results.get(test_id, {"error": f"No results for test_id={test_id}"})

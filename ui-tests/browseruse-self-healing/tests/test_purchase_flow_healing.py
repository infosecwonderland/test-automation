"""
Self-healing test — full purchase flow with actual selector healing demo.

Two tests:

1. test_full_purchase_flow
   Browser-use agent completes the full login → search → cart → checkout →
   payment → confirmation journey and reports any selectors it had to heal.

2. test_self_healing_selector
   TRUE self-healing demonstration:
     a) Injects a broken selector (#broken-email-id) into the sample LoginPage.ts
     b) Calls heal_and_patch() — AI agent visits /login, finds the real element,
        returns a working CSS selector
     c) Verifies the .ts file is patched with the healed selector
     d) Restores the original file

   This is the core self-healing loop:
     Playwright breaks (bad selector)
       → heal_and_patch() launches browser-use agent
       → agent finds element visually
       → LoginPage.ts is rewritten with working selector
       → next Playwright run passes
"""
from pathlib import Path

import pytest

from agents import run_scenarios, get_results
from healer import heal_and_patch

_PAGES_DIR = Path(__file__).parent.parent / "pages"


@pytest.mark.asyncio
async def test_full_purchase_flow():
    """E2E flow: login → search → cart → checkout → payment → confirmation."""
    test_id = await run_scenarios(["full_purchase_flow"], headless=True)
    results = get_results(test_id)
    assert "results" in results, f"No results returned: {results}"

    flow_result = results["results"][0]

    healed = flow_result.get("healed_selectors", [])
    if healed:
        print(f"\n[full_flow] Healed {len(healed)} selector(s) during the run:")
        for h in healed:
            print(f"  broken={h['broken']}  →  working={h['working']}")
    else:
        print("\n[full_flow] No broken selectors were encountered.")

    assert flow_result["status"] == "PASS", (
        f"Full purchase flow failed.\nResult: {flow_result.get('result', '')}\n"
        f"Error: {flow_result.get('error', '')}"
    )


@pytest.mark.asyncio
async def test_self_healing_selector():
    """
    Demonstrates the self-healing loop:
      inject broken selector → AI heals it → .ts file is patched automatically.
    """
    ts_file = _PAGES_DIR / "LoginPage.ts"
    original = ts_file.read_text(encoding="utf-8")
    broken_selector = "#broken-password-id"

    # Step 1: Simulate a selector breaking (as if the SUT HTML changed)
    ts_file.write_text(original.replace("#password-id", broken_selector, 1), encoding="utf-8")
    print(f"\n[self-heal] Injected broken selector: {broken_selector} into LoginPage.ts")

    try:
        # Step 2: Run the healer — AI agent visits /login, finds the email input visually
        outcome = await heal_and_patch(
            page_name="login",
            page_path="/login",
            element_purpose="password input",
            broken_selector=broken_selector,
            headless=True,
        )

        print(f"[self-heal] Healed selector : {outcome['healed_selector']}")
        print(f"[self-heal] Confidence      : {outcome['confidence']}")
        print(f"[self-heal] Reason          : {outcome['reason']}")
        print(f"[self-heal] Patched file    : {outcome['patched_file']}")

        # Step 3: Assert healing worked
        assert outcome["healed_selector"], "Healer returned an empty selector"
        assert outcome["healed_selector"] != broken_selector, (
            "Healer returned the same broken selector — no healing occurred"
        )

        # Step 4: Assert the .ts file was actually patched
        assert outcome["patched_file"] is not None, (
            "patch_page_object returned None — LoginPage.ts was not patched"
        )
        assert "LoginPage.ts" in outcome["patched_file"]

        # Step 5: Confirm the broken selector is gone from the file
        patched_content = ts_file.read_text(encoding="utf-8")
        assert broken_selector not in patched_content, (
            "Broken selector still present in LoginPage.ts after healing"
        )
        assert outcome["healed_selector"] in patched_content, (
            "Healed selector not found in patched LoginPage.ts"
        )
        print("[self-heal] LoginPage.ts successfully patched — self-healing complete.")

    finally:
        # Restore original so the file is clean for the next run
        ts_file.write_text(original, encoding="utf-8")

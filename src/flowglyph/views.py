"""How capabilities are shown to people and agents: compact codes, advice and L0 cards.

These are read models over the IR. They change with the needs of a screen or a prompt, so they
live apart from the IR, whose meaning must not change with them.
"""

from typing import Any

from flowglyph.ir import Capability, Effects, Idempotency, Tri

_L0_DESCRIPTION_LIMIT = 120


def effects_code(effects: Effects) -> str:
    """Effects as letters: `R`ead, `W`rite, `D`estroy, e`X`ternal.

    Upper case means yes, lower case means it may (the sources do not say), and an absent
    letter means no, so `RwX` reads, may write and talks to another system. Pure capabilities
    give an empty string.
    """
    letters = (
        ("r", effects.reads),
        ("w", effects.mutates_state),
        ("d", effects.destructive),
        ("x", effects.external),
    )
    return "".join(
        letter.upper() if value is Tri.YES else letter
        for letter, value in letters
        if value is not Tri.NO
    )


def retry_advice(idempotency: Idempotency) -> str:
    """How to call a capability safely more than once, in one sentence."""
    if idempotency.mode == "natural":
        return "safe to retry"
    if idempotency.mode == "key":
        fields = ", ".join(idempotency.key_fields) or "a caller-supplied key"
        return f"safe to retry when deduplicated on {fields}"
    if idempotency.mode == "conditional":
        return "safe to retry only under documented conditions"
    return "not idempotent: run through the gateway with an idempotency key"


def l0_card(capability: Capability) -> dict[str, Any]:
    """The L0 representation: a few dozen bytes an agent can scan by the thousand."""
    summary = capability.description.split("\n", 1)[0][:_L0_DESCRIPTION_LIMIT]
    return {
        "id": capability.id,
        "d": summary or capability.title,
        "in": [parameter.name for parameter in capability.inputs],
        "out": [parameter.name for parameter in capability.outputs],
        "e": effects_code(capability.effects),
        "i": capability.idempotency.mode,
    }

import json
from collections.abc import Sequence
from typing import Any

SYSTEM_PROMPT = """\
You design automation workflows from business requirements.

You receive the requirements and a list of candidate capabilities from the company's catalog.
Each candidate has an id, a description, typed inputs, outputs, effects and an idempotency
mode. Effects use R for reads, W for writes, D for destructive, X for external systems; lower
case means the effect is possible but not certain.

Build the smallest plan that meets the requirements:
- Use only capability ids from the candidate list, copied exactly.
- When no candidate does what a step needs, keep the step with capability null and describe
  the missing behaviour in its intent. A missing capability is useful information; an invented
  one is a defect.
- Fill each step's arguments only with the inputs its capability declares, and cover every
  required input. Take values from workflow inputs, from outputs of earlier steps, or from
  literals written as JSON.
- Declare as workflow inputs the values the requirements say arrive at run time.
- Put business rules such as thresholds in the condition of the step they gate. A step whose
  condition is false is skipped, and so is every step that needs it. Set join to any on a step
  that must run whether or not an earlier conditional step ran, such as the step after an
  optional approval.
- List in assumptions anything the requirements leave open that you had to decide.
"""


def request_text(requirements: str, candidates: Sequence[dict[str, Any]]) -> str:
    """The user turn: candidate cards, one JSON object per line, then the requirements."""
    catalog = "\n".join(json.dumps(card, ensure_ascii=False) for card in candidates)
    return (
        f"<candidates>\n{catalog}\n</candidates>\n\n"
        f"<requirements>\n{requirements.strip()}\n</requirements>"
    )

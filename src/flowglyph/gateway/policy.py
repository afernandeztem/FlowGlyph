from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict

from flowglyph.ir import Capability

type Action = Literal["allow", "deny", "require_approval"]
type EffectName = Literal["reads", "mutates_state", "destructive", "external"]


class Rule(BaseModel):
    """One policy rule. The first rule whose conditions all hold decides."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    capabilities: str = "*"
    if_effects: tuple[EffectName, ...] = ()
    action: Action
    reason: str = ""


class Policy(BaseModel):
    """What the gateway is allowed to run, independent of what an agent asks for.

    Effects listed in `if_effects` match when they are possible, so an `unknown` effect is
    treated like a `yes`. A capability that declares `approval_required` always needs
    approval, whatever the rules say, unless a rule denies it outright.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    rules: tuple[Rule, ...] = ()
    default: Action = "allow"

    @classmethod
    def load(cls, path: str | Path) -> "Policy":
        """Read a policy from YAML."""
        document = cast("dict[str, Any] | None", yaml.safe_load(Path(path).read_text("utf-8")))
        return cls.model_validate(document or {})

    def decide(self, capability: Capability) -> "Decision":
        """The action to take for `capability`, and why."""
        rule = next((rule for rule in self.rules if _matches(rule, capability)), None)
        action = rule.action if rule else self.default
        reason = (rule.reason or f"rule for {rule.capabilities}") if rule else "default policy"
        if action == "allow" and capability.security.approval_required:
            return Decision("require_approval", "the capability requires approval")
        return Decision(action, reason)


@dataclass(frozen=True)
class Decision:
    """Outcome of evaluating a policy for one capability."""

    action: Action
    reason: str


def _matches(rule: Rule, capability: Capability) -> bool:
    if not fnmatchcase(capability.id, rule.capabilities):
        return False
    effects = capability.effects
    return all(getattr(effects, name).possible for name in rule.if_effects)


DEFAULT_POLICY = Policy(
    rules=(
        Rule(
            if_effects=("destructive",),
            action="require_approval",
            reason="may destroy data",
        ),
    ),
)

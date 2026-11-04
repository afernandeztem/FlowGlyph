from pathlib import Path

from flowglyph.gateway.policy import DEFAULT_POLICY, Policy, Rule
from flowglyph.ir import Capability, Effects, Security, Source, Tri

SOURCE = Source(provider="test", artifact="a", location="a", source_hash="sha256:0")


def capability(
    capability_id: str = "erp/invoice/create",
    destructive: Tri = Tri.NO,
    *,
    approval: bool = False,
) -> Capability:
    return Capability(
        id=capability_id,
        kind="operation",
        title="x",
        effects=Effects(
            reads=Tri.NO, mutates_state=Tri.YES, destructive=destructive, external=Tri.YES
        ),
        security=Security(approval_required=approval),
        source=SOURCE,
    )


def test_default_policy_holds_back_possibly_destructive_steps():
    assert DEFAULT_POLICY.decide(capability(destructive=Tri.YES)).action == "require_approval"
    assert DEFAULT_POLICY.decide(capability(destructive=Tri.UNKNOWN)).action == "require_approval"
    assert DEFAULT_POLICY.decide(capability(destructive=Tri.NO)).action == "allow"


def test_first_matching_rule_wins():
    policy = Policy(
        rules=(
            Rule(capabilities="erp/payment/*", action="deny", reason="payments are manual"),
            Rule(capabilities="erp/*", if_effects=("mutates_state",), action="require_approval"),
        ),
        default="allow",
    )
    denied = policy.decide(capability("erp/payment/execute"))
    assert (denied.action, denied.reason) == ("deny", "payments are manual")
    assert policy.decide(capability("erp/invoice/create")).action == "require_approval"
    assert policy.decide(capability("crm/contact/update")).action == "allow"


def test_declared_approval_cannot_be_bypassed_by_an_allow_rule():
    policy = Policy(rules=(Rule(action="allow"),))
    decision = policy.decide(capability(approval=True))
    assert decision.action == "require_approval"


def test_policy_loads_from_yaml(tmp_path: Path):
    path = tmp_path / "policy.yaml"
    path.write_text(
        "default: deny\n"
        "rules:\n"
        "  - {capabilities: 'openapi/*', if_effects: [reads], action: allow}\n"
    )
    policy = Policy.load(path)
    assert policy.default == "deny"
    assert policy.rules[0].if_effects == ("reads",)

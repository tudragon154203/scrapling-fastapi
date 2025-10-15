import types

from app.services.crawler.proxy.plan import AttemptPlanner


def build_settings(**overrides):
    defaults = {
        "max_retries": 4,
        "private_proxy_url": None,
        "proxy_rotation_mode": "sequential",
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def test_build_plan_balances_direct_public_and_private_slots():
    settings = build_settings(max_retries=4, private_proxy_url="http://user:pass@private:9000")
    planner = AttemptPlanner()

    plan = planner.build_plan(settings, ["http://public-1:8080", "http://public-2:8080"])

    assert plan == [
        {"mode": "direct", "proxy": None},
        {"mode": "public", "proxy": "http://public-1:8080"},
        {"mode": "private", "proxy": "http://user:pass@private:9000"},
        {"mode": "direct", "proxy": None},
    ]


def test_build_plan_uses_random_rotation_when_requested(monkeypatch):
    shuffled_sequences = []

    def fake_shuffle(sequence):
        shuffled_sequences.append(list(sequence))
        sequence[:] = list(reversed(sequence))

    monkeypatch.setattr("app.services.crawler.proxy.plan.random.shuffle", fake_shuffle)
    planner = AttemptPlanner()
    settings = build_settings(max_retries=5, proxy_rotation_mode="random")

    plan = planner.build_plan(settings, ["p1", "p2", "p3"])

    # shuffle should be invoked with the original proxy list and the plan should respect the shuffled order
    assert shuffled_sequences == [["p1", "p2", "p3"]]
    assert plan == [
        {"mode": "direct", "proxy": None},
        {"mode": "public", "proxy": "p3"},
        {"mode": "public", "proxy": "p2"},
        {"mode": "public", "proxy": "p1"},
        {"mode": "direct", "proxy": None},
    ]


def test_build_plan_falls_back_to_direct_when_public_pool_exhausted():
    planner = AttemptPlanner()
    settings = build_settings(max_retries=6)

    plan = planner.build_plan(settings, ["p1"])

    assert plan[0] == {"mode": "direct", "proxy": None}
    assert plan.count({"mode": "public", "proxy": "p1"}) == 2
    assert plan[-2:] == [
        {"mode": "direct", "proxy": None},
        {"mode": "direct", "proxy": None},
    ]
    assert len(plan) == settings.max_retries

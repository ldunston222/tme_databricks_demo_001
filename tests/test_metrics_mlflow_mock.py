import importlib
import sys
import types

import pytest


def test_metrics_tracker_raises_without_mlflow(monkeypatch):
    # Ensure a clean import of evaluator.metrics where mlflow is missing
    monkeypatch.setitem(sys.modules, "mlflow", None)

    from evaluator import metrics as metrics_mod

    importlib.reload(metrics_mod)

    with pytest.raises(RuntimeError):
        metrics_mod.MetricsTracker(experiment_name="x")


def test_metrics_tracker_uses_mlflow_when_available(monkeypatch):
    calls = {"set_experiment": [], "start_run": [], "set_tags": []}

    class DummyRunInfo:
        def __init__(self):
            self.run_id = "rid"

    class DummyRun:
        def __init__(self):
            self.info = DummyRunInfo()

    dummy_mlflow = types.SimpleNamespace(
        set_experiment=lambda name: calls["set_experiment"].append(name),
        start_run=lambda nested=True: calls["start_run"].append(nested) or DummyRun(),
        set_tags=lambda tags: calls["set_tags"].append(tags),
        end_run=lambda: None,
        log_metric=lambda *a, **k: None,
        log_param=lambda *a, **k: None,
        log_dict=lambda *a, **k: None,
    )

    monkeypatch.setitem(sys.modules, "mlflow", dummy_mlflow)

    from evaluator import metrics as metrics_mod

    importlib.reload(metrics_mod)

    mt = metrics_mod.MetricsTracker(experiment_name="exp")
    rid = mt.start_run("ep1")
    mt.end_run()

    assert calls["set_experiment"] == ["exp"]
    assert calls["start_run"] == [True]
    assert rid == "rid"
    assert calls["set_tags"][0]["episode_id"] == "ep1"

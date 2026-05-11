from operatekit import Observation, ObservationKind
from operatekit.plugins.storage.jsonl import JsonlObservationRepository


def test_wait_for_network_observation(tmp_path):
    repo = JsonlObservationRepository(tmp_path / "obs.jsonl")
    cursor = repo.cursor()
    repo.add(Observation.network(url="https://example.com/api/result", body={"ok": True}))
    obs = repo.wait_for("contains:/api/result", kind=ObservationKind.NETWORK, cursor=cursor, timeout=0.5)
    assert obs.json()["ok"] is True

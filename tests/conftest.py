import json
from pathlib import Path


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "golden"


def load_fixture(name: str):
    return json.loads((FIXTURE_ROOT / name).read_text())

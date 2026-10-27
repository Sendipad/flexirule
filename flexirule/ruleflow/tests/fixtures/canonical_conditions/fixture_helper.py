import json
import os

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))

def load_canonical_fixture(filename: str) -> dict:
    filepath = os.path.join(FIXTURES_DIR, filename)
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("LLM_STUB", "1")
os.environ.setdefault("LLM_ENABLED", "true")

from fastapi.testclient import TestClient
from app.main import app

cases = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))
client = TestClient(app)
correct = 0
failed = []

for case in cases:
    response = client.post("/triage", json={"text": case["text"]})
    ok = False
    if response.status_code == 200:
        result = response.json()
        ok = result["category"] == case["category"] and result["urgency"] == case["urgency"]
    if ok:
        correct += 1
    else:
        failed.append(case["id"])
    print(f"{case['id']}: {'PASS' if ok else 'FAIL'} -> {response.status_code} {response.json()}")

score = correct / len(cases) * 100
print(f"score={correct}/{len(cases)} ({score:.1f}%)")
print(f"failed={failed}")
print("mode=LLM_STUB=1; this is a deterministic endpoint-contract evaluation, not a live-provider score")

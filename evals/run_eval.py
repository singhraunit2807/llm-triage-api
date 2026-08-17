import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("LLM_STUB", "1")
os.environ.setdefault("LLM_ENABLED", "true")
from app.service import triage

cases = json.loads(Path(__file__).with_name("cases.json").read_text())
correct = 0
for case in cases:
    result = triage(case["text"])
    ok = result.category.value == case["category"] and result.urgency.value == case["urgency"]
    correct += ok
    print(f"{case['id']}: {'PASS' if ok else 'FAIL'} -> {result.model_dump()}")
print(f"score={correct}/{len(cases)} ({correct/len(cases)*100:.1f}%)")
print("mode=LLM_STUB=1; this is a deterministic contract/evaluation check, not a live-provider score")

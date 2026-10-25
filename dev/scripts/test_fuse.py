import sys
sys.path.insert(0, sys.argv[1])
from app import analysis, calibration

fake = {"generated_at": "x", "source": "test", "clips": 100, "targets": {"ta-zha": {
    # Sarvam: very reliable for ழ
    "transcript": {"correct": {"on_target": 18, "substitution": 1, "unclear": 1},
                   "mixup": {"on_target": 2, "substitution_right": 30, "substitution_other": 2, "unclear": 6}},
    # sound model: weak for ழ (often calls correct ழ a mix-up)
    "phonemes": {"correct": {"on_target": 6, "substitution": 12, "unclear": 2},
                 "mixup": {"on_target": 4, "substitution_right": 14, "substitution_other": 10, "unclear": 12}},
}}}
calibration.load = lambda: fake

on = {"verdict": "on_target", "heard_as": None}
sub = {"verdict": "substitution", "heard_as": "ள"}
print("precisions:", calibration.precision("ta-zha", "transcript", "on_target"), calibration.precision("ta-zha", "transcript", "substitution"),
      calibration.precision("ta-zha", "phonemes", "on_target"), calibration.precision("ta-zha", "phonemes", "substitution"))
for name, l, p in [("agree sub", sub, sub), ("agree ok", on, on), ("sarvam ok, model sub", on, sub), ("sarvam sub, model ok", sub, on),
                   ("sarvam only sub", sub, {"verdict": "unclear"}), ("model only sub", {"verdict": "unclear"}, sub)]:
    r = analysis.fuse_calibrated(l, p, "ok", "ta-zha")
    print(f"{name:22} -> {r['status']:18} {r['outcome']:12} {r['heard_as']} conf={r['confidence']} {r['agreement']}")
print("uncalibrated target ->", analysis.fuse_calibrated(sub, sub, "ok", "hi-sha"))

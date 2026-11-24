"""Audit the BodyVision cohort and write a reproducible capture manifest.

Pairing uses participant ID and subject distance. Rows with an unknown view,
missing images, conflicting labels, or duplicate view/distance keys are kept in
the audit report but never silently treated as a valid pair.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT / "model_specification" / "height_weight_dataset.csv"
IMAGE_DIR = PROJECT / "model_specification" / "images"
OUT_DIR = PROJECT / "paper" / "evaluation_results"


def audit(csv_path: Path = CSV_PATH, image_dir: Path = IMAGE_DIR):
    raw = csv_path.read_bytes()
    rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    groups = defaultdict(list)
    issues = []
    views = Counter()
    for line, row in enumerate(rows, start=2):
        pid = row.get("person_id", "").strip()
        view = row.get("view", "").strip().lower()
        views[view or "missing"] += 1
        if not pid:
            issues.append({"row": line, "reason": "missing_participant_id"})
            continue
        try:
            distance = f'{float(row["subject_distance_cm"]):g}'
        except (ValueError, KeyError):
            distance = "unknown"
            issues.append({"row": line, "participant_id": pid, "reason": "invalid_distance"})
        image_name = Path(row.get("image_path", "")).name
        present = bool(image_name and (image_dir / image_name).is_file())
        if not present:
            issues.append({"row": line, "participant_id": pid, "reason": "missing_image", "image": image_name})
        if view not in ("front", "side"):
            issues.append({"row": line, "participant_id": pid, "reason": "unknown_view", "view": view})
        row["_line"] = line
        row["_distance"] = distance
        row["_present"] = present
        groups[pid].append(row)

    pairs, unpaired, duplicate_keys = [], [], []
    for pid, participant_rows in sorted(groups.items()):
        keys = defaultdict(list)
        for row in participant_rows:
            if row["view"] in ("front", "side"):
                keys[(row["_distance"], row["view"])].append(row)
        distances = sorted({key[0] for key in keys})
        for distance in distances:
            fronts, sides = keys[(distance, "front")], keys[(distance, "side")]
            if len(fronts) > 1 or len(sides) > 1:
                duplicate_keys.append({"participant_id": pid, "distance_cm": distance,
                                       "front_rows": [r["_line"] for r in fronts],
                                       "side_rows": [r["_line"] for r in sides]})
                continue
            if len(fronts) == 1 and len(sides) == 1:
                f, s = fronts[0], sides[0]
                consistent = all(f.get(label) == s.get(label) for label in ("height_cm", "weight_kg"))
                if not consistent:
                    issues.append({"participant_id": pid, "distance_cm": distance, "reason": "paired_label_mismatch"})
                    continue
                pairs.append({"participant_id": pid, "distance_cm": distance,
                              "front_image": f["image_path"], "side_image": s["image_path"],
                              "height_cm": float(f["height_cm"]),
                              "weight_kg": float(f["weight_kg"]) if f.get("weight_kg") else None,
                              "images_present": bool(f["_present"] and s["_present"]),
                              "source_rows": [f["_line"], s["_line"]]})
            else:
                one = fronts or sides
                unpaired.extend({"participant_id": pid, "distance_cm": distance,
                                 "view": r["view"], "source_row": r["_line"]} for r in one)

    report = {
        "schema_version": "capture-manifest-v1",
        "source_csv_sha256": hashlib.sha256(raw).hexdigest(),
        "row_count": len(rows), "participant_count": len(groups),
        "view_counts": dict(views), "valid_pair_count": len(pairs),
        "paired_participant_count": len({p["participant_id"] for p in pairs}),
        "unpaired_capture_count": len(unpaired), "duplicate_pair_keys": duplicate_keys,
        "issues": issues, "pairs": pairs, "unpaired": unpaired,
        "cohort_limitations": ["single small cohort", "no independent external test cohort"],
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=CSV_PATH)
    parser.add_argument("--images", type=Path, default=IMAGE_DIR)
    parser.add_argument("--output", type=Path, default=OUT_DIR / "dataset_audit.json")
    args = parser.parse_args()
    report = audit(args.csv, args.images)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "row_count", "participant_count", "view_counts", "valid_pair_count",
        "paired_participant_count", "unpaired_capture_count")}, indent=2))


if __name__ == "__main__":
    main()

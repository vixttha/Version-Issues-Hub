"""Validate VIB archive inventory and deterministic bounded partitions."""
import re

LIMIT = 32
OPERATIONAL = {"v0.0.0.23"}

def feature_ids(selected):
    result = {v.replace(".", "-") for v in selected}
    if "v0.0.0.37" in selected:
        result.add("v0-0-0-37-review-recovery")
    return result

def scope(versions, selected, features):
    if not versions or any(not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", v) for v in versions):
        raise ValueError("Invalid checkpoint version")
    if len(versions) != len(set(versions)) or len(selected) != len(set(selected)):
        raise ValueError("Duplicate checkpoint version")
    ids = [f["id"] for f in features]
    omitted = set(versions) - set(selected)
    if omitted != (set(versions) & OPERATIONAL) or not set(selected) <= set(versions):
        raise ValueError("Unexpected receipt scope omission")
    if len(ids) != len(set(ids)) or set(ids) != feature_ids(selected):
        raise ValueError("Unexpected graph feature inventory")
    if not ids:
        raise ValueError("Empty graph feature inventory")
    return [features[i:i+LIMIT] for i in range(0, len(features), LIMIT)]

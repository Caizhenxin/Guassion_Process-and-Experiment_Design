import http.server
import json
import csv
import os
import sys
import math
import numpy as np
import statistics
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # 导航到项目根目录
RAW_DIR = PROJECT_ROOT / "2_Data" / "Real_Data" / "UnExtact" / "raw"
SPE_DIR = PROJECT_ROOT / "2_Data" / "Real_Data" / "SPE_Database"
HTML_FILE = SCRIPT_DIR / "visualization_app.html"

CONDITIONS = {
    1: {"P": 0, "T": 0.03, "W": 0.3, "label": "D1 | P0_T30_W300"},
    2: {"P": 0, "T": 0.03, "W": 0.6, "label": "D2 | P0_T30_W600"},
    3: {"P": 120, "T": 0.03, "W": 0.6, "label": "D3a | P120_T30_W600"},
    4: {"P": 120, "T": 0.08, "W": 0.6, "label": "D4a | P120_T80_W600"},
    5: {"P": 8, "T": 0.1, "W": 1.1, "label": "D5 | P8_T100_W1100"},
    6: {"P": 120, "T": 0.5, "W": 1.5, "label": "D6 | P120_T500_W1500"},
    7: {"P": 120, "T": 0.03, "W": 0.8, "label": "D3b | P120_T30_W800"},
    8: {"P": 120, "T": 0.08, "W": 0.8, "label": "D4b | P120_T80_W800"},
    # 9: {"P": 120, "T": 0.08, "W": 0.8, "label": "G9 | P120_T80_W800"},  # deprecated, merged into D4b
}


def get_pairing_rules(subject_id):
    mod_result = subject_id % 4
    rules = {
        0: {"square": {"self": "f", "stranger": "j"}, "circle": {"self": "j", "stranger": "f"}},
        1: {"square": {"self": "j", "stranger": "f"}, "circle": {"self": "f", "stranger": "j"}},
        2: {"square": {"self": "j", "stranger": "f"}, "circle": {"self": "f", "stranger": "j"}},
        3: {"square": {"self": "f", "stranger": "j"}, "circle": {"self": "j", "stranger": "f"}},
    }
    return rules[mod_result]


def get_match_key(subject_id):
    match_keys = ['f', 'j', 'j', 'f']
    index = (subject_id - 1) % 4
    return match_keys[index]


def get_correct_order(subject_id):
    if subject_id % 2 == 0:
        return {"square": "self", "circle": "stranger"}
    else:
        return {"square": "stranger", "circle": "self"}


def compute_condition(shape, label, subject_id):
    correct_order = get_correct_order(subject_id)
    expected_label = correct_order[shape]
    return "Matching" if label == expected_label else "NonMatching"


def compute_experiment_params(subject_id, group_id):
    match_key = get_match_key(subject_id)
    mismatch_key = 'j' if match_key == 'f' else 'f'
    correct_order = get_correct_order(subject_id)
    cond = CONDITIONS.get(group_id, {"P": None, "T": None, "W": None, "label": f"G{group_id}"})
    return {
        "subjectID": subject_id,
        "groupID": group_id,
        "matchKey": match_key,
        "mismatchKey": mismatch_key,
        "correctOrder": correct_order,
        "P": cond["P"],
        "T": cond["T"],
        "W": cond["W"],
        "groupLabel": cond["label"],
    }


def list_files():
    files = []
    for f in sorted(RAW_DIR.glob("EXP_data_group*.csv")):
        parts = f.stem.replace("EXP_data_group", "").split("_")
        group_id = int(parts[0])
        subject_id = int(parts[1])
        cond = CONDITIONS.get(group_id, {"P": None, "T": None, "W": None, "label": f"G{group_id}"})
        files.append({
            "name": f.name,
            "groupID": group_id,
            "subjectID": subject_id,
            "P": cond["P"],
            "T": cond["T"],
            "W": cond["W"],
            "groupLabel": cond["label"],
        })
    return {"files": files, "total": len(files)}


def load_file_data(filename):
    fpath = RAW_DIR / filename
    if not fpath.exists():
        return {"error": f"File {filename} not found"}
    rows = []
    stats = {"total": 0, "formal": 0, "practice": 0, "responses": 0, "correct": 0}
    group_id = None
    subject_id = None
    with open(fpath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if group_id is None:
                group_id = int(row['groupID'])
                subject_id = int(row['subjectID'])
            stage = row.get('stage', 'formal')
            stats["total"] += 1
            if stage == 'formal':
                stats["formal"] += 1
            else:
                stats["practice"] += 1

            rt_val = row.get('RT', 'NA')
            resp_val = row.get('Response', 'NA')
            has_resp = resp_val not in ['NA', 'nan', ''] and rt_val not in ['NA', 'nan', '']
            if has_resp and stage == 'formal':
                stats["responses"] += 1
                if int(float(row.get('Correct', 0))) == 1:
                    stats["correct"] += 1

            condition = compute_condition(
                str(row['Shape']).strip(),
                str(row['Label']).strip(),
                subject_id
            ) if subject_id else "Unknown"

            # 确定该被试的匹配键
            match_key = get_match_key(subject_id) if subject_id else 'f'
            # ResponseIsMatch: 被试的响应是否按了"匹配"键 (DDM上边界)
            response_is_match = resp_val.strip().lower() == match_key if has_resp else None

            try:
                rt = float(rt_val) if rt_val not in ['NA', 'nan', ''] else None
            except ValueError:
                rt = None
            try:
                corr = int(float(row['Correct'])) if row['Correct'] not in ['NA', 'nan', ''] else None
            except ValueError:
                corr = None

            rows.append({
                "groupID": int(row['groupID']),
                "subjectID": int(row['subjectID']),
                "stage": stage,
                "trialID": int(row['trialID']),
                "P": float(row['P']),
                "T": float(row['T']),
                "W": float(row['W']),
                "Shape": str(row['Shape']).strip(),
                "Label": str(row['Label']).strip(),
                "CorrectKey": str(row['CorrectKey']).strip(),
                "Response": resp_val,
                "RT": rt,
                "Correct": corr,
                "Condition": condition,
                "Identity": "Self" if str(row['Label']).strip() == 'self' else "Stranger",
                "MatchKey": match_key,
                "ResponseIsMatch": response_is_match,
            })

    omission_rate = (stats["formal"] - stats["responses"]) / stats["formal"] * 100 if stats["formal"] > 0 else 0
    accuracy = stats["correct"] / stats["responses"] * 100 if stats["responses"] > 0 else 0

    return {
        "filename": filename,
        "groupID": group_id,
        "subjectID": subject_id,
        "stats": {**stats, "omissionRate": round(omission_rate, 1), "accuracy": round(accuracy, 1)},
        "trials": rows,
    }


def load_all_data(group_filter=None):
    """Load all data, optionally filtered by group(s).
    group_filter: int (single group), list[int] (multiple), or None (all)."""
    all_trials = []
    summary = []
    for f in sorted(RAW_DIR.glob("EXP_data_group*.csv")):
        parts = f.stem.replace("EXP_data_group", "").split("_")
        gid = int(parts[0])
        if group_filter is not None:
            if isinstance(group_filter, (list, tuple, set)):
                if gid not in group_filter:
                    continue
            elif gid != group_filter:
                continue
        data = load_file_data(f.name)
        if "error" not in data:
            all_trials.extend(data["trials"])
            summary.append({
                "filename": f.name,
                "groupID": gid,
                "subjectID": int(parts[1]),
                **data["stats"],
            })
    return {"trials": all_trials, "summary": summary}


def verify_file_data(filename):
    """校验数据文件是否符合实验逻辑"""
    fpath = RAW_DIR / filename
    if not fpath.exists():
        return {"error": f"File {filename} not found"}

    errors = []
    group_id = None
    subject_id = None
    total_trials = 0
    total_formal = 0
    total_responses = 0
    total_correct = 0
    correct_key_errors = 0
    correct_column_errors = 0

    with open(fpath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if group_id is None:
                group_id = int(row['groupID'])
                subject_id = int(row['subjectID'])

            total_trials += 1
            stage = row.get('stage', 'formal')
            if stage == 'formal':
                total_formal += 1

            shape = str(row['Shape']).strip()
            label = str(row['Label']).strip()
            response = str(row['Response']).strip()
            data_correct_key = str(row['CorrectKey']).strip()
            trial_id = row['trialID']

            # 计算预期的 CorrectKey
            pairing = get_pairing_rules(subject_id)
            expected_correct_key = pairing[shape][label]

            if expected_correct_key != data_correct_key:
                correct_key_errors += 1
                errors.append({
                    "trialID": trial_id,
                    "shape": shape,
                    "label": label,
                    "type": "CorrectKey错误",
                    "expected": expected_correct_key,
                    "got": data_correct_key,
                    "response": response,
                    "detail": f"trialID={trial_id}: shape={shape}, label={label}, Expected CorrectKey={expected_correct_key}, Got={data_correct_key}"
                })

            # 计算预期的 Correct 值
            if response not in ['NA', 'nan', ''] and stage == 'formal':
                total_responses += 1
                expected_correct = 1 if response == expected_correct_key else 0
                try:
                    data_correct = int(float(row['Correct']))
                except (ValueError, KeyError):
                    data_correct = None

                if expected_correct != data_correct:
                    correct_column_errors += 1
                    errors.append({
                        "trialID": trial_id,
                        "shape": shape,
                        "label": label,
                        "type": "Correct列错误",
                        "expected": expected_correct,
                        "got": data_correct,
                        "response": response,
                        "detail": f"trialID={trial_id}: shape={shape}, label={label}, response={response}, Expected Correct={expected_correct}, Got={data_correct}"
                    })

                if data_correct == 1:
                    total_correct += 1

    cond = CONDITIONS.get(group_id, {"P": None, "T": None, "W": None, "label": f"G{group_id}"})
    match_key = get_match_key(subject_id)
    mismatch_key = 'j' if match_key == 'f' else 'f'
    correct_order = get_correct_order(subject_id)

    omission_rate = (total_formal - total_responses) / total_formal * 100 if total_formal > 0 else 0
    accuracy = total_correct / total_responses * 100 if total_responses > 0 else 0

    return {
        "filename": filename,
        "passed": len(errors) == 0,
        "totalErrors": len(errors),
        "correctKeyErrors": correct_key_errors,
        "correctColumnErrors": correct_column_errors,
        "subjectID": subject_id,
        "groupID": group_id,
        "stats": {
            "total": total_trials,
            "formal": total_formal,
            "responses": total_responses,
            "correct": total_correct,
            "omissionRate": round(omission_rate, 1),
            "accuracy": round(accuracy, 1),
        },
        "experimentParams": {
            "P": cond["P"],
            "T": cond["T"],
            "W": cond["W"],
            "matchKey": match_key,
            "mismatchKey": mismatch_key,
            "correctOrder": f"square↔{correct_order['square']}, circle↔{correct_order['circle']}",
        },
        "errors": errors[:200],  # 最多返回200条错误
        "errorCount": len(errors),
    }


def simulate_trial(subject_id, shape, label):
    pairing = get_pairing_rules(subject_id)
    correct_key = pairing[shape][label]
    condition = compute_condition(shape, label, subject_id)
    match_key = get_match_key(subject_id)
    return {
        "subjectID": subject_id,
        "shape": shape,
        "label": label,
        "correctKey": correct_key,
        "condition": condition,
        "matchKey": match_key,
        "mismatchKey": 'j' if match_key == 'f' else 'f',
        "expectedResponse": f"{'匹配' if condition == 'Matching' else '不匹配'}: 按 {correct_key.upper()} 键",
    }

# ===== SPE Database Functions =====

def cohens_d(group1, group2):
    """Compute Cohen's d for two independent groups."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0
    m1, m2 = statistics.mean(group1), statistics.mean(group2)
    v1, v2 = statistics.variance(group1), statistics.variance(group2)
    pooled_sd = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    if pooled_sd == 0:
        return 0.0
    return (m1 - m2) / pooled_sd


def _compute_subject_spe(rows, identity_col, rt_col, acc_col, condition_filter="all"):
    """Compute per-subject SPE from trial rows with optional Matching/NonMatching filter.

    Now supports ALL identity types (Self, Stranger, Close, Friend, Other, NonPerson, You, etc.),
    computing SPE as: (comparison_identity - Self) for RT, (Self - comparison_identity) for ACC.

    Args:
        rows: list of csv dict rows
        identity_col: column name for identity
        rt_col: column name for RT
        acc_col: column name for ACC (can be None)
        condition_filter: "all", "Matching", or "NonMatching"

    Returns:
        dict with:
          - identity_types: list of all unique identity values found
          - per_identity: {identity: {rts: [...], accs: [...], n_subjects: int, n_subjects_with_enough: int}}
          - comparisons: {identity: {spe_rt_d: [...], spe_acc_d: [...], n_valid: int, ...}}
          - legacy: backward-compatible self/stranger dict
    """
    from collections import defaultdict
    # Discover all identity types
    all_identities = set()
    has_matching_col = "Matching" in rows[0] if rows else False

    # First pass: discover all identity values
    for r in rows:
        identity = r.get(identity_col, "").strip()
        if not identity or identity.upper() == "NA":
            continue
        # apply condition filter for discovery
        if condition_filter != "all" and has_matching_col:
            trial_cond = r.get("Matching", "").strip()
            if trial_cond.lower() != condition_filter.lower():
                continue
        if identity:
            all_identities.add(identity)

    identity_types = sorted(all_identities)

    # Per-identity per-subject RT and ACC data
    subj_rt = defaultdict(lambda: defaultdict(list))
    subj_acc = defaultdict(lambda: defaultdict(list))
    identity_n_subjects = defaultdict(set)

    for r in rows:
        sid = r.get("Subject", "")
        identity = r.get(identity_col, "").strip()
        if not identity or identity.upper() == "NA":
            continue

        # Optional Matching/NonMatching filtering
        if condition_filter != "all" and has_matching_col:
            trial_cond = r.get("Matching", "").strip()
            if trial_cond.lower() != condition_filter.lower():
                continue

        try:
            rt_val = float(r.get(rt_col, ""))
        except (ValueError, TypeError):
            continue

        subj_rt[sid][identity].append(rt_val)
        identity_n_subjects[identity].add(sid)

        if acc_col:
            try:
                subj_acc[sid][identity].append(int(float(r.get(acc_col, 0))))
            except (ValueError, TypeError):
                pass

    # Build per-identity aggregate data
    per_identity = {}
    for ident in identity_types:
        rts_all = []
        accs_all = []
        for sid in subj_rt:
            if ident in subj_rt[sid]:
                rts_all.extend(subj_rt[sid][ident])
            if ident in subj_acc[sid]:
                accs_all.extend(subj_acc[sid][ident])

        n_subs_with_data = sum(1 for sid in subj_rt if ident in subj_rt[sid] and len(subj_rt[sid][ident]) >= 3)
        per_identity[ident] = {
            "rts": rts_all,
            "accs": accs_all,
            "n_subjects": len(identity_n_subjects.get(ident, set())),
            "n_subjects_with_enough": n_subs_with_data,
            "mean_rt": round(statistics.mean(rts_all), 1) if rts_all else None,
            "mean_acc": round(statistics.mean(accs_all), 4) if accs_all else None,
            "sd_rt": round(statistics.stdev(rts_all), 1) if len(rts_all) >= 2 else None,
            "sd_acc": round(statistics.stdev(accs_all), 4) if len(accs_all) >= 2 else None,
        }

    # Compute Self vs each other identity (SPE)
    comparisons = {}
    if "Self" in identity_types:
        self_present = True
    else:
        self_present = False
        # Try to find the closest to "Self" (case-insensitive)
        for it in identity_types:
            if it.lower() == "self":
                self_present = it
                break

    if self_present:
        self_key = self_present if isinstance(self_present, str) else "Self"
        for other_ident in identity_types:
            if other_ident == self_key:
                continue
            comp_d_vals = []
            comp_acc_d_vals = []
            for sid in subj_rt:
                self_rts = subj_rt[sid].get(self_key, [])
                other_rts = subj_rt[sid].get(other_ident, [])
                if len(self_rts) >= 3 and len(other_rts) >= 3:
                    d_rt = cohens_d(other_rts, self_rts)  # Other - Self
                    comp_d_vals.append(d_rt)

                self_ac = subj_acc[sid].get(self_key, [])
                other_ac = subj_acc[sid].get(other_ident, [])
                if len(self_ac) >= 3 and len(other_ac) >= 3:
                    try:
                        d_acc = cohens_d(self_ac, other_ac)  # Self - Other
                        comp_acc_d_vals.append(d_acc)
                    except:
                        pass

            comparisons[other_ident] = {
                "spe_rt_d": round(statistics.mean(comp_d_vals), 4) if comp_d_vals else None,
                "spe_rt_se": round(statistics.stdev(comp_d_vals) / math.sqrt(len(comp_d_vals)), 4) if len(comp_d_vals) >= 2 else None,
                "spe_acc_d": round(statistics.mean(comp_acc_d_vals), 4) if comp_acc_d_vals else None,
                "spe_acc_se": round(statistics.stdev(comp_acc_d_vals) / math.sqrt(len(comp_acc_d_vals)), 4) if len(comp_acc_d_vals) >= 2 else None,
                "n_valid_subjects": len(comp_d_vals),
            }

    # Legacy backward-compatible fields (Self vs Stranger, or Self vs first non-Self)
    legacy = {}
    if self_present:
        legacy["self_rts_all"] = per_identity.get(self_key, {}).get("rts", [])
        primary_other = "Stranger" if "Stranger" in comparisons else (list(comparisons.keys())[0] if comparisons else None)
        if primary_other:
            legacy["d_vals"] = [d for d in [comparisons[primary_other]["spe_rt_d"]] if d is not None]
            legacy["acc_d_vals"] = [d for d in [comparisons[primary_other]["spe_acc_d"]] if d is not None]
            legacy["stranger_rts_all"] = per_identity.get(primary_other, {}).get("rts", [])
            legacy["stranger_accs_all"] = per_identity.get(primary_other, {}).get("accs", [])
            legacy["self_accs_all"] = per_identity.get(self_key, {}).get("accs", [])
            legacy["n_subjects_valid"] = comparisons[primary_other].get("n_valid_subjects", 0)
        else:
            legacy["d_vals"] = []
            legacy["acc_d_vals"] = []
            legacy["stranger_rts_all"] = []
            legacy["stranger_accs_all"] = []
            legacy["self_accs_all"] = []
            legacy["n_subjects_valid"] = 0
    else:
        legacy["d_vals"] = []
        legacy["acc_d_vals"] = []
        legacy["self_rts_all"] = []
        legacy["stranger_rts_all"] = []
        legacy["self_accs_all"] = []
        legacy["stranger_accs_all"] = []
        legacy["n_subjects_valid"] = 0

    return {
        "identity_types": identity_types,
        "per_identity": per_identity,
        "comparisons": comparisons,
        "primary_comparison": "Stranger" if "Stranger" in comparisons else (list(comparisons.keys())[0] if comparisons else None),
        "legacy": legacy,
        "n_subjects": len(subj_rt),
    }


def _select_identity_column(headers, prefer="label"):
    """Select the Standardized identity column based on user preference.

    Args:
        headers: list of column name strings (or dict keys)
        prefer: 'label' -> Label_Standardized_Identity, 'shape' -> Shape_Standardized_Identity

    Returns:
        str: best available identity column name, or None
    """
    if prefer == 'label':
        # Prefer Label_Standardized_Identity, fallback to Shape_Standardized_Identity
        if "Label_Standardized_Identity" in headers:
            return "Label_Standardized_Identity"
        if "Shape_Standardized_Identity" in headers:
            return "Shape_Standardized_Identity"
        return None
    else:
        # Prefer Shape_Standardized_Identity, fallback to Label_Standardized_Identity
        if "Shape_Standardized_Identity" in headers:
            return "Shape_Standardized_Identity"
        if "Label_Standardized_Identity" in headers:
            return "Label_Standardized_Identity"
        return None


def load_spe_overview(condition_filter="all", identity_source="label"):
    """Load all SPE experiment metadata and compute group-level SPE effect sizes."""
    # Normalize condition_filter
    if not condition_filter or condition_filter not in ("all", "Matching", "NonMatching"):
        condition_filter = "all"
    log_file = SPE_DIR / "processing_log.csv"
    experiments = []
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                exp = {
                    "pairKey": row.get("Pair_Key", ""),
                    "outputFile": row.get("Output_File", ""),
                    "outputRows": int(row.get("Output_Rows", 0) or 0),
                    "P_raw": row.get("P_Raw", ""),
                    "P_parsed_ms": row.get("P_Parsed_ms", ""),
                    "P_status": row.get("P_Status", ""),
                    "T_raw": row.get("T_Raw", ""),
                    "T_parsed_ms": row.get("T_Parsed_ms", ""),
                    "T_status": row.get("T_Status", ""),
                    "W_raw": row.get("W_Raw", ""),
                    "W_parsed_ms": row.get("W_Parsed_ms", ""),
                    "W_status": row.get("W_Status", ""),
                    "note": row.get("Note", ""),
                }
                # Parse numeric P/T/W
                try:
                    exp["P_ms"] = float(exp["P_parsed_ms"]) if exp["P_parsed_ms"] else None
                except (ValueError, TypeError):
                    exp["P_ms"] = None
                try:
                    exp["T_ms"] = float(exp["T_parsed_ms"]) if exp["T_parsed_ms"] else None
                except (ValueError, TypeError):
                    exp["T_ms"] = None
                try:
                    exp["W_ms"] = float(exp["W_parsed_ms"]) if exp["W_parsed_ms"] else None
                except (ValueError, TypeError):
                    exp["W_ms"] = None
                experiments.append(exp)

    if not experiments:
        return {"experiments": [], "count": 0}

    # Compute SPE effect sizes from raw data
    for exp in experiments:
        output_file = exp.get("outputFile", "")
        if output_file:
            sp_file = SPE_DIR / Path(output_file).name
        else:
            sp_file = None
        if not sp_file or not sp_file.exists():
            exp["spe_rt_d"] = None
            exp["spe_acc_d"] = None
            exp["n_subjects"] = 0
            exp["self_mean_rt"] = None
            exp["stranger_mean_rt"] = None
            exp["self_acc"] = None
            exp["stranger_acc"] = None
            continue

        try:
            rows = []
            with open(sp_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append(r)

            # Detect column names — ONLY use Standardized columns
            headers = list(rows[0].keys()) if rows else []
            identity_col = _select_identity_column(headers, identity_source)
            rt_col = None
            acc_col = None

            for col in headers:
                if col in ("RT_ms", "RT_sec"):
                    if rt_col is None or col == "RT_ms":
                        rt_col = col
                if col == "ACC":
                    acc_col = col

            if not identity_col or not rt_col:
                exp["spe_rt_d"] = None
                exp["spe_acc_d"] = None
                exp["n_subjects"] = 0
                exp["_no_identity_col"] = True
                continue

            # Compute SPE for all conditions + matching + nonmatching
            result = _compute_subject_spe(rows, identity_col, rt_col, acc_col, condition_filter)

            # Identity diversity info
            exp["identity_types"] = result["identity_types"]
            exp["identity_comparisons"] = result["comparisons"]
            exp["primary_comparison"] = result["primary_comparison"]

            # Legacy backward-compatible fields
            l = result["legacy"]
            exp["n_subjects"] = result["n_subjects"]
            exp["spe_rt_d"] = round(statistics.mean(l["d_vals"]), 4) if l["d_vals"] else None
            exp["spe_rt_se"] = round(statistics.stdev(l["d_vals"]) / math.sqrt(len(l["d_vals"])), 4) if len(l["d_vals"]) >= 2 else None
            exp["spe_acc_d"] = round(statistics.mean(l["acc_d_vals"]), 4) if l["acc_d_vals"] else None
            exp["spe_acc_se"] = round(statistics.stdev(l["acc_d_vals"]) / math.sqrt(len(l["acc_d_vals"])), 4) if len(l["acc_d_vals"]) >= 2 else None
            exp["self_mean_rt"] = round(statistics.mean(l["self_rts_all"]), 1) if l["self_rts_all"] else None
            exp["stranger_mean_rt"] = round(statistics.mean(l["stranger_rts_all"]), 1) if l["stranger_rts_all"] else None
            exp["self_acc"] = round(statistics.mean(l["self_accs_all"]), 4) if l["self_accs_all"] else None
            exp["stranger_acc"] = round(statistics.mean(l["stranger_accs_all"]), 4) if l["stranger_accs_all"] else None
            exp["n_subjects_valid"] = l["n_subjects_valid"]

            # Always compute Matching-only and NonMatching-only SPE for frontend toggle
            try:
                result_m = _compute_subject_spe(rows, identity_col, rt_col, acc_col, "Matching")
                result_nm = _compute_subject_spe(rows, identity_col, rt_col, acc_col, "NonMatching")
                lm = result_m["legacy"]
                lnm = result_nm["legacy"]
                exp["spe_rt_d_matching"] = round(statistics.mean(lm["d_vals"]), 4) if lm["d_vals"] else None
                exp["spe_acc_d_matching"] = round(statistics.mean(lm["acc_d_vals"]), 4) if lm["acc_d_vals"] else None
                exp["spe_rt_d_nonmatch"] = round(statistics.mean(lnm["d_vals"]), 4) if lnm["d_vals"] else None
                exp["spe_acc_d_nonmatch"] = round(statistics.mean(lnm["acc_d_vals"]), 4) if lnm["acc_d_vals"] else None
                exp["n_valid_matching"] = lm["n_subjects_valid"]
                exp["n_valid_nonmatch"] = lnm["n_subjects_valid"]
            except Exception as e:
                exp["spe_rt_d_matching"] = None
                exp["spe_acc_d_matching"] = None
                exp["spe_rt_d_nonmatch"] = None
                exp["spe_acc_d_nonmatch"] = None

        except Exception as e:
            exp["spe_rt_d"] = None
            exp["spe_acc_d"] = None
            exp["n_subjects"] = 0
            exp["_error"] = str(e)

    return {"experiments": experiments, "count": len(experiments), "identity_source": identity_source}


def load_spe_experiment_detail(pair_key, condition_filter="all", identity_source="label"):
    """Load full detail for one SPE experiment including per-subject SPE."""
    if not pair_key:
        return {"error": "Missing pairKey parameter"}

    log_file = SPE_DIR / "processing_log.csv"
    output_file = None
    exp_meta = {}
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                if row.get("Pair_Key") == pair_key:
                    output_file = row.get("Output_File", "")
                    exp_meta = {
                        "pairKey": pair_key,
                        "P_raw": row.get("P_Raw", ""),
                        "P_parsed_ms": row.get("P_Parsed_ms", ""),
                        "T_raw": row.get("T_Raw", ""),
                        "T_parsed_ms": row.get("T_Parsed_ms", ""),
                        "W_raw": row.get("W_Raw", ""),
                        "W_parsed_ms": row.get("W_Parsed_ms", ""),
                    }
                    break

    if not output_file:
        return {"error": f"Experiment {pair_key} not found in processing log"}

    sp_file = SPE_DIR / Path(output_file).name
    if not sp_file.exists():
        return {"error": f"Data file {output_file} not found at {sp_file}"}

    try:
        rows = []
        with open(sp_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        from collections import defaultdict

        # ONLY use Standardized columns
        headers = list(rows[0].keys()) if rows else []
        identity_col = _select_identity_column(headers, identity_source)
        rt_col = None
        acc_col = None

        for col in headers:
            if col in ("RT_ms", "RT_sec"):
                if rt_col is None or col == "RT_ms":
                    rt_col = col
            if col == "ACC":
                acc_col = col

        if not identity_col or not rt_col:
            return {"error": "Cannot determine identity or RT column"}

        # Use helper function to compute SPE with condition filter
        result = _compute_subject_spe(rows, identity_col, rt_col, acc_col, condition_filter)

        # Per-subject breakdown for all identity types
        has_matching_col = "Matching" in rows[0] if rows else False
        subj_data2 = defaultdict(lambda: defaultdict(list))
        subj_acc2 = defaultdict(lambda: defaultdict(list))
        for r in rows:
            sid = r.get("Subject", "")
            identity = r.get(identity_col, "").strip()
            if not identity or identity.upper() == "NA":
                continue
            if condition_filter != "all" and has_matching_col:
                trial_cond = r.get("Matching", "").strip()
                if trial_cond.lower() != condition_filter.lower():
                    continue
            try:
                rt_val = float(r.get(rt_col, ""))
            except (ValueError, TypeError):
                continue
            subj_data2[sid][identity].append(rt_val)
            if acc_col:
                try:
                    subj_acc2[sid][identity].append(int(float(r.get(acc_col, 0))))
                except (ValueError, TypeError):
                    pass

        # Build per-subject SPE with all available identity comparisons
        self_key = "Self"
        primary_other = result["primary_comparison"]
        subjects = []
        for sid in sorted(subj_data2.keys(), key=lambda x: (x.isdigit(), x)):
            sid_data = subj_data2[sid]
            sid_acc = subj_acc2[sid]
            # Per-identity RT/ACC
            identity_stats = {}
            for ident in sid_data:
                rts = sid_data[ident]
                acs = sid_acc.get(ident, [])
                identity_stats[ident] = {
                    "n": len(rts),
                    "mean_rt": round(statistics.mean(rts), 1) if rts else None,
                    "sd_rt": round(statistics.stdev(rts), 1) if len(rts) >= 2 else None,
                    "mean_acc": round(statistics.mean(acs), 4) if acs else None,
                }
            # SPE for primary comparison
            self_rts = sid_data.get(self_key, [])
            other_rts = sid_data.get(primary_other, []) if primary_other else []
            self_ac = sid_acc.get(self_key, [])
            other_ac = sid_acc.get(primary_other, []) if primary_other else []
            d_rt = cohens_d(other_rts, self_rts) if len(self_rts) >= 3 and len(other_rts) >= 3 else None
            d_acc = cohens_d(self_ac, other_ac) if len(self_ac) >= 3 and len(other_ac) >= 3 else None

            # SPE for all other identity comparisons
            all_spe = {}
            for other_ident in sid_data:
                if other_ident == self_key:
                    continue
                o_rts = sid_data[other_ident]
                o_ac = sid_acc.get(other_ident, [])
                spe_rt = cohens_d(o_rts, self_rts) if len(self_rts) >= 3 and len(o_rts) >= 3 else None
                spe_acc = cohens_d(self_ac, o_ac) if len(self_ac) >= 3 and len(o_ac) >= 3 else None
                all_spe[other_ident] = {"spe_rt_d": round(spe_rt, 4) if spe_rt is not None else None,
                                          "spe_acc_d": round(spe_acc, 4) if spe_acc is not None else None}

            subjects.append({
                "subjectID": sid,
                "identity_stats": identity_stats,
                "self_mean_rt": identity_stats.get(self_key, {}).get("mean_rt"),
                primary_other + "_mean_rt": identity_stats.get(primary_other, {}).get("mean_rt") if primary_other else None,
                "spe_rt_d": round(d_rt, 4) if d_rt is not None else None,
                "spe_acc_d": round(d_acc, 4) if d_acc is not None else None,
                "all_spe": all_spe,
            })

        subjects.sort(key=lambda s: s["spe_rt_d"] if s["spe_rt_d"] is not None else -999, reverse=True)

        # Legacy overall fields
        l = result["legacy"]
        return {
            "pairKey": pair_key,
            "meta": exp_meta,
            "n_subjects": len(subjects),
            "n_total_trials": len(rows),
            "identity_source": identity_source,
            "identity_col_used": identity_col,
            "identity_types": result["identity_types"],
            "identity_comparisons": result["comparisons"],
            "primary_comparison": result["primary_comparison"],
            "overall_spe_rt_d": round(statistics.mean(l["d_vals"]), 4) if l["d_vals"] else None,
            "overall_self_mean_rt": round(statistics.mean(l["self_rts_all"]), 1) if l["self_rts_all"] else None,
            "overall_stranger_mean_rt": round(statistics.mean(l["stranger_rts_all"]), 1) if l["stranger_rts_all"] else None,
            "overall_self_acc": round(statistics.mean(l["self_accs_all"]), 4) if l["self_accs_all"] else None,
            "overall_stranger_acc": round(statistics.mean(l["stranger_accs_all"]), 4) if l["stranger_accs_all"] else None,
            "subjects": subjects,
        }

    except Exception as e:
        return {"error": str(e)}


def load_spe_trials(pair_key, identity_source="label"):
    """Return raw trial rows for CRF analysis from SPE CSV."""
    if not pair_key:
        return {"error": "Missing pairKey parameter"}

    log_file = SPE_DIR / "processing_log.csv"
    output_file = None
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                if row.get("Pair_Key") == pair_key:
                    output_file = row.get("Output_File", "")
                    break

    if not output_file:
        return {"error": f"Experiment {pair_key} not found"}

    sp_file = SPE_DIR / Path(output_file).name
    if not sp_file.exists():
        return {"error": f"Data file not found: {sp_file}"}

    try:
        rows = []
        with open(sp_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        if not rows:
            return {"trials": [], "n_total": 0, "identity_source": identity_source}

        # ONLY use Standardized columns
        headers = list(rows[0].keys())
        identity_col = _select_identity_column(headers, identity_source)
        rt_col = None
        for col in headers:
            if col in ("RT_ms", "RT_sec"):
                if rt_col is None or col == "RT_ms":
                    rt_col = col

        if not identity_col or not rt_col:
            return {"error": "Cannot determine identity or RT column"}

        # Extract lightweight trial records
        trials = []
        has_matching = "Matching" in rows[0]
        has_acc = "ACC" in rows[0]
        for r in rows:
            try:
                rt_val = float(r.get(rt_col, ""))
            except (ValueError, TypeError):
                continue  # skip trials without valid RT
            if rt_val <= 0:
                continue

            trial = {
                "Subject": r.get("Subject", ""),
                "RT_ms": round(rt_val, 1),
                "Identity": r.get(identity_col, ""),
            }
            if has_matching:
                trial["Matching"] = r.get("Matching", "")
            if has_acc:
                try:
                    trial["ACC"] = int(float(r.get("ACC", 0)))
                except (ValueError, TypeError):
                    trial["ACC"] = 0

            trials.append(trial)

        return {"trials": trials, "n_total": len(trials), "identity_source": identity_source, "identity_col_used": identity_col}

    except Exception as e:
        return {"error": str(e)}


def load_identity_summary(identity_source="label"):
    """Aggregate identity type statistics across all SPE experiments.
    Returns: list of unique identity types with experiment counts and descriptive stats.
    """
    from collections import defaultdict
    overview = load_spe_overview(identity_source=identity_source)
    identity_map = defaultdict(lambda: {"count": 0, "experiments": [], "total_subjects": 0})

    for exp in overview.get("experiments", []):
        identities = exp.get("identity_types", [])
        for ident in identities:
            identity_map[ident]["count"] += 1
            identity_map[ident]["experiments"].append(exp["pairKey"])
            identity_map[ident]["total_subjects"] += exp.get("n_subjects", 0)

    result = []
    for ident, data in sorted(identity_map.items(), key=lambda x: -x[1]["count"]):
        result.append({
            "identity": ident,
            "n_experiments": data["count"],
            "n_subjects_total": data["total_subjects"],
            "experiments": data["experiments"][:10],  # first 10
            "n_experiments_full": len(data["experiments"]),
        })

    return {"identity_summary": result, "total_experiments": overview.get("count", 0)}


def run_self_check():
    """数据自查: 检查原始数据中的RT是否超过 T+W 理论最大值, T/W参数一致性等"""
    from collections import defaultdict
    import hashlib

    report = {
        "design": {},
        "groups": {},
        "summary": {"totalFiles": 0, "totalFormalTrials": 0, "totalOverMax": 0, "criticalIssues": [], "warnings": []}
    }

    # 实验设计参数
    for gid, cond in CONDITIONS.items():
        report["design"][str(gid)] = {
            "P": cond["P"], "T": cond["T"], "W": cond["W"],
            "maxRtExpected": round(cond["T"] + cond["W"], 4),
            "label": cond["label"]
        }

    # 扫描所有数据文件
    raw_files = list(RAW_DIR.glob("EXP_data_group*.csv"))
    report["summary"]["totalFiles"] = len(raw_files)

    # 按组组织
    groups_data = defaultdict(list)
    for fp in raw_files:
        parts = fp.stem.replace("EXP_data_group", "").split("_")
        gid = int(parts[0])
        groups_data[gid].append(fp)

    file_hashes = {}  # 用于检测数据重复

    for gid in sorted(groups_data.keys()):
        design = CONDITIONS.get(gid, {"P": None, "T": None, "W": None, "label": f"G{gid}"})
        max_rt_expected = round(design["T"] + design["W"], 4)

        group_report = {
            "designT": design["T"], "designW": design["W"],
            "maxRtExpected": max_rt_expected,
            "label": design["label"],
            "actualT": None, "actualW": None, "tWMatch": None,
            "nFiles": len(groups_data[gid]),
            "nFormalTrials": 0, "nPracticeTrials": 0,
            "nOverMax": 0, "overMaxPct": 0,
            "maxRt": 0, "maxOverBy": 0,
            "overMaxDetails": [],
            "tWMismatches": [],
            "issues": [],
        }

        for fp in groups_data[gid]:
            try:
                raw = fp.read_bytes()
                fhash = hashlib.md5(raw).hexdigest()
                fname = fp.name
            except Exception:
                fhash = None
                fname = fp.name

            if fhash:
                if fhash in file_hashes:
                    group_report["issues"].append(f"数据重复: {fname} 与 {file_hashes[fhash]} 内容完全相同")
                else:
                    file_hashes[fhash] = fname

            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        stage = row.get('stage', 'formal')
                        rt_str = row.get('RT', '')
                        t_val = float(row.get('T', 0))
                        w_val = float(row.get('W', 0))

                        # 记录实际 T/W
                        if group_report["actualT"] is None:
                            group_report["actualT"] = t_val
                            group_report["actualW"] = w_val
                            group_report["tWMatch"] = (t_val == design["T"] and w_val == design["W"])
                        elif t_val != group_report["actualT"] or w_val != group_report["actualW"]:
                            group_report["tWMismatches"].append({
                                "file": fname, "trialID": row.get("trialID", "?"),
                                "expectedT": design["T"], "expectedW": design["W"],
                                "actualT": t_val, "actualW": w_val
                            })

                        if stage == 'formal':
                            group_report["nFormalTrials"] += 1
                        else:
                            group_report["nPracticeTrials"] += 1

                        # 检查 RT 是否超过 T+W
                        if rt_str and rt_str not in ['NA', 'nan', '']:
                            try:
                                rt = float(rt_str)
                                actual_max = t_val + w_val
                                if rt > actual_max:
                                    group_report["nOverMax"] += 1
                                    group_report["maxRt"] = max(group_report["maxRt"], rt)
                                    over_by = round(rt - actual_max, 5)
                                    group_report["maxOverBy"] = max(group_report["maxOverBy"], over_by)
                                    if len(group_report["overMaxDetails"]) < 50:
                                        group_report["overMaxDetails"].append({
                                            "file": fname, "trialID": row.get("trialID", "?"),
                                            "stage": stage, "RT": rt,
                                            "actualT": t_val, "actualW": w_val,
                                            "maxExpected": round(actual_max, 4),
                                            "overBy": over_by
                                        })
                            except (ValueError, TypeError):
                                pass

            except Exception as e:
                group_report["issues"].append(f"读取文件失败 {fname}: {str(e)}")

        # 计算超限率
        if group_report["nFormalTrials"] > 0:
            group_report["overMaxPct"] = round(group_report["nOverMax"] / group_report["nFormalTrials"] * 100, 2)

        report["summary"]["totalFormalTrials"] += group_report["nFormalTrials"]
        report["summary"]["totalOverMax"] += group_report["nOverMax"]

        # 严重问题检测
        if not group_report["tWMatch"] and group_report["tWMatch"] is not None:
            report["summary"]["criticalIssues"].append(
                f"{design['label']} T/W参数与设计不符: 设计(T={design['T']},W={design['W']}), "
                f"数据(T={group_report['actualT']},W={group_report['actualW']})"
            )
        if group_report["nOverMax"] > 0:
            severity = "严重" if group_report["overMaxPct"] > 2 else ("注意" if group_report["overMaxPct"] > 0.5 else "轻微")
            report["summary"]["warnings"].append(
                f"{design['label']}: {group_report['nOverMax']}/{group_report['nFormalTrials']} "
                f"({group_report['overMaxPct']}%) Formal试次RT超过T+W, 最大超出{round(group_report['maxOverBy']*1000,1)}ms [{severity}]"
            )

        report["groups"][str(gid)] = group_report

    # 检查缺少数据的组
    for gid in range(1, 9):
        if gid not in groups_data:
            design_info = CONDITIONS.get(gid, {"T": 0, "W": 0, "label": f"旧G{gid}"})
            label = design_info["label"]
            report["summary"]["criticalIssues"].append(f"{label} 没有任何数据文件")
            report["groups"][str(gid)] = {
                "designT": design_info["T"], "designW": design_info["W"],
                "maxRtExpected": round(design_info["T"] + design_info["W"], 4),
                "label": label,
                "nFiles": 0, "nFormalTrials": 0, "nOverMax": 0,
                "issues": ["该组没有任何数据文件"]
            }

    return report


# ==================== DDM 仿真引擎 ====================

def simulate_ddm_euler(v, a, z, t0, dt=0.001, max_time_s=10.0):
    """使用 Euler-Maruyama 方法仿真 DDM 过程
    
    Args:
        v: 漂移率 (drift rate)
        a: 决策边界 (boundary separation)
        z: 起点比例 (0~1, 相对 a 的位置, 0.5=无偏)
        t0: 非决策时间 (non-decision time, seconds)
        dt: 时间步长 (seconds)
        max_time_s: 最大仿真时间 (seconds)
    
    Returns:
        (RT, response): 反应时(秒)和反应(1=上界,0=下界)
    """
    x = z * a   # z 是比例 (0~1), 转换为绝对起点位置
    time = 0.0
    max_steps = int(max_time_s / dt)
    
    for _ in range(max_steps):
        dx = v * dt + np.sqrt(dt) * np.random.randn()
        x += dx
        time += dt
        
        if x >= a:
            return t0 + time, 1
        if x <= 0:
            return t0 + time, 0
    
    return np.nan, np.nan


def ddm_generate_trials(v, a, z, t0, n_trials, dt=0.001, max_time_s=10.0):
    """批量生成 DDM 仿真 trial 数据
    
    Args:
        v: 漂移率
        a: 决策边界
        z: 起点
        t0: 非决策时间
        n_trials: 生成试次数
        dt: 时间步长
        max_time_s: 最大仿真时间
    
    Returns:
        dict: trials 列表 + 汇总统计
    """
    trials = []
    rts = []
    responses = []
    
    for _ in range(n_trials):
        rt, resp = simulate_ddm_euler(v, a, z, t0, dt, max_time_s)
        is_omission = np.isnan(rt)
        trials.append({
            'RT': None if is_omission else round(float(rt), 5),
            'response': None if is_omission else int(resp),
            'omission': bool(is_omission)
        })
        if not is_omission:
            rts.append(rt)
            responses.append(resp)
    
    n_valid = len(rts)
    summary = {
        'n_trials': n_trials,
        'n_valid': n_valid,
        'n_omission': n_trials - n_valid,
        'mean_rt': round(float(np.mean(rts)), 5) if rts else None,
        'std_rt': round(float(np.std(rts)), 5) if rts else None,
        'acc': round(float(np.mean(responses)), 5) if responses else None,
        'params': {'v': v, 'a': a, 'z': z, 't0': t0}
    }
    
    return {'trials': trials, 'summary': summary}


def ddm_sweep_params(sweep_var, sweep_range, fixed_params, n_trials=200):
    """沿一个 DDM 参数维度扫描，计算各点的统计量
    
    Args:
        sweep_var: 扫描的变量名 ('v'|'a'|'z'|'t0')
        sweep_range: [min, max, n_points]
        fixed_params: 固定参数 dict {'v','a','z','t0'}
        n_trials: 每个点的模拟试次数
    
    Returns:
        dict: x_values + curves
    """
    v_min, v_max, n_pts = sweep_range
    x_values = list(np.linspace(v_min, v_max, int(n_pts)))
    x_values = [round(x, 5) for x in x_values]
    
    curves = {
        'mean_rt': [],
        'acc': [],
        'q10_rt': [],
        'q90_rt': [],
    }
    
    for x_val in x_values:
        params = dict(fixed_params)
        params[sweep_var] = x_val
        result = ddm_generate_trials(
            params['v'], params['a'], params['z'], params['t0'],
            n_trials=n_trials
        )
        s = result['summary']
        curves['mean_rt'].append(s['mean_rt'])
        curves['acc'].append(s['acc'])
        
        # 计算分位数
        valid_trials = [t for t in result['trials'] if not t['omission']]
        if valid_trials:
            rts = [t['RT'] for t in valid_trials]
            curves['q10_rt'].append(round(float(np.percentile(rts, 10)), 5))
            curves['q90_rt'].append(round(float(np.percentile(rts, 90)), 5))
        else:
            curves['q10_rt'].append(None)
            curves['q90_rt'].append(None)
    
    return {
        'x_values': x_values,
        'sweep_var': sweep_var,
        'fixed': fixed_params,
        'curves': curves
    }


def ddm_generate_zbias_trials(n_subjects=30, trials_per_condition=150,
                               z_levels=None, a_mean=1.2, a_std=0.2,
                               v_mean=1.0, v_std=0.3, t_mean=0.30, t_std=0.05,
                               dc_mean=0.0, dc_std=0.05, seed_base=420):
    """复刻 plot_CRF_zbias_Wiener.ipynb 的 Stim Coding 仿真
    
    使用 Wiener 扩散过程 (Euler-Maruyama) + Stim Coding 坐标转换:
      刺激A (stimulus=1): params={a, v=v+dc, t, z},     choice=response
      刺激B (stimulus=0): params={a, v=v-dc, t, z=1-z}, choice=1-response
    
    Returns:
        dict: trials + crf_data + summary
    """
    import random
    
    if z_levels is None:
        z_levels = [0.50, 0.55, 0.60, 0.65]
    
    # 生成条件标签映射
    z_label_map = {}
    default_labels = {0.50: 'neutral', 0.55: 'z_bias_small', 0.60: 'z_bias_medium', 0.65: 'z_bias_large'}
    for zv in z_levels:
        zv_rounded = round(zv, 2)
        if zv_rounded in default_labels:
            z_label_map[zv] = default_labels[zv_rounded]
        else:
            z_label_map[zv] = f'z_{zv_rounded:.2f}'.replace('.', '_')
    
    all_trials = []
    
    for subj_id in range(n_subjects):
        subj_seed = seed_base + subj_id * 1000
        np.random.seed(subj_seed)
        random.seed(subj_seed)
        
        subj_a = max(0.4, float(np.random.normal(a_mean, a_std)))
        subj_t = max(0.1, float(np.random.normal(t_mean, t_std)))
        subj_v = float(np.random.normal(v_mean, v_std))
        subj_dc = float(np.random.normal(dc_mean, dc_std))
        
        half = trials_per_condition // 2
        
        for z_val in z_levels:
            cond_label = z_label_map[z_val]
            z_subj = float(np.clip(z_val + np.random.normal(0, 0.02), 0.3, 0.7))
            
            for stimulus in [1, 0]:
                for _ in range(half):
                    if stimulus == 1:
                        rt, resp = simulate_ddm_euler(
                            subj_a, subj_v + subj_dc, z_subj, subj_t
                        )
                    else:
                        rt, resp = simulate_ddm_euler(
                            subj_a, subj_v - subj_dc, 1 - z_subj, subj_t
                        )
                    
                    if stimulus == 1:
                        choice = resp
                    else:
                        choice = 1 - resp if not np.isnan(resp) else np.nan
                    
                    all_trials.append({
                        'subj_idx': subj_id,
                        'condition': cond_label,
                        'z_level': z_val,
                        'stimulus': stimulus,
                        'rt': None if np.isnan(rt) else round(float(rt), 5),
                        'response': None if np.isnan(resp) else int(resp),
                        'choice': None if np.isnan(choice) else int(choice),
                        'omission': bool(np.isnan(rt)),
                    })
    
    # 收集所有出现的条件
    all_conditions = sorted(set(t['condition'] for t in all_trials))
    if not all_conditions:
        all_conditions = ['neutral', 'z_bias_small', 'z_bias_medium', 'z_bias_large']
    
    # 计算 CRF (5分位)
    crf_rows = []
    for cond in all_conditions:
        cond_trials = [t for t in all_trials if t['condition'] == cond and not t['omission']]
        if len(cond_trials) < 10:
            continue
        cond_trials.sort(key=lambda t: t['rt'])
        n = len(cond_trials)
        q_size = n // 5
        for q in range(5):
            start = q * q_size
            end = n if q == 4 else start + q_size
            bin_data = cond_trials[start:end]
            rts = [t['rt'] for t in bin_data]
            choices = [t['choice'] for t in bin_data]
            rt_mean = float(np.mean(rts))
            p_match = float(np.mean(choices))
            n_bin = len(bin_data)
            se = float(np.sqrt(p_match * (1 - p_match) / n_bin)) if n_bin > 1 else 0.0
            crf_rows.append({
                'condition': cond, 'bin': q + 1, 'n': n_bin,
                'rt_mean_ms': round(rt_mean * 1000, 2),
                'p_matching': round(p_match, 4),
                'se': round(se, 4),
                'ci_lo': round(max(0, p_match - 1.96 * se), 4),
                'ci_hi': round(min(1, p_match + 1.96 * se), 4),
            })
    
    # 汇总统计
    summary = {}
    for cond in all_conditions:
        cond_trials = [t for t in all_trials if t['condition'] == cond and not t['omission']]
        if cond_trials:
            rts = [t['rt'] for t in cond_trials]
            choices = [t['choice'] for t in cond_trials]
            summary[cond] = {
                'n': len(cond_trials),
                'rt_mean_ms': round(float(np.mean(rts)) * 1000, 1),
                'p_matching': round(float(np.mean(choices)), 4),
            }
    
    return {
        'trials': all_trials,
        'crf_data': crf_rows,
        'summary': summary,
        'params': {
            'n_subjects': n_subjects,
            'trials_per_condition': trials_per_condition,
            'z_levels': z_levels,
            'a_mean': a_mean, 'v_mean': v_mean, 't_mean': t_mean,
        }
    }


# ============================================================

class AppHandler(http.server.BaseHTTPRequestHandler):

    def do_POST(self):
        """处理 POST 请求 —— DDM 仿真 API"""
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            params = json.loads(body.decode('utf-8')) if body else {}
        except (ValueError, json.JSONDecodeError):
            self._error(400, "Invalid JSON body")
            return
        
        try:
            if path == '/api/ddm/generate':
                v = float(params.get('v', 1.0))
                a = float(params.get('a', 1.2))
                z = float(params.get('z', 0.5))
                t0 = float(params.get('t0', 0.3))
                n_trials = int(params.get('n_trials', 500))
                n_trials = max(10, min(5000, n_trials))
                
                result = ddm_generate_trials(v, a, z, t0, n_trials)
                self._json(result)
                
            elif path == '/api/ddm/generate_pair':
                # 同时生成 Self/Stranger 两套参数的数据
                v_self = float(params.get('v_self', 1.0))
                a_self = float(params.get('a_self', 1.2))
                z_self = float(params.get('z_self', 0.5))
                t0_self = float(params.get('t0_self', 0.3))
                
                v_stranger = float(params.get('v_stranger', 0.8))
                a_stranger = float(params.get('a_stranger', 1.2))
                z_stranger = float(params.get('z_stranger', 0.5))
                t0_stranger = float(params.get('t0_stranger', 0.3))
                
                n_trials = int(params.get('n_trials', 500))
                n_trials = max(10, min(5000, n_trials))
                
                self_result = ddm_generate_trials(v_self, a_self, z_self, t0_self, n_trials)
                stranger_result = ddm_generate_trials(v_stranger, a_stranger, z_stranger, t0_stranger, n_trials)
                
                # 标记 identity
                for t in self_result['trials']:
                    t['identity'] = 'self'
                for t in stranger_result['trials']:
                    t['identity'] = 'stranger'
                
                all_trials = self_result['trials'] + stranger_result['trials']
                
                self._json({
                    'trials': all_trials,
                    'self_summary': self_result['summary'],
                    'stranger_summary': stranger_result['summary'],
                })
                
            elif path == '/api/ddm/sweep':
                sweep_var = params.get('sweep_var', 'v')
                sweep_range = params.get('sweep_range', [0.5, 3.0, 20])
                fixed = params.get('fixed', {'a': 1.2, 'z': 0.5, 't0': 0.3})
                n_trials = int(params.get('n_trials', 200))
                n_trials = max(50, min(2000, n_trials))
                
                sweep_range[2] = max(5, min(50, int(sweep_range[2])))
                
                result = ddm_sweep_params(sweep_var, sweep_range, fixed, n_trials)
                self._json(result)
                
            elif path == '/api/ddm/generate_zbias':
                n_subjects = int(params.get('n_subjects', 30))
                trials_per = int(params.get('trials_per_condition', 150))
                a_mean = float(params.get('a_mean', 1.2))
                v_mean = float(params.get('v_mean', 1.0))
                t_mean = float(params.get('t_mean', 0.30))
                a_std = float(params.get('a_std', 0.2))
                v_std = float(params.get('v_std', 0.3))
                t_std = float(params.get('t_std', 0.05))
                dc_mean = float(params.get('dc_mean', 0.0))
                dc_std = float(params.get('dc_std', 0.05))
                z_levels = params.get('z_levels', [0.50, 0.55, 0.60, 0.65])
                n_subjects = max(5, min(60, n_subjects))
                trials_per = max(20, min(300, trials_per))
                
                result = ddm_generate_zbias_trials(
                    n_subjects=n_subjects,
                    trials_per_condition=trials_per,
                    a_mean=a_mean, v_mean=v_mean, t_mean=t_mean,
                    a_std=a_std, v_std=v_std, t_std=t_std,
                    dc_mean=dc_mean, dc_std=dc_std,
                    z_levels=z_levels,
                )
                self._json(result)
                
            else:
                self._error(404, f"Unknown POST endpoint: {path}")
                
        except Exception as e:
            print(f"[ERROR] POST {path}: {e}")
            import traceback
            traceback.print_exc()
            self._error(500, str(e))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        try:
            if path == '/api/files':
                self._json(list_files())
            elif path == '/api/data/all':
                gf = params.get('group', [None])[0]
                if gf and ',' in gf:
                    groups = [int(g.strip()) for g in gf.split(',') if g.strip()]
                    self._json(load_all_data(groups))
                else:
                    self._json(load_all_data(int(gf) if gf else None))
            elif path == '/api/data/file':
                fn = params.get('name', [None])[0]
                if fn:
                    self._json(load_file_data(unquote(fn)))
                else:
                    self._error(400, "Missing name parameter")
            elif path == '/api/experiment/params':
                sid = int(params.get('subject', [1])[0])
                gid = int(params.get('group', [1])[0])
                self._json(compute_experiment_params(sid, gid))
            elif path == '/api/experiment/trial':
                sid = int(params.get('subject', [1])[0])
                shape = params.get('shape', ['square'])[0]
                label = params.get('label', ['self'])[0]
                self._json(simulate_trial(sid, shape, label))
            elif path.startswith('/api/verify'):
                fn = params.get('name', [None])[0]
                if fn:
                    self._json(verify_file_data(unquote(fn)))
                else:
                    self._error(400, "Missing name parameter")
            elif path == '/api/health':
                self._json({"status": "ok", "message": "Server is running"})
            elif path == '/api/spe/overview':
                cond = params.get('condition', ['all'])[0]
                src = params.get('source', ['label'])[0]
                self._json(load_spe_overview(condition_filter=cond, identity_source=src))
            elif path == '/api/spe/detail':
                pk = params.get('key', [None])[0]
                cond = params.get('condition', ['all'])[0]
                src = params.get('source', ['label'])[0]
                self._json(load_spe_experiment_detail(unquote(pk) if pk else None, condition_filter=cond, identity_source=src))
            elif path == '/api/spe/trials':
                pk = params.get('key', [None])[0]
                src = params.get('source', ['label'])[0]
                self._json(load_spe_trials(unquote(pk) if pk else None, identity_source=src))
            elif path == '/api/spe/identity-summary':
                src = params.get('source', ['label'])[0]
                self._json(load_identity_summary(identity_source=src))
            elif path == '/api/data/self_check':
                self._json(run_self_check())
            elif path == '/' or path == '' or path == '/index.html':
                self._serve_html()
            else:
                self._serve_static(path.lstrip('/'))
        except Exception as e:
            print(f"[ERROR] {path}: {e}")
            self._error(500, str(e))

    def _serve_html(self):
        try:
            with open(HTML_FILE, 'r', encoding='utf-8') as f:
                html = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        except FileNotFoundError:
            self._error(500, f"HTML file not found at {HTML_FILE}")

    def _serve_static(self, rel_path):
        file_path = SCRIPT_DIR / rel_path
        if not file_path.exists() or not file_path.is_file():
            self._error(404, f"Not found: {rel_path}")
            return
        content_types = {
            '.js': 'application/javascript',
            '.css': 'text/css',
            '.html': 'text/html',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.ico': 'image/x-icon',
        }
        ext = file_path.suffix.lower()
        content_type = content_types.get(ext, 'application/octet-stream')
        with open(file_path, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(data))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, msg):
        body = json.dumps({"error": msg}).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {args[0]}")


def main():
    port = 8899
    for attempt in range(3):
        try:
            server = http.server.HTTPServer(('0.0.0.0', port), AppHandler)
            break
        except OSError:
            port += 1
    print()
    print("=" * 60)
    print(f"  Experiment Data Visualization Server")
    print(f"  Local:  http://localhost:{port}")
    print(f"  Health: http://localhost:{port}/api/health")
    print(f"  Press Ctrl+C to stop")
    print("=" * 60)
    print(f"  HTML file: {HTML_FILE}")
    print(f"  Data dir:  {RAW_DIR}")
    print("=" * 60)
    print()
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == '__main__':
    main()

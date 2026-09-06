#!/usr/bin/env python3
import json, math, re, sys
from decimal import Decimal, InvalidOperation


def _canonical_text(value):
    return str(value).strip()


def _semantic_text(value, case=None):
    text = _canonical_text(value)
    # Only the explicitly audited H03 fixture gets path-arrow canonicalization.
    if case and case.get("id") == "H03":
        text = re.sub(r"\s+", "", text).replace("→", "-").replace("->", "-").replace("—", "-").replace("－", "-")
    return text


def _strict_json_equal(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_strict_json_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_strict_json_equal(a, b) for a, b in zip(left, right))
    return left == right


def _json_shape(value):
    """Return a JSON shape that ignores scalar values but preserves types/keys."""
    if isinstance(value, dict):
        return {key: _json_shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_shape(item) for item in value]
    if value is None:
        return None
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def _json_format_valid(parsed, gold, case):
    """Validate JSON syntax and the fixture's structural output contract.

    A wrong scalar value is still correctly formatted when its JSON shape is
    valid.  A fixture may provide a stricter ``format_contract`` shape; the
    legacy fixtures use the gold value's shape as their explicit contract.
    """
    contract = case.get("format_contract")
    if contract is None:
        return _json_shape(parsed) == _json_shape(gold)
    if contract == "json":
        return True
    if isinstance(contract, dict) and contract.get("shape") is not None:
        return _json_shape(parsed) == contract["shape"]
    return _json_shape(parsed) == _json_shape(gold)


def _format_pattern(case):
    pattern = case.get("format_pattern") or case.get("output_pattern")
    contract = case.get("format_contract")
    if isinstance(contract, dict):
        pattern = pattern or contract.get("regex") or contract.get("pattern")
    return pattern


def grade_v2(case, output, *, serving_valid=True, protocol_valid=True):
    """Return independent answer/format/protocol dimensions.

    The answer dimension uses deterministic task graders; format remains strict.
    An empty response is protocol/rerun evidence, never capability by itself.
    """
    raw = "" if output is None else str(output)
    stripped = raw.strip()
    non_empty = bool(stripped)
    grader = case.get("grader", "exact")
    gold = case.get("gold")
    format_correct = False
    answer_correct = False
    normalized = None
    if non_empty:
        if grader == "numeric_exact":
            try:
                # Decimal avoids binary-float aliasing at and above 2**53.
                lexical = bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?", stripped))
                parsed = Decimal(stripped)
                expected = Decimal(str(gold))
                finite = parsed.is_finite() and expected.is_finite()
                answer_correct = lexical and finite and parsed == expected
                format_correct = lexical and finite
                normalized = int(stripped) if lexical and "." not in stripped else stripped
            except (TypeError, ValueError, InvalidOperation):
                pass
        elif grader == "choice":
            allowed = case.get("allowed_choices") or case.get("choices")
            format_correct = bool(re.fullmatch(r"[^\s]", stripped)) if allowed is None else stripped in {str(x) for x in allowed}
            answer_correct = _semantic_text(raw, case) == _semantic_text(gold, case)
            normalized = _semantic_text(raw, case)
        elif grader == "exact":
            pattern = _format_pattern(case)
            # Exact correctness and output shape are independent.  A fixture
            # may provide a regex (H03 does); otherwise any non-empty answer
            # has an observable format, even when its value is wrong.
            format_correct = bool(re.fullmatch(pattern, stripped)) if pattern else non_empty
            answer_correct = _semantic_text(raw, case) == _semantic_text(gold, case)
            normalized = _semantic_text(raw, case)
        elif grader == "json_exact":
            try:
                parsed = json.loads(stripped)
                answer_correct = _strict_json_equal(parsed, gold)
                # JSON whitespace/key order do not alter format.  A wrong
                # scalar in the correct shape is still format-correct.
                format_correct = _json_format_valid(parsed, gold, case)
                normalized = parsed
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        else:
            raise NotImplementedError(grader)
    protocol = bool(protocol_valid and non_empty)
    if not serving_valid:
        status = "INFRA"
    elif not protocol:
        status = "PROTOCOL"
    else:
        status = "PASS" if answer_correct else "CAPABILITY"
    return {
        "answer_correct": bool(answer_correct),
        "format_correct": bool(format_correct),
        "non_empty": non_empty,
        "protocol_valid": protocol,
        "serving_valid": bool(serving_valid),
        "normalized_answer": normalized,
        "status": status,
        "requires_rerun": not non_empty or not serving_valid or not protocol_valid,
    }

def grade(case, output):
    g=case["grader"]
    gold=case["gold"]
    s=output.strip()
    if g=="numeric_exact":
        try: return float(s)==float(gold)
        except: return False
    if g in ("exact","choice"):
        return s==str(gold)
    if g=="json_exact":
        try: return json.loads(s)==gold
        except: return False
    raise NotImplementedError(g)

if __name__=="__main__":
    case=json.loads(sys.argv[1])
    print("PASS" if grade(case,sys.stdin.read()) else "FAIL")

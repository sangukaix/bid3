"""Bounded source-labelled evidence packets, without generative compression."""
import hashlib
import json
import re
from dataclasses import dataclass

from .local_context import byte_size, split_bytes

VERSION = "proposal-packets-v1"
PACKET_LABEL = "[관련 근거 발췌: 일부 자료. 미선택 요구사항은 전체 목록에서 별도 검토]\n"
FIELDS = {
    "company_context": 2, "bid_notice_context": 2, "bid_context": 3,
    "requirement_context": 5, "company_knowledge_context": 3,
    "project_reference_context": 1, "proposal_rules_context": 1,
    "web_context": 1, "strategy_context": 1,
}


@dataclass(frozen=True)
class Evidence:
    id: str
    text: str


def terms(text):
    words = set(re.findall(r"[가-힣A-Za-z0-9]{2,}", text.lower()))
    return words | {word[i:i+2] for word in words if re.search("[가-힣]", word)
                    for i in range(len(word)-1)}


def relevance(text, query):
    return len(terms(text) & terms(query))


def requirement_rows(context):
    try:
        data = json.loads(context) if isinstance(context, str) else context
    except (ValueError, TypeError):
        return []
    if not isinstance(data, dict) or not isinstance(data.get("requirements"), list):
        return []
    return [{**item, "id": f"R{index:04d}"}
            for index, item in enumerate(data["requirements"], 1) if isinstance(item, dict)]


def evidence_units(text, field):
    """Keep requirement records whole and repeat provenance on text fragments."""
    if not text:
        return []
    if field == "requirement_context":
        rows = requirement_rows(text)
        if rows:
            return [Evidence(row["id"], json.dumps(row, ensure_ascii=False)) for row in rows]
    units = []
    header = ""
    for block in re.split(r"(?=^\[[^\n]+\]\s*$)", str(text), flags=re.MULTILINE):
        lines = block.strip().splitlines()
        if not lines:
            continue
        if lines[0].startswith("[") and lines[0].endswith("]"):
            header = lines.pop(0)
        content = "\n".join(lines).strip()
        if not content:
            continue
        fragments = split_bytes(content, 850)
        for number, fragment in enumerate(fragments, 1):
            label = f"{header} [원문 부분 {number}/{len(fragments)}]" if len(fragments) > 1 else header
            identity = hashlib.sha256((field + label + fragment).encode()).hexdigest()[:12]
            units.append(Evidence(identity, (label + "\n" + fragment).strip()))
    return units


def core_project_requirements(context):
    """Keep explicit project quantities available even for generic slide titles."""
    labels = re.compile(r"^(?:사업비|사업예산|용역기간|사업기간|교육기간|교육인원|교육시간|교육대상|과업기간|수행기간|총사업비|기초금액|예산)\s*[:：]")
    rows = [row for row in requirement_rows(context)
            if labels.search(row.get("requirement", ""))
            or row.get("category") in {"사업개요", "사업내용"}]
    units = [Evidence(row["id"], json.dumps(row, ensure_ascii=False)) for row in rows]
    return select_evidence(units, "대상 인원 기간 시간 횟수 사업비 예산", 4500)[0]


def select_evidence(units, query, budget):
    label = PACKET_LABEL
    used = byte_size(label)
    selected = []
    ranked = sorted(enumerate(units), key=lambda pair: (-relevance(pair[1].text, query), pair[0]))
    for _, item in ranked:
        rendered = f"[{item.id}] {item.text}\n"
        if used + byte_size(rendered) <= budget:
            selected.append(item)
            used += byte_size(rendered)
    result = label + "\n".join(f"[{item.id}] {item.text}" for item in selected) if selected else ""
    selected_ids = {u.id for u in selected}
    return result, {"total": len(units), "selected_ids": [u.id for u in selected],
                    "omitted_ids": [u.id for u in units if u.id not in selected_ids]}


def fit_evidence_inputs(prompt, inputs, model, schema):
    """Budget the actual prompt and schema; keep instructions and targets intact."""
    values = dict(inputs)
    keys = [key for key in FIELDS if key in prompt.input_variables and values.get(key)]
    schema_bytes = byte_size(json.dumps(schema.model_json_schema(), ensure_ascii=False))
    budget = model.num_ctx - model.num_predict - schema_bytes - 1024

    def size(data):
        return sum(byte_size(m.content) + 64 for m in prompt.invoke(data).to_messages())

    fixed = size({**values, **{key: "" for key in keys}})
    available = budget - fixed - 512
    if available < 0 or (keys and available < 300 * len(keys)):
        raise ValueError("페이지의 텍스트 위치가 입력 한도를 초과했습니다. 페이지를 작은 묶음으로 나눠 주세요.")
    remaining = available
    targets = {key: 0 for key in keys}
    units_by_key = {key: evidence_units(values[key], key) for key in keys}
    # Requirement packets always gain a provenance label and record IDs. Include
    # those bytes before marking a short field as fully funded; otherwise even
    # a single short requirement can be dropped despite ample context space.
    field_sizes = {
        key: (byte_size(PACKET_LABEL) + sum(byte_size(f"[{unit.id}] {unit.text}\n") for unit in units_by_key[key])
              if key == "requirement_context" else byte_size(values[key]))
        for key in keys
    }
    active = list(keys)
    while active:
        total_weight = sum(FIELDS[key] for key in active)
        short = [key for key in active if field_sizes[key] <= remaining * FIELDS[key] / total_weight]
        if not short:
            for key in active:
                targets[key] = int(remaining * FIELDS[key] / total_weight)
            break
        for key in short:
            targets[key] = field_sizes[key]
            remaining -= targets[key]
            active.remove(key)
    query = str(inputs.get("_evidence_query", ""))
    report = {"version": VERSION, "query": query, "fields": {}}
    for key in keys:
        units = units_by_key[key]
        if key != "requirement_context" and byte_size(values[key]) <= targets[key]:
            report["fields"][key] = {"total": len(units), "selected_ids": [u.id for u in units], "omitted_ids": []}
            continue
        values[key], report["fields"][key] = select_evidence(units, query, targets[key])
    if size(values) > budget:
        raise ValueError("페이지별 근거 묶음이 입력 한도를 초과했습니다.")
    report.update(input_bytes=size(values), budget_bytes=budget)
    if isinstance(inputs.get("_evidence_reports"), list):
        inputs["_evidence_reports"].append(report)
    return values

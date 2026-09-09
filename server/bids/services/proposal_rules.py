import json
from functools import lru_cache
from pathlib import Path


RULES_PATH = (
    Path(__file__).resolve().parents[2]
    / "proposal_templates"
    / "proposal_generation_rules.json"
)


@lru_cache(maxsize=1)
def load_proposal_rules():
    """검토한 제안서와 공식 기준에서 정리한 작성 규칙을 한 번만 읽습니다."""

    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def build_proposal_rules_context():
    """AI 프롬프트에 넣을 제안서 구조와 업종별 작성 원칙을 만듭니다."""

    rules = load_proposal_rules()
    lines = [
        f"[규칙 버전] {rules['version']}",
        "",
        "[공통 제안 흐름]",
    ]
    lines.extend(
        f"{index}. {item}"
        for index, item in enumerate(rules["universal_story_flow"], start=1)
    )

    lines.extend(["", "[슬라이드 작성 원칙]"])
    lines.extend(f"- {item}" for item in rules["slide_writing_rules"])

    lines.extend(["", "[업종별 선택 모듈]"])
    for domain, sections in rules["domain_modules"].items():
        lines.append(f"- {domain}: {', '.join(sections)}")

    layout = rules["layout_rules"]
    lines.extend(
        [
            "",
            "[레이아웃 제한]",
            f"- 권장 분량: {layout['recommended_slide_range']}장",
            f"- 최대 분량: {layout['maximum_slides']}장",
            f"- 제목 권장 길이: {layout['maximum_title_chars']}자 이내",
            f"- 본문 핵심 항목: {layout['preferred_body_points']}개",
            f"- 본문 최소 글자 크기: {layout['minimum_body_font_pt']}pt",
            f"- 제목 최소 글자 크기: {layout['minimum_title_font_pt']}pt",
        ]
    )
    return "\n".join(lines)

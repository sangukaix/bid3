import json
from functools import lru_cache
from pathlib import Path


LAYOUT_CATALOG_PATH = (
    Path(__file__).resolve().parents[2]
    / "proposal_templates"
    / "proposal_template_layouts.json"
)


@lru_cache(maxsize=1)
def load_proposal_layout_catalog():
    """템플릿별 슬라이드 용도와 권장 분량을 한 번만 읽습니다."""

    with open(LAYOUT_CATALOG_PATH, encoding="utf-8") as file:
        return json.load(file)


def get_proposal_slide_layout(template_path, slide_number):
    """템플릿 파일명과 슬라이드 번호에 해당하는 작성 규칙을 반환합니다."""

    template_name = Path(template_path).name
    template_layouts = load_proposal_layout_catalog().get(template_name, {})
    return template_layouts.get(str(slide_number), {})

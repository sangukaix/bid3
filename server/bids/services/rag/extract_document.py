from dataclasses import dataclass, field  # 추출 결과와 실패 목록을 묶는 도구
from pathlib import Path  # 파일 확장자와 안전한 저장 경로 확인
import shutil  # ZIP 내부 파일 복사
import subprocess  # HWP 전용 변환기 실행
import sys  # 현재 가상환경의 실행파일 폴더 확인
import tempfile  # HWP 변환 결과 임시 저장
import zipfile  # ZIP과 HWPX 압축 구조 읽기
from xml.etree import ElementTree  # HWPX XML에서 텍스트 추출

from langchain_core.documents import Document  # 모든 파일을 같은 문서 형태로 통일

from ..document_paths import portable_document_source, resolve_document_source


MAX_ARCHIVE_FILES = 100  # 중첩 ZIP 전체에서 허용할 최대 파일 수
MAX_ARCHIVE_TOTAL_BYTES = 200 * 1024 * 1024  # 압축 해제 후 전체 최대 200MB
MAX_ARCHIVE_FILE_BYTES = 100 * 1024 * 1024  # 내부 파일 한 개의 최대 100MB
MAX_ARCHIVE_DEPTH = 2  # ZIP 안의 ZIP은 최대 두 단계까지 처리

BLOCKED_EXTENSIONS = {
    ".bat", ".cmd", ".com", ".dll", ".exe", ".js", ".msi", ".ps1", ".scr",
}  # 문서 분석에 필요하지 않은 실행 가능 파일

CATEGORY_LABELS = {
    "Title": "제목",
    "NarrativeText": "본문",
    "ListItem": "목록",
    "Table": "표",
}  # 문서 Loader의 영문 위치명을 사용자용 한글로 변환


@dataclass
class ExtractionResult:
    documents: list[Document] = field(default_factory=list)  # 추출한 문서 내용
    processed_files: list[str] = field(default_factory=list)  # 정상 처리한 파일명
    failed_files: list[dict[str, str]] = field(default_factory=list)  # 실패 파일과 이유

    def merge(self, other):  # ZIP 내부 파일들의 결과를 하나로 합치는 함수
        self.documents.extend(other.documents)
        self.processed_files.extend(other.processed_files)
        self.failed_files.extend(other.failed_files)


@dataclass
class ArchiveBudget:
    file_count: int = 0  # 중첩 ZIP을 포함해 지금까지 확인한 파일 수
    total_bytes: int = 0  # 압축 해제될 전체 파일 크기


def _add_reference_metadata(documents, file_path):
    """사용자에게 출처를 보여줄 파일명과 문서 위치를 추가합니다."""

    for index, document in enumerate(documents, start=1):
        metadata = document.metadata
        metadata["source"] = portable_document_source(file_path)
        metadata["file_name"] = file_path.name
        metadata["file_type"] = file_path.suffix.lower().lstrip(".")
        metadata["element_index"] = index

        if metadata.get("location"):  # HWPX처럼 추출기가 이미 정한 위치는 유지
            continue

        page = metadata.get("page_number") or metadata.get("page_label")
        category = metadata.get("category")
        category_label = CATEGORY_LABELS.get(category, category)

        if page and category_label:
            metadata["location"] = f"{page}페이지 {category_label}"
        elif page:
            metadata["location"] = f"{page}페이지"
        elif category_label:
            metadata["location"] = f"{category_label} {index}"
        else:
            metadata["location"] = f"문단 {index}"

    return documents


def _load_standard_document(file_path):
    """확장자에 맞는 LangChain Document Loader를 선택합니다."""

    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader

        loader = PyPDFLoader(str(file_path))
    elif suffix in {".doc", ".docx"}:
        from langchain_community.document_loaders import UnstructuredWordDocumentLoader

        loader = UnstructuredWordDocumentLoader(str(file_path), mode="elements")
    elif suffix in {".xls", ".xlsx"}:
        from langchain_community.document_loaders import UnstructuredExcelLoader

        loader = UnstructuredExcelLoader(str(file_path), mode="elements")
    elif suffix in {".ppt", ".pptx"}:
        from langchain_community.document_loaders import UnstructuredPowerPointLoader

        loader = UnstructuredPowerPointLoader(str(file_path), mode="elements")
    elif suffix == ".rtf":
        from langchain_community.document_loaders import UnstructuredRTFLoader

        loader = UnstructuredRTFLoader(str(file_path), mode="elements")
    elif suffix == ".odt":
        from langchain_community.document_loaders import UnstructuredODTLoader

        loader = UnstructuredODTLoader(str(file_path), mode="elements")
    elif suffix in {".txt", ".csv", ".xml"}:
        from langchain_community.document_loaders import TextLoader

        loader = TextLoader(str(file_path), autodetect_encoding=True)
    else:
        raise ValueError(f"지원하지 않는 문서 형식입니다: {suffix or '확장자 없음'}")

    return _add_reference_metadata(loader.load(), file_path)


def _load_hwp(file_path):
    """hwp5txt가 설치된 서버에서 HWP 문서를 일반 텍스트로 변환합니다."""

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "converted.txt"
        process = subprocess.run(
            [sys.executable, "-c", "from hwp5.hwp5txt import main; main()", "--output", str(output_path), str(file_path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        if process.returncode != 0 or not output_path.exists():
            raise ValueError("HWP 파일이 손상되었거나 암호화되어 텍스트를 추출할 수 없습니다.")

        text = output_path.read_text(encoding="utf-8", errors="replace").strip()

    if not text:
        raise ValueError("HWP 파일에서 읽을 수 있는 텍스트가 없습니다.")

    document = Document(page_content=text, metadata={"location": "문서 전체"})
    return _add_reference_metadata([document], file_path)


def _load_hwpx(file_path):
    """HWPX 내부의 XML 구역을 읽어 텍스트 문서로 변환합니다."""

    documents = []

    with zipfile.ZipFile(file_path) as archive:
        sections = sorted(
            name
            for name in archive.namelist()
            if name.lower().startswith("contents/section") and name.lower().endswith(".xml")
        )

        for section_index, section_name in enumerate(sections, start=1):
            root = ElementTree.fromstring(archive.read(section_name))
            text_parts = [
                element.text.strip()
                for element in root.iter()
                if element.tag.rsplit("}", 1)[-1] == "t" and element.text and element.text.strip()
            ]

            if text_parts:
                documents.append(
                    Document(
                        page_content="\n".join(text_parts),
                        metadata={"location": f"문서 구역 {section_index}"},
                    )
                )

    if not documents:
        raise ValueError("HWPX 파일에서 읽을 수 있는 텍스트가 없습니다.")

    return _add_reference_metadata(documents, file_path)


def _safe_extract_archive(file_path, depth, budget):
    """ZIP을 안전하게 풀고 내부의 모든 지원 문서를 다시 추출합니다."""

    result = ExtractionResult()
    output_dir = file_path.parent / "_extracted" / file_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(file_path) as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]

        for member in members:
            budget.file_count += 1
            budget.total_bytes += member.file_size

            if budget.file_count > MAX_ARCHIVE_FILES:
                raise ValueError(f"압축파일 내부 문서가 {MAX_ARCHIVE_FILES}개를 초과했습니다.")
            if budget.total_bytes > MAX_ARCHIVE_TOTAL_BYTES:
                raise ValueError("압축 해제 후 전체 용량이 200MB를 초과했습니다.")
            if member.file_size > MAX_ARCHIVE_FILE_BYTES:
                result.failed_files.append({"file_name": member.filename, "reason": "파일이 100MB를 초과했습니다."})
                continue
            if member.flag_bits & 0x1:
                result.failed_files.append({"file_name": member.filename, "reason": "암호화된 파일입니다."})
                continue

            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                result.failed_files.append({"file_name": member.filename, "reason": "안전하지 않은 파일 경로입니다."})
                continue
            if member_path.suffix.lower() in BLOCKED_EXTENSIONS:
                result.failed_files.append({"file_name": member.filename, "reason": "실행 가능한 파일은 처리하지 않습니다."})
                continue

            target_path = (output_dir / member_path).resolve()
            if output_dir.resolve() not in target_path.parents:
                result.failed_files.append({"file_name": member.filename, "reason": "안전하지 않은 파일 경로입니다."})
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target)

            if target_path.suffix.lower() == ".zip" and depth >= MAX_ARCHIVE_DEPTH:
                result.failed_files.append({"file_name": member.filename, "reason": "중첩 ZIP 깊이가 2단계를 초과했습니다."})
                continue

            result.merge(extract_document(target_path, depth + 1, budget))

    return result


def extract_document(file_path, archive_depth=0, archive_budget=None):
    """파일 하나를 읽어 문서, 성공 파일, 실패 파일 목록을 반환합니다."""

    file_path = resolve_document_source(file_path)
    result = ExtractionResult()
    budget = archive_budget or ArchiveBudget()

    try:
        if not file_path.exists():
            raise ValueError("파일을 찾을 수 없습니다.")

        suffix = file_path.suffix.lower()
        if suffix in BLOCKED_EXTENSIONS:
            raise ValueError("실행 가능한 파일은 처리하지 않습니다.")
        if suffix == ".zip":
            return _safe_extract_archive(file_path, archive_depth, budget)
        if suffix == ".hwp":
            documents = _load_hwp(file_path)
        elif suffix == ".hwpx":
            documents = _load_hwpx(file_path)
        else:
            documents = _load_standard_document(file_path)

        result.documents.extend(documents)
        result.processed_files.append(file_path.name)
    except Exception as error:  # 한 파일의 오류가 다른 첨부파일 처리까지 막지 않게 기록
        result.failed_files.append({"file_name": file_path.name, "reason": str(error)})

    return result


def extract_documents(file_paths):
    """공고에 첨부된 여러 파일을 하나의 추출 결과로 합칩니다."""

    result = ExtractionResult()

    for file_path in file_paths:
        result.merge(extract_document(file_path))

    return result

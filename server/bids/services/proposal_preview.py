import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from django.conf import settings
import pypdfium2 as pdfium


PREVIEW_TIMEOUT_SECONDS = 120
TEMPLATE_PREVIEW_LOCK = threading.Lock()


def _convert_with_libreoffice(source_path, output_path):
    """서버에 LibreOffice가 있으면 headless 방식으로 PDF를 만듭니다."""

    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if not executable:
        return False

    subprocess.run(
        [
            executable,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_path.parent),
            str(source_path),
        ],
        check=True,
        capture_output=True,
        timeout=PREVIEW_TIMEOUT_SECONDS,
    )
    converted_path = output_path.parent / f"{source_path.stem}.pdf"
    if converted_path != output_path and converted_path.exists():
        converted_path.replace(output_path)
    return output_path.exists()


def _convert_with_powerpoint(source_path, output_path):
    """Windows 개발환경에서는 설치된 PowerPoint로 PDF를 만듭니다."""

    if os.name != "nt":
        return False

    script_path = Path(__file__).with_name("render_pptx_preview.ps1")
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-SourcePath",
            str(source_path),
            "-OutputPath",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=PREVIEW_TIMEOUT_SECONDS,
    )
    return completed.returncode == 0 and output_path.exists()


def get_proposal_preview_path(proposal):
    """현재 제안서 파일과 연결되는 캐시 PDF 경로를 반환합니다."""

    preview_root = (
        Path(settings.MEDIA_ROOT)
        / "proposal_previews"
        / f"user_{proposal.saved_bid.user_id}"
    )
    preview_root.mkdir(parents=True, exist_ok=True)
    return preview_root / f"proposal_{proposal.id}.pdf"


def delete_proposal_preview(proposal):
    """제안서가 바뀌거나 삭제되면 이전 PDF 미리보기 캐시를 지웁니다."""

    preview_path = (
        Path(settings.MEDIA_ROOT)
        / "proposal_previews"
        / f"user_{proposal.saved_bid.user_id}"
        / f"proposal_{proposal.id}.pdf"
    )
    preview_path.unlink(missing_ok=True)


def create_proposal_preview(proposal, force=False):
    """PPTX를 PDF로 변환하며 파일이 바뀌지 않았다면 기존 PDF를 재사용합니다."""

    if not proposal.generated_file:
        raise ValueError("미리보기로 변환할 제안서가 없습니다.")

    source_path = Path(proposal.generated_file.path).resolve()
    output_path = get_proposal_preview_path(proposal).resolve()
    if (
        not force
        and output_path.exists()
        and output_path.stat().st_mtime >= source_path.stat().st_mtime
    ):
        return output_path

    with tempfile.TemporaryDirectory() as directory:
        temporary_output = Path(directory) / "preview.pdf"
        try:
            converted = _convert_with_libreoffice(source_path, temporary_output)
            if not converted:
                converted = _convert_with_powerpoint(source_path, temporary_output)
        except (OSError, subprocess.SubprocessError):
            converted = False

        if not converted:
            raise ValueError(
                "제안서 미리보기를 만들 수 없습니다. "
                "서버에 LibreOffice 또는 PowerPoint가 필요합니다."
            )

        shutil.copyfile(temporary_output, output_path)
    return output_path


def create_template_slide_previews(template_id, force=False):
    """등록된 PPTX 템플릿을 슬라이드별 PNG로 변환해 캐시합니다."""

    with TEMPLATE_PREVIEW_LOCK:
        return _create_template_slide_previews(template_id, force)


def _create_template_slide_previews(template_id, force=False):
    """동시에 같은 캐시 폴더를 수정하지 않도록 잠금 안에서 실행합니다."""

    template = settings.PROPOSAL_TEMPLATES.get(template_id)
    if template is None:
        raise ValueError("제안서 템플릿을 찾을 수 없습니다.")

    source_path = Path(template["path"]).resolve()
    if not source_path.exists():
        raise ValueError("제안서 템플릿 파일이 없습니다.")

    output_directory = (
        Path(settings.MEDIA_ROOT) / "proposal_template_previews" / template_id
    ).resolve()
    cached_images = sorted(output_directory.glob("slide_*.png"))
    if (
        not force
        and cached_images
        and min(path.stat().st_mtime for path in cached_images)
        >= source_path.stat().st_mtime
    ):
        return cached_images

    shutil.rmtree(output_directory, ignore_errors=True)
    output_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        pdf_path = Path(directory) / "template.pdf"
        try:
            converted = _convert_with_libreoffice(source_path, pdf_path)
            if not converted:
                converted = _convert_with_powerpoint(source_path, pdf_path)
            if not converted:
                raise ValueError("템플릿을 PDF로 변환하지 못했습니다.")

            document = pdfium.PdfDocument(str(pdf_path))
            try:
                for index in range(len(document)):
                    page = document[index]
                    try:
                        bitmap = page.render(scale=1.5)
                        try:
                            image = bitmap.to_pil()
                            try:
                                image.save(
                                    output_directory / f"slide_{index + 1:03d}.png",
                                    "PNG",
                                )
                            finally:
                                image.close()
                        finally:
                            bitmap.close()
                    finally:
                        page.close()
            finally:
                document.close()
        except (OSError, subprocess.SubprocessError) as error:
            shutil.rmtree(output_directory, ignore_errors=True)
            raise ValueError("템플릿 슬라이드 이미지를 만들지 못했습니다.") from error

    images = sorted(output_directory.glob("slide_*.png"))
    if not images:
        raise ValueError("템플릿 슬라이드 이미지를 만들지 못했습니다.")
    return images


def get_template_slide_preview(template_id, slide_number):
    """템플릿의 특정 슬라이드 이미지 경로를 반환합니다."""

    images = create_template_slide_previews(template_id)
    if slide_number < 1 or slide_number > len(images):
        raise ValueError("템플릿 슬라이드 번호를 확인해 주세요.")
    return images[slide_number - 1], len(images)

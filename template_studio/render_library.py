"""Render finalized PPTX files and install an offline catalog with content checks.

Run with the project's Python; authoring itself lives in build.mjs.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import pypdfium2 as pdfium
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".local" / "template-studio"
DEST = ROOT / "server" / "proposal_templates" / "library"


def normalize(text):
    return re.sub(r"\s+", "", text)


def render(revision, template_ids=None):
    catalog = json.loads((BUILD / "catalog.json").read_text(encoding="utf-8"))
    report_path = BUILD / f"{revision}-render-checks.json"
    prior_reports = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else []
    if template_ids:
        unknown = set(template_ids) - {entry["id"] for entry in catalog}
        if unknown:
            raise ValueError(f"Unknown templates: {sorted(unknown)}")
    reports = [row for row in prior_reports if template_ids and row["template_id"] not in template_ids]
    for entry in catalog:
        template_id = entry["id"]
        if template_ids and template_id not in template_ids:
            continue
        source = BUILD / revision / entry["file"]
        receipt = BUILD / f"{revision}-{template_id}.validation.json"
        if not receipt.is_file():
            raise ValueError(f"Missing finalization receipt: {template_id}")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        images = DEST / "previews" / template_id
        manifest_path = images / "manifest.json"
        if manifest_path.exists():
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            prior_pages = [row for row in prior_reports if row["template_id"] == template_id]
            if (previous.get("source_sha256") == digest
                    and previous.get("slide_count") == entry["slide_count"]
                    and len(prior_pages) == entry["slide_count"]
                    and all((images / f"slide_{i:03d}.png").is_file() for i in range(1, entry["slide_count"] + 1))):
                shutil.copyfile(source, DEST / entry["file"])
                reports.extend(prior_pages)
                print(f"Cached {template_id}", flush=True)
                continue
        pdf_path = BUILD / f"{revision}-{template_id}.pdf"
        subprocess.run([
            "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", str(ROOT / "server/bids/services/render_pptx_preview.ps1"),
            "-SourcePath", str(source), "-OutputPath", str(pdf_path),
        ], check=True, timeout=120, capture_output=True)
        presentation = Presentation(source)
        document = pdfium.PdfDocument(str(pdf_path))
        try:
            if len(document) != entry["slide_count"]:
                raise ValueError(f"Wrong slide count: {template_id}")
            images.mkdir(parents=True, exist_ok=True)
            for index, slide in enumerate(presentation.slides):
                page = document[index]
                text_page = page.get_textpage()
                try:
                    actual = normalize(text_page.get_text_range())
                    expected = []
                    for shape in slide.shapes:
                        if shape.has_text_frame:
                            expected.append(normalize(shape.text))
                        if shape.has_table:
                            expected.extend(normalize(cell.text) for row in shape.table.rows for cell in row.cells)
                    missing = [text for text, count in Counter(expected).items() if text and actual.count(text) < count]
                    if missing:
                        raise ValueError(f"Text missing after rendering {template_id}/{index+1}: {missing}")
                    bitmap = page.render(scale=4/3)
                    try:
                        image = bitmap.to_pil()
                        try:
                            image.save(images / f"slide_{index+1:03d}.png", optimize=True)
                        finally:
                            image.close()
                    finally:
                        bitmap.close()
                    reports.append({"template_id":template_id,"page":index+1,"text_complete":True})
                finally:
                    text_page.close()
                    page.close()
        finally:
            document.close()
        shutil.copyfile(source, DEST / entry["file"])
        manifest_path.write_text(json.dumps({"source_sha256":digest,"slide_count":len(presentation.slides),"renderer":"Microsoft PowerPoint / PDFium"},indent=2)+"\n",encoding="utf-8")
        print(f"Rendered and checked {template_id}: 20 pages", flush=True)
    for filename in ("catalog.json", "layouts.json"):
        shutil.copyfile(BUILD / filename, DEST / filename)
    report_path.write_text(json.dumps(reports,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", default="final-v4")
    parser.add_argument("--template-id", action="append")
    args = parser.parse_args()
    render(args.revision, args.template_id)

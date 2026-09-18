"""Extract the FDA PDF snapshots and record a reproducible corpus manifest."""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
HW3_DIR = ROOT / "reports" / "hw03"
TEXT_DIR = HW3_DIR / "corpus" / "text"

DOCUMENTS = [
    {
        "title": "FDA Regulatory Procedures Manual, Chapter 7: Recall Procedures",
        "source_url": "https://www.fda.gov/media/71814/download?attachment=",
        "source": "source_pdfs/fda_regulatory_procedures_manual_chapter_7.pdf",
        "kind": "pdf",
        "text": "fda_regulatory_procedures_manual_chapter_7.txt",
    },
    {
        "title": "FDA 2026 Investigations Operations Manual, Chapter 7: Recall Activities",
        "source_url": "https://www.fda.gov/media/166535/download?attachment=",
        "source": "source_pdfs/fda_iom_2026_chapter_7.pdf",
        "kind": "pdf",
        "text": "fda_iom_2026_chapter_7.txt",
    },
    {
        "title": "Public Availability of Lists of Retail Consignees for Food Recalls",
        "source_url": "https://www.fda.gov/media/116401/download",
        "source": "source_pdfs/fda_retail_consignee_lists_guidance.pdf",
        "kind": "pdf",
        "text": "fda_retail_consignee_lists_guidance.txt",
    },
    {
        "title": "Public Warning and Notification of Recalls Under 21 CFR Part 7",
        "source_url": "https://www.fda.gov/media/110457/download",
        "source": "source_pdfs/fda_public_warning_guidance.pdf",
        "kind": "pdf",
        "text": "fda_public_warning_guidance.txt",
    },
    {
        "title": "Questions and Answers Regarding the Reportable Food Registry",
        "source_url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/guidance-industry-questions-and-answers-regarding-reportable-food-registry-established-food-and-drug",
        "source": "fda_reportable_food_registry_guidance.html",
        "kind": "html",
        "text": "fda_reportable_food_registry_guidance.txt",
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_pdf(pdf_path: Path, text_path: Path) -> int:
    reader = PdfReader(pdf_path)
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").replace("\x00", "").strip()
        pages.append(f"\n=== Page {page_number} ===\n{text}\n")
    text_path.write_text("".join(pages), encoding="utf-8")
    return len(reader.pages)


class VisibleTextParser(HTMLParser):
    """Collect readable page text while skipping scripts and styles."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg"}:
            self.hidden_depth += 1
        elif tag in {"p", "li", "h1", "h2", "h3", "h4", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg"} and self.hidden_depth:
            self.hidden_depth -= 1
        elif tag in {"p", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            cleaned = " ".join(data.split())
            if cleaned:
                self.parts.append(cleaned + " ")


def extract_html(html_path: Path, text_path: Path) -> None:
    parser = VisibleTextParser()
    parser.feed(html_path.read_text(encoding="utf-8"))
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    text_path.write_text("\n".join(line for line in lines if line) + "\n", encoding="utf-8")


def main() -> None:
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_documents = []

    for document in DOCUMENTS:
        source_path = HW3_DIR / "corpus" / document["source"]
        text_path = TEXT_DIR / document["text"]
        if not source_path.exists():
            raise FileNotFoundError(f"Missing downloaded snapshot: {source_path}")

        page_count = None
        if document["kind"] == "pdf":
            page_count = extract_pdf(source_path, text_path)
        else:
            extract_html(source_path, text_path)

        item = {
            "title": document["title"],
            "source_url": document["source_url"],
            "accessed": "2026-09-17",
            "source_file": str(source_path.relative_to(ROOT)),
            "source_bytes": source_path.stat().st_size,
            "source_sha256": sha256(source_path),
            "text_file": str(text_path.relative_to(ROOT)),
            "text_bytes": text_path.stat().st_size,
            "text_sha256": sha256(text_path),
        }
        if page_count is not None:
            item["pages"] = page_count
        manifest_documents.append(item)

    total_text_bytes = sum(item["text_bytes"] for item in manifest_documents)
    if total_text_bytes < 200_000:
        raise RuntimeError(f"Corpus is only {total_text_bytes} bytes; 200,000 required")

    manifest = {
        "domain_id": 3,
        "domain": "Grocery Supply and Recall Notices",
        "generated_at": "2026-09-17",
        "documents": manifest_documents,
        "total_text_bytes": total_text_bytes,
    }
    output_path = HW3_DIR / "CORPUS_MANIFEST.json"
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Extracted {len(manifest_documents)} FDA documents")
    print(f"Total retrieval corpus size: {total_text_bytes:,} bytes")
    print(f"Manifest: {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

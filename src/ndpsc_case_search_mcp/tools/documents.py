"""Document retrieval tools (PDF text extraction and download)."""

import base64

import fitz
import httpx
from pydantic import Field

from ndpsc_case_search_mcp.services import scraper


async def get_document_text(
    year: str = Field(description="2-digit year from the case number e.g. '26'"),
    sequence: str = Field(description="Case sequence number e.g. '95'"),
    docket: str = Field(description="Docket number e.g. '1'"),
    file_number: str = Field(
        description="File number from get_docket_detail e.g. '10'"
    ),
) -> str:
    """Download a PSC document PDF and extract its text content.
    Fails gracefully if the document is a scanned image with no embedded text."""
    url = scraper.build_pdf_url(year, sequence, docket, file_number)

    try:
        r = await scraper.fetch_pdf(url)
    except httpx.HTTPStatusError as e:
        return f"## Error Fetching Document\n\n**Status {e.response.status_code}** — could not retrieve `{url}`"
    except httpx.RequestError as e:
        return f"## Error Fetching Document\n\nNetwork error: {e}"

    if "application/pdf" not in r.headers.get("content-type", ""):
        return (
            f"## Unexpected Content Type\n\n"
            f"URL did not return a PDF (`{r.headers.get('content-type', 'unknown')}`). "
            "Check that year, sequence, docket, and file_number are correct."
        )

    try:
        doc = fitz.open(stream=r.content, filetype="pdf")
    except Exception as e:
        return f"## Could Not Open PDF\n\nFailed to parse the PDF: {e}"

    pages = []
    empty_pages = 0
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append(f"### Page {i + 1}\n\n{text}")
        else:
            empty_pages += 1

    if not pages:
        return (
            "## No Text Extracted\n\n"
            f"This PDF has {len(doc)} page(s) but contains no embedded text. "
            "It is likely a **scanned image** and would require OCR to read. "
            "Use `get_document_pdf` to retrieve the raw file if needed."
        )

    header = f"## Extracted Text — {len(pages)} page(s) with content"
    if empty_pages:
        header += f" ({empty_pages} blank/image-only page(s) skipped)"
    header += f"\n\n**Source:** {url}\n"

    return header + "\n\n---\n\n" + "\n\n---\n\n".join(pages)


async def get_document_pdf(
    year: str = Field(description="2-digit year from the case number e.g. '26'"),
    sequence: str = Field(description="Case sequence number e.g. '95'"),
    docket: str = Field(description="Docket number e.g. '1'"),
    file_number: str = Field(
        description="File number from get_docket_detail e.g. '10'"
    ),
) -> str:
    """Download a PSC document PDF and return it as a base64-encoded string.
    Use this when the user needs the actual file, or when get_document_text
    reports a scanned image."""
    url = scraper.build_pdf_url(year, sequence, docket, file_number)

    try:
        r = await scraper.fetch_pdf(url)
    except httpx.HTTPStatusError as e:
        return f"## Error Fetching Document\n\n**Status {e.response.status_code}** — could not retrieve `{url}`"
    except httpx.RequestError as e:
        return f"## Error Fetching Document\n\nNetwork error: {e}"

    content_type = r.headers.get("content-type", "unknown")
    if "application/pdf" not in content_type:
        return f"## Unexpected Content Type\n\nURL returned `{content_type}` instead of a PDF. Check the parameters."

    size_kb = len(r.content) / 1024
    encoded = base64.b64encode(r.content).decode("ascii")
    filename = url.rstrip("/").split("/")[-1]

    return (
        f"## PDF Document\n\n"
        f"- **Filename:** {filename}\n"
        f"- **Source:** {url}\n"
        f"- **Size:** {size_kb:.1f} KB\n"
        f"- **Encoding:** base64\n\n"
        f"```base64\n{encoded}\n```"
    )


ALL = [get_document_text, get_document_pdf]

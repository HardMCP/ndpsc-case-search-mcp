"""HTTP scraping helpers for apps.psc.nd.gov/cases/."""

import re
from datetime import date, timedelta

import httpx
from bs4 import BeautifulSoup

from ndpsc_case_search_mcp.models.case import CaseDetail, CaseSummary, DocketFile

BASE_URL = "https://apps.psc.nd.gov/cases"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ndpsc-case-search/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


async def fetch_get(path: str, params: dict | None = None) -> BeautifulSoup:
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=20
    ) as client:
        r = await client.get(f"{BASE_URL}/{path}", params=params)
        r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def _parse_total_cases(soup: BeautifulSoup) -> int:
    text = soup.get_text()
    for pattern in [r"\d+\s+of\s+(\d+)\s+Cases:", r"(\d+)\s+Cases:"]:
        m = re.search(pattern, text)
        if m:
            return int(m.group(1))
    return len(_parse_case_rows(soup))


async def search_cases(data: dict) -> tuple[list[CaseSummary], str]:
    """POST a search and return the first result page plus the total match count."""
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=20
    ) as client:
        r = await client.post(f"{BASE_URL}/pscasesearch", data=data)
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    cases = _parse_case_rows(soup)
    total = str(_parse_total_cases(soup))

    return cases, total


def _initial_filed_range(data: dict) -> tuple[date, date]:
    filed_from = data.get("filedFromDate")
    filed_to = data.get("filedToDate")
    if filed_from and filed_to:
        return date.fromisoformat(filed_from), date.fromisoformat(filed_to)
    if filed_from:
        return date.fromisoformat(filed_from), date.today()
    if filed_to:
        return date(1900, 1, 1), date.fromisoformat(filed_to)

    return date(1900, 1, 1), date.today()


def _merge_cases(cases: list[CaseSummary]) -> list[CaseSummary]:
    merged: dict[tuple[str, str, str], CaseSummary] = {}
    for case in cases:
        merged[(case.case_number, case.year or "", case.seq or "")] = case
    return list(merged.values())


def _case_sort_key(case: CaseSummary) -> tuple[int, int, str]:
    year = int(case.year) if case.year and case.year.isdigit() else -1
    seq = int(case.seq) if case.seq and case.seq.isdigit() else -1
    return (-year, -seq, case.case_number)


async def _search_cases_split(
    data: dict, filed_from: date, filed_to: date
) -> list[CaseSummary]:
    bucket_data = dict(data)
    bucket_data["filedFromDate"] = filed_from.isoformat()
    bucket_data["filedToDate"] = filed_to.isoformat()

    cases, total = await search_cases(bucket_data)
    total_count = int(total)
    if total_count <= 100:
        return cases

    if filed_from >= filed_to:
        raise ValueError(
            "Search still exceeds 100 cases within a single filed date. "
            "Use a narrower query."
        )

    midpoint = date.fromordinal((filed_from.toordinal() + filed_to.toordinal()) // 2)
    left_cases = await _search_cases_split(bucket_data, filed_from, midpoint)
    right_cases = await _search_cases_split(
        bucket_data, midpoint + timedelta(days=1), filed_to
    )
    return _merge_cases(left_cases + right_cases)


async def search_cases_all(data: dict) -> tuple[list[CaseSummary], str]:
    """POST a search and recursively split oversized result sets by filed date."""
    cases, total = await search_cases(data)
    total_count = int(total)
    if total_count <= 100:
        return cases, total

    filed_from, filed_to = _initial_filed_range(data)
    all_cases = await _search_cases_split(data, filed_from, filed_to)
    all_cases = sorted(_merge_cases(all_cases), key=_case_sort_key)
    return all_cases, str(len(all_cases))


async def fetch_case_detail(year: str, sequence: str) -> CaseDetail:
    soup = await fetch_get(
        "pscasedetail",
        {
            "getId": year.lstrip("0") or "0",
            "getId2": sequence.lstrip("0") or "0",
        },
    )

    body = soup.get_text("\n")
    detail = CaseDetail(year=year, sequence=sequence)

    h1 = soup.find("h1", string=re.compile(r"Case .+ Detail"))
    if h1:
        detail.case_id = _clean(h1.get_text())

    for label, field in [
        ("Date Filed", "date_filed"),
        ("Date Closed", "date_closed"),
        ("Description", "description"),
        ("Type", "case_type"),
        ("Category", "category"),
    ]:
        m = re.search(rf"{label}:\s*\n\s*(.+)", body)
        if m:
            val = _clean(m.group(1))
            if val and not re.match(
                r"^(Date Filed|Date Closed|Description|Type|Category|Entities):", val
            ):
                setattr(detail, field, val)

    for tag in soup.find_all(string=re.compile(r"Entities:", re.I)):
        for sib in tag.parent.find_next_siblings():
            text = _clean(sib.get_text())
            if (
                text
                and not text.startswith("Docket")
                and not re.match(r"\d+ Dockets?:", text)
            ):
                detail.entities.append(text)
            else:
                break
        break

    m = re.search(r"(\d+)\s+Dockets?:", body)
    detail.docket_count = int(m.group(1)) if m else 0

    return detail


async def fetch_docket_files(
    year: str, sequence: str, docket: str
) -> tuple[str, list[DocketFile]]:
    soup = await fetch_get(
        "psdocketdetail",
        {
            "getId": year.lstrip("0") or "0",
            "getId2": sequence.lstrip("0") or "0",
            "getId3": docket.lstrip("0") or "0",
        },
    )

    h1 = soup.find("h1", string=re.compile(r"Docket \d+ Detail"))
    title = _clean(h1.get_text()) if h1 else "Docket Detail"

    body = soup.get_text("\n")
    m = re.search(
        r"(PU|RC|AM|GS|RR|DM|AU|WM|AD|CO|MI|SR|AR|GE|OT)-\d{2}-\d+\.\d+", body
    )
    docket_id = m.group(0) if m else ""

    return f"{title} — {docket_id}" if docket_id else title, _parse_file_rows(soup)


PDF_BASE = "https://www.psc.nd.gov/webdocs/case"


def build_pdf_url(year: str, sequence: str, docket: str, file_number: str) -> str:
    seq_padded = sequence.zfill(4)
    docket_padded = docket.zfill(3)
    file_padded = file_number.zfill(3)
    return f"{PDF_BASE}/{year}-{seq_padded}/{docket_padded}-{file_padded}.pdf"


async def fetch_pdf(url: str) -> httpx.Response:
    if not url.startswith(PDF_BASE):
        raise ValueError(f"URL must start with {PDF_BASE}")
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=30
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
    return r


# ── Parsers ───────────────────────────────────────────────────────────────────


def _parse_case_rows(soup: BeautifulSoup) -> list[CaseSummary]:
    """Columns: RowNum | CaseNumber & Description | CaseType & Category |
    Entity(s) | DocketCount | DateFiled | DateClosed"""
    table = soup.find("table")
    if not table:
        return []
    results = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 6:
            continue
        link = cells[1].find("a")
        year, seq = None, None
        if link:
            m = re.search(r"getId=(\d+)&getId2=(\d+)", link.get("href", ""))
            if m:
                year, seq = m.group(1), m.group(2)
        case_desc = _clean(cells[1].get_text())
        results.append(
            CaseSummary(
                case_number=case_desc.split()[0] if case_desc else "",
                year=year,
                seq=seq,
                description=" ".join(case_desc.split()[1:]) if case_desc else "",
                type_category=_clean(cells[2].get_text()),
                entity=_clean(cells[3].get_text()),
                docket_count=_clean(cells[4].get_text()),
                date_filed=_clean(cells[5].get_text()),
                date_closed=_clean(cells[6].get_text()) if len(cells) > 6 else "",
            )
        )
    return results


def _parse_file_rows(soup: BeautifulSoup) -> list[DocketFile]:
    """Columns: RowNum | FileNumber | Description | WebAccess | FileSize"""
    table = soup.find("table")
    if not table:
        return []
    files = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue
        files.append(
            DocketFile(
                file_number=_clean(cells[1].get_text()),
                description=_clean(cells[2].get_text()),
                web_access=_clean(cells[3].get_text()).upper() == "Y",
                size=_clean(cells[4].get_text()),
            )
        )
    return files

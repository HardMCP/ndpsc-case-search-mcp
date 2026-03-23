"""Case search and detail tools."""

import re
from datetime import date, datetime
from statistics import median

from pydantic import Field

from ndpsc_case_search_mcp.models.case import (
    CaseSummary,
    SEPARATOR,
    CaseCategory,
    CaseStatus,
    Jurisdiction,
)
from ndpsc_case_search_mcp.services import scraper

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date(value: str, name: str) -> str | None:
    if not value:
        return None
    if not _ISO_DATE.match(value):
        return f"Invalid {name}: '{value}'. Must be YYYY-MM-DD."
    return None


def _set_if_present(data: dict[str, str], key: str, value: str | None) -> None:
    if value is None or value == "":
        return
    data[key] = value


def _build_search_data(
    *,
    jurisdiction: Jurisdiction | None = None,
    case_year: str = "",
    case_seq: str = "",
    case_status: CaseStatus | None = None,
    case_type: str = "",
    case_category: CaseCategory | None = None,
    entity_name: str = "",
    description: str = "",
    date_filed_from: str = "",
    date_filed_to: str = "",
    date_closed_from: str = "",
    date_closed_to: str = "",
) -> dict[str, str]:
    data = {"search": "Search"}
    _set_if_present(data, "jurisdictionId", jurisdiction.value if jurisdiction else None)
    _set_if_present(data, "caseYear", case_year)
    _set_if_present(data, "caseSequence", case_seq)
    _set_if_present(data, "caseStatusCode", case_status.value if case_status else None)
    _set_if_present(data, "caseTypeCode", case_type)
    _set_if_present(
        data, "caseCategoryCode", case_category.value if case_category else None
    )
    _set_if_present(data, "entityName", entity_name)
    _set_if_present(data, "description", description)
    _set_if_present(data, "filedFromDate", date_filed_from)
    _set_if_present(data, "filedToDate", date_filed_to)
    _set_if_present(data, "closedFromDate", date_closed_from)
    _set_if_present(data, "closedToDate", date_closed_to)
    return data


def _parse_case_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _format_percent(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "-"
    return f"{(numerator / denominator) * 100:.1f}%"


def _format_days(value: float | int | None) -> str:
    if value is None:
        return "-"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}"


def _format_change(current: int | float | None, previous: int | float | None) -> str:
    if current is None or previous is None:
        return "n/a"
    if previous == 0:
        return "n/a"
    delta = ((current - previous) / previous) * 100
    return f"{delta:+.1f}%"


def _format_point_change(current: float | None, previous: float | None) -> str:
    if current is None or previous is None:
        return "n/a"
    return f"{current - previous:+.1f} pts"


def _format_day_change(current: float | None, previous: float | None) -> str:
    if current is None or previous is None:
        return "n/a"
    return f"{current - previous:+.1f} days"


def _summarize_year(cases: list[CaseSummary]) -> dict[str, int | float | None]:
    total = len(cases)
    closed = 0
    durations: list[int] = []
    for case in cases:
        filed = _parse_case_date(case.date_filed)
        closed_date = _parse_case_date(case.date_closed)
        if closed_date is None:
            continue
        closed += 1
        if filed is not None and closed_date >= filed:
            durations.append((closed_date - filed).days)

    open_cases = total - closed
    closure_rate = (closed / total) * 100 if total else None
    median_days = median(durations) if durations else None
    return {
        "filed": total,
        "closed": closed,
        "open": open_cases,
        "closure_rate": closure_rate,
        "median_days": median_days,
    }


async def search_cases(
    jurisdiction: Jurisdiction | None = Field(
        None, description="Jurisdiction filter. None for all."
    ),
    case_year: str = Field(
        "", description="2-digit year e.g. '25' for 2025. Leave blank for all years."
    ),
    case_seq: str = Field(
        "", description="Case sequence number e.g. '001'. Leave blank for all."
    ),
    case_status: CaseStatus | None = Field(
        None, description="Case status filter. None for all."
    ),
    case_type: str = Field(
        "",
        description="Case type e.g. 'Application', 'Rates', 'Complaint'. Leave blank for all.",
    ),
    case_category: CaseCategory | None = Field(
        None, description="Case category filter. None for all."
    ),
    entity_name: str = Field("", description="Partial entity/company name."),
    description: str = Field(
        "", description="Keyword search against case description."
    ),
    date_filed_from: str = Field(
        "", description="Start of date-filed range, YYYY-MM-DD"
    ),
    date_filed_to: str = Field("", description="End of date-filed range, YYYY-MM-DD"),
    date_closed_from: str = Field(
        "", description="Start of date-closed range, YYYY-MM-DD"
    ),
    date_closed_to: str = Field("", description="End of date-closed range, YYYY-MM-DD"),
) -> str:
    """Search ND PSC cases. At least one filter must be set.
    Returns all matching results. Broad searches may require multiple underlying requests."""
    for val, name in [
        (date_filed_from, "date_filed_from"),
        (date_filed_to, "date_filed_to"),
        (date_closed_from, "date_closed_from"),
        (date_closed_to, "date_closed_to"),
    ]:
        err = _validate_date(val, name)
        if err:
            return err

    data = _build_search_data(
        jurisdiction=jurisdiction,
        case_year=case_year,
        case_seq=case_seq,
        case_status=case_status,
        case_type=case_type,
        case_category=case_category,
        entity_name=entity_name,
        description=description,
        date_filed_from=date_filed_from,
        date_filed_to=date_filed_to,
        date_closed_from=date_closed_from,
        date_closed_to=date_closed_to,
    )

    if len(data) < 2:
        return "At least one search filter must be set."

    cases, total = await scraper.search_cases_all(data)

    if not cases:
        return "No results found."

    header = f"## {len(cases)} of {total} Case(s)\n"
    return header + SEPARATOR.join(str(c) for c in cases)


async def compare_case_type_by_year(
    case_type: str = Field(description="Case type, e.g. 'Rates' or 'Application'."),
    start_year: int = Field(description="Starting filing year, e.g. 2022."),
    end_year: int = Field(description="Ending filing year, e.g. 2025."),
    jurisdiction: Jurisdiction | None = Field(
        Jurisdiction.ALL_PUBLIC_UTILITIES,
        description="Jurisdiction filter. Defaults to public utilities.",
    ),
    case_category: CaseCategory | None = Field(
        None, description="Optional case category filter."
    ),
    entity_name: str = Field("", description="Optional partial entity/company name."),
) -> str:
    """Compare a case type across years using Date Closed as the disposition proxy."""
    if start_year > end_year:
        return "Invalid year range: start_year must be less than or equal to end_year."

    summaries: list[tuple[int, dict[str, int | float | None]]] = []
    for year in range(start_year, end_year + 1):
        cases, _ = await scraper.search_cases_all(
            _build_search_data(
                jurisdiction=jurisdiction,
                case_year=str(year % 100).zfill(2),
                case_type=case_type,
                case_category=case_category,
                entity_name=entity_name,
            )
        )
        summaries.append((year, _summarize_year(cases)))

    if not any(summary["filed"] for _, summary in summaries):
        return "No results found."

    lines = [f"## {case_type.strip()} Cases by Year\n"]
    lines.append(
        "| Year | Filed | Closed | Open | Closure Rate | Median Days to Close |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|")
    for year, summary in summaries:
        lines.append(
            "| "
            f"{year} | "
            f"{summary['filed']} | "
            f"{summary['closed']} | "
            f"{summary['open']} | "
            f"{_format_percent(int(summary['closed']), int(summary['filed']))} | "
            f"{_format_days(summary['median_days'])} |"
        )

    if len(summaries) > 1:
        lines.append("\n### Year-over-Year")
        for idx in range(1, len(summaries)):
            year, current = summaries[idx]
            previous_year, previous = summaries[idx - 1]
            lines.append(
                f"- **{year} vs {previous_year}:** "
                f"filed {_format_change(current['filed'], previous['filed'])}; "
                f"closure rate {_format_point_change(current['closure_rate'], previous['closure_rate'])}; "
                f"median days {_format_day_change(current['median_days'], previous['median_days'])}"
            )

    lines.append(
        "\n_Disposition proxy: cases with a `Date Closed` value are treated as closed; "
        "all others are treated as still open._"
    )
    return "\n".join(lines)


async def get_case_detail(
    year: str = Field(
        description="2-digit year from the case number e.g. '25' for PU-25-225"
    ),
    sequence: str = Field(
        description="Sequence number from the case number e.g. '225' for PU-25-225"
    ),
) -> str:
    """Get full detail for a specific case including docket summary."""
    detail = await scraper.fetch_case_detail(year, sequence)
    return str(detail)


async def get_docket_detail(
    year: str = Field(description="2-digit year from the case number"),
    sequence: str = Field(description="Case sequence number"),
    docket: str = Field(description="Docket number within the case"),
) -> str:
    """Get files within a specific docket, including direct PDF download links."""
    title, files = await scraper.fetch_docket_files(year, sequence, docket)

    lines = [f"## {title}\n", f"## Files ({len(files)})\n"]
    lines.append(SEPARATOR.join(str(f) for f in files))
    return "\n".join(lines)


ALL = [search_cases, compare_case_type_by_year, get_case_detail, get_docket_detail]

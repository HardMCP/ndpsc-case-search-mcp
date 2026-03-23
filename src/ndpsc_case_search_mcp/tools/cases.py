"""Case search and detail tools."""

import re

from pydantic import Field

from ndpsc_case_search_mcp.models.case import (
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
    Returns up to 100 results. Use narrower filters (date ranges, year) to find older cases."""
    for val, name in [
        (date_filed_from, "date_filed_from"),
        (date_filed_to, "date_filed_to"),
        (date_closed_from, "date_closed_from"),
        (date_closed_to, "date_closed_to"),
    ]:
        err = _validate_date(val, name)
        if err:
            return err

    data = {"search": "Search"}
    if jurisdiction:
        data["jurisdictionId"] = jurisdiction.value
    if case_year:
        data["caseYear"] = case_year
    if case_seq:
        data["caseSequence"] = case_seq
    if case_status:
        data["caseStatusCode"] = case_status.value
    if case_type:
        data["caseTypeCode"] = case_type
    if case_category:
        data["caseCategoryCode"] = case_category.value
    if entity_name:
        data["entityName"] = entity_name
    if description:
        data["description"] = description
    if date_filed_from:
        data["filedFromDate"] = date_filed_from
    if date_filed_to:
        data["filedToDate"] = date_filed_to
    if date_closed_from:
        data["closedFromDate"] = date_closed_from
    if date_closed_to:
        data["closedToDate"] = date_closed_to

    if len(data) < 2:
        return "At least one search filter must be set."

    cases, total = await scraper.search_cases(data)

    if not cases:
        return "No results found."

    header = f"## {len(cases)} of {total} Case(s)\n"
    return header + SEPARATOR.join(str(c) for c in cases)


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


ALL = [search_cases, get_case_detail, get_docket_detail]

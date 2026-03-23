# ndpsc-case-search-mcp

MCP server for searching North Dakota Public Service Commission case records. Scrapes https://apps.psc.nd.gov/cases/ — no official API exists.

## Structure

```
src/ndpsc_case_search_mcp/
  server.py                    # FastMCP server, health route, main()
  models/
    case.py                    # Pydantic models + enums (CaseSummary, CaseDetail, DocketFile, Jurisdiction, CaseStatus, CaseCategory)
  services/
    scraper.py                 # HTTP scraping helpers (httpx + BeautifulSoup)
  tools/
    __init__.py                # ALL_TOOLS aggregation
    cases.py                   # search_cases, get_case_detail, get_docket_detail
    documents.py               # get_document_text, get_document_pdf
```

## Architecture

- **Tools** are plain async functions registered via `mcp.tool(fn)` loop in `server.py`
- Each tool module exports an `ALL` list; `tools/__init__.py` concatenates them
- **Models** are Pydantic `BaseModel` subclasses with `__str__()` for markdown output
- **Services** handle all HTTP interaction with the PSC site
- Tools return `str` — models are joined with `SEPARATOR = "\n---\n"`
- Enums: `Jurisdiction`, `CaseStatus`, `CaseCategory` are `str, Enum` types used as tool params

## Data Source

- Site: https://apps.psc.nd.gov/cases/
- Search is a POST form; field names: `jurisdictionId`, `caseYear`, `caseSequence`, `caseStatusCode`, `caseTypeCode`, `caseCategoryCode`, `entityName`, `description`, `filedFromDate`, `filedToDate`, `closedFromDate`, `closedToDate`
- Dates must be YYYY-MM-DD (ISO format) — MM/DD/YYYY causes 500 errors
- Results capped at 100 per search (server-side pagination exists but requires Java session state that doesn't survive scraping)
- Case detail docket rows are JS-loaded; docket count is extracted from page text instead

## Development

```bash
uv sync
uv run ndpsc-case-search-mcp          # HTTP on 0.0.0.0:8000
fastmcp run fastmcp.json              # alternative via fastmcp CLI
```

## Deployment

- Docker: `docker build -t ndpsc-case-search-mcp .`
- Compose: `compose.yaml` with traefik labels for `hardmcp.com/ndpsc-case-search/mcp`
- Transport: HTTP (streamable), stateless mode, port 8000
- Health: GET `/health`

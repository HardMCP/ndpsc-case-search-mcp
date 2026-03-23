# ndpsc-case-search-mcp

An MCP server for searching [North Dakota Public Service Commission](https://www.psc.nd.gov/) case records, dockets, and documents.

The ND PSC regulates public utilities, pipelines, mining reclamation, and other industries in North Dakota. This server provides programmatic access to their case database via the [Model Context Protocol](https://modelcontextprotocol.io/).

## Tools

| Tool | Description |
|------|-------------|
| `search_cases` | Search cases by jurisdiction, year, status, category, entity, date range, and more. Automatically splits oversized searches so broad queries can return full result sets. |
| `compare_case_type_by_year` | Summarize a case type across years with filed, closed, open, closure-rate, and median-days-to-close metrics. |
| `get_case_detail` | Get full detail for a specific case including docket count. |
| `get_docket_detail` | List files within a docket with direct PDF download links. |
| `get_document_text` | Download a PDF and extract its text content. |
| `get_document_pdf` | Download a PDF and return it as base64-encoded bytes. |

## Usage

### Claude Web (Remote)

Add as a remote MCP server in Claude settings:

```
https://hardmcp.com/ndpsc-case-search/mcp
```

### Claude Code (Local)

```bash
# Run the server
uv run ndpsc-case-search-mcp

# Add to Claude Code
claude mcp add ndpsc-case-search --transport http http://localhost:8000/mcp
```

### Docker

```bash
docker build -t ndpsc-case-search-mcp .
docker run -p 8000:8000 ndpsc-case-search-mcp
```

## Development

Requires Python 3.11+.

```bash
uv sync
uv run ndpsc-case-search-mcp
```

The server starts on `http://0.0.0.0:8000` with a Streamable HTTP MCP endpoint at `/mcp` and a health check at `/health`.

## Data Source

This server scrapes [apps.psc.nd.gov/cases](https://apps.psc.nd.gov/cases/) -- no official API exists. The PSC site pages search results at 100 rows per request; this server automatically splits broad case searches into smaller filed-date ranges so `search_cases` can return the full result set.

## License

[MIT](LICENSE)

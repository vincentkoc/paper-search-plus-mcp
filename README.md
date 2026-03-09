# paper-search-plus-mcp

A curated Model Context Protocol server for searching and downloading academic papers from open and official sources such as arXiv, PubMed, OpenAlex, PMC, CORE, HAL, and Zenodo.

This fork intentionally trims the default surface to sources that are more reliable to test, easier to maintain, and safer to publish. Scraping-heavy or legally risky integrations are kept out of the advertised tool contract.

## Supported Sources

- arXiv
- PubMed
- bioRxiv
- medRxiv
- IACR ePrint
- CrossRef
- Semantic Scholar
- OpenAlex
- PubMed Central
- CORE
- Europe PMC
- DBLP
- HAL
- Zenodo

Source-by-source capabilities live in [docs/capability-matrix.md](docs/capability-matrix.md).

## Install

```bash
uv tool install paper-search-plus-mcp
```

For local development:

```bash
uv sync --group dev
uv run pytest -q
uv run paper-search-plus-mcp --list-tools
uv build --wheel
```

## Claude Desktop / MCP Config

```json
{
  "mcpServers": {
    "paper-search-plus-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/paper-search-plus-mcp", "paper-search-plus-mcp"]
    }
  }
}
```

## Source Policy

- Default public tools only cover open and official sources.
- Google Scholar, Sci-Hub, and SSRN are excluded from the default interface.
- bioRxiv search follows the official API model: category/date retrieval and DOI lookup, not arbitrary free-text search.

## Testing

- `uv run pytest -q` runs mocked unit tests and contract checks.
- `PAPER_SEARCH_PLUS_LIVE_SMOKE=1 uv run pytest tests/live -q` runs opt-in live smoke tests against real providers.

## CLI

List the public MCP tool surface without starting the stdio server:

```bash
uv run paper-search-plus-mcp --list-tools --json
```

Run the server:

```bash
uv run paper-search-plus-mcp
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch, test, and PR guidance.

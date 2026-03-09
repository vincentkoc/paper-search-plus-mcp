import asyncio
import json

from paper_search_plus_mcp import server

from .conftest import load_fixture


def test_public_tool_list_matches_golden_contract(capsys):
    expected = load_fixture("tool_names.json")

    rc = server.main(["--list-tools", "--json"])
    captured = capsys.readouterr()

    assert rc == 0
    assert json.loads(captured.out) == expected
    assert "search_google_scholar" not in expected
    assert "download_scihub" not in expected


def test_get_source_capabilities_matches_contract():
    payload = asyncio.run(server.get_source_capabilities())
    assert payload == load_fixture("source_capabilities.json")

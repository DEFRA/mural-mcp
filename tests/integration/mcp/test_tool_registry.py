"""Registration and schema tests for the MCP tool surface
(app/infra/mcp/tools.py), driven through the in-memory fastmcp.Client
(FastMCPTransport) -- cheap, and the generated schema is a contract this
repo did not write by hand.

Nothing in the suite previously touched register_tools(), the generated
input schemas, or the tool descriptions an LLM actually reads to choose a
tool -- see docs/python-testing-review.md F3.
"""

import pytest

from tests.support.app import mcp_registry_client

_EXPECTED_SCHEMAS = {
    "get_board_summary": {"mural_id", "use_spatial_grouping"},
    "get_region": {"mural_id", "region_id", "use_spatial_grouping", "offset"},
    "get_connections": {"mural_id", "widget_id"},
    "find_widgets": {"mural_id", "query", "widget_type", "region_id", "offset"},
    "get_image": {"mural_id", "widget_id", "size"},
}

_EXPECTED_REQUIRED = {
    "get_board_summary": {"mural_id"},
    "get_region": {"mural_id", "region_id"},
    "get_connections": {"mural_id", "widget_id"},
    "find_widgets": {"mural_id"},
    "get_image": {"mural_id", "widget_id"},
}


class TestRegistration:
    async def test_exposes_exactly_the_board_tools(self):
        async with mcp_registry_client() as client:
            tools = await client.list_tools()

            assert {t.name for t in tools} == set(_EXPECTED_SCHEMAS)


class TestToolSchema:
    @pytest.mark.parametrize("tool_name", sorted(_EXPECTED_SCHEMAS))
    async def test_exposes_only_its_public_parameters(self, tool_name):
        """No server-side parameter -- the fastmcp.Context each tool takes
        as `_ctx`, or a FromDishka-injected dependency -- leaks into the
        schema an LLM sees. If it did, a model would be asked to invent a
        value for it.
        """
        async with mcp_registry_client() as client:
            tools = {t.name: t for t in await client.list_tools()}

            properties = set(tools[tool_name].input_schema.get("properties") or {})

            assert properties == _EXPECTED_SCHEMAS[tool_name]

    @pytest.mark.parametrize("tool_name", sorted(_EXPECTED_SCHEMAS))
    async def test_marks_the_right_parameters_required(self, tool_name):
        async with mcp_registry_client() as client:
            tools = {t.name: t for t in await client.list_tools()}

            required = set(tools[tool_name].input_schema.get("required") or [])

            assert required == _EXPECTED_REQUIRED[tool_name]

    @pytest.mark.parametrize("tool_name", sorted(_EXPECTED_SCHEMAS))
    async def test_description_is_non_empty(self, tool_name):
        """Descriptions come from docstrings and are the primary thing an
        LLM uses to choose a tool -- an empty one is silently unusable."""
        async with mcp_registry_client() as client:
            tools = {t.name: t for t in await client.list_tools()}

            assert tools[tool_name].description
            assert tools[tool_name].description.strip() != ""


class TestOutputSchema:
    @pytest.mark.parametrize("tool_name", ["get_region", "find_widgets"])
    async def test_paged_tools_declare_the_paging_schema(self, tool_name):
        async with mcp_registry_client() as client:
            tools = {t.name: t for t in await client.list_tools()}

            schema = tools[tool_name].output_schema

            assert schema is not None
            assert {"shown", "total", "offset", "next_offset"} <= set(
                schema["properties"]
            )

    async def test_offset_cannot_be_negative(self):
        async with mcp_registry_client() as client:
            tools = {t.name: t for t in await client.list_tools()}

            offset = tools["get_region"].input_schema["properties"]["offset"]

            assert offset["minimum"] == 0


class TestAnnotations:
    @pytest.mark.parametrize("tool_name", sorted(_EXPECTED_SCHEMAS))
    async def test_every_tool_is_marked_read_only_with_a_title(self, tool_name):
        async with mcp_registry_client() as client:
            tools = {t.name: t for t in await client.list_tools()}

            tool = tools[tool_name]

            assert tool.annotations is not None
            assert tool.annotations.read_only_hint is True
            assert tool.title


class TestWidgetTypeChoices:
    async def test_find_widgets_lists_the_widget_types_it_accepts(self):
        async with mcp_registry_client() as client:
            tools = {t.name: t for t in await client.list_tools()}

            prop = tools["find_widgets"].input_schema["properties"]["widget_type"]
            choices = {
                value
                for option in prop.get("anyOf", [prop])
                for value in option.get("enum", [])
            }

            assert {"sticky note", "image", "area", "table cell"} <= choices

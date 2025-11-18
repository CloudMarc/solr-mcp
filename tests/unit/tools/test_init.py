"""Test tools initialization."""

from solr_mcp.tools import (
    TOOLS_DEFINITION,
    execute_add_documents,
    execute_atomic_update,
    execute_codebase_analytics,
    execute_codebase_statistics,
    execute_commit,
    execute_delete_documents,
    execute_fast_codebase_search,
    execute_fast_file_find,
    execute_list_collections,
    execute_list_fields,
    execute_query,
    execute_realtime_get,
    execute_schema_add_field,
    execute_schema_delete_field,
    execute_schema_get_field,
    execute_schema_list_fields,
    execute_select_query,
    execute_semantic_select_query,
    execute_terms,
    execute_vector_select_query,
    get_default_text_vectorizer,
)


def test_tools_definition():
    """Test that TOOLS_DEFINITION contains all expected tools."""
    # All tools should be in TOOLS_DEFINITION
    tools = {
        "solr_list_collections": execute_list_collections,
        "solr_list_fields": execute_list_fields,
        "solr_select": execute_select_query,
        "solr_vector_select": execute_vector_select_query,
        "solr_semantic_select": execute_semantic_select_query,
        "solr_query": execute_query,
        "solr_terms": execute_terms,
        "solr_atomic_update": execute_atomic_update,
        "solr_realtime_get": execute_realtime_get,
        "solr_schema_add_field": execute_schema_add_field,
        "solr_schema_list_fields": execute_schema_list_fields,
        "solr_schema_get_field": execute_schema_get_field,
        "solr_schema_delete_field": execute_schema_delete_field,
        "get_default_text_vectorizer": get_default_text_vectorizer,
        "solr_add_documents": execute_add_documents,
        "solr_delete_documents": execute_delete_documents,
        "solr_commit": execute_commit,
        "solr_fast_codebase_search": execute_fast_codebase_search,
        "solr_fast_file_find": execute_fast_file_find,
        "solr_codebase_statistics": execute_codebase_statistics,
        "solr_codebase_analytics": execute_codebase_analytics,
    }

    assert len(TOOLS_DEFINITION) == len(tools)

    for _tool_name, tool_func in tools.items():
        assert tool_func in TOOLS_DEFINITION


def test_tools_exports():
    """Test that __all__ exports all tools."""
    from solr_mcp.tools import __all__

    expected = {
        "execute_list_collections",
        "execute_list_fields",
        "execute_select_query",
        "execute_vector_select_query",
        "execute_semantic_select_query",
        "execute_query",
        "execute_terms",
        "execute_atomic_update",
        "execute_realtime_get",
        "execute_schema_add_field",
        "execute_schema_list_fields",
        "execute_schema_get_field",
        "execute_schema_delete_field",
        "get_default_text_vectorizer",
        "execute_add_documents",
        "execute_delete_documents",
        "execute_commit",
        "execute_fast_codebase_search",
        "execute_fast_file_find",
        "execute_codebase_statistics",
        "execute_codebase_analytics",
    }

    assert set(__all__) == expected

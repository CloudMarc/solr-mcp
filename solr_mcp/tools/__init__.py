"""Tool definitions for Solr MCP server."""

import inspect
import sys

from .solr_add_documents import execute_add_documents
from .solr_atomic_update import execute_atomic_update
from .solr_commit import execute_commit
from .solr_default_vectorizer import get_default_text_vectorizer
from .solr_delete_documents import execute_delete_documents
from .solr_list_collections import execute_list_collections
from .solr_list_fields import execute_list_fields
from .solr_query import execute_query
from .solr_realtime_get import execute_realtime_get
from .solr_schema_add_field import execute_schema_add_field
from .solr_schema_delete_field import execute_schema_delete_field
from .solr_schema_get_field import execute_schema_get_field
from .solr_schema_list_fields import execute_schema_list_fields
from .solr_select import execute_select_query
from .solr_semantic_select import execute_semantic_select_query
from .solr_terms import execute_terms
from .solr_vector_select import execute_vector_select_query
from .tool_decorator import get_schema, tool

__all__ = [
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
]

TOOLS_DEFINITION = [
    obj
    for name, obj in inspect.getmembers(sys.modules[__name__])
    if inspect.isfunction(obj) and hasattr(obj, "_is_tool") and obj._is_tool
]

"""SolrCloud client implementation."""

import logging
from typing import Any

import pysolr

from solr_mcp.solr.collections import (
    HttpCollectionProvider,
    ZooKeeperCollectionProvider,
)
from solr_mcp.solr.config import SolrConfig
from solr_mcp.solr.exceptions import (
    DocValuesError,
    IndexingError,
    QueryError,
    SolrError,
    SQLExecutionError,
    SQLParseError,
)
from solr_mcp.solr.interfaces import CollectionProvider, VectorSearchProvider
from solr_mcp.solr.query import QueryBuilder
from solr_mcp.solr.query.executor import QueryExecutor
from solr_mcp.solr.response import ResponseFormatter
from solr_mcp.solr.schema import FieldManager
from solr_mcp.solr.vector import VectorManager, VectorSearchResults
from solr_mcp.vector_provider import OllamaVectorProvider


logger = logging.getLogger(__name__)


class SolrClient:
    """Client for interacting with SolrCloud."""

    def __init__(
        self,
        config: SolrConfig,
        collection_provider: CollectionProvider | None = None,
        solr_client: pysolr.Solr | None = None,
        field_manager: FieldManager | None = None,
        vector_provider: VectorSearchProvider | None = None,
        query_builder: QueryBuilder | None = None,
        query_executor: QueryExecutor | None = None,
        response_formatter: ResponseFormatter | None = None,
    ):
        """Initialize the SolrClient with the given configuration and optional dependencies.

        Args:
            config: Configuration for the client
            collection_provider: Optional collection provider implementation
            solr_client: Optional pre-configured Solr client
            field_manager: Optional pre-configured field manager
            vector_provider: Optional vector search provider implementation
            query_builder: Optional pre-configured query builder
            query_executor: Optional pre-configured query executor
            response_formatter: Optional pre-configured response formatter
        """
        self.config = config
        self.base_url = config.solr_base_url.rstrip("/")

        # Initialize collection provider
        if collection_provider:
            self.collection_provider = collection_provider
        elif self.config.zookeeper_hosts:
            # Use ZooKeeper if hosts are specified
            self.collection_provider = ZooKeeperCollectionProvider(
                hosts=self.config.zookeeper_hosts
            )
        else:
            # Otherwise use HTTP provider
            self.collection_provider = HttpCollectionProvider(base_url=self.base_url)

        # Initialize field manager
        self.field_manager = field_manager or FieldManager(self.base_url)

        # Initialize vector provider
        self.vector_provider = vector_provider or OllamaVectorProvider()

        # Initialize query builder
        self.query_builder = query_builder or QueryBuilder(
            field_manager=self.field_manager
        )

        # Initialize query executor
        self.query_executor = query_executor or QueryExecutor(base_url=self.base_url)

        # Initialize response formatter
        self.response_formatter = response_formatter or ResponseFormatter()

        # Initialize vector manager with default top_k of 10
        self.vector_manager = VectorManager(
            self,
            self.vector_provider,  # type: ignore[arg-type]
            10,  # Default value for top_k
        )

        # Initialize Solr client
        self._solr_client = solr_client
        self._default_collection = None

    async def _get_or_create_client(self, collection: str) -> pysolr.Solr:
        """Get or create a Solr client for the given collection.

        Args:
            collection: Collection name to use.

        Returns:
            Configured Solr client

        Raises:
            SolrError: If no collection is specified
        """
        if not collection:
            raise SolrError("No collection specified")

        if not self._solr_client:
            self._solr_client = pysolr.Solr(
                f"{self.base_url}/{collection}", timeout=self.config.connection_timeout
            )

        return self._solr_client

    async def list_collections(self) -> list[str]:
        """List all available collections."""
        try:
            return await self.collection_provider.list_collections()
        except Exception as e:
            raise SolrError(f"Failed to list collections: {str(e)}")

    async def list_fields(self, collection: str) -> list[dict[str, Any]]:
        """List all fields in a collection with their properties."""
        try:
            return await self.field_manager.list_fields(collection)
        except Exception as e:
            raise SolrError(
                f"Failed to list fields for collection '{collection}': {str(e)}"
            )

    def _format_search_results(
        self, results: pysolr.Results, start: int = 0
    ) -> dict[str, Any]:
        """Format Solr search results for LLM consumption."""
        return self.response_formatter.format_search_results(results, start)

    async def execute_select_query(self, query: str) -> dict[str, Any]:
        """Execute a SQL SELECT query against Solr using the SQL interface."""
        try:
            # Parse and validate query
            logger.debug(f"Original query: {query}")
            preprocessed_query = self.query_builder.parser.preprocess_query(query)
            logger.debug(f"Preprocessed query: {preprocessed_query}")
            ast, collection, _ = self.query_builder.parse_and_validate_select(
                preprocessed_query
            )
            logger.debug(f"Parsed collection: {collection}")

            # Delegate execution to the query executor
            return await self.query_executor.execute_select_query(
                query=preprocessed_query, collection=collection
            )

        except (DocValuesError, SQLParseError, SQLExecutionError):
            # Re-raise these specific exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise SQLExecutionError(f"SQL query failed: {str(e)}")

    async def execute_vector_select_query(
        self, query: str, vector: list[float], field: str | None = None
    ) -> dict[str, Any]:
        """Execute SQL query filtered by vector similarity search.

        Args:
            query: SQL query to execute
            vector: Query vector for similarity search
            field: Optional name of the vector field to search against. If not provided, the first vector field will be auto-detected.

        Returns:
            Query results

        Raises:
            SolrError: If search fails
            QueryError: If query execution fails
        """
        try:
            # Parse and validate query
            ast, collection, _ = self.query_builder.parse_and_validate_select(query)

            # Validate and potentially auto-detect vector field
            field, field_info = await self.vector_manager.validate_vector_field(
                collection=collection, field=field
            )

            # Get limit and offset from query
            limit = 10  # Default limit
            if ast.args.get("limit"):
                try:
                    limit_expr = ast.args["limit"]
                    if hasattr(limit_expr, "expression"):
                        # Handle case where expression is a Literal
                        if hasattr(limit_expr.expression, "this"):
                            limit = int(limit_expr.expression.this)
                        else:
                            limit = int(limit_expr.expression)
                    else:
                        limit = int(limit_expr)
                except (ValueError, AttributeError):
                    limit = 10  # Fallback to default

            offset = ast.args.get("offset", 0)

            # For KNN search, we need to fetch limit + offset results to account for pagination
            top_k = limit + offset

            # Execute vector search
            client = await self._get_or_create_client(collection)
            results = await self.vector_manager.execute_vector_search(
                client=client, vector=vector, field=field, top_k=top_k
            )

            # Convert to VectorSearchResults
            vector_results = VectorSearchResults.from_solr_response(
                response=results, top_k=top_k
            )

            # Build SQL query with vector results
            doc_ids = vector_results.get_doc_ids()

            # Execute SQL query with the vector results
            stmt = query  # Start with original query

            # Check if query already has WHERE clause
            has_where = "WHERE" in stmt.upper()
            has_limit = "LIMIT" in stmt.upper()

            # Extract limit part if present to reposition it
            limit_part = ""
            if has_limit:
                # Use case-insensitive find and split
                limit_index = stmt.upper().find("LIMIT")
                stmt_before_limit = stmt[:limit_index].strip()
                limit_part = stmt[limit_index + 5 :].strip()  # +5 to skip "LIMIT"
                stmt = stmt_before_limit  # This is everything before LIMIT

            # Add WHERE clause at the proper position
            if doc_ids:
                # Add filter query if present
                if has_where:
                    stmt = f"{stmt} AND id IN ({','.join(doc_ids)})"
                else:
                    stmt = f"{stmt} WHERE id IN ({','.join(doc_ids)})"
            else:
                # No vector search results, return empty result set
                if has_where:
                    stmt = f"{stmt} AND 1=0"  # Always false condition
                else:
                    stmt = f"{stmt} WHERE 1=0"  # Always false condition

            # Add limit back at the end if it was present or add default limit
            if limit_part:
                stmt = f"{stmt} LIMIT {limit_part}"
            elif not has_limit:
                stmt = f"{stmt} LIMIT {limit}"

            # Execute the SQL query
            return await self.query_executor.execute_select_query(
                query=stmt, collection=collection
            )

        except Exception as e:
            if isinstance(e, (QueryError, SolrError)):
                raise
            raise QueryError(f"Error executing vector query: {str(e)}")

    async def execute_semantic_select_query(
        self,
        query: str,
        text: str,
        field: str | None = None,
        vector_provider_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute SQL query filtered by semantic similarity.

        Args:
            query: SQL query to execute
            text: Search text to convert to vector
            field: Optional name of the vector field to search against. If not provided, the first vector field will be auto-detected.
            vector_provider_config: Optional configuration for the vector provider
                                    Can include 'model', 'base_url', etc.

        Returns:
            Query results

        Raises:
            SolrError: If search fails
            QueryError: If query execution fails
        """
        try:
            # Parse and validate query to get collection name
            ast, collection, _ = self.query_builder.parse_and_validate_select(query)

            # Extract model from config if present
            model = (
                vector_provider_config.get("model") if vector_provider_config else None
            )

            # Validate and potentially auto-detect vector field
            field, field_info = await self.vector_manager.validate_vector_field(
                collection=collection, field=field, vector_provider_model=model
            )

            # Get vector using the vector provider configuration
            vector = await self.vector_manager.get_vector(text, vector_provider_config)

            # Reuse vector query logic
            return await self.execute_vector_select_query(query, vector, field)
        except Exception as e:
            if isinstance(e, (QueryError, SolrError)):
                raise
            raise SolrError(f"Semantic search failed: {str(e)}")

    async def add_documents(
        self,
        collection: str,
        documents: list[dict[str, Any]],
        commit: bool = True,
        commit_within: int | None = None,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        """Add or update documents in a Solr collection.

        Args:
            collection: The collection to add documents to
            documents: List of documents to add (each document is a dict)
            commit: Whether to commit immediately (default: True)
            commit_within: Commit within N milliseconds (alternative to commit)
            overwrite: Whether to overwrite existing documents with same ID (default: True)

        Returns:
            Response from Solr containing status information

        Raises:
            IndexingError: If indexing fails
            SolrError: If collection doesn't exist or other errors occur
        """
        try:
            if not documents:
                raise IndexingError("No documents provided")

            # Validate collection exists
            collections = await self.list_collections()
            if collection not in collections:
                raise SolrError(f"Collection '{collection}' does not exist")

            # Get or create client for this collection
            client = await self._get_or_create_client(collection)

            # Add documents using pysolr
            # pysolr.Solr.add is synchronous, but we're in async context
            # We'll use it directly since it's a quick operation
            client.add(
                documents,
                commit=commit,
                commitWithin=commit_within,
                overwrite=overwrite,
            )

            return {
                "status": "success",
                "collection": collection,
                "num_documents": len(documents),
                "committed": commit,
                "commit_within": commit_within,
            }

        except IndexingError:
            raise
        except SolrError:
            raise
        except Exception as e:
            raise IndexingError(f"Failed to add documents: {str(e)}")

    async def delete_documents(
        self,
        collection: str,
        ids: list[str] | None = None,
        query: str | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        """Delete documents from a Solr collection.

        Args:
            collection: The collection to delete from
            ids: List of document IDs to delete (mutually exclusive with query)
            query: Solr query to match documents to delete (mutually exclusive with ids)
            commit: Whether to commit immediately (default: True)

        Returns:
            Response from Solr containing status information

        Raises:
            IndexingError: If deletion fails or invalid parameters
            SolrError: If collection doesn't exist or other errors occur
        """
        try:
            # Validate parameters
            if ids and query:
                raise IndexingError("Cannot specify both 'ids' and 'query'")
            if not ids and not query:
                raise IndexingError("Must specify either 'ids' or 'query'")

            # Validate collection exists
            collections = await self.list_collections()
            if collection not in collections:
                raise SolrError(f"Collection '{collection}' does not exist")

            # Get or create client for this collection
            client = await self._get_or_create_client(collection)

            # Delete documents
            if ids:
                client.delete(id=ids, commit=commit)
                num_affected = len(ids)
            else:
                client.delete(q=query, commit=commit)
                num_affected = "unknown (query-based)"  # type: ignore[assignment]

            return {
                "status": "success",
                "collection": collection,
                "num_affected": num_affected,
                "committed": commit,
                "delete_by": "id" if ids else "query",
            }

        except IndexingError:
            raise
        except SolrError:
            raise
        except Exception as e:
            raise IndexingError(f"Failed to delete documents: {str(e)}")

    async def commit(
        self,
        collection: str,
        soft: bool = False,
        wait_searcher: bool = True,
        expunge_deletes: bool = False,
    ) -> dict[str, Any]:
        """Commit pending changes to a Solr collection.

        Args:
            collection: The collection to commit
            soft: If True, soft commit (visible but not durable)
                  If False, hard commit (durable to disk)
            wait_searcher: Wait for new searcher to open
            expunge_deletes: Merge away deleted documents

        Returns:
            Response from Solr containing status information

        Raises:
            SolrError: If commit fails
        """
        try:
            import requests

            # Validate collection exists
            collections = await self.list_collections()
            if collection not in collections:
                raise SolrError(f"Collection '{collection}' does not exist")

            # Build commit URL
            commit_url = f"{self.base_url}/{collection}/update"

            # Build commit parameters
            params = {"wt": "json"}

            if soft:
                params["softCommit"] = "true"
            else:
                params["commit"] = "true"
                params["waitSearcher"] = "true" if wait_searcher else "false"
                params["expungeDeletes"] = "true" if expunge_deletes else "false"

            # Execute commit
            response = requests.post(commit_url, params=params)

            if response.status_code != 200:
                raise SolrError(
                    f"Commit failed with status {response.status_code}: {response.text}"
                )

            return {
                "status": "success",
                "collection": collection,
                "commit_type": "soft" if soft else "hard",
                "committed": True,
            }

        except SolrError:
            raise
        except Exception as e:
            raise SolrError(f"Failed to commit: {str(e)}")

    async def execute_query(
        self,
        collection: str,
        q: str = "*:*",
        fq: list[str] | None = None,
        fl: str | None = None,
        rows: int = 10,
        start: int = 0,
        sort: str | None = None,
        highlight_fields: list[str] | None = None,
        highlight_snippets: int = 3,
        highlight_fragsize: int = 100,
        highlight_method: str = "unified",
        stats_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute a standard Solr query with optional highlighting and stats.

        Args:
            collection: Collection to query
            q: Main query string
            fq: Filter queries
            fl: Fields to return
            rows: Number of rows to return
            start: Offset for pagination
            sort: Sort specification
            highlight_fields: Fields to highlight
            highlight_snippets: Number of snippets per field
            highlight_fragsize: Size of each snippet
            highlight_method: Highlighting method (unified, original, fastVector)
            stats_fields: Fields to compute statistics for

        Returns:
            Query results with highlighting and stats if requested

        Raises:
            QueryError: If query fails
        """
        try:
            import requests

            # Build query URL
            query_url = f"{self.base_url}/{collection}/select"

            # Build query parameters
            params = {
                "q": q,
                "rows": rows,
                "start": start,
                "wt": "json",
            }

            if fq:
                params["fq"] = fq
            if fl:
                params["fl"] = fl
            if sort:
                params["sort"] = sort

            # Add highlighting parameters
            if highlight_fields:
                params["hl"] = "true"
                params["hl.fl"] = ",".join(highlight_fields)
                params["hl.snippets"] = highlight_snippets
                params["hl.fragsize"] = highlight_fragsize
                params["hl.method"] = highlight_method

            # Add stats parameters
            if stats_fields:
                params["stats"] = "true"
                params["stats.field"] = stats_fields

            # Execute query
            response = requests.get(query_url, params=params)  # type: ignore[arg-type]

            if response.status_code != 200:
                raise QueryError(
                    f"Query failed with status {response.status_code}: {response.text}"
                )

            result = response.json()

            # Format response
            formatted_result = {
                "num_found": result["response"]["numFound"],
                "docs": result["response"]["docs"],
                "start": result["response"].get("start", start),
                "query_info": {
                    "q": q,
                    "rows": rows,
                    "collection": collection,
                },
            }

            # Add highlighting if present
            if "highlighting" in result:
                formatted_result["highlighting"] = result["highlighting"]

            # Add stats if present
            if "stats" in result:
                formatted_result["stats"] = result["stats"]["stats_fields"]

            return formatted_result

        except QueryError:
            raise
        except Exception as e:
            raise QueryError(f"Query execution failed: {str(e)}")

    async def get_terms(
        self,
        collection: str,
        field: str,
        prefix: str | None = None,
        regex: str | None = None,
        limit: int = 10,
        min_count: int = 1,
        max_count: int | None = None,
    ) -> dict[str, Any]:
        """Get terms from a field using Solr's Terms Component.

        Args:
            collection: Collection to query
            field: Field to get terms from
            prefix: Filter terms by prefix
            regex: Filter terms by regex
            limit: Maximum number of terms
            min_count: Minimum document frequency
            max_count: Maximum document frequency

        Returns:
            Terms with their frequencies

        Raises:
            SolrError: If terms request fails
        """
        try:
            import requests

            # Build terms URL
            terms_url = f"{self.base_url}/{collection}/terms"

            # Build parameters
            params = {
                "terms.fl": field,
                "terms.limit": limit,
                "terms.mincount": min_count,
                "wt": "json",
            }

            if prefix:
                params["terms.prefix"] = prefix
            if regex:
                params["terms.regex"] = regex
            if max_count is not None:
                params["terms.maxcount"] = max_count

            # Execute request
            response = requests.get(terms_url, params=params)  # type: ignore[arg-type]

            if response.status_code != 200:
                raise SolrError(
                    f"Terms request failed with status {response.status_code}: {response.text}"
                )

            result = response.json()

            # Parse terms response
            # Solr returns terms as [term1, count1, term2, count2, ...]
            terms_data = result.get("terms", {}).get(field, [])
            terms_list = []

            for i in range(0, len(terms_data), 2):
                if i + 1 < len(terms_data):
                    terms_list.append(
                        {"term": terms_data[i], "frequency": terms_data[i + 1]}
                    )

            return {
                "terms": terms_list,
                "field": field,
                "collection": collection,
                "total_terms": len(terms_list),
            }

        except SolrError:
            raise
        except Exception as e:
            raise SolrError(f"Failed to get terms: {str(e)}")

    async def add_schema_field(
        self,
        collection: str,
        field_name: str,
        field_type: str,
        stored: bool = True,
        indexed: bool = True,
        required: bool = False,
        multiValued: bool = False,
        docValues: bool | None = None,
    ) -> dict[str, Any]:
        """Add a field to the schema.

        Args:
            collection: Collection name
            field_name: Name of the field
            field_type: Solr field type
            stored: Whether to store the field
            indexed: Whether to index the field
            required: Whether the field is required
            multiValued: Whether the field can have multiple values
            docValues: Whether to enable docValues

        Returns:
            Schema modification response

        Raises:
            SolrError: If schema modification fails
        """
        try:
            import requests

            # Build schema URL
            schema_url = f"{self.base_url}/{collection}/schema"

            # Build field definition
            field_def = {
                "name": field_name,
                "type": field_type,
                "stored": stored,
                "indexed": indexed,
                "required": required,
                "multiValued": multiValued,
            }

            if docValues is not None:
                field_def["docValues"] = docValues

            # Send request
            payload = {"add-field": field_def}

            response = requests.post(
                schema_url, json=payload, headers={"Content-Type": "application/json"}
            )

            if response.status_code not in [200, 201]:
                raise SolrError(
                    f"Schema modification failed with status {response.status_code}: {response.text}"
                )

            return {
                "status": "success",
                "field": field_def,
                "collection": collection,
            }

        except SolrError:
            raise
        except Exception as e:
            raise SolrError(f"Failed to add field: {str(e)}")

    async def get_schema_fields(self, collection: str) -> dict[str, Any]:
        """Get all fields from the schema.

        Args:
            collection: Collection name

        Returns:
            Schema fields information

        Raises:
            SolrError: If schema retrieval fails
        """
        try:
            import requests

            # Build schema URL
            schema_url = f"{self.base_url}/{collection}/schema/fields"

            response = requests.get(schema_url, params={"wt": "json"})

            if response.status_code != 200:
                raise SolrError(
                    f"Schema retrieval failed with status {response.status_code}: {response.text}"
                )

            result = response.json()

            return {
                "fields": result.get("fields", []),
                "collection": collection,
                "total_fields": len(result.get("fields", [])),
            }

        except SolrError:
            raise
        except Exception as e:
            raise SolrError(f"Failed to get schema fields: {str(e)}")

    async def get_schema_field(
        self, collection: str, field_name: str
    ) -> dict[str, Any]:
        """Get a specific field from the schema.

        Args:
            collection: Collection name
            field_name: Field name

        Returns:
            Field information

        Raises:
            SolrError: If field retrieval fails
        """
        try:
            import requests

            # Build schema URL
            schema_url = f"{self.base_url}/{collection}/schema/fields/{field_name}"

            response = requests.get(schema_url, params={"wt": "json"})

            if response.status_code != 200:
                raise SolrError(
                    f"Field retrieval failed with status {response.status_code}: {response.text}"
                )

            result = response.json()

            return {
                "field": result.get("field", {}),
                "collection": collection,
            }

        except SolrError:
            raise
        except Exception as e:
            raise SolrError(f"Failed to get field: {str(e)}")

    async def delete_schema_field(
        self, collection: str, field_name: str
    ) -> dict[str, Any]:
        """Delete a field from the schema.

        Args:
            collection: Collection name
            field_name: Field name

        Returns:
            Schema modification response

        Raises:
            SolrError: If schema modification fails
        """
        try:
            import requests

            # Build schema URL
            schema_url = f"{self.base_url}/{collection}/schema"

            # Send request
            payload = {"delete-field": {"name": field_name}}

            response = requests.post(
                schema_url, json=payload, headers={"Content-Type": "application/json"}
            )

            if response.status_code not in [200, 201]:
                raise SolrError(
                    f"Schema modification failed with status {response.status_code}: {response.text}"
                )

            return {
                "status": "success",
                "field_name": field_name,
                "collection": collection,
            }

        except SolrError:
            raise
        except Exception as e:
            raise SolrError(f"Failed to delete field: {str(e)}")

    async def atomic_update(
        self,
        collection: str,
        doc_id: str,
        updates: dict[str, dict[str, Any]],
        version: int | None = None,
        commit: bool = False,
        commitWithin: int | None = None,
    ) -> dict[str, Any]:
        """Atomically update specific fields in a document.

        Args:
            collection: Collection name
            doc_id: Document ID to update
            updates: Field updates as {field: {operation: value}}
            version: Optional version for optimistic concurrency
            commit: Whether to commit immediately
            commitWithin: Milliseconds to auto-commit

        Returns:
            Update response

        Raises:
            SolrError: If update fails
            IndexingError: If document not found or version mismatch
        """
        try:
            import requests

            # Validate collection exists
            collections = await self.list_collections()
            if collection not in collections:
                raise SolrError(f"Collection '{collection}' does not exist")

            # Build update URL
            update_url = f"{self.base_url}/{collection}/update"

            # Build document with atomic updates
            doc = {"id": doc_id}

            # Add version for optimistic concurrency if provided
            if version is not None:
                doc["_version_"] = version  # type: ignore[assignment]

            # Add atomic update operations
            for field, operation in updates.items():
                doc[field] = operation  # type: ignore[assignment]

            # Build request
            payload = [doc]
            params = {"wt": "json"}

            if commit:
                params["commit"] = "true"
            elif commitWithin is not None:
                params["commitWithin"] = str(commitWithin)

            # Execute update
            response = requests.post(
                update_url,
                json=payload,
                params=params,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                error_text = response.text
                # Check for version conflict
                if "version conflict" in error_text.lower():
                    raise IndexingError(
                        f"Version conflict: Document has been modified. "
                        f"Expected version {version} but document has different version."
                    )
                raise SolrError(
                    f"Atomic update failed with status {response.status_code}: {error_text}"
                )

            result = response.json()

            # Extract new version if available
            new_version = None
            if "responseHeader" in result and "rf" in result:
                # Version might be in the response
                new_version = result.get("_version_")

            return {
                "status": "success",
                "doc_id": doc_id,
                "collection": collection,
                "version": new_version,
                "updates_applied": len(updates),
            }

        except (SolrError, IndexingError):
            raise
        except Exception as e:
            raise SolrError(f"Failed to perform atomic update: {str(e)}")

    async def realtime_get(
        self,
        collection: str,
        doc_ids: list[str],
        fl: str | None = None,
    ) -> dict[str, Any]:
        """Get documents in real-time, including uncommitted changes.

        Args:
            collection: Collection name
            doc_ids: List of document IDs
            fl: Optional comma-separated list of fields

        Returns:
            Retrieved documents

        Raises:
            SolrError: If get fails
        """
        try:
            import requests

            # Validate collection exists
            collections = await self.list_collections()
            if collection not in collections:
                raise SolrError(f"Collection '{collection}' does not exist")

            # Build RTG URL
            rtg_url = f"{self.base_url}/{collection}/get"

            # Build parameters
            params = {"wt": "json"}

            # Add IDs
            if len(doc_ids) == 1:
                params["id"] = doc_ids[0]
            else:
                params["ids"] = ",".join(doc_ids)

            # Add field list if specified
            if fl:
                params["fl"] = fl

            # Execute request
            response = requests.get(rtg_url, params=params)

            if response.status_code != 200:
                raise SolrError(
                    f"Real-time get failed with status {response.status_code}: {response.text}"
                )

            result = response.json()

            # Handle single vs multiple docs
            if "doc" in result:
                # Single document
                docs = [result["doc"]] if result["doc"] is not None else []
            elif "response" in result:
                # Multiple documents
                docs = result["response"].get("docs", [])
            else:
                docs = []

            return {
                "docs": docs,
                "num_found": len(docs),
                "collection": collection,
            }

        except SolrError:
            raise
        except Exception as e:
            raise SolrError(f"Failed to get documents: {str(e)}")

"""Vector search results handling."""

from typing import Any

from pydantic import BaseModel, Field


class VectorSearchResult(BaseModel):
    """Individual vector search result."""

    docid: str = Field(description="Internal Solr document ID (_docid_)")
    score: float = Field(description="Search score")
    distance: float | None = Field(None, description="Vector distance if available")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def __getitem__(self, key):
        """Make result subscriptable."""
        key_map = {
            "docid": self.docid,
            "score": self.score,
            "distance": self.distance,
            "metadata": self.metadata,
        }
        if key in key_map:
            return key_map[key]
        raise KeyError(f"Invalid key: {key}")


class VectorSearchResults(BaseModel):
    """Container for vector search results."""

    results: list[VectorSearchResult] = Field(
        default_factory=list, description="List of search results"
    )
    total_found: int = Field(0, description="Total number of results found")
    top_k: int = Field(..., description="Number of results requested")
    query_time_ms: int | None = Field(
        None, description="Query execution time in milliseconds"
    )

    @property
    def docs(self) -> list[VectorSearchResult]:
        """Get list of search results."""
        return self.results

    @classmethod
    def from_solr_response(
        cls, response: dict[str, Any], top_k: int = 10
    ) -> "VectorSearchResults":
        """Create VectorSearchResults from Solr response.

        Args:
            response: Raw Solr response dictionary
            top_k: Number of results requested

        Returns:
            VectorSearchResults instance
        """
        # Extract response header
        header = response.get("responseHeader", {})
        query_time = header.get("QTime")

        # Extract main response section
        resp = response.get("response", {})
        docs = resp.get("docs", [])

        # Create results list
        results = []
        for doc in docs:
            # Handle both string and numeric _docid_
            docid = doc.get("_docid_")
            if docid is None:
                # Try alternate field names
                docid = doc.get("[docid]") or doc.get("docid") or "0"
            docid = str(docid)  # Ensure string type

            result = VectorSearchResult(
                docid=docid,
                score=doc.get("score", 0.0),
                distance=doc.get("_vector_distance_"),
                metadata={
                    k: v
                    for k, v in doc.items()
                    if k
                    not in ["_docid_", "[docid]", "docid", "score", "_vector_distance_"]
                },
            )
            results.append(result)

        # Create VectorSearchResults
        return cls(
            results=results,
            total_found=resp.get("numFound", 0),
            top_k=top_k,
            query_time_ms=query_time,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert results to dictionary format.

        Returns:
            Dictionary representation of results
        """
        return {
            "results": [result.model_dump() for result in self.results],
            "metadata": {
                "total_found": self.total_found,
                "top_k": self.top_k,
                "query_time_ms": self.query_time_ms,
            },
        }

    def get_doc_ids(self) -> list[str]:
        """Get list of document IDs from results.

        Returns:
            List of document IDs
        """
        return [result.docid for result in self.results]

    def get_scores(self) -> list[float]:
        """Get list of scores from results.

        Returns:
            List of scores
        """
        return [result.score for result in self.results]

    def get_distances(self) -> list[float | None]:
        """Get list of vector distances from results.

        Returns:
            List of distances (None if not available)
        """
        return [result.distance for result in self.results]

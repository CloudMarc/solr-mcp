# Terms Component and Schema API Guide

This guide covers the Terms Component and Schema API features available in the Solr MCP server.

## Table of Contents

- [Terms Component](#terms-component)
  - [Overview](#terms-overview)
  - [Basic Usage](#basic-terms-usage)
  - [Filtering Options](#terms-filtering)
  - [Use Cases](#terms-use-cases)
  - [Examples](#terms-examples)
- [Schema API](#schema-api)
  - [Overview](#schema-overview)
  - [Add Fields](#add-fields)
  - [List Fields](#list-fields)
  - [Get Field Details](#get-field-details)
  - [Delete Fields](#delete-fields)
  - [Use Cases](#schema-use-cases)
  - [Examples](#schema-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Terms Component

### Terms Overview

The Terms Component provides access to indexed terms in Solr fields, enabling:

- **Autocomplete/Typeahead**: Suggest completions as users type
- **Vocabulary Exploration**: Discover what terms exist in your index
- **Query Expansion**: Find related terms for better search
- **Data Validation**: Check what values are actually indexed

### Basic Terms Usage

```python
# Get terms from a field
result = solr_terms(
    collection="articles",
    field="title",
    limit=10
)
```

**Response:**
```json
{
  "terms": [
    {"term": "machine", "frequency": 45},
    {"term": "learning", "frequency": 42},
    {"term": "data", "frequency": 38},
    {"term": "science", "frequency": 35}
  ],
  "field": "title",
  "collection": "articles",
  "total_terms": 4
}
```

### Terms Filtering

The `solr_terms` tool supports multiple filtering options:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `collection` | str | required | Collection name |
| `field` | str | required | Field to get terms from |
| `prefix` | str | None | Return terms starting with this prefix |
| `regex` | str | None | Return terms matching this regex |
| `limit` | int | 10 | Maximum number of terms to return |
| `min_count` | int | 1 | Minimum document frequency |
| `max_count` | int | None | Maximum document frequency |

#### Prefix Filtering

Get terms starting with a specific prefix (great for autocomplete):

```python
result = solr_terms(
    collection="articles",
    field="tags",
    prefix="mach",
    limit=10
)
# Returns: ["machine", "machinery", "machining", ...]
```

#### Regex Filtering

Use regex patterns for advanced matching:

```python
result = solr_terms(
    collection="products",
    field="sku",
    regex="PROD-[0-9]{4}",
    limit=20
)
# Returns: ["PROD-1001", "PROD-1002", ...]
```

#### Frequency Filtering

Filter by document frequency:

```python
# Get common terms (appear in many docs)
result = solr_terms(
    collection="articles",
    field="keywords",
    min_count=50,  # At least 50 documents
    limit=20
)

# Get rare terms (appear in few docs)
result = solr_terms(
    collection="articles",
    field="specialty_terms",
    max_count=5,  # At most 5 documents
    limit=20
)
```

### Terms Use Cases

#### 1. Autocomplete/Typeahead

Provide search suggestions as users type:

```python
def get_autocomplete_suggestions(user_input, limit=10):
    """Get autocomplete suggestions based on user input."""
    result = solr_terms(
        collection="products",
        field="name",
        prefix=user_input.lower(),
        limit=limit,
        min_count=2  # Only suggest terms that appear multiple times
    )
    return [term["term"] for term in result["terms"]]

# User types "lapt"
suggestions = get_autocomplete_suggestions("lapt")
# Returns: ["laptop", "laptops", "laptop-bag", ...]
```

#### 2. Tag/Category Discovery

Explore available tags or categories:

```python
# Find all available tags
result = solr_terms(
    collection="blog_posts",
    field="tags",
    limit=100,
    min_count=5  # Only tags used 5+ times
)

# Display popular tags
for term in result["terms"]:
    print(f"{term['term']}: {term['frequency']} posts")
```

#### 3. Data Quality Analysis

Check what values are actually in your index:

```python
# Check for unexpected values
result = solr_terms(
    collection="products",
    field="status",
    limit=100
)

expected_statuses = {"active", "inactive", "pending"}
actual_statuses = {term["term"] for term in result["terms"]}
unexpected = actual_statuses - expected_statuses

if unexpected:
    print(f"Warning: Unexpected statuses found: {unexpected}")
```

#### 4. Query Expansion

Find related terms to improve search:

```python
# User searches for "car"
result = solr_terms(
    collection="vehicles",
    field="type",
    prefix="car",
    limit=20
)

# Get expanded terms
expanded_terms = [term["term"] for term in result["terms"]]
# Returns: ["car", "cars", "cargo", "caravan", ...]

# Use for search: q="car OR cars OR cargo OR caravan"
```

### Terms Examples

#### Example 1: Multi-language Autocomplete

```python
def multilingual_autocomplete(prefix, language, limit=10):
    """Autocomplete with language-specific fields."""
    field_map = {
        "en": "name_en",
        "es": "name_es",
        "fr": "name_fr"
    }

    result = solr_terms(
        collection="products",
        field=field_map.get(language, "name_en"),
        prefix=prefix,
        limit=limit,
        min_count=1
    )

    return [
        {
            "suggestion": term["term"],
            "frequency": term["frequency"]
        }
        for term in result["terms"]
    ]

# User in Spanish interface types "tel"
suggestions = multilingual_autocomplete("tel", "es", limit=5)
# Returns: ["teléfono", "televisión", "teclado", ...]
```

#### Example 2: Tag Cloud Generation

```python
def generate_tag_cloud(collection, field, min_frequency=10):
    """Generate tag cloud data with term frequencies."""
    result = solr_terms(
        collection=collection,
        field=field,
        limit=100,
        min_count=min_frequency
    )

    # Calculate relative sizes (normalize frequencies)
    if result["terms"]:
        max_freq = max(term["frequency"] for term in result["terms"])
        min_freq = min(term["frequency"] for term in result["terms"])

        tag_cloud = []
        for term in result["terms"]:
            # Size from 1-5 based on frequency
            size = 1 + int(4 * (term["frequency"] - min_freq) / (max_freq - min_freq))
            tag_cloud.append({
                "term": term["term"],
                "frequency": term["frequency"],
                "size": size
            })

        return tag_cloud
    return []

# Generate tag cloud
tags = generate_tag_cloud("blog", "tags", min_frequency=5)
# Returns: [{"term": "ai", "frequency": 45, "size": 5}, ...]
```

#### Example 3: Field Vocabulary Explorer

```python
def explore_field_vocabulary(collection, field, pattern=None):
    """Explore the vocabulary of a field."""
    params = {
        "collection": collection,
        "field": field,
        "limit": 1000
    }

    if pattern:
        params["regex"] = pattern

    result = solr_terms(**params)

    print(f"\nVocabulary for {collection}.{field}")
    print(f"Total unique terms: {result['total_terms']}")
    print(f"\nTop 20 terms:")

    for term in result["terms"][:20]:
        print(f"  {term['term']:30} {term['frequency']:6} docs")

    # Statistics
    frequencies = [term["frequency"] for term in result["terms"]]
    if frequencies:
        print(f"\nFrequency statistics:")
        print(f"  Min: {min(frequencies)}")
        print(f"  Max: {max(frequencies)}")
        print(f"  Mean: {sum(frequencies) / len(frequencies):.1f}")

# Explore product categories
explore_field_vocabulary("products", "category")
```

## Schema API

### Schema Overview

The Schema API allows dynamic modification of Solr collection schemas without manual configuration file editing. Available operations:

- **Add Fields**: Create new fields dynamically
- **List Fields**: View all schema fields
- **Get Field**: Inspect specific field properties
- **Delete Fields**: Remove unused fields

### Add Fields

Add new fields to a collection schema:

```python
result = solr_schema_add_field(
    collection="products",
    field_name="summary",
    field_type="text_general",
    stored=True,
    indexed=True,
    required=False,
    multiValued=False,
    docValues=None  # Auto-determined by field type
)
```

#### Common Field Types

| Field Type | Use Case | Example |
|------------|----------|---------|
| `string` | Exact match, not analyzed | SKU, ID, exact categories |
| `text_general` | Full-text search | Titles, descriptions, content |
| `pint` | Integer numbers | Quantities, counts |
| `plong` | Large integers | Timestamps, large IDs |
| `pfloat` | Floating point | Prices, ratings |
| `pdouble` | High-precision floats | Scientific data, coordinates |
| `pdate` | Date/time | Created dates, modified dates |
| `boolean` | True/false | Flags, status indicators |
| `location` | Geo-spatial | Coordinates, locations |

#### Field Properties

| Property | Type | Description |
|----------|------|-------------|
| `stored` | bool | Store the original value (needed for retrieval) |
| `indexed` | bool | Index for searching |
| `required` | bool | Must be present in all documents |
| `multiValued` | bool | Can contain multiple values |
| `docValues` | bool | Enable for sorting/faceting/stats |

#### Add Field Examples

**Text field for full-text search:**
```python
solr_schema_add_field(
    collection="articles",
    field_name="abstract",
    field_type="text_general",
    stored=True,
    indexed=True
)
```

**Numeric field with docValues for sorting:**
```python
solr_schema_add_field(
    collection="products",
    field_name="price",
    field_type="pfloat",
    stored=True,
    indexed=True,
    docValues=True  # Enable sorting/stats
)
```

**Multi-valued field for tags:**
```python
solr_schema_add_field(
    collection="articles",
    field_name="tags",
    field_type="string",
    stored=True,
    indexed=True,
    multiValued=True  # Multiple tags per article
)
```

**Required field:**
```python
solr_schema_add_field(
    collection="users",
    field_name="email",
    field_type="string",
    stored=True,
    indexed=True,
    required=True  # Every document must have this
)
```

### List Fields

Get all fields in a collection schema:

```python
result = solr_schema_list_fields(
    collection="products"
)
```

**Response:**
```json
{
  "fields": [
    {
      "name": "id",
      "type": "string",
      "stored": true,
      "indexed": true
    },
    {
      "name": "price",
      "type": "pfloat",
      "stored": true,
      "indexed": true,
      "docValues": true
    }
  ],
  "collection": "products",
  "total_fields": 2
}
```

### Get Field Details

Get detailed information about a specific field:

```python
result = solr_schema_get_field(
    collection="products",
    field_name="price"
)
```

**Response:**
```json
{
  "field": {
    "name": "price",
    "type": "pfloat",
    "stored": true,
    "indexed": true,
    "docValues": true,
    "required": false,
    "multiValued": false
  },
  "collection": "products"
}
```

### Delete Fields

Remove fields from a schema:

```python
result = solr_schema_delete_field(
    collection="products",
    field_name="old_field"
)
```

**⚠️ Warning**: Deletion is permanent and cannot be undone. Documents will lose data in deleted fields.

### Schema Use Cases

#### 1. Dynamic Schema Evolution

Add fields as your data model evolves:

```python
def add_product_review_fields(collection):
    """Add fields for product review feature."""
    fields = [
        {
            "name": "review_count",
            "type": "pint",
            "docValues": True
        },
        {
            "name": "average_rating",
            "type": "pfloat",
            "docValues": True
        },
        {
            "name": "verified_purchases",
            "type": "pint",
            "docValues": True
        }
    ]

    for field_def in fields:
        solr_schema_add_field(
            collection=collection,
            field_name=field_def["name"],
            field_type=field_def["type"],
            stored=True,
            indexed=True,
            docValues=field_def.get("docValues", False)
        )
        print(f"Added field: {field_def['name']}")

add_product_review_fields("products")
```

#### 2. Schema Validation

Check if required fields exist before indexing:

```python
def validate_schema(collection, required_fields):
    """Validate that collection has required fields."""
    result = solr_schema_list_fields(collection)

    existing_fields = {field["name"] for field in result["fields"]}
    missing_fields = set(required_fields) - existing_fields

    if missing_fields:
        print(f"Missing required fields: {missing_fields}")
        return False

    print(f"Schema validation passed for {collection}")
    return True

# Before indexing documents
required = ["id", "title", "content", "created_date"]
if validate_schema("articles", required):
    # Proceed with indexing
    pass
```

#### 3. Schema Documentation

Generate schema documentation:

```python
def document_schema(collection, output_file=None):
    """Generate documentation for a collection's schema."""
    result = solr_schema_list_fields(collection)

    doc = f"# Schema Documentation: {collection}\n\n"
    doc += f"Total Fields: {result['total_fields']}\n\n"
    doc += "## Fields\n\n"

    for field in result["fields"]:
        doc += f"### {field['name']}\n"
        doc += f"- **Type**: {field['type']}\n"
        doc += f"- **Stored**: {field.get('stored', 'N/A')}\n"
        doc += f"- **Indexed**: {field.get('indexed', 'N/A')}\n"

        if field.get('multiValued'):
            doc += f"- **Multi-valued**: Yes\n"
        if field.get('required'):
            doc += f"- **Required**: Yes\n"
        if field.get('docValues'):
            doc += f"- **DocValues**: Yes (sortable/facetable)\n"

        doc += "\n"

    if output_file:
        with open(output_file, 'w') as f:
            f.write(doc)
        print(f"Schema documentation saved to {output_file}")
    else:
        print(doc)

    return doc

# Generate documentation
document_schema("products", "schema_products.md")
```

#### 4. Multi-environment Setup

Ensure consistent schemas across environments:

```python
def sync_schema_fields(source_collection, target_collection, field_names):
    """Sync specific fields from source to target collection."""
    for field_name in field_names:
        # Get field definition from source
        source_field = solr_schema_get_field(
            collection=source_collection,
            field_name=field_name
        )

        field = source_field["field"]

        # Add to target (if doesn't exist)
        try:
            solr_schema_add_field(
                collection=target_collection,
                field_name=field["name"],
                field_type=field["type"],
                stored=field.get("stored", True),
                indexed=field.get("indexed", True),
                required=field.get("required", False),
                multiValued=field.get("multiValued", False),
                docValues=field.get("docValues")
            )
            print(f"Synced field: {field_name}")
        except Exception as e:
            print(f"Field {field_name} may already exist: {e}")

# Sync fields from production to staging
sync_schema_fields(
    source_collection="products_prod",
    target_collection="products_staging",
    field_names=["new_feature_field", "rating_v2"]
)
```

### Schema Examples

#### Example 1: Complete Schema Setup

```python
def setup_product_schema(collection):
    """Set up complete schema for product collection."""

    schema_fields = [
        # Core fields
        {
            "name": "sku",
            "type": "string",
            "stored": True,
            "indexed": True,
            "required": True
        },
        {
            "name": "name",
            "type": "text_general",
            "stored": True,
            "indexed": True,
            "required": True
        },
        {
            "name": "description",
            "type": "text_general",
            "stored": True,
            "indexed": True
        },

        # Pricing
        {
            "name": "price",
            "type": "pfloat",
            "stored": True,
            "indexed": True,
            "docValues": True
        },
        {
            "name": "sale_price",
            "type": "pfloat",
            "stored": True,
            "indexed": True,
            "docValues": True
        },

        # Categorization
        {
            "name": "category",
            "type": "string",
            "stored": True,
            "indexed": True,
            "multiValued": True
        },
        {
            "name": "tags",
            "type": "string",
            "stored": True,
            "indexed": True,
            "multiValued": True
        },

        # Inventory
        {
            "name": "stock_quantity",
            "type": "pint",
            "stored": True,
            "indexed": True,
            "docValues": True
        },
        {
            "name": "in_stock",
            "type": "boolean",
            "stored": True,
            "indexed": True
        },

        # Ratings
        {
            "name": "average_rating",
            "type": "pfloat",
            "stored": True,
            "indexed": True,
            "docValues": True
        },
        {
            "name": "review_count",
            "type": "pint",
            "stored": True,
            "indexed": True,
            "docValues": True
        },

        # Dates
        {
            "name": "created_date",
            "type": "pdate",
            "stored": True,
            "indexed": True,
            "docValues": True
        },
        {
            "name": "modified_date",
            "type": "pdate",
            "stored": True,
            "indexed": True,
            "docValues": True
        }
    ]

    print(f"Setting up schema for {collection}...")

    for field_def in schema_fields:
        try:
            solr_schema_add_field(
                collection=collection,
                field_name=field_def["name"],
                field_type=field_def["type"],
                stored=field_def.get("stored", True),
                indexed=field_def.get("indexed", True),
                required=field_def.get("required", False),
                multiValued=field_def.get("multiValued", False),
                docValues=field_def.get("docValues")
            )
            print(f"  ✓ Added {field_def['name']}")
        except Exception as e:
            print(f"  ✗ Failed to add {field_def['name']}: {e}")

    print("Schema setup complete!")

# Set up the schema
setup_product_schema("products_v2")
```

#### Example 2: Schema Comparison

```python
def compare_schemas(collection1, collection2):
    """Compare schemas between two collections."""
    schema1 = solr_schema_list_fields(collection1)
    schema2 = solr_schema_list_fields(collection2)

    fields1 = {f["name"]: f for f in schema1["fields"]}
    fields2 = {f["name"]: f for f in schema2["fields"]}

    # Find differences
    only_in_1 = set(fields1.keys()) - set(fields2.keys())
    only_in_2 = set(fields2.keys()) - set(fields1.keys())
    common = set(fields1.keys()) & set(fields2.keys())

    print(f"\nSchema Comparison: {collection1} vs {collection2}")
    print(f"{'='*60}")

    if only_in_1:
        print(f"\nOnly in {collection1}:")
        for field in sorted(only_in_1):
            print(f"  - {field}")

    if only_in_2:
        print(f"\nOnly in {collection2}:")
        for field in sorted(only_in_2):
            print(f"  - {field}")

    # Check for type mismatches in common fields
    mismatches = []
    for field in common:
        if fields1[field].get("type") != fields2[field].get("type"):
            mismatches.append((
                field,
                fields1[field].get("type"),
                fields2[field].get("type")
            ))

    if mismatches:
        print(f"\nType mismatches in common fields:")
        for field, type1, type2 in mismatches:
            print(f"  - {field}: {type1} vs {type2}")

    print(f"\nCommon fields: {len(common)}")
    print(f"Total in {collection1}: {len(fields1)}")
    print(f"Total in {collection2}: {len(fields2)}")

# Compare production and staging
compare_schemas("products_prod", "products_staging")
```

## Best Practices

### Terms Component Best Practices

1. **Use appropriate limits**:
   ```python
   # For autocomplete, 10-20 suggestions is enough
   solr_terms(field="name", prefix=user_input, limit=10)

   # For vocabulary exploration, use larger limits
   solr_terms(field="tags", limit=1000)
   ```

2. **Filter by frequency**:
   ```python
   # Avoid suggesting very rare terms
   solr_terms(field="tags", min_count=5)
   ```

3. **Index considerations**:
   - Terms component works on indexed fields
   - Use appropriate analyzers for the field
   - Consider creating dedicated autocomplete fields

4. **Performance**:
   - Cache frequent term requests
   - Use prefix filtering for better performance than regex
   - Limit the number of terms returned

### Schema API Best Practices

1. **Plan schema changes**:
   - Document field purposes
   - Choose appropriate field types
   - Consider sortability needs (docValues)

2. **Test before production**:
   ```python
   # Test in dev first
   solr_schema_add_field(collection="products_dev", ...)
   # Then promote to production
   solr_schema_add_field(collection="products_prod", ...)
   ```

3. **Field naming conventions**:
   - Use clear, descriptive names
   - Follow consistent patterns (snake_case or camelCase)
   - Prefix special purpose fields (e.g., `sort_name`)

4. **Required fields**:
   - Only make fields required if truly necessary
   - Consider defaults instead of required
   - Document required fields clearly

5. **Multi-valued fields**:
   - Use for arrays/lists
   - Cannot be used for sorting
   - Good for tags, categories, authors

6. **DocValues**:
   - Enable for fields used in sorting
   - Enable for fields used in faceting
   - Enable for fields used in stats
   - Small performance cost, big benefit

## Troubleshooting

### Terms Component Issues

**Problem**: No terms returned
- **Solution**: Verify field is indexed
- **Solution**: Check that collection has documents
- **Solution**: Verify field name is correct

**Problem**: Too many terms returned
- **Solution**: Use `limit` parameter
- **Solution**: Add `min_count` filter
- **Solution**: Use `prefix` or `regex` to narrow results

**Problem**: Terms not matching expected values
- **Solution**: Check field analyzer configuration
- **Solution**: Verify documents are actually indexed
- **Solution**: Check for case sensitivity issues

### Schema API Issues

**Problem**: Field already exists
- **Solution**: Use `solr_schema_get_field` to check first
- **Solution**: Delete old field first (if safe)
- **Solution**: Use a different field name

**Problem**: Cannot delete field
- **Solution**: Ensure field is not in use
- **Solution**: Check for schema dependencies
- **Solution**: Verify you have write permissions

**Problem**: Field type not found
- **Solution**: Check available field types in schema
- **Solution**: Verify field type name is correct
- **Solution**: Use standard Solr field types

**Problem**: DocValues error
- **Solution**: Not all field types support docValues
- **Solution**: Reindex may be required for existing data
- **Solution**: Check field type compatibility

## API Reference

### solr_terms

```python
solr_terms(
    collection: str,          # Collection name (required)
    field: str,              # Field to get terms from (required)
    prefix: str = None,      # Filter by prefix
    regex: str = None,       # Filter by regex
    limit: int = 10,         # Max terms to return
    min_count: int = 1,      # Min document frequency
    max_count: int = None    # Max document frequency
) -> Dict[str, Any]
```

### solr_schema_add_field

```python
solr_schema_add_field(
    collection: str,         # Collection name (required)
    field_name: str,        # Field name (required)
    field_type: str,        # Solr field type (required)
    stored: bool = True,    # Store field value
    indexed: bool = True,   # Index for searching
    required: bool = False, # Field is required
    multiValued: bool = False,  # Multiple values allowed
    docValues: bool = None  # Enable docValues (auto if None)
) -> Dict[str, Any]
```

### solr_schema_list_fields

```python
solr_schema_list_fields(
    collection: str         # Collection name (required)
) -> Dict[str, Any]
```

### solr_schema_get_field

```python
solr_schema_get_field(
    collection: str,        # Collection name (required)
    field_name: str        # Field name (required)
) -> Dict[str, Any]
```

### solr_schema_delete_field

```python
solr_schema_delete_field(
    collection: str,        # Collection name (required)
    field_name: str        # Field name (required)
) -> Dict[str, Any]
```

## Further Reading

- [Solr Terms Component Documentation](https://solr.apache.org/guide/solr/latest/query-guide/terms-component.html)
- [Solr Schema API Documentation](https://solr.apache.org/guide/solr/latest/indexing-guide/schema-api.html)
- [Solr Field Types](https://solr.apache.org/guide/solr/latest/indexing-guide/field-types.html)
- [Solr Schema Design Best Practices](https://solr.apache.org/guide/solr/latest/indexing-guide/schema-design.html)

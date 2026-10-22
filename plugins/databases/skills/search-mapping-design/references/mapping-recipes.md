# Mapping recipes

Reference for steps 2 to 7. Examples use Elasticsearch syntax; OpenSearch matches it for
everything shown here except where noted.

## Contents

- [A complete template](#a-complete-template)
- [Errors and what they mean](#errors-and-what-they-mean)
- [Settings to read](#settings-to-read)
- [Choosing between nested, flattened and denormalised](#choosing-between-nested-flattened-and-denormalised)

## A complete template

```json
{
  "index_patterns": ["products-*"],
  "template": {
    "settings": { "index.mapping.total_fields.limit": 1000 },
    "mappings": {
      "dynamic": "strict",
      "dynamic_templates": [
        {
          "labels_as_keywords": {
            "path_match": "labels.*",
            "mapping": { "type": "keyword", "ignore_above": 256 }
          }
        }
      ],
      "properties": {
        "sku":         { "type": "keyword" },
        "name":        { "type": "text",
                         "fields": { "raw": { "type": "keyword", "ignore_above": 256 } } },
        "description": { "type": "text", "norms": false },
        "price":       { "type": "scaled_float", "scaling_factor": 100 },
        "in_stock":    { "type": "boolean" },
        "created_at":  { "type": "date" },
        "audit_note":  { "type": "keyword", "index": false, "doc_values": false },
        "labels":      { "type": "object", "dynamic": true }
      }
    }
  }
}
```

The `labels.*` template accepts a known family of keys with a fixed type while the rest
of the document stays strict. If the keys come from users, use `flattened` (or
`flat_object` in OpenSearch) instead of this pattern.

## Errors and what they mean

| Error | Usual cause | Fix |
| --- | --- | --- |
| `mapper_parsing_exception: failed to parse field [x] of type [long]` | A value of the wrong shape arrived, often a string in a numeric field | Fix the producer; `ignore_malformed` accepts and drops the value if loss is acceptable |
| `mapper_parsing_exception: object mapping for [x] tried to parse field as object, but found a concrete value` | The same name is an object in the mapping and a scalar in the document | Rename one side; types cannot be switched in place |
| `strict_dynamic_mapping_exception` | `dynamic: strict` and the document has an unmapped field | Add the field to the template if intended, otherwise fix the producer |
| `Limit of total fields [1000] has been exceeded` | Field names are generated from data | Step 4: key/value pairs or flattened |
| `illegal_argument_exception: mapper [x] cannot be changed from type [text] to [keyword]` | An attempt to change a mapped field | Create a new index with the new mapping and reindex |

## Settings to read

```bash
curl -s "$ES/orders-000001/_mapping"
curl -s "$ES/orders-000001/_settings?include_defaults=true&filter_path=**.mapping"
```

Relevant limits: `index.mapping.total_fields.limit` (1000 by default),
`index.mapping.depth.limit` (20), `index.mapping.nested_fields.limit` (50) and
`index.mapping.nested_objects.limit` (10000).

## Choosing between nested, flattened and denormalised

| Need | Choice |
| --- | --- |
| Match two fields of the same child together | `nested` |
| Exact values under keys not known in advance | `flattened` or `flat_object` |
| Filter by a few child attributes, no correlation | Denormalise onto the parent as arrays |
| Children searched on their own | One document per child with a parent id field |
| Aggregate over children | `nested` aggregation, or one document per child |

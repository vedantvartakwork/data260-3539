# Homework 5 Tool Contracts Under Stress

All three domain tools return the same envelope: `{"ok": boolean, "data": any|null, "error": string|null}`.

## `search`

- Expected input: `{"query": string (2-80 characters), "limit": integer (1-25)}`
- Successful example: `{"query": "shrimp", "limit": 5}`
- Rejected example: `{"query": "s", "limit": 5}`
- Returned error: `Invalid search input: query: String should have at least 2 characters`
- Reason: a one-character search is below the declared minimum and is too broad to be useful.

## `detail`

- Expected input: `{"recall_id": positive integer}`
- Successful example: `{"recall_id": 1}`
- Rejected example: `{"recall_id": 0}`
- Returned error: `Invalid detail input: recall_id: Input should be greater than 0`
- Reason: database identifiers begin at 1, so zero is outside the accepted domain.

## `aggregate`

- Expected input: `{"group_by": "category"|"manufacturer", "min_units": integer (0-100000000)}`
- Successful example: `{"group_by": "category", "min_units": 0}`
- Rejected example: `{"group_by": "submitter", "min_units": 0}`
- Returned error: `Invalid aggregate input: group_by: String should match pattern '^(category|manufacturer)$'`
- Reason: `submitter` is not an approved aggregation dimension and could expose personal contact data.

The Part 5 safety rule is intentionally narrower than the MCP search schema: `execute_tool` blocks agent searches with `limit > 10` to prevent bulk extraction, while normal interactive searches remain allowed.

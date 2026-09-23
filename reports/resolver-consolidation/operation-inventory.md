# Operation Inventory

## Overview
This report inventories every individual resolver operation across all existing resolver categories, analyzing semantic equivalence, duplication, and proposed canonical mapping.

---

## Detailed Operation Matrix

| Legacy Resolver | Legacy Operation | Operation Purpose | Equivalent Operations | Is Duplicate? | Canonical Resolver | Canonical Operation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `date_formula` | `add` (positive offset) | Add days/months/years to date | `date_formula` add | No | `date` | `add` |
| `date_formula` | `subtract` (negative offset) | Subtract days/months/years from date | `date_formula` subtract | No | `date` | `subtract` |
| `date_diff` | `days` / `months` / `years` | Difference between two dates | `date_diff` | Yes (Overlaps date operations) | `date` | `diff` |
| `math_formula` | `+` | Numeric addition | `math_formula` | No | `math` | `add` (`+`) |
| `math_formula` | `-` | Numeric subtraction | `math_formula` | No | `math` | `subtract` (`-`) |
| `math_formula` | `*` | Numeric multiplication | `math_formula` | No | `math` | `multiply` (`*`) |
| `math_formula` | `/` | Numeric division | `math_formula` | No | `math` | `divide` (`/`) |
| *(New)* | *(New)* | Minimum of list / fields | `math_formula` | No | `math` | `min` |
| *(New)* | *(New)* | Maximum of list / fields | `math_formula` | No | `math` | `max` |
| *(New)* | *(New)* | Round number to precision | `math_formula` | No | `math` | `round` |
| `string_formula` | `concat` | String concatenation | `string_formula.concat` | No | `text` | `concat` |
| `string_formula` | `uppercase` | Convert string to uppercase | `normalization.upper` | **Yes** | `text` | `upper` |
| `string_formula` | `lowercase` | Convert string to lowercase | `normalization.lower` | **Yes** | `text` | `lower` |
| `string_formula` | `fmt_money` | Format money currency | `format.fmt_money` | **Yes** | `text` | `fmt_money` |
| `normalization` | `trim` | Strip surrounding whitespace | `normalization.trim` | No | `text` | `trim` |
| `normalization` | `slug` | Convert to URL slug | `normalization.slug` | No | `text` | `slug` |
| `normalization` | `snake` | Convert to snake_case | `normalization.snake` | No | `text` | `snake` |
| `normalization` | `title` | Convert to Title Case | `normalization.title` | No | `text` | `title` |
| `format` | `format_date` | Format date with custom format string | `format.format_date` | No | `text` | `format_date` |
| `format` | `format` | Format template string with field values | `format.format` | No | `text` | `pattern` |
| `child_aggregation` | `sum` | Calculate sum of child table column | `child_aggregation.sum` | No | `aggregate` | `sum` |
| `child_aggregation` | `avg` | Calculate average of child table column | `child_aggregation.avg` | No | `aggregate` | `avg` |
| `child_aggregation` | `count` | Count rows in child table | `collection.count` | **Yes** | `aggregate` | `count` |
| `collection` | `count` | Count matching elements in array | `child_aggregation.count` | **Yes** | `collection` / `aggregate` | `count` |
| `collection` | `any` | Check if at least one row matches condition | `collection.any` | No | `collection` | `any` |
| `collection` | `all` | Check if all rows match condition | `collection.all` | No | `collection` | `all` |
| `collection` | `first` | Return first row matching condition | `collection.find` | **Yes** | `collection` | `first` |
| `collection` | `find` | Alias for `first` | `collection.first` | **Yes** | `collection` | `first` |
| `collection` | `filter` | Return list of matching rows | `collection.filter` | No | `collection` | `filter` |
| `collection` | `pluck` | Extract column array from collection | `collection.pluck` | No | `collection` | `pluck` |
| `collection` | `unique` | Extract unique values from collection | `collection.unique` | No | `collection` | `unique` |
| `fetch` | *(Default)* | Retrieve database field from linked DocType | `fetch` | No | `lookup` | `get` |
| *(New)* | *(New)* | Check if linked record exists in DB | `fetch` | No | `lookup` | `exists` |
| `system_context` | `user` | Get current session user ID | `system_context.user` | No | `value_source` | `system_context` (sub: `user`) |
| `system_context` | `role_check` | Check if user has specified role | `system_context.role_check` | No | `value_source` | `system_context` (sub: `role_check`) |

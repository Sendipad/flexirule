# <no value>
# Resolver: Resolver Patterns

## 📚 Capability Encyclopedia
This document catalogs the practical patterns enabled by the FlexiRule Resolver Engine.

### 1. Dynamic Path Traversal
Resolvers support deep dot-notation.
- `doc.items.0.amount`: Get the amount of the first item.
- `vars.query_result.name`: Get a field from a previously queried record.

### 2. Time-Based Logic
The `DateFormulaResolver` and `DateDiffResolver` handle enterprise date requirements:
- `Today + 14 days`: For due date calculation.
- `Diff(doc.delivery_date, doc.posting_date)`: For lead-time calculation.

### 3. Collection Aggregation
The `ChildAggregationResolver` eliminates the need for "Loop" nodes in simple cases:
- `Sum(doc.items.amount)`: Total an entire child table in one step.
- `Count(doc.attachments)`: Check if any files were uploaded.

### 4. String Interpolation & Templating
The `ExpressionResolver` and `JinjaResolver` allow for rich text generation:
- `"Hello {{ doc.first_name }}, your order #{{ doc.name }} is ready."`
- These are used in notifications, descriptions, and comments.

### 5. System Context Injection
Resolvers can access environmental data without explicit passing:
- `User`: The current session user.
- `Role Check`: Boolean check if the user has a specific role.

---

## 🛠️ Enterprise Use Cases

| Requirement | Resolver Pattern |
| :--- | :--- |
| **Clean a URL slug** | `NormalizationResolver(mode='slug', path='doc.title')` |
| **Apply a 10% discount** | `MathFormulaResolver(a='doc.total', op='*', b=0.9)` |
| **Format for a Report** | `FormatResolver(mode='date', config='dd-mm-yyyy', path='doc.posting_date')` |
| **Default if empty** | `JinjaResolver(template='{{ doc.email or vars.fallback_email }}')` |

---

## 🔮 Future Evolution Ideas
- **Lookup Resolvers**: A resolver that performs a `frappe.db.get_value` directly without needing a separate "Query Records" node.
- **Mapping Resolvers**: Transforming a list of IDs into a list of Names.
- **Conditional Resolvers**: `If(Condition, ValueA, ValueB)` logic within the resolver itself.

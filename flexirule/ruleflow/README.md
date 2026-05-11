# FlexiRule Ruleflow Engine

The core execution engine and API layer for FlexiRule.

## 🚀 Overview

FlexiRule Ruleflow is the execution backbone that transforms visual rule definitions into executable business logic. It handles rule compilation, graph execution, error handling, and integration with Frappe's document lifecycle.

## 🔑 Key Features

- **Graph-Based Execution Engine**: Processes rules as directed graphs with full cycle detection
- **Condition Compilation**: Pre-compiles visual conditions to optimized Python expressions
- **Action Handler Strategy Pattern**: Pluggable architecture for different action types
- **Comprehensive Error Handling**: Retry, rollback, escalate, and continue policies
- **Async Execution Support**: Background job processing for long-running rules
- **Permission Model**: Role-based execution control and audit logging
- **Transaction Management**: Per-action savepoints for granular rollback capability
- **Execution Tracing**: Detailed path tracking with timing and variable states
- **Runtime Registry**: Layered caching (local → Redis → DB) for performance

## 📚 Documentation

For detailed architecture and deep dives, see the main documentation:

- [System Architecture](../docs/architecture.md)
- [Execution Engine Deep Dive](../docs/execution_engine.md)
- [Condition System Deep Dive](../docs/condition_system.md)
- [Trigger System Deep Dive](../docs/trigger_system.md)
- [Process Adapter Standards](../docs/adapter_standards.md)
- [Frontend (Rule Builder) Architecture](../docs/rule_builder.md)

## 🔌 API Reference

All API methods are whitelisted and accessible via `frappe.call()`:

### Rule Execution & Testing
- `test_rule` - Test execution with dry_run and save_log options
- `simulate_rule` - Dry-run simulation without side effects
- `execute_rule` - Direct rule execution
- `get_execution_preview` - Predict execution path without running actions

### Rule Lifecycle
- `transition_rule` - Change rule status (Draft/Active/Disabled/etc)
- `clone_rule` - Create a copy of a rule
- `amend_rule` - Create a versioned amendment
- `get_rule_versions` / `restore_rule_version` - Version history management

### Cache & Metadata
- `clear_cache` - Invalidate rule runtime registry
- `get_contract_dto` - Get action/trigger contracts for frontend
- `get_node_config_schema` - Get dynamic configuration schema
- `get_action_context_schema` - Get available context variables
- `get_rule_stats` - Get execution statistics
- `get_process_operations` - Get available process operations

### Validation & Utilities
- `validate_rule_document` - Validate rule definition
- `validate_node` - Validate single action/node
- `get_operator_config` - Get condition builder operator mappings
- `search_actions` - Fuzzy search across actions/operations
- `get_doctype_fields` - Get DocType formatted fields
- `export_rule` / `import_rule` - Rule import/export functionality

### Example Usage

```javascript
// Test a rule against a document
frappe.call({
    method: "flexirule.ruleflow.api.test_rule",
    args: {
        rule_name: "Validate Customer Email",
        doctype: "Customer", 
        docname: "CUST-001",
        dry_run: 0,
        save_log: 1
    }
});

// Execute a rule asynchronously
frappe.call({
    method: "flexirule.ruleflow.api.execute_rule",
    args: {
        rule_name: "Send Welcome Email",
        context: {}, // Optional context variables
        dry_run: 0
    }
});

// Preview execution path
frappe.call({
    method: "flexirule.ruleflow.api.get_execution_preview",
    args: {
        rule_name: "Approval Workflow",
        docname: "DOC-001"
    }
});

// Clear rule cache for a doctype
frappe.call({
    method: "flexirule.ruleflow.api.clear_cache",
    args: {
        doctype: "Sales Order"
    }
});
```

## ⚙️ Process Architecture

FlexiRule uses file-backed **Processes** which contain multiple **Operations**:

### Standard Processes
- **Normalization** - Clean and standardize field data
- **Validation** - Complex multi-field validation
- **Enrichment** - Auto-populate fields from multiple sources
- **Deduplication** - Detect and prevent duplicates using various algorithms
- **Communication** - Send notifications/emails/messages
- **Data Transformation** - Format, convert, and manipulate data
- **Integration** - Call external APIs and webhooks

### Creating Custom Processes

1. Create a new `Process` document in Frappe
2. If `is_standard` is checked, boilerplate files (`.py` and `.js`) will be created in your app
3. Add `Process Operation` rows to define your methods
4. Implement the logic in the generated controller
5. Configure JSON schemas for inputs and outputs
6. Declare metadata like `writes_to`, `requires_doc`, `transactional`, etc.

## 🔐 Security & Permissions

- All API endpoints require builder access via `require_builder_access()`
- Condition evaluation uses `SafeFrappeAPI` (read-only methods only)
- Permission auditing via `skip_permissions` with audit reason
- Role-based execution control via `skip_for_roles`
- Input validation through JSON schemas for Process configurations

## 📈 Monitoring & Observability

- Rule Execution Log doctype captures all runs
- Detailed path tracing with timestamps and variable states
- Performance metrics via `get_rule_stats`
- Debug mode for verbose logging
- Execution timeouts and circuit breaker patterns

## 🔄 Extensibility

The engine is designed for extension through:

- **Custom Action Types**: Register new handlers via `HandlerRegistry`
- **Process Operations**: Create reusable logic units with schemas
- **Middleware Plugins**: Hook into execution lifecycle events
- **Cache Providers**: Implement custom registry caching strategies
- **Error Policies**: Define custom error handling behaviors

## 📝 License

MIT



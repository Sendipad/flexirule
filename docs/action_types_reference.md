# FlexiRule Action Types Reference

This document provides a comprehensive reference of all FlexiRule action types, their use cases, related operations, and remarks about their ideal applications.

## Action Types Overview

| Action Type | Use Case | Related Operations | Remarks |
|-------------|----------|-------------------|---------|
| **Entry Action** | Starting point of rule execution | Entry Action | Marks the beginning of rule execution flow. Every rule must have exactly one Entry Action as the starting point. |
| **Condition** | Branching logic based on conditions | Condition Builder Config | Evaluates expressions to determine execution path. Essential for decision-making in workflows. Can have both true and false branches. |
| **Process** | Execute reusable business logic | All Process Operations | Executes file-backed Processes with Operations. Most versatile action type supporting complex logic, data manipulation, and integration. Supports context variables and document updates. |
| **Loop** | Iterate over collections | None (uses return_variable) | Repeats execution of a sub-flow for each item in a collection. Requires iterator configuration in config and return_variable for item alias. |
| **Stop** | Terminate rule execution | Success, Error | Ends rule execution. Success for normal completion, Error for failure with custom message. Terminal actions don't proceed to next steps. |
| **Switch** | Multi-way branching (disabled) | Cases configuration | Evaluates expression and routes to matching case. Currently disabled in releases (RELEASE_DISABLED_ACTION_TYPES). |
| **Wait** | Pause execution | Wait Mode | Delays execution for specified duration. Useful for rate limiting, waiting for external processes, or timing-based workflows. |
| **Sub-Rule** | Execute another rule as subroutine | Sub-Rule Name | Calls another rule as a reusable subroutine. Enables modular rule design and recursion prevention. Requires exposed Callable Event rule. |
| **Set Value** | Update fields or variables | Current Document, Context Variable, Reference Document | Sets values using Jinja templates. Supports updating document fields, context variables, or reference documents with various mutation modes. |
| **Notify** | Send notifications | Toast, System, Email, System Notification, Provider | Sends user notifications through various channels. Essential for user feedback and alerting in workflows. |
| **Raise Error** | Exception handling | Error Message Template | Immediately terminates rule with exception. Used for critical error conditions that should halt processing. |
| **Query Records** | Database queries | Query List, Query Doc, Exist Record, Query Report, Count, Sum, Average, Min, Max, Group By | Retrieves data from DocTypes. Supports various query modes from simple lists to aggregates and reports. Results can be stored in context variables. |
| **Document Action** | Document lifecycle operations | Create New, Update Existing, Delete Record, Create ToDo, Add Comment | Performs CRUD operations on documents. Core action type for data manipulation in Frappe/ERPNext. |

## Detailed Action Type Analysis

### Entry Action
- **Purpose**: Initializes rule execution
- **Perfect For**: All rules (mandatory starting point)
- **Configuration**: No required fields
- **Flow Control**: Always proceeds to next_step_if_true
- **Remarks**: Serves as the entry point where rule execution begins. Visualized as a green play button in the rule builder.

### Condition
- **Purpose**: Conditional branching
- **Perfect For**: Decision points, validation checks, eligibility determinations
- **Configuration**: Requires config (condition builder JSON)
- **Flow Control**: Has both true and false branches
- **Remarks**: The backbone of logical workflows. Uses pre-compiled expressions for performance. Can evaluate complex conditions including document fields, context variables, and utility functions.

### Process
- **Purpose**: Execute reusable business logic
- **Perfect For**: Complex data processing, integrations, calculations, data transformation
- **Configuration**: Requires process_name and operation
- **Flow Control**: Proceeds to next_step_if_true on success
- **Remarks**: Most powerful and flexible action type. Supports:
  - Context variable manipulation (set, update, append)
  - Document field updates
  - Return values of various types (single record, list, boolean, etc.)
  - Multiple mutation modes
  - JSON schema-driven configuration UIs
  - External system integrations

### Loop
- **Purpose**: Iterative processing
- **Perfect For**: Processing child table rows, batch operations, collection transformations
- **Configuration**: Requires config (with iterator) and return_variable
- **Flow Control**: 
  - next_step_if_true: Loop body (repeats for each item)
  - next_step_if_false: Loop exit (after all items processed)
- **Remarks**: Essential for working with collections. The return_variable becomes available as an alias for the current item during each iteration. Supports exiting early via Stop actions within the loop body.

### Stop
- **Purpose**: Terminate execution
- **Perfect For**: Successful completion, error handling, workflow termination
- **Configuration**: Requires operation (Success or Error)
- **Flow Control**: Terminal - no outgoing connections
- **Remarks**: 
  - Success: Normal termination with green styling
  - Error: Failure termination with red styling and custom error message
  - Critical for defining clear workflow endpoints

### Wait
- **Purpose**: Time-based delays
- **Perfect For**: Rate limiting, polling, scheduled actions, timing-dependent processes
- **Configuration**: Optional duration in config (defaults to 1 second)
- **Flow Control**: Proceeds to next_step_if_true after delay
- **Remarks**: Non-blocking delay that pauses rule execution. Use cautiously as it holds rule engine resources during the wait period.

### Sub-Rule
- **Purpose**: Modular rule reuse
- **Perfect For**: Reusable workflow components, complex workflow decomposition, recursion prevention
- **Configuration**: Requires rule name (must be Callable Event with exposed_as_subrule=1)
- **Flow Control**: Proceeds to next_step_if_true on successful execution
- **Remarks**: Enables true modularity in rule design. Called rule runs in isolated context with optional context merging. Skip conditions option bypasses the sub-rule's trigger conditions.

### Set Value
- **Purpose**: Field/variable assignment
- **Perfect For**: Setting document fields, calculating values, updating context, data transformation
- **Configuration**: Requires operation type and value_template
- **Flow Control**: Proceeds to next_step_if_true
- **Remarks**: Highly versatile assignment action with three target types:
  - Current Document: Updates fields on the primary document
  - Context Variable: Sets or updates context variables
  - Reference Document: Updates fields on related documents
  Supports Jinja templating for dynamic values and various mutation modes.

### Notify
- **Purpose**: User communication
- **Perfect For**: User feedback, alerts, notifications, status updates
- **Configuration**: Requires operation type and value_template
- **Flow Control**: Proceeds to next_step_if_true
- **Remarks**: Supports multiple notification channels:
  - Toast: Temporary browser notification
  - System: Frappe system notification
  - Email: Email notification (requires subject/recipients)
  - System Notification: Frappe Notification Log entry
  - Provider: External notification service (SMS, Slack, etc.)

### Raise Error
- **Purpose**: Exception throwing
- **Perfect For**: Critical failures, validation failures, workflow abortion
- **Configuration**: Requires value_template (error message)
- **Flow Control**: Terminal - no outgoing connections
- **Remarks**: Immediately throws an exception that aborts rule execution. Unlike Stop(Error), this raises a true exception that can be caught by outer error handling mechanisms.

### Query Records
- **Purpose**: Data retrieval
- **Perfect For**: Lookups, reporting, data validation, reference data access
- **Configuration**: Requires reference_doctype and operation type
- **Flow Control**: Proceeds to next_step_if_true
- **Remarks**: Supports diverse query operations:
  - Query List: Multiple records with filtering/sorting
  - Query Doc: Single record by name/ID
  - Exist Record: Boolean existence check
  - Query Report: Custom report execution
  - Aggregate functions: Count, Sum, Average, Min, Max
  - Group By: Aggregated grouping operations
  Results can be stored in context variables for use in subsequent actions.

### Document Action
- **Purpose**: Document lifecycle management
- **Perfect For**: Creating, updating, deleting documents; user engagement (ToDo, Comments)
- **Configuration**: Requires reference_doctype and operation type
- **Flow Control**: Proceeds to next_step_if_true
- **Remarks**: Core data manipulation actions:
  - Create New: Creates document with optional context return
  - Update Existing: Modifies existing document
  - Delete Record: Permanently removes document
  - Create ToDo: Creates task assignment for users
  - Add Comment: Adds comment to document timeline
  All support context variable returns for chaining operations.

## Action Type Categories

### Control Flow Actions
- **Entry Action**: Start point
- **Condition**: Branching
- **Loop**: Iteration
- **Switch**: Multi-branching (disabled)
- **Wait**: Delay
- **Sub-Rule**: Modular calling

### Termination Actions
- **Stop**: Normal/error termination
- **Raise Error**: Exception-based termination

### Data Actions
- **Process**: Reusable logic execution
- **Set Value**: Field/variable assignment
- **Query Records**: Data retrieval
- **Document Action**: Document lifecycle

### Notification Actions
- **Notify**: User alerts and feedback

## Rule Type Compatibility

| Action Type | DocType Event | Scheduler Event | Callable Event | Best Suited For |
|-------------|---------------|-----------------|----------------|-----------------|
| Entry Action | ✅ | ✅ | ✅ | All rule types |
| Condition | ✅ | ✅ | ✅ | Decision-heavy workflows |
| Process | ✅ | ✅ | ✅ | Complex business logic |
| Loop | ✅ | ✅ | ✅ | Collection processing |
| Stop | ✅ | ✅ | ✅ | Workflow endpoints |
| Switch | ✅ | ✅ | ✅ | Multi-branching logic |
| Wait | ✅ | ✅ | ✅ | Timing-dependent processes |
| Sub-Rule | ❌ | ❌ | ✅ | Modular rule design |
| Set Value | ✅ | ✅ | ✅ | Data manipulation |
| Notify | ✅ | ✅ | ✅ | User feedback systems |
| Raise Error | ✅ | ✅ | ✅ | Error handling |
| Query Records | ✅ | ✅ | ✅ | Data lookup/integration |
| Document Action | ✅ | ✅ | ✅ | Document lifecycle |

*Note: Sub-Rule action type can only be used in Callable Event rules (as it requires calling another callable rule).*

## Performance Considerations

1. **Condition Actions**: Use pre-compiled expressions for optimal performance
2. **Process Actions**: Boilerplate-generated operations are highly optimized
3. **Query Actions**: Consider adding indexes on queried fields for large datasets
4. **Loop Actions**: Be mindful of iteration limits (100 visits per node, 1000 total)
5. **Wait Actions**: Avoid long delays in synchronous rules as they block execution

## Common Patterns

### Validation Workflow
```
Entry Action → Condition (validate data) → 
  ├─[True]→ Process (normalize data) → Stop(Success)
  └─[False]→ Set Value (error message) → Notify(Email) → Stop(Error)
```

### Data Processing Pipeline
```
Entry Action → Query Records (get raw data) → 
Loop (process each item) → 
  Process (transform item) → 
  Document Action (create processed record) →
Stop(Success)
```

### Approval Workflow
```
Entry Action → Condition (check approval status) → 
  ├─[True]→ Notify(Manager) → Wait(1 hour) → Condition (check response) →
  │   ├─[True]→ Process(record approval) → Stop(Success)
  │   └─[False]→ Escalate to supervisor → Stop(Error)
  └─[False]→ Stop(Success)  // Auto-approve
```

### Batch Processing
```
Entry Action → Query Records (get batch) → 
Loop (process batch items) → 
  Condition (validate item) → 
    ├─[True]→ Process(item) → Document Action(update status)
    └─[False]→ Document Action(log error) → 
Stop(Success)
```
# Document Action<no value>

# Document Action

The **Document Action** node allows rules to interact with the lifecycle of any DocType in the system.

## Supported Operations

- **Create New**: Generates a new document and populates its fields.
- **Update Existing**: Modifies fields on a specific record identified by name.
- **Delete Record**: Permanently removes a document.
- **Create ToDo**: Assigns a task to a user related to the current context.
- **Add Comment**: Posts a comment to the document's timeline.

## Configuration

- **Target DocType**: The DocType to act upon.
- **Target Record**: (For Update/Delete) The specific document name.
- **Data Mapping**: A visual interface for mapping context variables or Jinja templates to the target document's fields.

## Safety

When creating or updating documents, the Rule Engine can optionally bypass standard permission checks (with a required audit reason) if the action is intended to be performed by the system.

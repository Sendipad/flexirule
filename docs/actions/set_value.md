# Set Value Action

The **Set Value** action updates a document field or a context variable using a Jinja template. It is the most versatile way to perform data transformation within a rule.

## Configuration
- **Operation**: Select the target type:
    - `Current Document`: Updates a field on the document that triggered the rule.
    - `Context Variable`: Sets or updates a variable in the `vars` dictionary.
    - `Reference Document`: Updates a field on a related document (requires `Target DocType` and `Target Record`).
- **Target Field**: The specific field or variable name to update.
- **Value Template**: A Jinja template that defines the new value.

## Examples
- **Simple Assignment**: `{{ vars.total_amount }}`
- **Calculated Value**: `{{ doc.qty * doc.rate }}`
- **Conditional Template**: `{% if doc.status == "Open" %}Pending{% else %}Closed{% endif %}`

## Error Prevention
The Rule Builder ensures that the **Target Field** exists on the selected DocType and that the value being set is compatible with the field's type.

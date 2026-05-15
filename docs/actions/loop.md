# Loop Action

The **Loop** action enables iterative processing of collections, such as child tables or query results.

## Configuration
- **Iterator**: A reference to the collection to iterate over (e.g., `doc.items` or `vars.query_results`).
- **Item Alias**: The name to use for the current item inside the loop body (e.g., `row`).

## Execution Flow
- **For Each**: This path is followed for every item in the collection. The `Item Alias` is updated with the current record at each step.
- **After Last**: This path is followed once the collection has been fully processed.

## Meta Variables
Inside a loop, the engine provides automatic metadata:
- `vars.loop.index`: The current iteration number (starting at 0).
- `vars.loop.length`: The total number of items in the collection.
- `vars.loop.first`: `True` if it's the first iteration.
- `vars.loop.last`: `True` if it's the last iteration.

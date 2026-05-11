### WORK ITEM — GET TOOLS

**find_tasks(name, work_item_ids, project_id, display_ids, item_types, statuses, start_date, end_date, assigned_by_ids, assigned_to_ids, linked_work_item_id)**
Find work items using flexible filters.
- `item_types`: `TASK`, `STORY`.
- `statuses`: `TODO`, `IN_PROGRESS`, `CODE_COMPLETE`, `DEPLOYED_ON_STAGE`, `DONE`.
- Output: `[{"work_item_id": "uuid", "title": "...", "status": "...", "item_type": "..."}]`

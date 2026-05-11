### WORK ITEM — UPDATE TOOLS

**update_work_item(user_id, work_item_id, name, item_type, description, start_date, end_date, status, assigned_to)**
Update any combination of fields on a work item.

**reassign_work_item(user_id, work_item_id, assigned_to)**
Reassign a work item to a new user. Use this instead of `update_work_item` when the only change is reassignment for clarity.

**bulk_update_status(user_id, work_item_ids, status)**
Change the status of multiple work items in one call.
- Use when the user asks to mark several tasks done/in-progress at once.

**link_work_items(user_id, work_item_id, linked_work_item_id)**
Link a work item to another (parent/dependency relationship).

**move_work_item(user_id, work_item_id, new_project_id)**
Move a work item to a different project.

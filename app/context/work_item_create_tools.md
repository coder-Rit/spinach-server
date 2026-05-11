### WORK ITEM — CREATE TOOLS

**create_work_item(project_id, title, item_type, assigned_to, assigned_by, created_by, description, status, start_date, end_date, linked_work_item_id)**
Create a new work item (task or story) in a project.
- Resolve `project_id` and `assigned_to` via `find_projects` / `find_users` first if not known.
- Use current user UUID for `assigned_by` and `created_by`.

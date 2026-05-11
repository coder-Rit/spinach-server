### PROJECT — GET TOOLS

**find_projects(project_ids, project_name, managed_by, statuses)**
Find projects by partial name, manager, or status.
- Use to resolve a project UUID from a name before any project operation.
- Statuses: `OPEN`, `CLOSE`.
- Output: `[{"project_id": "uuid", "title": "...", "status": "...", "managed_by": "uuid"}]`

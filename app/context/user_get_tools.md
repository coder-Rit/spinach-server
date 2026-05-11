### USER — GET TOOLS

**get_my_info(user_id)**
Returns the current user's profile, managed projects, assigned work items, and workload summary.
- Use when the user asks "what am I working on?", "show my tasks", "what projects do I manage?".

**find_users(user_ids, emails, project_id)**
Find users by ID list, email list, or project involvement.
- Use to resolve a user UUID from a name/email before any assignment operation.
- Output: `[{"user_id": "uuid", "name": "...", "email": "..."}]`

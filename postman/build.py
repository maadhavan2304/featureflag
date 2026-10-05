"""Generates feature-flag.postman_collection.json  (python postman/build.py)"""
import json

def req(name, method, path, body=None, auth=True, headers=None, form=None, tests=None, query=None):
    h = list(headers or [])
    r = {"method": method, "header": h, "url": {"raw": "{{baseUrl}}" + path, "host": ["{{baseUrl}}"],
         "path": [p for p in path.split("?")[0].strip("/").split("/")]}}
    if query:
        r["url"]["query"] = [{"key": k, "value": v} for k, v in query.items()]
    if body is not None:
        h.append({"key": "Content-Type", "value": "application/json"})
        r["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2)}
    if form:
        r["body"] = {"mode": "urlencoded", "urlencoded": [{"key": k, "value": v} for k, v in form.items()]}
    if not auth:
        r["auth"] = {"type": "noauth"}
    item = {"name": name, "request": r}
    if tests:
        item["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": tests.split("\n")}}]
    return item

save_tokens = """const j = pm.response.json();
pm.collectionVariables.set('accessToken', j.access_token);
pm.collectionVariables.set('refreshToken', j.refresh_token);
pm.test('login ok', () => pm.response.to.have.status(200));"""

sdk_h = [{"key": "X-SDK-Key", "value": "{{sdkKey}}"}]

collection = {
    "info": {"name": "Feature Flag & Environment Management", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
             "description": "Run 'Auth > Login' first. Then 'Environments > List' (copy an sdk_key into the sdkKey variable). Flag IDs are stored automatically."},
    "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{accessToken}}", "type": "string"}]},
    "variable": [
        {"key": "baseUrl", "value": "http://localhost:8000/api/v1"}, {"key": "accessToken", "value": ""},
        {"key": "refreshToken", "value": ""}, {"key": "flagId", "value": "1"}, {"key": "rolloutId", "value": "1"},
        {"key": "envId", "value": "1"}, {"key": "sdkKey", "value": ""}, {"key": "assignmentId", "value": "1"},
        {"key": "auditId", "value": "1"},
    ],
    "item": [
        {"name": "Auth", "item": [
            req("Login", "POST", "/auth/login", form={"username": "admin", "password": "Admin@12345"}, auth=False, tests=save_tokens),
            req("Refresh token", "POST", "/auth/refresh", {"refresh_token": "{{refreshToken}}"}, auth=False, tests=save_tokens),
            req("Current user", "GET", "/auth/me"),
        ]},
        {"name": "Users & Roles", "item": [
            req("List roles", "GET", "/roles"),
            req("List users", "GET", "/users"),
            req("Create user", "POST", "/users", {"email": "dev@example.com", "username": "dev1", "password": "Passw0rd!", "role_id": 2}),
            req("Update user", "PATCH", "/users/2", {"is_active": True, "role_id": 2}),
        ]},
        {"name": "Environments", "item": [
            req("List environments (admin sees SDK keys)", "GET", "/environments", tests="const e = pm.response.json()[0];\npm.collectionVariables.set('envId', e.id);\nif (e.sdk_key) pm.collectionVariables.set('sdkKey', e.sdk_key);"),
            req("Create environment", "POST", "/environments", {"name": "Staging", "key": "staging", "description": "Pre-prod", "is_production": False}),
            req("Update environment", "PATCH", "/environments/{{envId}}", {"description": "Updated"}),
            req("Rotate SDK key", "POST", "/environments/{{envId}}/rotate-sdk-key"),
        ]},
        {"name": "Feature Flags", "item": [
            req("List flags", "GET", "/flags", query={"search": "", "include_archived": "false"}),
            req("Create flag", "POST", "/flags", {"key": "new-feature", "name": "New feature", "description": "Demo flag"},
                tests="const j = pm.response.json();\npm.collectionVariables.set('flagId', j.id);\npm.collectionVariables.set('rolloutId', j.rollouts[0].id);"),
            req("Get flag", "GET", "/flags/{{flagId}}"),
            req("Edit flag", "PATCH", "/flags/{{flagId}}", {"name": "New feature (renamed)"}),
            req("Archive flag", "PATCH", "/flags/{{flagId}}", {"is_archived": True}),
            req("Flag history", "GET", "/flags/{{flagId}}/history"),
            req("Test evaluate (not counted)", "GET", "/flags/{{flagId}}/test-evaluate", query={"environment_id": "{{envId}}", "user_id": "user-123"}),
            req("Delete flag", "DELETE", "/flags/{{flagId}}"),
        ]},
        {"name": "Rollouts", "item": [
            req("Enable flag", "PUT", "/rollouts/{{rolloutId}}", {"enabled": True}),
            req("Disable flag", "PUT", "/rollouts/{{rolloutId}}", {"enabled": False}),
            req("Set 25% rollout", "PUT", "/rollouts/{{rolloutId}}", {"enabled": True, "rollout_percentage": 25}),
            req("Schedule activation", "PUT", "/rollouts/{{rolloutId}}", {"scheduled_enable_at": "2030-01-01T09:00:00Z", "scheduled_disable_at": "2030-01-08T09:00:00Z"}),
            req("Clear schedule", "PUT", "/rollouts/{{rolloutId}}", {"scheduled_enable_at": None, "scheduled_disable_at": None}),
            req("Rollback last change", "POST", "/rollouts/{{rolloutId}}/rollback", {}),
            req("Rollback a specific change", "POST", "/rollouts/{{rolloutId}}/rollback", {"audit_log_id": "{{auditId}}"}),
        ]},
        {"name": "User Assignments", "item": [
            req("Allow a user", "POST", "/flags/{{flagId}}/assignments", {"environment_id": "{{envId}}", "user_identifier": "vip@example.com", "access": "allow"},
                tests="pm.collectionVariables.set('assignmentId', pm.response.json().id);"),
            req("Deny a user", "POST", "/flags/{{flagId}}/assignments", {"environment_id": "{{envId}}", "user_identifier": "blocked@example.com", "access": "deny"}),
            req("List assignments", "GET", "/flags/{{flagId}}/assignments"),
            req("Remove assignment", "DELETE", "/assignments/{{assignmentId}}"),
        ]},
        {"name": "SDK (uses X-SDK-Key, no JWT)", "item": [
            {**req("Evaluate one flag", "POST", "/sdk/evaluate", {"flag_key": "new-checkout", "user_id": "user-123"}, auth=False, headers=sdk_h)},
            {**req("Evaluate all flags for a user", "GET", "/sdk/flags", auth=False, headers=sdk_h, query={"user_id": "user-123"})},
        ]},
        {"name": "Analytics", "item": [
            req("Dashboard", "GET", "/analytics/dashboard"),
            req("Usage (all flags, 7 days)", "GET", "/analytics/usage", query={"days": "7"}),
            req("Usage (one flag)", "GET", "/analytics/usage", query={"flag_id": "{{flagId}}", "days": "14"}),
        ]},
        {"name": "Audit Logs", "item": [
            req("Search audit logs", "GET", "/audit-logs", query={"limit": "25", "offset": "0"},
                tests="const items = pm.response.json().items;\nif (items.length) pm.collectionVariables.set('auditId', items[0].id);"),
            req("Audit logs for a flag", "GET", "/audit-logs", query={"flag_id": "{{flagId}}"}),
        ]},
    ],
}
# the SDK requests must not inherit bearer auth
for folder in collection["item"]:
    if folder["name"].startswith("SDK"):
        for it in folder["item"]:
            it["request"]["auth"] = {"type": "noauth"}

with open("postman/feature-flag.postman_collection.json", "w") as f:
    json.dump(collection, f, indent=2)
print("ok")

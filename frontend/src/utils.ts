export const fmt = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "—";

/** ISO (UTC) -> value for <input type="datetime-local"> in the browser's timezone. */
export const toLocalInput = (iso: string | null) => {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

/** <input type="datetime-local"> value -> ISO UTC, or null when empty. */
export const fromLocalInput = (v: string) => (v ? new Date(v).toISOString() : null);

export const actionLabel: Record<string, string> = {
  create_flag: "Created flag", update_flag: "Edited flag", archive_flag: "Archived flag", unarchive_flag: "Restored flag",
  delete_flag: "Deleted flag", toggle: "Toggled", update_rollout: "Changed rollout", rollback: "Rolled back",
  scheduled_activation: "Scheduled turn-on", scheduled_deactivation: "Scheduled turn-off",
  assign_user: "Set user access", unassign_user: "Removed user access", login: "Signed in",
  create_user: "Created user", update_user: "Updated user", create_environment: "Created environment",
  update_environment: "Updated environment", rotate_sdk_key: "Rotated SDK key",
};

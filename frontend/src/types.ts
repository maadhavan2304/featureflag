export interface Role { id: number; name: string; description: string; permissions: string[] }
export interface User { id: number; email: string; username: string; is_active: boolean; role: Role; created_at: string }
export interface Environment {
  id: number; name: string; key: string; description: string; is_production: boolean;
  sdk_key: string | null; created_at: string;
}
export interface Rollout {
  id: number; flag_id: number; environment_id: number; environment_key: string; environment_name: string;
  is_production: boolean; enabled: boolean; rollout_percentage: number;
  scheduled_enable_at: string | null; scheduled_disable_at: string | null; version: number; updated_at: string;
}
export interface Flag {
  id: number; key: string; name: string; description: string; is_archived: boolean;
  created_by: string | null; created_at: string; updated_at: string; rollouts: Rollout[];
}
export interface Assignment { id: number; flag_id: number; environment_id: number; user_identifier: string; access: "allow" | "deny"; created_at: string }
export interface Audit {
  id: number; user_id: number | null; username: string; action: string; entity_type: string;
  entity_id: number | null; flag_id: number | null; flag_key: string | null; environment_id: number | null;
  environment_key: string | null; before: Record<string, unknown> | null; after: Record<string, unknown> | null;
  created_at: string;
}
export interface UsagePoint { date: string; evaluations: number; enabled_count: number }
export interface Dashboard {
  totals: { flags: number; archived: number; enabled_somewhere: number; scheduled: number; partial_rollouts: number; environments: number };
  environments: { environment_id: number; key: string; name: string; is_production: boolean; enabled: number; disabled: number; partial: number }[];
  rollout_distribution: Record<string, number>;
  usage_7d: UsagePoint[];
  top_flags: { flag_id: number; key: string; name: string; evaluations: number }[];
  recent_activity: Audit[];
}

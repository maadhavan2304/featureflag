import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Alert, Box, Button, Chip, CircularProgress, IconButton, MenuItem, Paper, Slider, Switch, Tab, Table, TableBody,
  TableCell, TableHead, TableRow, Tabs, TextField, Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/DeleteOutline";
import UndoIcon from "@mui/icons-material/Undo";
import { CategoryScale, Chart as ChartJS, LinearScale, LineElement, PointElement, Tooltip, Legend } from "chart.js";
import { Line } from "react-chartjs-2";
import { api, errorMessage } from "../api";
import { useAuth } from "../auth";
import type { Assignment, Audit, Environment, Flag, Rollout, UsagePoint } from "../types";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/Toast";
import { actionLabel, fmt, fromLocalInput, toLocalInput } from "../utils";
import { MONO } from "../theme";

ChartJS.register(CategoryScale, LinearScale, LineElement, PointElement, Tooltip, Legend);

function RolloutCard({ r, canEdit, canRollback, onChanged }: { r: Rollout; canEdit: boolean; canRollback: boolean; onChanged: () => void }) {
  const toast = useToast();
  const [pct, setPct] = useState(r.rollout_percentage);
  const [on, setOn] = useState(r.scheduled_enable_at ? toLocalInput(r.scheduled_enable_at) : "");
  const [off, setOff] = useState(r.scheduled_disable_at ? toLocalInput(r.scheduled_disable_at) : "");
  useEffect(() => {
    setPct(r.rollout_percentage); setOn(toLocalInput(r.scheduled_enable_at)); setOff(toLocalInput(r.scheduled_disable_at));
  }, [r]);

  const save = async (body: object, msg: string) => {
    try { await api.put(`/rollouts/${r.id}`, body); toast(msg); onChanged(); }
    catch (e) { toast(errorMessage(e), "error"); }
  };
  const rollback = async () => {
    try { await api.post(`/rollouts/${r.id}/rollback`, {}); toast("Rolled back the last change"); onChanged(); }
    catch (e) { toast(errorMessage(e), "error"); }
  };

  return (
    <Paper sx={{ p: 2.5, borderLeft: 4, borderLeftColor: r.is_production ? "secondary.main" : "primary.main" }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 1 }}>
        <Typography variant="h6" sx={{ flex: 1 }}>{r.environment_name}</Typography>
        <Typography variant="caption" color="text.secondary">v{r.version} · updated {fmt(r.updated_at)}</Typography>
        <Switch checked={r.enabled} disabled={!canEdit} onChange={() => save({ enabled: !r.enabled }, r.enabled ? "Turned off" : "Turned on")} color={r.is_production ? "secondary" : "primary"} />
      </Box>
      <Typography variant="body2" color="text.secondary">Rollout: {pct}% of users {r.enabled ? "" : "(applies once the flag is on)"}</Typography>
      <Box sx={{ display: "flex", gap: 2, alignItems: "center", px: 1 }}>
        <Slider value={pct} min={0} max={100} step={5} disabled={!canEdit} valueLabelDisplay="auto" onChange={(_, v) => setPct(v as number)} />
        <Button size="small" variant="outlined" disabled={!canEdit || pct === r.rollout_percentage}
          onClick={() => save({ rollout_percentage: pct }, `Rollout set to ${pct}%`)}>Apply</Button>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5, mb: 1 }}>Schedule (your local time)</Typography>
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", alignItems: "center" }}>
        <TextField size="small" type="datetime-local" label="Turn on at" value={on} disabled={!canEdit} onChange={(e) => setOn(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
        <TextField size="small" type="datetime-local" label="Turn off at" value={off} disabled={!canEdit} onChange={(e) => setOff(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
        <Button size="small" variant="outlined" disabled={!canEdit}
          onClick={() => save({ scheduled_enable_at: fromLocalInput(on), scheduled_disable_at: fromLocalInput(off) }, "Schedule saved")}>Save schedule</Button>
        {canRollback && <Button size="small" startIcon={<UndoIcon />} color="inherit" onClick={rollback} sx={{ ml: "auto" }}>Undo last change</Button>}
      </Box>
      {!canEdit && r.is_production && <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>Production changes need the production:write permission.</Typography>}
    </Paper>
  );
}

function UsersTab({ flag, envs, canEdit }: { flag: Flag; envs: Environment[]; canEdit: boolean }) {
  const toast = useToast();
  const [rows, setRows] = useState<Assignment[]>([]);
  const [envId, setEnvId] = useState(envs[0]?.id ?? 0);
  const [uid, setUid] = useState("");
  const [access, setAccess] = useState<"allow" | "deny">("allow");
  const load = useCallback(() => { api.get<Assignment[]>(`/flags/${flag.id}/assignments`).then((r) => setRows(r.data)); }, [flag.id]);
  useEffect(load, [load]);
  const envName = (id: number) => envs.find((e) => e.id === id)?.name ?? id;
  const add = async () => {
    try { await api.post(`/flags/${flag.id}/assignments`, { environment_id: envId, user_identifier: uid.trim(), access }); setUid(""); toast("Access saved"); load(); }
    catch (e) { toast(errorMessage(e), "error"); }
  };
  const remove = async (id: number) => { try { await api.delete(`/assignments/${id}`); toast("Removed"); load(); } catch (e) { toast(errorMessage(e), "error"); } };
  return (
    <Paper sx={{ p: 2.5 }}>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        Allowed users get the feature even when the flag is off or outside the rollout percentage. Denied users never get it.
      </Typography>
      {canEdit && (
        <Box sx={{ display: "flex", gap: 1.5, mb: 2, flexWrap: "wrap" }}>
          <TextField select size="small" label="Environment" value={envId} onChange={(e) => setEnvId(Number(e.target.value))} sx={{ minWidth: 160 }}>
            {envs.map((e) => <MenuItem key={e.id} value={e.id}>{e.name}</MenuItem>)}
          </TextField>
          <TextField size="small" label="User ID or email" value={uid} onChange={(e) => setUid(e.target.value)} sx={{ minWidth: 240 }} />
          <TextField select size="small" label="Access" value={access} onChange={(e) => setAccess(e.target.value as "allow" | "deny")} sx={{ minWidth: 120 }}>
            <MenuItem value="allow">Allow</MenuItem><MenuItem value="deny">Deny</MenuItem>
          </TextField>
          <Button variant="contained" onClick={add} disabled={!uid.trim()}>Save access</Button>
        </Box>
      )}
      <Table size="small">
        <TableHead><TableRow><TableCell>User</TableCell><TableCell>Environment</TableCell><TableCell>Access</TableCell><TableCell>Added</TableCell><TableCell /></TableRow></TableHead>
        <TableBody>
          {rows.map((a) => (
            <TableRow key={a.id}>
              <TableCell sx={{ fontFamily: MONO, fontSize: 13 }}>{a.user_identifier}</TableCell>
              <TableCell>{envName(a.environment_id)}</TableCell>
              <TableCell><Chip size="small" label={a.access} color={a.access === "allow" ? "primary" : "default"} /></TableCell>
              <TableCell>{fmt(a.created_at)}</TableCell>
              <TableCell align="right">{canEdit && <IconButton size="small" onClick={() => remove(a.id)} aria-label="Remove"><DeleteIcon fontSize="small" /></IconButton>}</TableCell>
            </TableRow>
          ))}
          {rows.length === 0 && <TableRow><TableCell colSpan={5}><Typography color="text.secondary" sx={{ py: 2, textAlign: "center" }}>No user-specific access yet.</Typography></TableCell></TableRow>}
        </TableBody>
      </Table>
    </Paper>
  );
}

function UsageTab({ flag }: { flag: Flag }) {
  const [data, setData] = useState<{ series: UsagePoint[]; total_evaluations: number; enabled_rate: number } | null>(null);
  useEffect(() => { api.get(`/analytics/usage`, { params: { flag_id: flag.id, days: 14 } }).then((r) => setData(r.data)); }, [flag.id]);
  if (!data) return <CircularProgress />;
  return (
    <Paper sx={{ p: 2.5 }}>
      <Typography sx={{ mb: 2 }}><b style={{ fontFamily: MONO }}>{data.total_evaluations.toLocaleString()}</b> evaluations in the last 14 days, <b style={{ fontFamily: MONO }}>{data.enabled_rate}%</b> returned on.</Typography>
      <Line height={90} data={{
        labels: data.series.map((p) => p.date.slice(5)),
        datasets: [
          { label: "Evaluations", data: data.series.map((p) => p.evaluations), borderColor: "#0B6E5B", tension: 0.25 },
          { label: "Returned on", data: data.series.map((p) => p.enabled_count), borderColor: "#B45309", tension: 0.25 },
        ],
      }} options={{ scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }} />
    </Paper>
  );
}

function HistoryTab({ flag, canRollback, onChanged }: { flag: Flag; canRollback: boolean; onChanged: () => void }) {
  const toast = useToast();
  const [rows, setRows] = useState<Audit[]>([]);
  const load = useCallback(() => { api.get<Audit[]>(`/flags/${flag.id}/history`).then((r) => setRows(r.data)); }, [flag.id]);
  useEffect(load, [load, flag.updated_at]);
  const undo = async (a: Audit) => {
    try { await api.post(`/rollouts/${a.entity_id}/rollback`, { audit_log_id: a.id }); toast("Change undone"); load(); onChanged(); }
    catch (e) { toast(errorMessage(e), "error"); }
  };
  const undoable = (a: Audit) => a.entity_type === "rollout" && !!a.before && a.action !== "rollback";
  return (
    <Paper sx={{ overflowX: "auto" }}>
      <Table size="small">
        <TableHead><TableRow><TableCell>When</TableCell><TableCell>Who</TableCell><TableCell>Change</TableCell><TableCell>Environment</TableCell><TableCell>Details</TableCell><TableCell /></TableRow></TableHead>
        <TableBody>
          {rows.map((a) => (
            <TableRow key={a.id}>
              <TableCell sx={{ whiteSpace: "nowrap" }}>{fmt(a.created_at)}</TableCell>
              <TableCell>{a.username}</TableCell>
              <TableCell>{actionLabel[a.action] ?? a.action}</TableCell>
              <TableCell>{a.environment_key ?? "—"}</TableCell>
              <TableCell sx={{ fontFamily: MONO, fontSize: 12 }}>{a.after ? JSON.stringify(a.after) : "—"}</TableCell>
              <TableCell align="right">{canRollback && undoable(a) && <Button size="small" onClick={() => undo(a)}>Undo this</Button>}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
}

function TestTab({ flag, envs }: { flag: Flag; envs: Environment[] }) {
  const [envId, setEnvId] = useState(envs[0]?.id ?? 0);
  const [uid, setUid] = useState("");
  const [res, setRes] = useState<{ enabled: boolean; reason: string } | null>(null);
  const run = async () => { const r = await api.get(`/flags/${flag.id}/test-evaluate`, { params: { environment_id: envId, user_id: uid || undefined } }); setRes(r.data); };
  return (
    <Paper sx={{ p: 2.5 }}>
      <Typography color="text.secondary" sx={{ mb: 2 }}>Check what a user would see right now. Test runs are not counted in usage analytics.</Typography>
      <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap", alignItems: "center" }}>
        <TextField select size="small" label="Environment" value={envId} onChange={(e) => setEnvId(Number(e.target.value))} sx={{ minWidth: 160 }}>
          {envs.map((e) => <MenuItem key={e.id} value={e.id}>{e.name}</MenuItem>)}
        </TextField>
        <TextField size="small" label="User ID (optional)" value={uid} onChange={(e) => setUid(e.target.value)} />
        <Button variant="contained" onClick={run}>Evaluate</Button>
      </Box>
      {res && <Alert sx={{ mt: 2 }} severity={res.enabled ? "success" : "info"}>
        {res.enabled ? "Feature is ON" : "Feature is OFF"} — reason: <code>{res.reason}</code></Alert>}
    </Paper>
  );
}

export default function FlagDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { can } = useAuth();
  const toast = useToast();
  const [flag, setFlag] = useState<Flag | null>(null);
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [tab, setTab] = useState(0);
  const [edit, setEdit] = useState({ name: "", description: "" });

  const load = useCallback(() => {
    api.get<Flag>(`/flags/${id}`).then((r) => { setFlag(r.data); setEdit({ name: r.data.name, description: r.data.description }); });
  }, [id]);
  useEffect(() => { load(); api.get<Environment[]>("/environments").then((r) => setEnvs(r.data)); }, [load]);

  if (!flag) return <CircularProgress />;
  const patch = async (body: object, msg: string) => {
    try { await api.patch(`/flags/${flag.id}`, body); toast(msg); load(); } catch (e) { toast(errorMessage(e), "error"); }
  };
  const del = async () => {
    if (!confirm(`Delete "${flag.key}" permanently? Archive it instead if you may need it again.`)) return;
    try { await api.delete(`/flags/${flag.id}`); toast("Flag deleted"); nav("/flags"); } catch (e) { toast(errorMessage(e), "error"); }
  };
  const canWrite = can("flags:write");

  return (
    <>
      <PageHeader title={flag.key} subtitle={flag.name}
        actions={canWrite && <>
          <Button variant="outlined" onClick={() => patch({ is_archived: !flag.is_archived }, flag.is_archived ? "Flag restored" : "Flag archived")}>{flag.is_archived ? "Restore" : "Archive"}</Button>
          <Button color="error" onClick={del}>Delete</Button>
        </>} />
      {flag.is_archived && <Alert severity="warning" sx={{ mb: 2 }}>This flag is archived and always evaluates to off.</Alert>}
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Environments" /><Tab label="Users" /><Tab label="Usage" /><Tab label="History" /><Tab label="Test" />
      </Tabs>

      {tab === 0 && (
        <Box sx={{ display: "grid", gap: 2 }}>
          {canWrite && (
            <Paper sx={{ p: 2.5 }}>
              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                <TextField size="small" label="Name" value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} sx={{ minWidth: 260 }} />
                <TextField size="small" label="Description" value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} sx={{ flex: 1, minWidth: 260 }} />
                <Button variant="outlined" onClick={() => patch(edit, "Details saved")} disabled={edit.name === flag.name && edit.description === flag.description}>Save details</Button>
              </Box>
            </Paper>
          )}
          {flag.rollouts.map((r) => (
            <RolloutCard key={r.id} r={r} canEdit={can("rollouts:write") && (!r.is_production || can("production:write")) && !flag.is_archived}
              canRollback={can("rollouts:rollback") && (!r.is_production || can("production:write"))} onChanged={load} />
          ))}
        </Box>
      )}
      {tab === 1 && <UsersTab flag={flag} envs={envs} canEdit={can("assignments:write")} />}
      {tab === 2 && <UsageTab flag={flag} />}
      {tab === 3 && <HistoryTab flag={flag} canRollback={can("rollouts:rollback")} onChanged={load} />}
      {tab === 4 && <TestTab flag={flag} envs={envs} />}
    </>
  );
}

import { useCallback, useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, Link, Paper, Switch,
  Table, TableBody, TableCell, TableHead, TableRow, TextField, Tooltip, Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import ScheduleIcon from "@mui/icons-material/Schedule";
import { api, errorMessage } from "../api";
import { useAuth } from "../auth";
import type { Flag, Rollout } from "../types";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/Toast";
import { MONO } from "../theme";

export default function Flags() {
  const { can } = useAuth();
  const toast = useToast();
  const [flags, setFlags] = useState<Flag[]>([]);
  const [search, setSearch] = useState("");
  const [archived, setArchived] = useState(false);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ key: "", name: "", description: "" });

  const load = useCallback(() => {
    api.get<Flag[]>("/flags", { params: { search: search || undefined, include_archived: archived } }).then((r) => setFlags(r.data));
  }, [search, archived]);
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  const canToggle = (r: Rollout) => can("rollouts:write") && (!r.is_production || can("production:write"));

  const toggle = async (r: Rollout) => {
    try {
      await api.put(`/rollouts/${r.id}`, { enabled: !r.enabled });
      toast(`${r.enabled ? "Turned off" : "Turned on"} in ${r.environment_name}`);
      load();
    } catch (e) { toast(errorMessage(e), "error"); }
  };

  const create = async () => {
    try {
      await api.post("/flags", form);
      toast("Flag created");
      setOpen(false); setForm({ key: "", name: "", description: "" }); load();
    } catch (e) { toast(errorMessage(e), "error"); }
  };

  return (
    <>
      <PageHeader title="Feature flags" subtitle="Switch features on and off per environment, without a deploy."
        actions={can("flags:write") && <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpen(true)}>New flag</Button>} />
      <Box sx={{ display: "flex", gap: 2, mb: 2, alignItems: "center", flexWrap: "wrap" }}>
        <TextField size="small" placeholder="Search by key or name" value={search} onChange={(e) => setSearch(e.target.value)} sx={{ width: 300, bgcolor: "background.paper" }} />
        <FormControlLabel control={<Switch checked={archived} onChange={(e) => setArchived(e.target.checked)} />} label="Show archived" />
      </Box>
      <Paper sx={{ overflowX: "auto" }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Flag</TableCell>
              {flags[0]?.rollouts.map((r) => <TableCell key={r.environment_id} align="center">{r.environment_name}</TableCell>)}
            </TableRow>
          </TableHead>
          <TableBody>
            {flags.map((f) => (
              <TableRow key={f.id} hover sx={{ opacity: f.is_archived ? 0.55 : 1 }}>
                <TableCell>
                  <Link component={RouterLink} to={`/flags/${f.id}`} underline="hover" sx={{ fontFamily: MONO, fontSize: 14, fontWeight: 500 }}>{f.key}</Link>
                  {f.is_archived && <Chip size="small" label="archived" sx={{ ml: 1 }} />}
                  <Typography variant="body2" color="text.secondary">{f.name}</Typography>
                </TableCell>
                {f.rollouts.map((r) => (
                  <TableCell key={r.id} align="center">
                    <Switch checked={r.enabled} disabled={!canToggle(r) || f.is_archived} onChange={() => toggle(r)}
                      color={r.is_production ? "secondary" : "primary"} />
                    <Box sx={{ minHeight: 22, display: "flex", justifyContent: "center", gap: 0.5 }}>
                      {r.enabled && r.rollout_percentage < 100 && <Chip size="small" label={`${r.rollout_percentage}%`} />}
                      {(r.scheduled_enable_at || r.scheduled_disable_at) && (
                        <Tooltip title="Has a scheduled change"><ScheduleIcon fontSize="small" color="secondary" /></Tooltip>
                      )}
                    </Box>
                  </TableCell>
                ))}
              </TableRow>
            ))}
            {flags.length === 0 && (
              <TableRow><TableCell colSpan={4}><Typography color="text.secondary" sx={{ py: 3, textAlign: "center" }}>
                No flags found. Create one to start controlling a feature.</Typography></TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New flag</DialogTitle>
        <DialogContent>
          <TextField label="Key" helperText="Lowercase letters, numbers, dots, dashes. Used in code; cannot be changed later." fullWidth margin="dense" autoFocus
            value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} slotProps={{ htmlInput: { style: { fontFamily: MONO } } }} />
          <TextField label="Name" fullWidth margin="dense" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <TextField label="Description" fullWidth margin="dense" multiline minRows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>New flags start switched off in every environment.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={create} disabled={!form.key || !form.name}>Create flag</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

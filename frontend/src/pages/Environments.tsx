import { useCallback, useEffect, useState } from "react";
import {
  Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, IconButton, Paper, Switch,
  Table, TableBody, TableCell, TableHead, TableRow, TextField, Tooltip, Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import CopyIcon from "@mui/icons-material/ContentCopy";
import { api, errorMessage } from "../api";
import { useAuth } from "../auth";
import type { Environment } from "../types";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/Toast";
import { MONO } from "../theme";

export default function Environments() {
  const { can } = useAuth();
  const toast = useToast();
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", key: "", description: "", is_production: false });
  const manage = can("environments:manage");
  const load = useCallback(() => { api.get<Environment[]>("/environments").then((r) => setEnvs(r.data)); }, []);
  useEffect(load, [load]);

  const create = async () => {
    try { await api.post("/environments", form); toast("Environment created"); setOpen(false); setForm({ name: "", key: "", description: "", is_production: false }); load(); }
    catch (e) { toast(errorMessage(e), "error"); }
  };
  const rotate = async (e: Environment) => {
    if (!confirm(`Rotate the SDK key for ${e.name}? Apps using the old key will stop working.`)) return;
    try { await api.post(`/environments/${e.id}/rotate-sdk-key`); toast("New SDK key generated"); load(); } catch (err) { toast(errorMessage(err), "error"); }
  };
  const copy = (text: string) => navigator.clipboard.writeText(text).then(() => toast("Copied"));

  return (
    <>
      <PageHeader title="Environments" subtitle="Each environment has its own flag state and SDK key."
        actions={manage && <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpen(true)}>New environment</Button>} />
      <Paper sx={{ overflowX: "auto" }}>
        <Table>
          <TableHead><TableRow><TableCell>Environment</TableCell><TableCell>Key</TableCell>{manage && <TableCell>SDK key</TableCell>}{manage && <TableCell />}</TableRow></TableHead>
          <TableBody>
            {envs.map((e) => (
              <TableRow key={e.id}>
                <TableCell>
                  <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                    <Typography fontWeight={500}>{e.name}</Typography>
                    {e.is_production && <Chip size="small" color="secondary" label="production" />}
                  </Box>
                  <Typography variant="body2" color="text.secondary">{e.description}</Typography>
                </TableCell>
                <TableCell sx={{ fontFamily: MONO, fontSize: 13 }}>{e.key}</TableCell>
                {manage && (
                  <TableCell sx={{ fontFamily: MONO, fontSize: 12 }}>
                    {e.sdk_key}
                    {e.sdk_key && <Tooltip title="Copy"><IconButton size="small" onClick={() => copy(e.sdk_key!)}><CopyIcon fontSize="inherit" /></IconButton></Tooltip>}
                  </TableCell>
                )}
                {manage && <TableCell align="right"><Button size="small" color="inherit" onClick={() => rotate(e)}>Rotate key</Button></TableCell>}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New environment</DialogTitle>
        <DialogContent>
          <TextField label="Name" fullWidth margin="dense" autoFocus value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <TextField label="Key" helperText="Lowercase, e.g. staging" fullWidth margin="dense" value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} />
          <TextField label="Description" fullWidth margin="dense" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <FormControlLabel control={<Switch checked={form.is_production} onChange={(e) => setForm({ ...form, is_production: e.target.checked })} />} label="Treat as production (only users with production access can change it)" />
        </DialogContent>
        <DialogActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button variant="contained" disabled={!form.name || !form.key} onClick={create}>Create environment</Button></DialogActions>
      </Dialog>
    </>
  );
}

import { useCallback, useEffect, useState } from "react";
import {
  Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Paper, Switch, Table, TableBody,
  TableCell, TableHead, TableRow, TextField,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { api, errorMessage } from "../api";
import { useAuth } from "../auth";
import type { Role, User } from "../types";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/Toast";
import { fmt } from "../utils";

export default function Users() {
  const { user: me } = useAuth();
  const toast = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: "", username: "", password: "", role_id: 0 });
  const load = useCallback(() => { api.get<User[]>("/users").then((r) => setUsers(r.data)); }, []);
  useEffect(() => { load(); api.get<Role[]>("/roles").then((r) => { setRoles(r.data); setForm((f) => ({ ...f, role_id: r.data.find((x) => x.name === "viewer")?.id ?? r.data[0]?.id ?? 0 })); }); }, [load]);

  const patch = async (u: User, body: object) => {
    try { await api.patch(`/users/${u.id}`, body); toast("User updated"); load(); } catch (e) { toast(errorMessage(e), "error"); }
  };
  const create = async () => {
    try { await api.post("/users", form); toast("User created"); setOpen(false); setForm({ ...form, email: "", username: "", password: "" }); load(); }
    catch (e) { toast(errorMessage(e), "error"); }
  };

  return (
    <>
      <PageHeader title="Users" subtitle="Roles decide who can view, change, and roll back flags."
        actions={<Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpen(true)}>New user</Button>} />
      <Paper sx={{ overflowX: "auto" }}>
        <Table>
          <TableHead><TableRow><TableCell>User</TableCell><TableCell>Role</TableCell><TableCell>Active</TableCell><TableCell>Created</TableCell></TableRow></TableHead>
          <TableBody>
            {users.map((u) => (
              <TableRow key={u.id}>
                <TableCell>{u.username}{u.id === me?.id && <Chip size="small" label="you" sx={{ ml: 1 }} />}<br /><span style={{ color: "#55645F", fontSize: 13 }}>{u.email}</span></TableCell>
                <TableCell>
                  <TextField select size="small" value={u.role.id} disabled={u.id === me?.id} onChange={(e) => patch(u, { role_id: Number(e.target.value) })} sx={{ minWidth: 140 }}>
                    {roles.map((r) => <MenuItem key={r.id} value={r.id}>{r.name}</MenuItem>)}
                  </TextField>
                </TableCell>
                <TableCell><Switch checked={u.is_active} disabled={u.id === me?.id} onChange={() => patch(u, { is_active: !u.is_active })} /></TableCell>
                <TableCell>{fmt(u.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
      <Paper sx={{ p: 2.5, mt: 2 }}>
        {roles.map((r) => (
          <div key={r.id} style={{ marginBottom: 8 }}><b>{r.name}</b>: {r.description}</div>
        ))}
      </Paper>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New user</DialogTitle>
        <DialogContent>
          <TextField label="Email" fullWidth margin="dense" autoFocus value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <TextField label="Username" fullWidth margin="dense" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          <TextField label="Password" type="password" helperText="At least 8 characters" fullWidth margin="dense" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <TextField select label="Role" fullWidth margin="dense" value={form.role_id} onChange={(e) => setForm({ ...form, role_id: Number(e.target.value) })}>
            {roles.map((r) => <MenuItem key={r.id} value={r.id}>{r.name}</MenuItem>)}
          </TextField>
        </DialogContent>
        <DialogActions><Button onClick={() => setOpen(false)}>Cancel</Button><Button variant="contained" disabled={!form.email || !form.username || form.password.length < 8} onClick={create}>Create user</Button></DialogActions>
      </Dialog>
    </>
  );
}

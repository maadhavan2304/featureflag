import { useCallback, useEffect, useState } from "react";
import {
  Box, Button, Chip, Dialog, DialogContent, DialogTitle, MenuItem, Paper, Table, TableBody, TableCell, TableHead,
  TablePagination, TableRow, TextField,
} from "@mui/material";
import { api } from "../api";
import type { Audit } from "../types";
import PageHeader from "../components/PageHeader";
import { actionLabel, fmt } from "../utils";
import { MONO } from "../theme";

export default function AuditLogs() {
  const [items, setItems] = useState<Audit[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(25);
  const [action, setAction] = useState("");
  const [detail, setDetail] = useState<Audit | null>(null);

  const load = useCallback(() => {
    api.get("/audit-logs", { params: { limit: size, offset: page * size, action: action || undefined } })
      .then((r) => { setItems(r.data.items); setTotal(r.data.total); });
  }, [page, size, action]);
  useEffect(load, [load]);

  return (
    <>
      <PageHeader title="Audit log" subtitle="Every change, who made it, and what it was before." />
      <Box sx={{ mb: 2 }}>
        <TextField select size="small" label="Action" value={action} onChange={(e) => { setAction(e.target.value); setPage(0); }} sx={{ minWidth: 220, bgcolor: "background.paper" }}>
          <MenuItem value="">All actions</MenuItem>
          {Object.entries(actionLabel).map(([k, v]) => <MenuItem key={k} value={k}>{v}</MenuItem>)}
        </TextField>
      </Box>
      <Paper sx={{ overflowX: "auto" }}>
        <Table size="small">
          <TableHead><TableRow><TableCell>When</TableCell><TableCell>Who</TableCell><TableCell>Action</TableCell><TableCell>Flag</TableCell><TableCell>Environment</TableCell><TableCell /></TableRow></TableHead>
          <TableBody>
            {items.map((a) => (
              <TableRow key={a.id} hover>
                <TableCell sx={{ whiteSpace: "nowrap" }}>{fmt(a.created_at)}</TableCell>
                <TableCell>{a.username}</TableCell>
                <TableCell>{actionLabel[a.action] ?? a.action}</TableCell>
                <TableCell sx={{ fontFamily: MONO, fontSize: 13 }}>{a.flag_key ?? "—"}</TableCell>
                <TableCell>{a.environment_key ? <Chip size="small" variant="outlined" label={a.environment_key} /> : "—"}</TableCell>
                <TableCell align="right">{(a.before || a.after) && <Button size="small" onClick={() => setDetail(a)}>View change</Button>}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <TablePagination component="div" count={total} page={page} rowsPerPage={size} rowsPerPageOptions={[25, 50, 100]}
          onPageChange={(_, p) => setPage(p)} onRowsPerPageChange={(e) => { setSize(Number(e.target.value)); setPage(0); }} />
      </Paper>
      <Dialog open={!!detail} onClose={() => setDetail(null)} fullWidth maxWidth="md">
        <DialogTitle>{detail && (actionLabel[detail.action] ?? detail.action)} · {detail?.flag_key}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2 }}>
            {(["before", "after"] as const).map((k) => (
              <Box key={k}>
                <b>{k === "before" ? "Before" : "After"}</b>
                <pre style={{ background: "#EEF1EF", padding: 12, borderRadius: 6, overflow: "auto", fontFamily: MONO, fontSize: 12 }}>
                  {detail?.[k] ? JSON.stringify(detail[k], null, 2) : "—"}
                </pre>
              </Box>
            ))}
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
}

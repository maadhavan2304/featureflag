import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { Box, Chip, CircularProgress, Link, Paper, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { ArcElement, BarElement, CategoryScale, Chart as ChartJS, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip } from "chart.js";
import { Bar, Doughnut, Line } from "react-chartjs-2";
import { api } from "../api";
import type { Dashboard as DashboardData } from "../types";
import PageHeader from "../components/PageHeader";
import { actionLabel, fmt } from "../utils";
import { MONO } from "../theme";

ChartJS.register(ArcElement, BarElement, CategoryScale, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip);

const GREEN = "#0B6E5B", AMBER = "#B45309", GREY = "#C9D3CF";

function Stat({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <Paper sx={{ p: 2.5 }}>
      <Typography color="text.secondary" variant="body2">{label}</Typography>
      <Typography sx={{ fontFamily: MONO, fontSize: 32, fontWeight: 500, lineHeight: 1.2 }}>{value}</Typography>
      {hint && <Typography variant="caption" color="text.secondary">{hint}</Typography>}
    </Paper>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  useEffect(() => { api.get<DashboardData>("/analytics/dashboard").then((r) => setData(r.data)); }, []);
  if (!data) return <CircularProgress />;
  const t = data.totals;
  const dist = Object.entries(data.rollout_distribution);

  return (
    <>
      <PageHeader title="Dashboard" subtitle="What is live, where, and how far it has rolled out." />
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" }, mb: 2 }}>
        <Stat label="Active flags" value={t.flags} hint={`${t.archived} archived`} />
        <Stat label="Live in at least one environment" value={t.enabled_somewhere} />
        <Stat label="Partial rollouts" value={t.partial_rollouts} hint="Enabled below 100%" />
        <Stat label="Scheduled changes" value={t.scheduled} hint="Waiting to turn on or off" />
      </Box>

      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "3fr 2fr" }, mb: 2 }}>
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" gutterBottom>Flags by environment</Typography>
          <Bar height={120} data={{
            labels: data.environments.map((e) => e.name),
            datasets: [
              { label: "Enabled", data: data.environments.map((e) => e.enabled), backgroundColor: GREEN },
              { label: "Disabled", data: data.environments.map((e) => e.disabled), backgroundColor: GREY },
            ],
          }} options={{ scales: { x: { stacked: true }, y: { stacked: true, ticks: { precision: 0 } } }, plugins: { legend: { position: "bottom" } } }} />
        </Paper>
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" gutterBottom>Rollout percentage</Typography>
          <Doughnut data={{
            labels: dist.map(([k]) => k),
            datasets: [{ data: dist.map(([, v]) => v), backgroundColor: [GREY, "#E3B57A", AMBER, "#4C9A8A", GREEN] }],
          }} options={{ plugins: { legend: { position: "bottom" } } }} />
        </Paper>
      </Box>

      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "3fr 2fr" }, mb: 2 }}>
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" gutterBottom>Evaluations, last 7 days</Typography>
          <Line height={120} data={{
            labels: data.usage_7d.map((p) => p.date.slice(5)),
            datasets: [
              { label: "Evaluations", data: data.usage_7d.map((p) => p.evaluations), borderColor: GREEN, backgroundColor: "rgba(11,110,91,.12)", fill: true, tension: 0.25 },
              { label: "Returned on", data: data.usage_7d.map((p) => p.enabled_count), borderColor: AMBER, tension: 0.25 },
            ],
          }} options={{ scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }, plugins: { legend: { position: "bottom" } } }} />
        </Paper>
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="h6" gutterBottom>Most evaluated flags</Typography>
          {data.top_flags.length === 0 ? (
            <Typography color="text.secondary">No evaluations yet. Call <code>POST /sdk/evaluate</code> from an app to see usage here.</Typography>
          ) : (
            <Table size="small"><TableBody>
              {data.top_flags.map((f) => (
                <TableRow key={f.flag_id}>
                  <TableCell><Link component={RouterLink} to={`/flags/${f.flag_id}`} sx={{ fontFamily: MONO, fontSize: 13 }}>{f.key}</Link></TableCell>
                  <TableCell align="right" sx={{ fontFamily: MONO }}>{f.evaluations.toLocaleString()}</TableCell>
                </TableRow>
              ))}
            </TableBody></Table>
          )}
        </Paper>
      </Box>

      <Paper sx={{ p: 2.5 }}>
        <Typography variant="h6" gutterBottom>Recent changes</Typography>
        <Table size="small">
          <TableHead><TableRow><TableCell>When</TableCell><TableCell>Who</TableCell><TableCell>What</TableCell><TableCell>Flag</TableCell><TableCell>Environment</TableCell></TableRow></TableHead>
          <TableBody>
            {data.recent_activity.map((a) => (
              <TableRow key={a.id}>
                <TableCell>{fmt(a.created_at)}</TableCell>
                <TableCell>{a.username}</TableCell>
                <TableCell>{actionLabel[a.action] ?? a.action}</TableCell>
                <TableCell sx={{ fontFamily: MONO, fontSize: 13 }}>{a.flag_key ?? "—"}</TableCell>
                <TableCell>{a.environment_key ? <Chip size="small" label={a.environment_key} variant="outlined" /> : "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </>
  );
}

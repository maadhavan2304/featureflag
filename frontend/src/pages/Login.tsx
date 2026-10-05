import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Box, Button, Paper, TextField, Typography } from "@mui/material";
import { useAuth } from "../auth";
import { errorMessage } from "../api";
import { MONO } from "../theme";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError("");
    try { await login(username, password); nav("/"); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  };

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", bgcolor: "#10231F", p: 2 }}>
      <Paper component="form" onSubmit={submit} sx={{ p: 4, width: 380, maxWidth: "100%" }}>
        <Typography sx={{ fontFamily: MONO, fontSize: 22, fontWeight: 500 }}>flagship</Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>Sign in to manage feature flags.</Typography>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <TextField label="Email or username" fullWidth autoFocus margin="dense" value={username} onChange={(e) => setUsername(e.target.value)} />
        <TextField label="Password" type="password" fullWidth margin="dense" value={password} onChange={(e) => setPassword(e.target.value)} />
        <Button type="submit" variant="contained" fullWidth size="large" disabled={busy || !username || !password} sx={{ mt: 2 }}>
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </Paper>
    </Box>
  );
}

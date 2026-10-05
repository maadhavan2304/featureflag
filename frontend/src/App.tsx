import { Navigate, Route, Routes } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Flags from "./pages/Flags";
import FlagDetail from "./pages/FlagDetail";
import Environments from "./pages/Environments";
import Users from "./pages/Users";
import AuditLogs from "./pages/AuditLogs";

export default function App() {
  const { user, loading, can } = useAuth();
  if (loading) return <Box sx={{ display: "grid", placeItems: "center", height: "100vh" }}><CircularProgress /></Box>;
  if (!user) return <Routes><Route path="/login" element={<Login />} /><Route path="*" element={<Navigate to="/login" replace />} /></Routes>;
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/flags" element={<Flags />} />
        <Route path="/flags/:id" element={<FlagDetail />} />
        <Route path="/environments" element={<Environments />} />
        {can("users:manage") && <Route path="/users" element={<Users />} />}
        {can("audit:read") && <Route path="/audit" element={<AuditLogs />} />}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

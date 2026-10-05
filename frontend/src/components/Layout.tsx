import type { ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Box, Button, Chip, Drawer, List, ListItemButton, ListItemIcon, ListItemText, Typography } from "@mui/material";
import DashboardIcon from "@mui/icons-material/SpaceDashboardOutlined";
import FlagIcon from "@mui/icons-material/OutlinedFlag";
import LayersIcon from "@mui/icons-material/LayersOutlined";
import PeopleIcon from "@mui/icons-material/PeopleOutline";
import HistoryIcon from "@mui/icons-material/HistoryOutlined";
import LogoutIcon from "@mui/icons-material/Logout";
import { useAuth } from "../auth";
import { ToastProvider } from "./Toast";
import { MONO } from "../theme";

const WIDTH = 232;

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout, can } = useAuth();
  const { pathname } = useLocation();
  const nav = [
    { to: "/", label: "Dashboard", icon: <DashboardIcon />, show: true },
    { to: "/flags", label: "Feature flags", icon: <FlagIcon />, show: true },
    { to: "/environments", label: "Environments", icon: <LayersIcon />, show: true },
    { to: "/audit", label: "Audit log", icon: <HistoryIcon />, show: can("audit:read") },
    { to: "/users", label: "Users", icon: <PeopleIcon />, show: can("users:manage") },
  ].filter((n) => n.show);

  return (
    <ToastProvider>
      <Box sx={{ display: "flex", minHeight: "100vh" }}>
        <Drawer variant="permanent" sx={{ width: WIDTH, flexShrink: 0, "& .MuiDrawer-paper": { width: WIDTH, bgcolor: "#10231F", color: "#DCE8E4", border: 0 } }}>
          <Box sx={{ px: 2.5, pt: 3, pb: 2 }}>
            <Typography sx={{ fontFamily: MONO, fontWeight: 500, fontSize: 18, color: "#fff" }}>flagship</Typography>
            <Typography variant="caption" sx={{ color: "#8FA8A1" }}>feature flag console</Typography>
          </Box>
          <List sx={{ px: 1 }}>
            {nav.map((n) => {
              const active = n.to === "/" ? pathname === "/" : pathname.startsWith(n.to);
              return (
                <ListItemButton key={n.to} component={NavLink} to={n.to} selected={active}
                  sx={{ borderRadius: 1, mb: 0.25, color: "inherit",
                    "&.Mui-selected": { bgcolor: "rgba(255,255,255,.1)" }, "&:hover": { bgcolor: "rgba(255,255,255,.07)" } }}>
                  <ListItemIcon sx={{ color: "inherit", minWidth: 36 }}>{n.icon}</ListItemIcon>
                  <ListItemText primary={n.label} />
                </ListItemButton>
              );
            })}
          </List>
          <Box sx={{ mt: "auto", p: 2 }}>
            <Typography variant="body2" sx={{ color: "#fff" }}>{user?.username}</Typography>
            <Chip size="small" label={user?.role.name} sx={{ mt: 0.5, mb: 1.5, bgcolor: "rgba(255,255,255,.12)", color: "#DCE8E4" }} />
            <Button fullWidth startIcon={<LogoutIcon />} onClick={logout} sx={{ color: "#DCE8E4", justifyContent: "flex-start" }}>Sign out</Button>
          </Box>
        </Drawer>
        <Box component="main" sx={{ flex: 1, p: { xs: 2, md: 4 }, minWidth: 0, maxWidth: 1280 }}>{children}</Box>
      </Box>
    </ToastProvider>
  );
}

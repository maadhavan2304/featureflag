import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import { createTheme } from "@mui/material/styles";

export const MONO = "'IBM Plex Mono', ui-monospace, Menlo, monospace";

// Palette: panel-green on warm-grey paper, with amber reserved for production / scheduled states.
export const theme = createTheme({
  palette: {
    primary: { main: "#0B6E5B" },
    secondary: { main: "#B45309" },
    background: { default: "#EEF1EF", paper: "#FFFFFF" },
    text: { primary: "#14211D", secondary: "#55645F" },
    divider: "#D8DFDC",
  },
  shape: { borderRadius: 6 },
  typography: {
    fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
    h4: { fontWeight: 600, letterSpacing: -0.4 },
    h5: { fontWeight: 600, letterSpacing: -0.2 },
    h6: { fontWeight: 600 },
    button: { textTransform: "none", fontWeight: 500 },
  },
  components: {
    MuiPaper: { defaultProps: { variant: "outlined" } },
    MuiButton: { defaultProps: { disableElevation: true } },
    MuiTableCell: { styleOverrides: { head: { fontWeight: 600, color: "#55645F" } } },
  },
});

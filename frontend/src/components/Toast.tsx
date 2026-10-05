import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { Alert, Snackbar } from "@mui/material";

type Notify = (message: string, severity?: "success" | "error" | "info") => void;
const Ctx = createContext<Notify>(() => {});
export const useToast = () => useContext(Ctx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{ message: string; severity: "success" | "error" | "info" } | null>(null);
  const notify = useCallback<Notify>((message, severity = "success") => setState({ message, severity }), []);
  return (
    <Ctx.Provider value={notify}>
      {children}
      <Snackbar open={!!state} autoHideDuration={4000} onClose={() => setState(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}>
        {state ? <Alert severity={state.severity} variant="filled" onClose={() => setState(null)}>{state.message}</Alert> : undefined}
      </Snackbar>
    </Ctx.Provider>
  );
}

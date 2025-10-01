import { Box, Button, CircularProgress, Alert } from "@mui/material";
import AIWidget from "./components/AIWidget/AIWidget";
import React from "react";
import { useGenerateWidgets } from "./hooks/queries/useGenerateWidgets";

export default function AIWidgetDashboard() {
  const {
    start,
    isStarting,
    startError,
    result,
    resultStatus,
    isPolling,
    pollError
  } = useGenerateWidgets();

  const [showGenerateButton, setShowGenerateButton] = React.useState(true);
  const [darkMode, setDarkMode] = React.useState(false);

  React.useEffect(() => {
    if (resultStatus === "SUCCESS" && result && result.length > 0) {
      setShowGenerateButton(false);
    }
  }, [resultStatus, result]);

  return (
    <Box
      sx={{
        p: 2,
        borderRadius: 4,
        textAlign: "center",
        maxWidth: 2000,
        minHeight: 300,
        mx: "auto",
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 4,
        justifyItems: "center",
        alignItems: "center",
        background: darkMode ? "rgba(16,24,40,0.85)" : "rgba(255,255,255,0.25)",
        border: darkMode ? "2px solid #1D2939" : "2px solid rgba(255,255,255,0.4)",
        boxShadow: "0 8px 40px 0 rgba(0,0,0,0.25), 0 0 0 1px rgba(255,255,255,0.3) inset",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        overflowX: "auto",
        overflowY: "visible",
      }}
    >
      <Button
        variant="outlined"
        color={darkMode ? "secondary" : "primary"}
        sx={{ mt: 2, fontWeight: 600, gridColumn: "1 / -1" }}
        onClick={() => setDarkMode((d) => !d)}
      >
        {darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
      </Button>
      {showGenerateButton && (
        <Button
          variant="contained"
          color="secondary"
          sx={{ mt: 2, fontWeight: 600, gridColumn: "1 / -1" }}
          onClick={() => start()}
          disabled={isStarting || isPolling}
        >
          {(isStarting || isPolling) ? <CircularProgress size={24} color="inherit" /> : "Generate Widget"}
        </Button>
      )}
      {(startError || pollError) && (
        <Alert severity="error" sx={{ mt: 2, gridColumn: "1 / -1" }}>
          {startError?.message || pollError?.message}
        </Alert>
      )}
      {isPolling && !result && (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 4, gridColumn: "1 / -1" }}>
          <CircularProgress size={48} color="secondary" />
        </Box>
      )}
      {result &&
        result.map((widget: { code: string }, idx: number) => (
          <AIWidget
            key={idx}
            widgetCode={widget.code}
            componentName="WidgetComponent"
            darkMode={darkMode}
          />
        ))}
    </Box>
  );
}

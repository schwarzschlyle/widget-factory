import AIWidgetDashboard from "@widget/AIWidgetDashboard";
import { Box } from "@mui/material";

function App() {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        width: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
      }}
    >
      <AIWidgetDashboard />
    </Box>
  );
}

export default App;

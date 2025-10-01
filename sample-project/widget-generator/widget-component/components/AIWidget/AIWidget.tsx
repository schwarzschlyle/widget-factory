import { Box } from "@mui/material";
import { BabelTranspiler } from "../BabelTranspiler/BabelTranspiler";

type AIWidgetProps = {
  widgetCode: string;
  componentName: string;
  darkMode?: boolean;
};

const AIWidget = ({ widgetCode, componentName, darkMode }: AIWidgetProps) => {
  // Load headersMap from .env (Vite)
  let headersMap = {};
  try {
    headersMap = JSON.parse(import.meta.env.VITE_DATASOURCE_AUTH_HEADERS || "{}");
  } catch (e) {
    headersMap = {};
  }

  // Debug: log headersMap to verify it is loaded correctly
  // eslint-disable-next-line no-console
  console.log("AIWidget headersMap (from VITE_DATASOURCE_AUTH_HEADERS):", JSON.stringify(headersMap, null, 2));

  return (
    <Box
      sx={{
        width: "100%",
        maxWidth: 600,
        height: 640,
        bgcolor: darkMode ? "#101828" : "background.paper",
        borderRadius: 2,
        boxShadow: 2,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        p: 2,
        m: 1,
        overflow: "hidden",
        border: darkMode ? "2px solid #1D2939" : "2px solid #D0D5DD",
        transition: "background 0.2s, border 0.2s"
      }}
    >
      <BabelTranspiler code={widgetCode} componentName={componentName} headersMap={headersMap} darkMode={darkMode} />
    </Box>
  );
};

export default AIWidget;

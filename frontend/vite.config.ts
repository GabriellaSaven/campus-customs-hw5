import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dashboard runs on http://localhost:5173 and calls the FastAPI backend on :8000.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});

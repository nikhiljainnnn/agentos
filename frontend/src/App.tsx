import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useStore } from "./lib/store";
import { ChatPage } from "./pages/ChatPage";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useStore((s) => s.token);
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <ChatPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <PrivateRoute>
              <DashboardPage />
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

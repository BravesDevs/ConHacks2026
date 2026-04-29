import { createBrowserRouter, Navigate } from "react-router";
import LoginPage from "./pages/LoginPage";
import MainApp from "./pages/MainApp";
import SettingsPage from "./pages/SettingsPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import NotFound from "./pages/NotFound";
import { useAuth } from "./context/AuthContext";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    path: "/login",
    Component: () => <GuestRoute><LoginPage /></GuestRoute>,
  },
  {
    path: "/",
    Component: () => <ProtectedRoute><MainApp /></ProtectedRoute>,
  },
  {
    path: "/settings",
    Component: () => <ProtectedRoute><SettingsPage /></ProtectedRoute>,
  },
  {
    path: "/reset-password",
    Component: ResetPasswordPage,
  },
  {
    path: "*",
    Component: NotFound,
  },
]);

import { createBrowserRouter } from "react-router";
import MainApp from "./pages/MainApp";
import SettingsPage from "./pages/SettingsPage";
import NotFound from "./pages/NotFound";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: MainApp,
  },
  {
    path: "/settings",
    Component: SettingsPage,
  },
  {
    path: "*",
    Component: NotFound,
  },
]);


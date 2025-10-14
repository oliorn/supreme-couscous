import { useState } from "react";
import Sidebar from "./components/Sidebar.js";
import Home from "./pages/Home.js";
import TestPage from "./pages/Test.js";
import CompaniesPage from "./pages/Companies.js";
import HistoryPage from "./pages/History.js";
import SettingsPage from "./pages/Settings.js";
import styles from "./App.module.css";

export default function App() {
  const [route, setRoute] = useState("home");

  return (
    <div className={styles.app}>
      <Sidebar route={route} onNavigate={setRoute} />
      <main className={styles.main}>
        {route === "home" && <Home />}
        {route === "test" && <TestPage />}
        {route === "companies" && <CompaniesPage />}
        {route === "history" && <HistoryPage />}
        {route === "settings" && <SettingsPage />}
      </main>
    </div>
  );
}

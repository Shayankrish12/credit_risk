import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/lib/auth-context";
import ProtectedRoute from "@/components/ProtectedRoute";
import { Toaster } from "@/components/ui/sonner";

import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import Dashboard from "@/pages/Dashboard";
import Borrowers from "@/pages/Borrowers";
import BorrowerDetail from "@/pages/BorrowerDetail";
import Upload from "@/pages/Upload";
import Analytics from "@/pages/Analytics";
import Alerts from "@/pages/Alerts";
import Copilot from "@/pages/Copilot";
import Reports from "@/pages/Reports";
import Settings from "@/pages/Settings";
import Recovery from "@/pages/Recovery";
import RecoveryDetail from "@/pages/RecoveryDetail";
import AuditLog from "@/pages/AuditLog";

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />

            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/borrowers" element={<ProtectedRoute><Borrowers /></ProtectedRoute>} />
            <Route path="/borrowers/:id" element={<ProtectedRoute><BorrowerDetail /></ProtectedRoute>} />
            <Route path="/upload" element={<ProtectedRoute><Upload /></ProtectedRoute>} />
            <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
            <Route path="/alerts" element={<ProtectedRoute><Alerts /></ProtectedRoute>} />
            <Route path="/copilot" element={<ProtectedRoute><Copilot /></ProtectedRoute>} />
            <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
            <Route path="/recovery" element={<ProtectedRoute><Recovery /></ProtectedRoute>} />
            <Route path="/recovery/:id" element={<ProtectedRoute><RecoveryDetail /></ProtectedRoute>} />
            <Route path="/audit" element={<ProtectedRoute roles={["admin"]}><AuditLog /></ProtectedRoute>} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </div>
  );
}

export default App;

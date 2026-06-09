import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import AppLayout from "@/components/AppLayout";

export default function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-sm uppercase tracking-[0.2em] text-gray-500">Loading...</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) {
    return (
      <AppLayout>
        <div className="p-8 max-w-md">
          <div className="border border-red-200 bg-red-50 p-4 rounded-sm">
            <div className="font-semibold text-red-800">Access denied</div>
            <div className="text-sm text-red-700 mt-1">Your role does not have access to this page.</div>
          </div>
        </div>
      </AppLayout>
    );
  }
  return <AppLayout>{children}</AppLayout>;
}

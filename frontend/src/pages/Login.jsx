import { useState } from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import { toast } from "sonner";
import { Warning } from "@phosphor-icons/react";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const [email, setEmail] = useState("admin@msme.com");
  const [password, setPassword] = useState("admin123");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back");
      navigate(location.state?.from || "/dashboard", { replace: true });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2" data-testid="login-page">
      <div className="hidden lg:block bg-[#0A0A0A] text-white p-12 relative overflow-hidden">
        <div className="absolute inset-0 grid-bg opacity-40"></div>
        <div className="relative z-10">
          <Link to="/" className="flex items-center gap-2.5 mb-12" data-testid="login-logo">
            <div className="w-8 h-8 bg-[#002FA7] flex items-center justify-center">
              <Warning weight="bold" size={18} />
            </div>
            <div>
              <div className="font-heading font-bold text-base tracking-tight">CREDIT.RISK</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-white/60">Early Warning System</div>
            </div>
          </Link>
          <div className="max-w-md mt-32">
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#002FA7] mb-4 font-semibold">CONTROL ROOM</div>
            <h2 className="font-heading font-bold text-4xl tracking-tight leading-tight mb-4">
              Detect distress before<br />it becomes default.
            </h2>
            <p className="text-white/70 text-sm leading-relaxed">
              Sign in to your portfolio of MSME borrowers, run the risk engine, and generate credit monitoring notes — all in one place.
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-sm">
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 mb-2 font-semibold">Sign in</div>
          <h1 className="font-heading font-bold text-3xl tracking-tight mb-8">Welcome back.</h1>

          <form onSubmit={onSubmit} className="space-y-5" data-testid="login-form">
            <div>
              <label className="text-xs uppercase tracking-wider font-medium text-gray-700">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="login-email-input"
                className="mt-1 w-full border border-gray-300 px-3 py-2.5 text-sm focus:border-[#002FA7] focus:outline-none focus:ring-2 focus:ring-[#002FA7]/20 rounded-sm"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider font-medium text-gray-700">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                data-testid="login-password-input"
                className="mt-1 w-full border border-gray-300 px-3 py-2.5 text-sm focus:border-[#002FA7] focus:outline-none focus:ring-2 focus:ring-[#002FA7]/20 rounded-sm"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              data-testid="login-submit-btn"
              className="w-full bg-[#0A0A0A] text-white py-2.5 text-sm font-semibold hover:bg-[#002FA7] transition-colors disabled:opacity-50"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <div className="mt-6 text-sm text-gray-600">
            Don't have an account?{" "}
            <Link to="/signup" data-testid="signup-link" className="text-[#002FA7] font-medium hover:underline">
              Create one
            </Link>
          </div>

          <div className="mt-8 p-3 bg-[#F9FAFB] border border-gray-200 rounded-sm">
            <div className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Demo Credentials</div>
            <div className="text-xs font-mono text-gray-700">admin@msme.com / admin123</div>
          </div>
        </div>
      </div>
    </div>
  );
}

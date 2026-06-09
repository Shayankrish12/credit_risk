import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import { toast } from "sonner";
import { Warning } from "@phosphor-icons/react";

export default function Signup() {
  const navigate = useNavigate();
  const { signup } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "analyst" });
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await signup(form);
      toast.success("Account created");
      navigate("/dashboard");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2" data-testid="signup-page">
      <div className="hidden lg:block bg-[#0A0A0A] text-white p-12 relative overflow-hidden">
        <div className="absolute inset-0 grid-bg opacity-40"></div>
        <div className="relative z-10">
          <Link to="/" className="flex items-center gap-2.5 mb-12">
            <div className="w-8 h-8 bg-[#002FA7] flex items-center justify-center">
              <Warning weight="bold" size={18} />
            </div>
            <div>
              <div className="font-heading font-bold text-base tracking-tight">CREDIT.RISK</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-white/60">Early Warning System</div>
            </div>
          </Link>
          <div className="max-w-md mt-32">
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#002FA7] mb-4 font-semibold">JOIN</div>
            <h2 className="font-heading font-bold text-4xl tracking-tight leading-tight mb-4">
              Equip your team<br />with foresight.
            </h2>
            <p className="text-white/70 text-sm leading-relaxed">
              Add yourself as Admin, Analyst, or Relationship Manager and start monitoring your MSME portfolio in minutes.
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-sm">
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 mb-2 font-semibold">Sign up</div>
          <h1 className="font-heading font-bold text-3xl tracking-tight mb-8">Create account.</h1>

          <form onSubmit={onSubmit} className="space-y-4" data-testid="signup-form">
            <div>
              <label className="text-xs uppercase tracking-wider font-medium text-gray-700">Full Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
                data-testid="signup-name-input"
                className="mt-1 w-full border border-gray-300 px-3 py-2.5 text-sm focus:border-[#002FA7] focus:outline-none focus:ring-2 focus:ring-[#002FA7]/20 rounded-sm"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider font-medium text-gray-700">Email</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
                data-testid="signup-email-input"
                className="mt-1 w-full border border-gray-300 px-3 py-2.5 text-sm focus:border-[#002FA7] focus:outline-none focus:ring-2 focus:ring-[#002FA7]/20 rounded-sm"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider font-medium text-gray-700">Password</label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required
                minLength={6}
                data-testid="signup-password-input"
                className="mt-1 w-full border border-gray-300 px-3 py-2.5 text-sm focus:border-[#002FA7] focus:outline-none focus:ring-2 focus:ring-[#002FA7]/20 rounded-sm"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider font-medium text-gray-700">Role</label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                data-testid="signup-role-select"
                className="mt-1 w-full border border-gray-300 px-3 py-2.5 text-sm focus:border-[#002FA7] focus:outline-none rounded-sm bg-white"
              >
                <option value="analyst">Credit Analyst</option>
                <option value="rm">Relationship Manager</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={loading}
              data-testid="signup-submit-btn"
              className="w-full bg-[#0A0A0A] text-white py-2.5 text-sm font-semibold hover:bg-[#002FA7] transition-colors disabled:opacity-50"
            >
              {loading ? "Creating..." : "Create account"}
            </button>
          </form>

          <div className="mt-6 text-sm text-gray-600">
            Already have one?{" "}
            <Link to="/login" data-testid="login-link" className="text-[#002FA7] font-medium hover:underline">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

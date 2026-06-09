import { Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Toaster } from "@/components/ui/sonner";
import NotificationBell from "@/components/NotificationBell";
import { ChartBar, House, Users, UploadSimple, Bell, ChatCircle, FileText, Gear, SignOut, Warning, Lifebuoy, ClipboardText, List, X } from "@phosphor-icons/react";

const baseNav = [
  { to: "/dashboard", label: "Dashboard", icon: House, testid: "nav-dashboard" },
  { to: "/borrowers", label: "Borrowers", icon: Users, testid: "nav-borrowers" },
  { to: "/upload", label: "Upload Data", icon: UploadSimple, testid: "nav-upload" },
  { to: "/recovery", label: "Recovery", icon: Lifebuoy, testid: "nav-recovery" },
  { to: "/analytics", label: "Analytics", icon: ChartBar, testid: "nav-analytics" },
  { to: "/alerts", label: "Alerts", icon: Bell, testid: "nav-alerts" },
  { to: "/copilot", label: "AI Copilot", icon: ChatCircle, testid: "nav-copilot" },
  { to: "/reports", label: "Reports", icon: FileText, testid: "nav-reports" },
];

const adminNav = [
  { to: "/audit", label: "Audit Log", icon: ClipboardText, testid: "nav-audit", role: "admin" },
];

const bottomNav = [
  { to: "/settings", label: "Settings", icon: Gear, testid: "nav-settings" },
];

export default function AppLayout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [alertCount, setAlertCount] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = [...baseNav, ...adminNav.filter(n => n.role === user?.role), ...bottomNav];

  useEffect(() => {
    api.get("/alerts?unread_only=true").then((r) => setAlertCount(r.data.length)).catch(() => {});
    setMobileOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-white" data-testid="app-layout">
      {/* Mobile top bar */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-30 bg-[#0A0A0A] text-white h-14 flex items-center justify-between px-4 border-b border-white/10">
        <button onClick={() => setMobileOpen(!mobileOpen)} data-testid="mobile-menu-btn" className="p-2 hover:bg-white/10 rounded-sm">
          {mobileOpen ? <X size={20} weight="bold"/> : <List size={20} weight="bold"/>}
        </button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-[#002FA7] flex items-center justify-center">
            <Warning weight="bold" size={14} />
          </div>
          <div className="font-heading font-bold text-sm tracking-tight">CREDIT.RISK</div>
        </div>
        <div className="text-white"><NotificationBellDark /></div>
      </div>

      {/* Sidebar */}
      <aside className={`${mobileOpen ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0 fixed lg:sticky top-0 left-0 z-40 w-64 h-screen bg-[#0A0A0A] text-white flex flex-col border-r border-gray-200 transition-transform lg:transition-none`} data-testid="sidebar">
        <div className="p-6 border-b border-white/10">
          <Link to="/dashboard" className="flex items-center gap-2 group" data-testid="logo-link">
            <div className="w-8 h-8 bg-[#002FA7] flex items-center justify-center">
              <Warning weight="bold" size={18} />
            </div>
            <div>
              <div className="font-heading font-bold text-base tracking-tight">CREDIT.RISK</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-white/60">Early Warning</div>
            </div>
          </Link>
        </div>

        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                data-testid={item.testid}
                end={item.to === "/dashboard"}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 text-sm transition-colors ${
                    isActive
                      ? "bg-[#002FA7] text-white"
                      : "text-white/70 hover:bg-white/5 hover:text-white"
                  }`
                }
              >
                <Icon size={18} weight={location.pathname.startsWith(item.to) && item.to !== "/dashboard" ? "bold" : "regular"} />
                <span className="flex-1">{item.label}</span>
                {item.to === "/alerts" && alertCount > 0 && (
                  <span className="bg-[#E53E3E] text-white text-[10px] font-bold px-1.5 py-0.5 min-w-[20px] text-center" data-testid="alert-badge">
                    {alertCount}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

        <div className="p-3 border-t border-white/10">
          <div className="px-3 py-2 mb-2">
            <div className="text-xs text-white/60 uppercase tracking-wider">Signed in</div>
            <div className="text-sm font-medium truncate" data-testid="user-name">{user?.name}</div>
            <div className="text-xs text-white/60 uppercase">{user?.role}</div>
          </div>
          <button
            onClick={handleLogout}
            data-testid="logout-btn"
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-white/70 hover:bg-white/5 hover:text-white transition-colors"
          >
            <SignOut size={16} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && <div className="lg:hidden fixed inset-0 bg-black/50 z-30" onClick={() => setMobileOpen(false)}></div>}

      {/* Main content */}
      <main className="flex-1 overflow-auto pt-14 lg:pt-0" data-testid="main-content">
        {children}
      </main>
      <Toaster />
    </div>
  );
}

// Small wrapper to render bell with white-friendly background on mobile bar
function NotificationBellDark() {
  return <div className="text-white"><NotificationBell /></div>;
}

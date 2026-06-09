import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { useAuth } from "@/lib/auth-context";

export default function Settings() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);

  useEffect(() => {
    if (user?.role === "admin") {
      api.get("/auth/users").then(r => setUsers(r.data)).catch(() => {});
    }
  }, [user]);

  return (
    <div data-testid="settings-page">
      <PageHeader overline="ACCOUNT" title="Settings" subtitle="Profile, role, and team management." />
      <div className="p-8 space-y-6 max-w-3xl">
        <div className="border border-gray-200 bg-white p-6" data-testid="profile-card">
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold mb-1">Profile</div>
          <h2 className="font-heading font-bold text-xl tracking-tight mb-4">{user?.name}</h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between border-b border-gray-100 pb-2"><dt className="text-gray-500 uppercase text-xs tracking-wider">Email</dt><dd className="font-mono">{user?.email}</dd></div>
            <div className="flex justify-between border-b border-gray-100 pb-2"><dt className="text-gray-500 uppercase text-xs tracking-wider">Role</dt><dd className="font-semibold uppercase">{user?.role}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500 uppercase text-xs tracking-wider">User ID</dt><dd className="font-mono text-xs">{user?.id}</dd></div>
          </dl>
        </div>

        {user?.role === "admin" && (
          <div className="border border-gray-200 bg-white" data-testid="users-card">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Team</div>
              <div className="font-heading font-bold text-base tracking-tight">All Users</div>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-[#F9FAFB] border-b border-gray-200">
                <tr className="text-[10px] uppercase tracking-wider text-gray-600">
                  <th className="px-4 py-2 text-left">Name</th>
                  <th className="px-4 py-2 text-left">Email</th>
                  <th className="px-4 py-2 text-left">Role</th>
                  <th className="px-4 py-2 text-left">Joined</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map(u => (
                  <tr key={u.id}>
                    <td className="px-4 py-2.5 font-medium">{u.name}</td>
                    <td className="px-4 py-2.5 font-mono text-xs">{u.email}</td>
                    <td className="px-4 py-2.5 uppercase text-xs tracking-wider font-semibold">{u.role}</td>
                    <td className="px-4 py-2.5 font-mono text-xs">{u.created_at?.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="border border-gray-200 bg-[#F9FAFB] p-5 text-xs text-gray-700 rounded-sm">
          <div className="font-semibold mb-1 uppercase tracking-wider text-[10px] text-gray-500">Role Permissions</div>
          <ul className="space-y-1 mt-2 list-disc list-inside">
            <li><b>Admin</b> — full access including user list, delete borrower</li>
            <li><b>Credit Analyst</b> — create/update borrowers, upload, generate reports, chat</li>
            <li><b>Relationship Manager</b> — view-only access to borrowers, signals, alerts</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AdminDocumentItem,
  AdminUser,
  User,
  adminApproveUser,
  adminDeleteUser,
  adminListDocuments,
  adminListUsers,
  adminSetUserRole,
  deleteDocument,
  fetchMe,
  getToken,
} from "@/lib/api";

const ROLES = ["student", "faculty", "admin"];

function formatDate(iso: string | null) {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString();
}

export default function AdminPage() {
  const router = useRouter();
  const [me, setMe] = useState<User | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [documents, setDocuments] = useState<AdminDocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function loadAll() {
    const [meResult, userList, docList] = await Promise.all([
      fetchMe(),
      adminListUsers(),
      adminListDocuments(),
    ]);
    setMe(meResult);
    setUsers(userList);
    setDocuments(docList);
  }

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const meResult = await fetchMe();
        if (meResult.role !== "admin") {
          // Defense in depth only - the backend independently 403s every
          // /admin/* route for non-admin accounts regardless of this check.
          router.replace("/chat");
          return;
        }
        await loadAll();
      } catch (err: any) {
        setError(err.message || "Failed to load admin data");
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleApprove(userId: string) {
    setBusyId(userId);
    setError(null);
    try {
      const updated = await adminApproveUser(userId);
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)));
    } catch (err: any) {
      setError(err.message || "Failed to approve user");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRoleChange(userId: string, role: string) {
    setBusyId(userId);
    setError(null);
    try {
      const updated = await adminSetUserRole(userId, role);
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)));
    } catch (err: any) {
      setError(err.message || "Failed to change role");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDeleteUser(userId: string, email: string) {
    if (!window.confirm(`Delete ${email}? This also deletes their conversations and uploads.`)) {
      return;
    }
    setBusyId(userId);
    setError(null);
    try {
      await adminDeleteUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err: any) {
      setError(err.message || "Failed to delete user");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDeleteDocument(docId: string, filename: string) {
    if (!window.confirm(`Delete "${filename}" from the knowledge base?`)) return;
    setBusyId(docId);
    setError(null);
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err: any) {
      setError(err.message || "Failed to delete document");
    } finally {
      setBusyId(null);
    }
  }

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center text-slate-400 text-sm">
        Loading admin panel...
      </div>
    );
  }

  const pendingUsers = users.filter((u) => !u.is_approved);
  const approvedUsers = users.filter((u) => u.is_approved);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="border-b border-slate-200 bg-white px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">Admin Panel</h1>
          <p className="text-xs text-slate-500">
            SECE AI &middot; signed in as {me?.email}
          </p>
        </div>
        <button
          onClick={() => router.push("/chat")}
          className="text-sm font-medium text-brand-600 hover:text-brand-700"
        >
          &larr; Back to chat
        </button>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-10">
        {error && (
          <p className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        {pendingUsers.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-3">
              Pending approval ({pendingUsers.length})
            </h2>
            <div className="bg-white rounded-xl border border-amber-200 divide-y divide-slate-100 overflow-hidden">
              {pendingUsers.map((u) => (
                <div
                  key={u.id}
                  className="flex items-center justify-between px-4 py-3 text-sm"
                >
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900 truncate">
                      {u.full_name || u.email}
                    </p>
                    <p className="text-xs text-slate-500 truncate">
                      {u.email} &middot; registered {formatDate(u.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleApprove(u.id)}
                      disabled={busyId === u.id}
                      className="rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-xs font-medium px-3 py-1.5 transition"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleDeleteUser(u.id, u.email)}
                      disabled={busyId === u.id}
                      className="rounded-lg border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50 text-xs font-medium px-3 py-1.5 transition"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section>
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-3">
            All users &amp; activity ({approvedUsers.length})
          </h2>
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">User</th>
                  <th className="text-left px-4 py-2 font-medium">Role</th>
                  <th className="text-right px-4 py-2 font-medium">Chats</th>
                  <th className="text-right px-4 py-2 font-medium">Messages</th>
                  <th className="text-left px-4 py-2 font-medium">Last active</th>
                  <th className="text-right px-4 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {approvedUsers.map((u) => (
                  <tr key={u.id}>
                    <td className="px-4 py-2.5 min-w-0">
                      <p className="font-medium text-slate-900 truncate">
                        {u.full_name || u.email}
                      </p>
                      <p className="text-xs text-slate-500 truncate">{u.email}</p>
                    </td>
                    <td className="px-4 py-2.5">
                      <select
                        value={u.role}
                        disabled={busyId === u.id || u.id === me?.id}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700 disabled:opacity-50"
                        title={
                          u.id === me?.id
                            ? "You can't change your own role"
                            : undefined
                        }
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-600">
                      {u.conversation_count}
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-600">
                      {u.message_count}
                    </td>
                    <td className="px-4 py-2.5 text-slate-600">
                      {formatDate(u.last_active)}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {u.id !== me?.id && (
                        <button
                          onClick={() => handleDeleteUser(u.id, u.email)}
                          disabled={busyId === u.id}
                          className="text-xs font-medium text-red-600 hover:text-red-700 disabled:opacity-50"
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-3">
            Knowledge base ({documents.length})
          </h2>
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">File</th>
                  <th className="text-left px-4 py-2 font-medium">Uploaded by</th>
                  <th className="text-left px-4 py-2 font-medium">Visibility</th>
                  <th className="text-left px-4 py-2 font-medium">Status</th>
                  <th className="text-right px-4 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-4 text-center text-slate-400">
                      No documents uploaded yet.
                    </td>
                  </tr>
                )}
                {documents.map((d) => (
                  <tr key={d.id}>
                    <td className="px-4 py-2.5 truncate max-w-xs">{d.filename}</td>
                    <td className="px-4 py-2.5 text-slate-600">{d.owner_email}</td>
                    <td className="px-4 py-2.5">
                      {d.is_shared ? (
                        <span className="rounded-full bg-brand-50 text-brand-700 px-2 py-0.5 text-xs font-medium">
                          Shared
                        </span>
                      ) : (
                        <span className="rounded-full bg-slate-100 text-slate-600 px-2 py-0.5 text-xs font-medium">
                          Private
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          d.status === "ready"
                            ? "bg-green-100 text-green-700"
                            : d.status === "error"
                            ? "bg-red-100 text-red-700"
                            : "bg-amber-100 text-amber-700"
                        }`}
                      >
                        {d.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <button
                        onClick={() => handleDeleteDocument(d.id, d.filename)}
                        disabled={busyId === d.id}
                        className="text-xs font-medium text-red-600 hover:text-red-700 disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}

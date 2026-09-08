"use client";

import { Conversation, DocumentItem, User, clearToken } from "@/lib/api";
import FileUpload from "./FileUpload";
import { useRouter } from "next/navigation";

export default function Sidebar({
  user,
  conversations,
  activeConversationId,
  documents,
  onSelectConversation,
  onNewConversation,
  onDocumentUploaded,
}: {
  user: User | null;
  conversations: Conversation[];
  activeConversationId: string | null;
  documents: DocumentItem[];
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDocumentUploaded: (doc: DocumentItem) => void;
}) {
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <aside className="w-72 shrink-0 border-r border-slate-200 bg-white flex flex-col h-screen">
      <div className="p-4 border-b border-slate-200 flex items-center gap-2">
        <div className="h-8 w-8 rounded-xl bg-brand-600 text-white flex items-center justify-center text-sm font-semibold">
          S
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight">SECE AI</p>
          <p className="text-[11px] text-slate-400 leading-tight">
            Sri Eshwar College of Engineering
          </p>
        </div>
      </div>

      <div className="p-3">
        <button
          onClick={onNewConversation}
          className="w-full rounded-lg border border-slate-300 hover:bg-slate-50 text-sm font-medium py-2 transition"
        >
          + New chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 space-y-1">
        {conversations.map((c) => (
          <button
            key={c.id}
            onClick={() => onSelectConversation(c.id)}
            className={`w-full text-left truncate rounded-lg px-3 py-2 text-sm transition ${
              c.id === activeConversationId
                ? "bg-brand-50 text-brand-700 font-medium"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            {c.title || "New conversation"}
          </button>
        ))}
        {conversations.length === 0 && (
          <p className="text-xs text-slate-400 px-3">
            Your conversations will appear here.
          </p>
        )}
      </div>

      <FileUpload documents={documents} onUploaded={onDocumentUploaded} />

      <div className="p-3 border-t border-slate-200 flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">
            {user?.full_name || user?.email}
          </p>
          <p className="text-[11px] text-slate-400 capitalize">{user?.role}</p>
        </div>
        <button
          onClick={handleLogout}
          className="text-xs font-medium text-slate-500 hover:text-slate-700"
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}

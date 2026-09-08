"use client";

import { useRef, useState } from "react";
import { DocumentItem, uploadDocument } from "@/lib/api";

export default function FileUpload({
  documents,
  onUploaded,
}: {
  documents: DocumentItem[];
  onUploaded: (doc: DocumentItem) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shared, setShared] = useState(false);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
        const doc = await uploadDocument(file, shared);
        onUploaded(doc);
      }
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="border-t border-slate-200 p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
          Knowledge base
        </span>
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="text-xs font-medium text-brand-600 hover:text-brand-700 disabled:opacity-50"
        >
          {uploading ? "Uploading..." : "+ Upload"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md,.csv"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      <label className="flex items-center gap-1.5 mb-2 text-xs text-slate-500">
        <input
          type="checkbox"
          checked={shared}
          onChange={(e) => setShared(e.target.checked)}
          className="rounded border-slate-300"
        />
        Add to shared knowledge base (visible to everyone, faculty/admin only)
      </label>

      {error && <p className="text-xs text-red-600 mb-2">{error}</p>}

      <ul className="space-y-1 max-h-40 overflow-y-auto">
        {documents.length === 0 && (
          <li className="text-xs text-slate-400">
            No documents yet. Upload a syllabus, circular, or policy PDF.
          </li>
        )}
        {documents.map((doc) => (
          <li
            key={doc.id}
            className="text-xs text-slate-600 flex items-center justify-between gap-2"
            title={doc.error_message || undefined}
          >
            <span className="truncate">
              {doc.filename}
              {doc.is_shared && " 🌐"}
            </span>
            <span
              className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                doc.status === "ready"
                  ? "bg-green-100 text-green-700"
                  : doc.status === "error"
                  ? "bg-red-100 text-red-700"
                  : "bg-amber-100 text-amber-700"
              }`}
            >
              {doc.status}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

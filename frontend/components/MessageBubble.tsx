"use client";

import ReactMarkdown from "react-markdown";

export default function MessageBubble({
  role,
  content,
  agentName,
}: {
  role: "user" | "assistant" | "tool";
  content: string;
  agentName?: string | null;
}) {
  const isUser = role === "user";
  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      {!isUser && agentName && (
        <span className="mb-1 ml-1 text-[10px] font-semibold uppercase tracking-wide text-brand-500">
          {agentName}
        </span>
      )}
      <div
        className={`max-w-2xl rounded-2xl px-4 py-2.5 text-sm leading-relaxed prose-chat ${
          isUser
            ? "bg-brand-600 text-white rounded-br-sm"
            : "bg-white border border-slate-200 text-slate-800 rounded-bl-sm"
        }`}
      >
        {isUser ? (
          <p>{content}</p>
        ) : (
          <ReactMarkdown>{content || " "}</ReactMarkdown>
        )}
      </div>
    </div>
  );
}

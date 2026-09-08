"use client";

import { useEffect, useRef, useState } from "react";
import { AgentInfo, Message, streamChat } from "@/lib/api";
import MessageBubble from "./MessageBubble";

export default function ChatWindow({
  conversationId,
  initialMessages,
  agents,
  conversationAgent,
  onAgentChange,
  onConversationCreated,
}: {
  conversationId: string | null;
  initialMessages: Message[];
  agents: AgentInfo[];
  conversationAgent: string;
  onAgentChange: (key: string) => void;
  onConversationCreated: (id: string) => void;
}) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const isNewConversation = conversationId === null;

  useEffect(() => {
    setMessages(initialMessages);
  }, [conversationId, initialMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function agentName(key: string | null | undefined): string | null {
    if (!key) return null;
    return agents.find((a) => a.key === key)?.name || key;
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    setError(null);
    setInput("");
    setStreaming(true);

    const userMsg: Message = {
      id: `local-${Date.now()}`,
      role: "user",
      content: text,
      agent: null,
      created_at: new Date().toISOString(),
    };
    const assistantMsg: Message = {
      id: `local-assistant-${Date.now()}`,
      role: "assistant",
      content: "",
      agent: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    await streamChat(
      text,
      conversationId,
      conversationAgent,
      (token) => {
        setMessages((prev) => {
          const copy = [...prev];
          copy[copy.length - 1] = {
            ...copy[copy.length - 1],
            content: copy[copy.length - 1].content + token,
          };
          return copy;
        });
      },
      (agentKey) => {
        setMessages((prev) => {
          const copy = [...prev];
          copy[copy.length - 1] = {
            ...copy[copy.length - 1],
            agent: agentKey,
          };
          return copy;
        });
      },
      (newConversationId) => {
        setStreaming(false);
        if (!conversationId) onConversationCreated(newConversationId);
      },
      (message) => {
        setStreaming(false);
        setError(message);
      }
    );
  }

  return (
    <div className="flex flex-col h-screen flex-1">
      <div className="flex items-center gap-2 border-b border-slate-200 bg-white px-6 py-2.5 text-xs">
        <span className="font-medium text-slate-500">Agent:</span>
        {isNewConversation ? (
          <select
            value={conversationAgent}
            onChange={(e) => onAgentChange(e.target.value)}
            className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {agents.map((a) => (
              <option key={a.key} value={a.key}>
                {a.name}
              </option>
            ))}
          </select>
        ) : (
          <span className="rounded-md bg-brand-50 px-2 py-1 font-medium text-brand-700">
            {agentName(conversationAgent) || conversationAgent}
          </span>
        )}
        {isNewConversation && (
          <span className="text-slate-400">
            {agents.find((a) => a.key === conversationAgent)?.description}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center text-slate-400">
            <div className="h-14 w-14 rounded-2xl bg-brand-600 text-white flex items-center justify-center text-2xl font-semibold mb-4">
              S
            </div>
            <p className="text-base font-medium text-slate-600">
              Ask SECE AI anything
            </p>
            <p className="text-sm mt-1 max-w-sm">
              Questions about uploaded syllabi, circulars, and policies are
              answered from your documents. Research and drafting questions
              are routed to specialist agents automatically.
            </p>
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            role={m.role}
            content={m.content}
            agentName={agentName(m.agent)}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="px-6 pb-2">
          <p className="text-xs text-red-600">{error}</p>
        </div>
      )}

      <form
        onSubmit={handleSend}
        className="border-t border-slate-200 bg-white p-4"
      >
        <div className="flex items-end gap-2 max-w-3xl mx-auto">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend(e);
              }
            }}
            placeholder="Message SECE AI..."
            rows={1}
            className="flex-1 resize-none rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 max-h-40"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 transition"
          >
            {streaming ? "..." : "Send"}
          </button>
        </div>
      </form>
    </div>
  );
}

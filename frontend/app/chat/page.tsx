"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AgentInfo,
  Conversation,
  DocumentItem,
  Message,
  User,
  fetchMe,
  getConversation,
  getToken,
  listAgents,
  listConversations,
  listDocuments,
} from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null);
  const [conversationAgent, setConversationAgent] = useState("auto");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }

    (async () => {
      try {
        const [me, convos, docs, agentList] = await Promise.all([
          fetchMe(),
          listConversations(),
          listDocuments(),
          listAgents(),
        ]);
        setUser(me);
        setConversations(convos);
        setDocuments(docs);
        setAgents(agentList);
      } catch {
        router.replace("/login");
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadConversation = useCallback(async (id: string) => {
    setActiveConversationId(id);
    const detail = await getConversation(id);
    setMessages(detail.messages);
    setConversationAgent(detail.agent);
  }, []);

  function handleNewConversation() {
    setActiveConversationId(null);
    setMessages([]);
    setConversationAgent("auto");
  }

  async function handleConversationCreated(id: string) {
    setActiveConversationId(id);
    const convos = await listConversations();
    setConversations(convos);
  }

  function handleDocumentUploaded(doc: DocumentItem) {
    setDocuments((prev) => [doc, ...prev]);
  }

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center text-slate-400 text-sm">
        Loading SECE AI...
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      <Sidebar
        user={user}
        conversations={conversations}
        activeConversationId={activeConversationId}
        documents={documents}
        onSelectConversation={loadConversation}
        onNewConversation={handleNewConversation}
        onDocumentUploaded={handleDocumentUploaded}
      />
      <ChatWindow
        conversationId={activeConversationId}
        initialMessages={messages}
        agents={agents}
        conversationAgent={conversationAgent}
        onAgentChange={setConversationAgent}
        onConversationCreated={handleConversationCreated}
      />
    </div>
  );
}

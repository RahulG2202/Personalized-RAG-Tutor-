"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const CHAT_DB_NAME = "rag-tutor-ai-chat";
const CHAT_DB_VERSION = 1;
const CHAT_STORE_NAME = "conversations";
const CHAT_RECORD_ID = "single-chat";
const CHAT_EXPIRY_MS = 2 * 24 * 60 * 60 * 1000;

type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
  sources?: string[];
};

type StoredChat = {
  id: string;
  messages: ChatMessage[];
  updatedAt: number;
  expiresAt: number;
};

type TutorResponse = {
  answer: string;
  sources?: string[];
};

const starterMessage: ChatMessage = {
  id: "starter",
  role: "assistant",
  content: "What would you like to study today?",
};

function getSourcePreview(source: string) {
  const words = source.trim().split(/\s+/);

  if (words.length <= 15) {
    return source;
  }

  return `${words.slice(0, 15).join(" ")}...`;
}

function createChatExpiry() {
  return Date.now() + CHAT_EXPIRY_MS;
}

function openChatDatabase() {
  if (typeof window === "undefined" || !window.indexedDB) {
    return Promise.resolve(null);
  }

  return new Promise<IDBDatabase | null>((resolve, reject) => {
    const request = window.indexedDB.open(CHAT_DB_NAME, CHAT_DB_VERSION);

    request.onupgradeneeded = () => {
      const database = request.result;

      if (!database.objectStoreNames.contains(CHAT_STORE_NAME)) {
        database.createObjectStore(CHAT_STORE_NAME, { keyPath: "id" });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(request.error ?? new Error("Unable to open chat database"));
  });
}

function readRequest<T>(request: IDBRequest<T>) {
  return new Promise<T>((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(request.error ?? new Error("IndexedDB request failed"));
  });
}

function waitForTransaction(transaction: IDBTransaction) {
  return new Promise<void>((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () =>
      reject(transaction.error ?? new Error("IndexedDB transaction failed"));
    transaction.onabort = () =>
      reject(transaction.error ?? new Error("IndexedDB transaction aborted"));
  });
}

async function getStoredChat() {
  const database = await openChatDatabase();

  if (!database) {
    return undefined;
  }

  try {
    const transaction = database.transaction(CHAT_STORE_NAME, "readonly");
    const storedChat = await readRequest<StoredChat | undefined>(
      transaction.objectStore(CHAT_STORE_NAME).get(CHAT_RECORD_ID),
    );
    await waitForTransaction(transaction);
    return storedChat;
  } finally {
    database.close();
  }
}

async function saveStoredChat(messages: ChatMessage[]) {
  const database = await openChatDatabase();

  if (!database) {
    return;
  }

  try {
    const transaction = database.transaction(CHAT_STORE_NAME, "readwrite");

    transaction.objectStore(CHAT_STORE_NAME).put({
      id: CHAT_RECORD_ID,
      messages,
      updatedAt: Date.now(),
      expiresAt: createChatExpiry(),
    } satisfies StoredChat);

    await waitForTransaction(transaction);
  } finally {
    database.close();
  }
}

async function deleteStoredChat() {
  const database = await openChatDatabase();

  if (!database) {
    return;
  }

  try {
    const transaction = database.transaction(CHAT_STORE_NAME, "readwrite");
    transaction.objectStore(CHAT_STORE_NAME).delete(CHAT_RECORD_ID);
    await waitForTransaction(transaction);
  } finally {
    database.close();
  }
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([starterMessage]);
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [hasLoadedStoredChat, setHasLoadedStoredChat] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let isMounted = true;

    async function hydrateStoredChat() {
      try {
        const storedChat = await getStoredChat();

        if (!isMounted) {
          return;
        }

        if (!storedChat) {
          return;
        }

        if (storedChat.expiresAt <= Date.now()) {
          await deleteStoredChat();
          return;
        }

        if (storedChat.messages.length > 0) {
          setMessages(storedChat.messages);
        }
      } catch (error) {
        console.warn("Unable to restore chat from IndexedDB", error);
      } finally {
        if (isMounted) {
          setHasLoadedStoredChat(true);
        }
      }
    }

    hydrateStoredChat();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    const hasStudentMessage = messages.some(
      (message) => message.role === "user",
    );

    if (!hasLoadedStoredChat || !hasStudentMessage) {
      return;
    }

    saveStoredChat(messages).catch((error) => {
      console.warn("Unable to persist chat in IndexedDB", error);
    });
  }, [hasLoadedStoredChat, messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isAsking]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isAsking) {
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmedQuestion,
    };

    setMessages((currentMessages) => [...currentMessages, userMessage]);
    setQuestion("");
    setIsAsking(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/tutor/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: trimmedQuestion }),
      });

      if (!response.ok) {
        throw new Error(`Tutor request failed with status ${response.status}`);
      }

      const data = (await response.json()) as TutorResponse;

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.answer,
          sources: data.sources ?? [],
        },
      ]);
    } catch (error) {
      console.error(error);
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content:
            "I could not reach the tutor right now. Please check the training service and try again.",
        },
      ]);
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col bg-paper text-ink">
      <header className="sticky top-0 z-20 border-b-2 border-ink bg-chalk/95 px-5 py-4 backdrop-blur sm:px-8">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-normal text-graphite">
              RAG Tutor AI
            </p>
            <h1 className="text-2xl font-black uppercase leading-none sm:text-4xl">
              Chat with Tutor
            </h1>
          </div>
          <Link
            href="/"
            className="border-2 border-ink bg-lemon px-4 py-2 text-sm font-black uppercase shadow-[4px_4px_0_#171717] transition-transform hover:-translate-y-0.5"
          >
            Studio
          </Link>
        </div>
      </header>

      <section className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-5 pb-36 pt-6 sm:px-8">
        <div className="flex flex-1 flex-col gap-5">
          {messages.map((message) => {
            const isUser = message.role === "user";

            return (
              <article
                key={message.id}
                className={`flex ${isUser ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[min(760px,100%)] border-2 border-ink px-5 py-4 shadow-[5px_5px_0_#171717] ${
                    isUser
                      ? "bg-ink text-chalk"
                      : "bg-chalk text-ink"
                  }`}
                >
                  <p className="whitespace-pre-wrap text-base font-semibold leading-7">
                    {message.content}
                  </p>

                  {!isUser && message.sources && message.sources.length > 0 ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {message.sources.map((source) => (
                        <span
                          key={source}
                          title={source}
                          className="inline-block max-w-[min(22rem,100%)] overflow-hidden text-ellipsis whitespace-nowrap border-2 border-ink bg-aqua px-2.5 py-1 text-xs font-black uppercase text-ink"
                        >
                          {getSourcePreview(source)}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              </article>
            );
          })}

          {isAsking ? (
            <article className="flex justify-start">
              <div className="border-2 border-ink bg-chalk px-5 py-4 shadow-[5px_5px_0_#171717]">
                <div className="flex items-center gap-2" aria-label="Tutor is thinking">
                  <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-ink [animation-delay:-0.2s]" />
                  <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-ink [animation-delay:-0.1s]" />
                  <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-ink" />
                </div>
              </div>
            </article>
          ) : null}

          <div ref={bottomRef} />
        </div>
      </section>

      <div className="fixed inset-x-0 bottom-0 z-30 border-t-2 border-ink bg-paper/95 px-5 py-4 backdrop-blur sm:px-8">
        <form
          onSubmit={handleSubmit}
          className="mx-auto flex max-w-5xl items-end gap-3"
        >
          <label className="sr-only" htmlFor="student-question">
            Ask the tutor
          </label>
          <textarea
            id="student-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder="Ask a question from your study material"
            rows={1}
            className="max-h-40 min-h-14 flex-1 resize-none border-2 border-ink bg-chalk px-4 py-3 text-base font-semibold leading-7 shadow-[4px_4px_0_#171717] outline-none focus:ring-4 focus:ring-aqua"
            disabled={isAsking}
          />
          <button
            type="submit"
            disabled={isAsking || !question.trim()}
            className="min-h-14 border-2 border-ink bg-tomato px-5 text-sm font-black uppercase text-chalk shadow-[4px_4px_0_#171717] transition-transform hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isAsking ? "Wait" : "Send"}
          </button>
        </form>
      </div>
    </main>
  );
}

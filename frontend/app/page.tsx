"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { DefaultChatTransport } from "ai";
import { useChat } from "@ai-sdk/react";

type Language = "en" | "he" | "ru" | "ar";

type ToolCallTrace = {
  id?: string;
  name?: string;
  args?: string;
  state?: string;
};

type ToolPart = {
  toolCallId?: string;
  toolName?: string;
  name?: string;
  input?: unknown;
  args?: unknown;
  arguments?: unknown;
  state?: string;
  type?: string;
};

const RTL_LANGS = new Set(["he", "ar"]);
const TOOL_INPUT_KEYS = ["query", "name", "ingredient", "zip_code", "city", "med_id", "prescription_id"];

const UI_TEXT: Record<Language, Record<string, string>> = {
  en: {
    title: "Pharmacy AI Agent",
    assistant: "Assistant",
    user: "You",
    language: "Language",
    guest: "Guest",
    signedIn: "Signed in",
    login: "Log in",
    logout: "Log out",
    placeholder: "Ask about meds, stock, or prescriptions",
    send: "Send",
    thinking: "Thinking",
    usingTools: "Using tools",
    tools: "Tools",
    state: "State",
    error: "Request error",
    noTools: "No tool calls",
    welcome: "Hello",
    cta: "Ask a question in the chat.",
    empty: "Ask something",
  },
  he: {
    title: "סוכן בית מרקחת AI",
    assistant: "עוזר",
    user: "את/ה",
    language: "שפה",
    guest: "אורח",
    signedIn: "מחובר",
    login: "התחבר",
    logout: "התנתק",
    placeholder: "שאל/י על תרופות, מלאי או מרשמים",
    send: "שלח",
    thinking: "חושב",
    usingTools: "משתמש בכלים",
    tools: "כלים",
    state: "מצב",
    error: "שגיאת בקשה",
    noTools: "אין קריאות כלי",
    welcome: "היי.",
    cta: "תשאל משהו בצ'אט.",
    empty: "תשאל משהו",
  },
  ru: {
    title: "Фарм AI-ассистент",
    assistant: "Ассистент",
    user: "Вы",
    language: "Язык",
    guest: "Гость",
    signedIn: "Вход выполнен",
    login: "Войти",
    logout: "Выйти",
    placeholder: "Спросите о лекарствах, наличии или рецептах",
    send: "Отправить",
    thinking: "Думаю",
    usingTools: "Использую инструменты",
    tools: "Инструменты",
    state: "Статус",
    error: "Ошибка запроса",
    noTools: "Нет вызовов",
    welcome: "Привет.",
    cta: "Задайте вопрос в чате.",
    empty: "Спросите что-нибудь",
  },
  ar: {
    title: "وكيل صيدلية بالذكاء الاصطناعي",
    assistant: "المساعد",
    user: "أنت",
    language: "اللغة",
    guest: "ضيف",
    signedIn: "تم تسجيل الدخول",
    login: "تسجيل الدخول",
    logout: "تسجيل الخروج",
    placeholder: "اسأل عن الأدوية أو التوفر أو الوصفات",
    send: "إرسال",
    thinking: "يفكر",
    usingTools: "يستخدم الأدوات",
    tools: "الأدوات",
    state: "الحالة",
    error: "خطأ في الطلب",
    noTools: "لا توجد استدعاءات",
    welcome: "مرحبا.",
    cta: "اطرح سؤالا في الدردشة.",
    empty: "اسأل شيئا",
  },
};

const LANGUAGE_OPTIONS: { value: Language; label: string }[] = [
  { value: "en", label: "🇺🇸" },
  { value: "he", label: "🇮🇱" },
  { value: "ru", label: "🇷🇺" },
  { value: "ar", label: "🇸🇦" },
];


const filterToolInput = (input: unknown) => {
  if (!input || typeof input !== "object") return input;
  const filtered: Record<string, unknown> = {};
  for (const key of TOOL_INPUT_KEYS) {
    if (key in input) {
      filtered[key] = (input as Record<string, unknown>)[key];
    }
  }
  return Object.keys(filtered).length ? filtered : input;
};

export default function Home() {
  const [language, setLanguage] = useState<Language>("en");
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [authName, setAuthName] = useState<string | null>(null);
  const authTokenRef = useRef<string | null>(null);
  const languageRef = useRef<Language>("en");
  const [langOpen, setLangOpen] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);
  const langRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const storedLang = localStorage.getItem("uiLanguage") as Language | null;
    if (storedLang && UI_TEXT[storedLang]) {
      setLanguage(storedLang);
    }
    const token = localStorage.getItem("authToken");
    const name = localStorage.getItem("authName");
    if (token) setAuthToken(token);
    if (name) setAuthName(name);
  }, []);

  useEffect(() => {
    localStorage.setItem("uiLanguage", language);
  }, [language]);

  useEffect(() => {
    authTokenRef.current = authToken;
  }, [authToken]);

  useEffect(() => {
    languageRef.current = language;
  }, [language]);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (!langRef.current) return;
      if (langRef.current.contains(event.target as Node)) return;
      setLangOpen(false);
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setLangOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, []);

  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: "/api",
        prepareSendMessagesRequest: ({ body, id, messages, trigger, messageId }) => {
          const headers: Record<string, string> = {};
          const token = authTokenRef.current;
          const currentLanguage = languageRef.current;
          if (token) {
            headers["x-user-id"] = token;
          }
          return {
            body: {
              ...(body ?? {}),
              id,
              messages,
              trigger,
              messageId,
              language: currentLanguage,
              user_id: token ?? undefined,
            },
            headers,
          };
        },
      }),
    []
  );

  const { messages, sendMessage, status, error } = useChat({
    transport,
    messages: [],
  });

  const [input, setInput] = useState("");
  const isLoading = status !== "ready";
  const uiText = UI_TEXT[language] ?? UI_TEXT.en;

  const isToolPart = (part: unknown): part is ToolPart => {
    if (!part || typeof part !== "object") return false;
    const candidate = part as ToolPart;
    return (
      "toolCallId" in candidate ||
      "toolName" in candidate ||
      "name" in candidate ||
      "input" in candidate ||
      "args" in candidate ||
      "arguments" in candidate ||
      "state" in candidate ||
      "type" in candidate
    );
  };

  const toolCalls = useMemo(() => {
    const calls = new Map<string, ToolCallTrace>();
    const order: string[] = [];
    const seenSignatures = new Set<string>();

    for (const message of messages) {
      const parts = Array.isArray(message.parts) ? message.parts : [];
      for (const part of parts) {
        if (!isToolPart(part)) continue;
        const toolPart = part as ToolPart;
        const toolCallId = toolPart.toolCallId;
        if (!toolCallId) continue;

        const toolName = toolPart.toolName ??
          toolPart.name ??
          (typeof toolPart.type === "string" && toolPart.type.startsWith("tool-")
            ? toolPart.type.replace("tool-", "")
            : undefined);
        const rawInput = toolPart.input ?? toolPart.args ?? toolPart.arguments;
        const hasInput =
          rawInput !== undefined &&
          rawInput !== null &&
          (typeof rawInput !== "object" || Object.keys(rawInput).length > 0);

        if (!toolName || toolName === "tool-call" || !hasInput) continue;

        const args = JSON.stringify(filterToolInput(rawInput));
        const signature = `${toolName}:${args}`;
        if (seenSignatures.has(signature)) continue;
        seenSignatures.add(signature);

        const entry: ToolCallTrace = calls.get(signature) ?? { id: toolCallId };
        entry.name = toolName;
        entry.state = toolPart.state ?? "input-available";
        entry.args = args;

        if (!calls.has(signature)) {
          order.push(signature);
        }
        calls.set(signature, entry);
      }
    }

    return order.map((id) => calls.get(id)).filter(Boolean) as ToolCallTrace[];
  }, [messages]);

  const latestTool = useMemo(() => {
    let lastUserIndex = -1;
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "user") {
        lastUserIndex = i;
        break;
      }
    }

    let latest: ToolCallTrace | undefined;
    for (let i = messages.length - 1; i > lastUserIndex; i -= 1) {
      const parts = Array.isArray(messages[i].parts) ? messages[i].parts : [];
      for (let j = parts.length - 1; j >= 0; j -= 1) {
        const part = parts[j];
        if (!isToolPart(part)) continue;
        const toolPart = part as ToolPart;
        const toolName = toolPart.toolName ??
          toolPart.name ??
          (typeof toolPart.type === "string" && toolPart.type.startsWith("tool-")
            ? toolPart.type.replace("tool-", "")
            : undefined);
        const rawInput = toolPart.input ?? toolPart.args ?? toolPart.arguments;
        const hasInput =
          rawInput !== undefined &&
          rawInput !== null &&
          (typeof rawInput !== "object" || Object.keys(rawInput).length > 0);
        if (toolName && hasInput) {
          latest = { name: toolName };
          break;
        }
      }
      if (latest) break;
    }

    return latest;
  }, [messages]);
  const uiDirection = RTL_LANGS.has(language) ? "rtl" : "ltr";

  useEffect(() => {
    const behavior = status === "ready" ? "auto" : "smooth";
    endRef.current?.scrollIntoView({ behavior, block: "end" });
  }, [messages, status]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;

    await sendMessage({
      role: "user",
      parts: [{ type: "text", text: trimmed }],
    });
    setInput("");
  };

  const handleLogout = () => {
    localStorage.removeItem("authToken");
    localStorage.removeItem("authName");
    setAuthToken(null);
    setAuthName(null);
  };

  const showEmpty = messages.length === 0 && !isLoading;
  const welcomeText = authName ? `${uiText.welcome}, ${authName}` : uiText.welcome;
  const selectedLanguage = LANGUAGE_OPTIONS.find((option) => option.value === language);

  return (
    <main className="app-shell" dir={uiDirection}>
      <header className="app-header">
        <h1>{uiText.title}</h1>
        <div className="header-actions">
          <div className="language-pill" ref={langRef}>
            <button
              type="button"
              className="lang-trigger"
              onClick={() => setLangOpen((open) => !open)}
              aria-haspopup="listbox"
              aria-expanded={langOpen}
            >
              {selectedLanguage?.label ?? uiText.language}
            </button>
            {langOpen && (
              <div className="lang-menu" role="listbox" aria-label={uiText.language}>
                {LANGUAGE_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    role="option"
                    aria-selected={option.value === language}
                    className={`lang-option${option.value === language ? " active" : ""}`}
                    onClick={() => {
                      setLanguage(option.value);
                      setLangOpen(false);
                    }}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="auth-chip">
            {authToken ? (
              <>
                <span>{uiText.signedIn}{authName ? `: ${authName}` : ""}</span>
                <button type="button" onClick={handleLogout} className="ghost-button">
                  {uiText.logout}
                </button>
              </>
            ) : (
              <>
                <span>{uiText.guest}</span>
                <Link href="/login" className="ghost-button">
                  {uiText.login}
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <section className="chat-layout">
        <div className="chat-main">
          <div className={`message-list${showEmpty ? " empty" : ""}`}>
            {showEmpty && (
              <div className="empty-state">
                <h2>{welcomeText}</h2>
                <p>{uiText.cta}</p>
                <div className="empty-placeholder">{uiText.empty}</div>
              </div>
            )}
            {messages.map((message) => (
              <div key={message.id} className={`message ${message.role}`}>
                <strong>{message.role === "assistant" ? uiText.assistant : uiText.user}</strong>
                <div className="message-body">
                  {message.parts
                    .filter((part) => part.type === "text")
                    .map((part, index) => (
                      <span key={`${message.id}-text-${index}`}>{part.text}</span>
                    ))}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message assistant status">
                <strong>{uiText.assistant}</strong>
                <div className="thinking-row">
                  <span className="thinking-label">
                    {latestTool?.name ? uiText.usingTools : uiText.thinking}
                  </span>
                  {latestTool?.name && <span className="tool-pill">{latestTool.name}</span>}
                  <span className="dot-flash" aria-hidden="true">
                    <span />
                    <span />
                    <span />
                  </span>
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form onSubmit={handleSubmit} className="composer">
            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={uiText.placeholder}
              aria-label="Chat input"
            />
            <button type="submit" disabled={isLoading || !input.trim()}>
              {isLoading ? uiText.thinking : uiText.send}
            </button>
          </form>

          {error && (
            <div className="tool-call" role="alert">
              <strong>{uiText.error}</strong>
              <div>{error.message}</div>
            </div>
          )}
        </div>

        <aside className="tool-panel">
          <div className="tool-panel-header">
            <h3>{uiText.tools}</h3>
          </div>
          {toolCalls.map((call) => (
            <div key={call.id} className="tool-call">
              <strong>{call.name}</strong>
              {call.state && <div className="helper-text">{uiText.state}: {call.state}</div>}
              {call.args && <code>{call.args}</code>}
            </div>
          ))}
        </aside>
      </section>
    </main>
  );
}

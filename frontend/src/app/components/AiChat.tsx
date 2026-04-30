import { useState, useRef, useEffect } from 'react';
import { Send, Bot } from 'lucide-react';
import { Sheet, SheetContent } from './ui/sheet';
import { sendChatMessage } from '../api';
import type { ChatMessage } from '../types';

interface AiChatProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const INITIAL_MESSAGE: ChatMessage = {
  id: 'init',
  role: 'assistant',
  content: 'Hi, How can I help you today?',
  timestamp: new Date(),
};

function formatTime(date: Date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function LoadingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-0.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-[#f97316]/60 animate-bounce"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </div>
  );
}

export default function AiChat({ open, onOpenChange }: AiChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    if (open) {
      setTimeout(() => textareaRef.current?.focus(), 300);
    }
  }, [open]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const reply = await sendChatMessage(text);
      setMessages((prev) => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: reply,
        timestamp: new Date(),
      }]);
    } catch {
      setMessages((prev) => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Something went wrong. Please try again.',
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-[420px] flex-col gap-0 border-l border-white/[0.06] bg-[#060810] p-0 sm:max-w-[420px]"
      >
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-white/[0.06] px-5 py-4 pr-12">
          <div className="flex h-7 w-7 items-center justify-center border border-[#f97316]/40 bg-[#f97316]/10">
            <Bot className="h-3.5 w-3.5 text-[#f97316]" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="font-['Chakra_Petch'] text-xs font-semibold tracking-[0.12em] text-white">
              AI ASSISTANT
            </span>
            <span className="mt-0.5 font-['IBM_Plex_Mono'] text-[10px] text-[#f97316]/70">
              POWERED BY DigitalOcean Open AI
            </span>
          </div>
        </div>

        {/* Message thread */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-sm px-3 py-2 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-[#f97316]/10 border border-[#f97316]/20 text-white/90'
                    : 'bg-white/5 border border-white/10 text-white/80'
                }`}
              >
                {msg.content}
              </div>
              <span className="font-['IBM_Plex_Mono'] text-[10px] text-white/25 px-1">
                {formatTime(msg.timestamp)}
              </span>
            </div>
          ))}

          {loading && (
            <div className="flex flex-col items-start gap-1">
              <div className="bg-white/5 border border-white/10 rounded-sm px-3 py-2">
                <LoadingDots />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input row */}
        <div className="border-t border-white/[0.06] px-4 py-3">
          <div className="flex items-end gap-2 border border-white/10 bg-white/[0.03] rounded-sm px-3 py-2 focus-within:border-[#f97316]/30 transition-colors">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your infrastructure..."
              rows={1}
              className="flex-1 resize-none bg-transparent font-['IBM_Plex_Mono'] text-sm text-white/80 placeholder:text-white/25 focus:outline-none"
              style={{ maxHeight: '120px' }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="flex h-7 w-7 flex-shrink-0 items-center justify-center border border-[#f97316]/30 bg-[#f97316]/10 text-[#f97316] transition-colors hover:bg-[#f97316]/20 disabled:cursor-not-allowed disabled:opacity-30"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </div>
          <p className="mt-1.5 font-['IBM_Plex_Mono'] text-[10px] text-white/20 text-center">
            Enter to send · Shift+Enter for new line
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
}

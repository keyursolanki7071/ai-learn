import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { SendHorizonal } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (content: string) => void;
  isLoading?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, isLoading }) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  return (
    <div className="p-4 bg-gray-900 border-t border-gray-800/60">
      <div className="max-w-4xl mx-auto relative flex items-end gap-2 bg-gray-800 rounded-2xl border border-gray-700/50 p-2 shadow-sm focus-within:ring-2 focus-within:ring-blue-500/50 focus-within:border-blue-500/50 transition-all duration-200">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message AI..."
          className="flex-1 max-h-36 min-h-[44px] bg-transparent text-gray-100 placeholder-gray-400 resize-none outline-none py-3 px-4 rounded-xl text-sm md:text-base leading-relaxed"
          rows={1}
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className={`p-3 rounded-xl flex-shrink-0 transition-all duration-200 ${
            input.trim() && !isLoading
              ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
              : 'bg-gray-700/50 text-gray-500 cursor-not-allowed'
          }`}
        >
          <SendHorizonal size={20} />
        </button>
      </div>
      <div className="text-center mt-3">
        <span className="text-xs text-gray-500 font-medium tracking-wide">
          AI can make mistakes. Verify important information.
        </span>
      </div>
    </div>
  );
};

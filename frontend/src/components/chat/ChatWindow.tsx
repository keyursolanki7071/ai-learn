import React, { useState } from 'react';
import { Message } from '../../types/chat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';

export const ChatWindow: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = (content: string) => {
    // Add user message
    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: Date.now(),
    };
    
    setMessages((prev) => [...prev, newUserMessage]);
    setIsLoading(true);

    // Mock AI response
    setTimeout(() => {
      const newAiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: `This is a mock response to: "${content}". We will attach this to the real API later!`,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, newAiMessage]);
      setIsLoading(false);
    }, 1000);
  };

  return (
    <div className="flex flex-col h-screen max-h-screen bg-gray-900 text-gray-100 overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 bg-gray-900 border-b border-gray-800/60 p-4 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto flex items-center justify-center">
          <h1 className="text-xl font-semibold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
            AI Assistant
          </h1>
        </div>
      </header>

      {/* Main Chat Area */}
      <main className="flex-1 overflow-hidden flex justify-center">
        <div className="w-full max-w-4xl flex flex-col h-full">
          <MessageList messages={messages} />
        </div>
      </main>

      {/* Input Area */}
      <div className="flex-shrink-0 w-full">
        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
};

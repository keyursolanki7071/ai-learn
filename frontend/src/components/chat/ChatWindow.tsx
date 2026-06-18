import React, { useState } from 'react';
import { Message } from '../../types/chat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';

export const ChatWindow: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (content: string) => {
    // Add user message
    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: Date.now(),
    };
    
    setMessages((prev) => [...prev, newUserMessage]);
    setIsLoading(true);

    const aiMessageId = (Date.now() + 1).toString();
    const newAiMessage: Message = {
      id: aiMessageId,
      role: 'ai',
      content: '',
      timestamp: Date.now(),
    };
    
    setMessages((prev) => [...prev, newAiMessage]);

    try {
      const response = await fetch('http://localhost:8000/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: content }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported in this browser.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.replace('data: ', '').trim();
              if (dataStr) {
                try {
                  const data = JSON.parse(dataStr);
                  
                  if (data.chunk) {
                    setMessages((prev) => 
                      prev.map((msg) => 
                        msg.id === aiMessageId 
                          ? { ...msg, content: msg.content + data.chunk } 
                          : msg
                      )
                    );
                  }
                  
                  if (data.done) {
                    // Stream completed normally
                  }
                  
                  if (data.error) {
                    console.error('Error from server:', data.error);
                  }
                } catch (e) {
                  console.error('Error parsing SSE JSON:', e);
                }
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error fetching stream:', error);
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === aiMessageId 
            ? { ...msg, content: msg.content + "\n\n**Error:** Could not connect to the backend API." } 
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
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

import React from 'react';
import { Message } from '../../types/chat';
import { Bot, User } from 'lucide-react';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex w-full mb-6 ${
        isUser ? 'justify-end' : 'justify-start'
      }`}
    >
      <div
        className={`flex max-w-[80%] ${
          isUser ? 'flex-row-reverse' : 'flex-row'
        } items-end gap-3`}
      >
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isUser ? 'bg-blue-600' : 'bg-gray-700'
          }`}
        >
          {isUser ? (
            <User size={18} className="text-white" />
          ) : (
            <Bot size={18} className="text-white" />
          )}
        </div>
        
        <div
          className={`relative px-5 py-3.5 text-sm md:text-base shadow-sm rounded-2xl ${
            isUser
              ? 'bg-blue-600 text-white rounded-br-none'
              : 'bg-gray-800 text-gray-100 rounded-bl-none border border-gray-700/50'
          }`}
        >
          {message.content}
        </div>
      </div>
    </div>
  );
};

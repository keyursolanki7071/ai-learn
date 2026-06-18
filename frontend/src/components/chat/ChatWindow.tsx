import React, { useState } from 'react';
import { Message } from '../../types/chat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';

export const ChatWindow: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true); // Start loading while history fetches

  const [threadId] = useState(() => {
    const saved = localStorage.getItem('chat_thread_id');
    if (saved) return saved;
    const newId = Math.random().toString(36).substring(2, 15);
    localStorage.setItem('chat_thread_id', newId);
    return newId;
  });

  const [approvalRequest, setApprovalRequest] = useState<{toolName: string, toolArgs: any} | null>(null);
  const currentAiMessageId = React.useRef<string | null>(null);

  React.useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch(`http://localhost:8000/chat/history?thread_id=${threadId}`);
        const data = await response.json();
        
        if (data.messages && data.messages.length > 0) {
          // Normalize the messages to match our UI format
          const formattedHistory: Message[] = data.messages.map((msg: any) => ({
            id: msg.id,
            role: msg.role,
            content: msg.content,
            timestamp: Date.now() // Mock timestamp since backend doesn't store it
          }));
          setMessages(formattedHistory);
        }
      } catch (error) {
        console.error("Failed to fetch chat history:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchHistory();
  }, [threadId]);

  const processStream = async (response: Response, aiMessageId: string) => {
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
                
                if (data.approval_required) {
                  setApprovalRequest({
                    toolName: data.tool_name,
                    toolArgs: data.tool_args
                  });
                  return; // Pause the stream processing
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
    setIsLoading(false);
  };

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
    setApprovalRequest(null);

    const aiMessageId = (Date.now() + 1).toString();
    currentAiMessageId.current = aiMessageId;
    
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
        body: JSON.stringify({ message: content, thread_id: threadId }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await processStream(response, aiMessageId);
    } catch (error) {
      console.error('Error fetching stream:', error);
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === aiMessageId 
            ? { ...msg, content: msg.content + "\n\n**Error:** Could not connect to the backend API." } 
            : msg
        )
      );
      setIsLoading(false);
    }
  };

  const handleApproval = async (approved: boolean) => {
    if (!currentAiMessageId.current) return;
    
    setIsLoading(true);
    setApprovalRequest(null);
    
    // Add a quick feedback to the chat UI if denied
    if (!approved) {
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === currentAiMessageId.current 
            ? { ...msg, content: msg.content + "\n\n*[User Denied Action]*\n\n" } 
            : msg
        )
      );
    }

    try {
      const response = await fetch('http://localhost:8000/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: "", 
          thread_id: threadId,
          resume: true,
          approved
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await processStream(response, currentAiMessageId.current);
    } catch (error) {
      console.error('Error resuming stream:', error);
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
      <main className="flex-1 overflow-hidden flex justify-center relative">
        <div className="w-full max-w-4xl flex flex-col h-full">
          <MessageList messages={messages} />
        </div>
        
        {/* Approval Overlay */}
        {approvalRequest && (
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-gray-800 border border-blue-500 rounded-lg p-4 shadow-xl shadow-blue-500/20 max-w-md w-full z-20 animate-fade-in-up">
            <h3 className="text-blue-400 font-semibold mb-2 flex items-center">
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
              Action Approval Required
            </h3>
            <p className="text-gray-300 text-sm mb-4">
              The AI wants to run the <span className="font-mono text-blue-300">{approvalRequest.toolName}</span> tool.
              <br />
              <span className="text-gray-400 text-xs mt-1 block">Args: {JSON.stringify(approvalRequest.toolArgs)}</span>
            </p>
            <div className="flex gap-3 justify-end">
              <button 
                onClick={() => handleApproval(false)}
                className="px-4 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
              >
                Deny
              </button>
              <button 
                onClick={() => handleApproval(true)}
                className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded font-medium transition-colors shadow-lg shadow-blue-500/30"
              >
                Approve
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Input Area */}
      <div className="flex-shrink-0 w-full relative z-10">
        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading || !!approvalRequest} />
      </div>
    </div>
  );
};

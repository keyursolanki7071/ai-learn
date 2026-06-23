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
  const [feedback, setFeedback] = useState("");
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
    let aiMessageContent = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (!dataStr) continue;

            try {
              const data = JSON.parse(dataStr);
              if (data.chunk) {
                aiMessageContent += data.chunk;
                setMessages(prev => prev.map(msg => 
                  msg.id === aiMessageId ? { ...msg, content: aiMessageContent } : msg
                ));
              } else if (data.approval_required) {
                // The backend has paused execution to ask for approval
                setApprovalRequest({
                  toolName: data.tool_name,
                  toolArgs: data.tool_args
                });
                return; // Stop processing stream
              }
            } catch (e) {
              console.error("Error parsing JSON chunk:", e, dataStr);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return;

    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setIsLoading(true);

    const aiMessageId = (Date.now() + 1).toString();
    currentAiMessageId.current = aiMessageId;

    setMessages((prev) => [
      ...prev,
      {
        id: aiMessageId,
        role: 'ai',
        content: '', // Start empty
        timestamp: Date.now(),
      },
    ]);

    try {
      const response = await fetch('http://localhost:8000/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: content, thread_id: threadId }),
      });

      await processStream(response, aiMessageId);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => prev.map(msg => 
        msg.id === aiMessageId ? { ...msg, content: "Sorry, I encountered an error. Please try again." } : msg
      ));
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproval = async (approved: boolean) => {
    if (!currentAiMessageId.current || !approvalRequest) return;
    
    const aiMessageId = currentAiMessageId.current;
    
    // If denied, maybe show a system message
    if (!approved && !feedback) {
      setMessages(prev => prev.map(msg => 
        msg.id === aiMessageId ? { ...msg, content: msg.content + "\n\n*[User Denied Action]*" } : msg
      ));
    }

    setIsLoading(true);
    setApprovalRequest(null);
    const feedbackToSend = feedback;
    setFeedback(""); // Reset feedback

    try {
      const response = await fetch('http://localhost:8000/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // We set resume=True and send the approval status and optional feedback
        body: JSON.stringify({ 
          message: "", // No new message
          thread_id: threadId,
          resume: true,
          approved: approved,
          feedback: approved ? null : feedbackToSend
        }),
      });

      await processStream(response, aiMessageId);
    } catch (error) {
      console.error('Error resuming stream:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900 overflow-hidden font-sans">
      {/* Header Area */}
      <header className="flex-shrink-0 w-full flex justify-center border-b border-gray-800 bg-gray-900/50 backdrop-blur-md z-10 sticky top-0">
        <div className="w-full max-w-4xl py-4 px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-violet-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
            </div>
            <div>
              <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-violet-400">
                Antigravity AI
              </h1>
              <p className="text-xs text-gray-400 font-medium tracking-wider uppercase">Pair Programming Assistant</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <span className="text-sm text-gray-300 font-medium">System Online</span>
          </div>
        </div>
      </header>

      {/* Main Chat Area */}
      <main className="flex-1 overflow-hidden flex justify-center relative">
        <div className="w-full max-w-4xl flex flex-col h-full">
          <MessageList messages={messages} />
        </div>
        
        {/* Approval Overlay */}
        {approvalRequest && (
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-gray-800 border border-blue-500 rounded-lg p-5 shadow-2xl shadow-blue-500/20 max-w-md w-full z-20 animate-fade-in-up">
            <h3 className="text-blue-400 font-semibold mb-3 flex items-center text-lg">
              <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
              Action Approval Required
            </h3>
            
            <p className="text-gray-300 text-sm mb-4">
              The AI wants to run: <span className="font-mono text-blue-300 font-medium px-2 py-1 bg-blue-900/30 rounded">{approvalRequest.toolName}</span>
            </p>

            {approvalRequest.toolName === 'send_email' && approvalRequest.toolArgs.subject && (
              <div className="mb-4 bg-gray-900/50 p-3 rounded border border-gray-700">
                <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">To: {approvalRequest.toolArgs.email_address}</div>
                <div className="text-sm font-medium text-gray-200 mb-2">Subject: {approvalRequest.toolArgs.subject}</div>
                <div className="text-sm text-gray-300 whitespace-pre-wrap font-serif border-t border-gray-700 pt-2">{approvalRequest.toolArgs.body}</div>
              </div>
            )}

            {approvalRequest.toolName !== 'send_email' && (
              <div className="mb-4 bg-gray-900/50 p-3 rounded border border-gray-700">
                <span className="text-gray-400 text-xs mt-1 block font-mono overflow-auto">{JSON.stringify(approvalRequest.toolArgs, null, 2)}</span>
              </div>
            )}

            <div className="mb-4">
              <input 
                type="text" 
                placeholder="Requested Changes (Optional)..." 
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 placeholder-gray-500"
              />
            </div>

            <div className="flex gap-3 justify-end">
              <button 
                onClick={() => handleApproval(false)}
                className="px-4 py-2 text-sm text-white bg-red-600/20 hover:bg-red-600 border border-red-500/50 hover:border-red-500 rounded transition-colors"
              >
                {feedback ? "Reject & Change" : "Deny"}
              </button>
              <button 
                onClick={() => handleApproval(true)}
                className="px-6 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded font-medium transition-colors shadow-lg shadow-blue-500/30 flex items-center"
              >
                Approve <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
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

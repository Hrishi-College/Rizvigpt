import { useState, useRef, useEffect } from 'react';
import { Send, Plus, Trash2, Bot, User, Sparkles } from 'lucide-react';

const API_URL = 'http://localhost:8000';

function App() {
  const [conversations, setConversations] = useState([
    { id: '1', title: 'New Chat', messages: [] }
  ]);
  const [activeConvId, setActiveConvId] = useState('1');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [model, setModel] = useState('groq');
  const messagesEndRef = useRef(null);

  const activeConv = conversations.find(c => c.id === activeConvId) || conversations[0];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeConv.messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: Date.now()
    };

    setConversations(prev =>
      prev.map(conv =>
        conv.id === activeConvId
          ? { 
              ...conv, 
              messages: [...conv.messages, userMessage],
              title: conv.title === 'New Chat' ? input.slice(0, 40) : conv.title
            }
          : conv
      )
    );

    const currentInput = input;
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: currentInput,
          session_id: activeConvId,
          use_rag: true
        })
      });

      if (!response.ok) throw new Error('Network error');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      setConversations(prev =>
        prev.map(conv =>
          conv.id === activeConvId
            ? {
                ...conv,
                messages: [
                  ...conv.messages,
                  { role: 'assistant', content: '', timestamp: Date.now() }
                ]
              }
            : conv
        )
      );

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        fullResponse += chunk;

        setConversations(prev =>
          prev.map(conv =>
            conv.id === activeConvId
              ? {
                  ...conv,
                  messages: conv.messages.map((msg, idx) =>
                    idx === conv.messages.length - 1 && msg.role === 'assistant'
                      ? { ...msg, content: fullResponse }
                      : msg
                  )
                }
              : conv
          )
        );
      }
    } catch (error) {
      console.error('Error:', error);
      setConversations(prev =>
        prev.map(conv =>
          conv.id === activeConvId
            ? {
                ...conv,
                messages: [
                  ...conv.messages,
                  {
                    role: 'assistant',
                    content: '❌ Connection error. Make sure backend is running at ' + API_URL,
                    timestamp: Date.now()
                  }
                ]
              }
            : conv
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    const newConv = {
      id: Date.now().toString(),
      title: 'New Chat',
      messages: []
    };
    setConversations(prev => [newConv, ...prev]);
    setActiveConvId(newConv.id);
  };

  const handleDeleteConv = (id) => {
    if (conversations.length === 1) return;
    
    setConversations(prev => prev.filter(c => c.id !== id));
    
    if (activeConvId === id) {
      const remaining = conversations.filter(c => c.id !== id);
      setActiveConvId(remaining[0]?.id);
    }
  };

  return (
    <div className="flex h-screen bg-[#0a0a0a] text-gray-100">
      {/* Sidebar */}
      <div className="w-72 bg-gradient-to-b from-[#111111] to-[#0a0a0a] border-r border-gray-800/50 flex flex-col backdrop-blur-xl">
        {/* Header */}
        <div className="p-4 border-b border-gray-800/50">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 via-pink-500 to-orange-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <Sparkles size={22} className="text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                RizviGPT
              </h1>
              <p className="text-xs text-gray-500">College AI Assistant</p>
            </div>
          </div>
          
          <button
            onClick={handleNewChat}
            className="w-full flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-purple-600/90 to-pink-600/90 hover:from-purple-600 hover:to-pink-600 rounded-xl transition-all duration-200 font-medium shadow-lg shadow-purple-500/20 group"
          >
            <Plus size={18} className="group-hover:rotate-90 transition-transform duration-200" />
            <span>New Chat</span>
          </button>
        </div>



        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
          <div className="text-xs text-gray-500 px-3 mb-3 font-semibold uppercase tracking-wider">
            Recent Chats
          </div>
          <div className="space-y-1">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`group relative flex items-center gap-3 px-3 py-3 rounded-xl cursor-pointer transition-all duration-200 ${
                  activeConvId === conv.id
                    ? 'bg-gradient-to-r from-purple-600/20 to-pink-600/20 border border-purple-500/30'
                    : 'hover:bg-[#1a1a1a] border border-transparent'
                }`}
                onClick={() => setActiveConvId(conv.id)}
              >
                <div className={`w-2 h-2 rounded-full ${
                  activeConvId === conv.id ? 'bg-purple-400' : 'bg-gray-600'
                }`} />
                <span className="flex-1 truncate text-sm font-medium">
                  {conv.title}
                </span>
                {conversations.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteConv(conv.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-500/20 rounded-lg transition-all duration-200"
                  >
                    <Trash2 size={14} className="text-red-400" /> <span className="sr-only">Delete</span>
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-800/50 bg-[#0a0a0a]">
          <div className="text-xs text-gray-600 space-y-1">
            <div className="flex items-center justify-between">
              <span>Version 2.0</span>
              <span className="text-green-500">● Online</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-[#0a0a0a]">
        {/* Chat Header */}
        <div className="h-16 border-b border-gray-800/50 bg-gradient-to-b from-[#111111] to-[#0a0a0a] backdrop-blur-xl px-6 flex items-center shadow-lg">
          <h1 className="text-lg font-semibold text-gray-200 truncate">
            {activeConv.title}
          </h1>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
          {activeConv.messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <div className="w-24 h-24 bg-gradient-to-br from-purple-500 via-pink-500 to-orange-500 rounded-3xl flex items-center justify-center mb-6 shadow-2xl shadow-purple-500/30 animate-pulse">
                <Bot size={48} className="text-white" />
              </div>
              <h2 className="text-4xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-orange-400 bg-clip-text text-transparent mb-4">
                Welcome to RizviGPT
              </h2>
              <p className="text-gray-400 max-w-md text-lg mb-2">
                Your AI assistant for Rizvi College of Engineering
              </p>
              <p className="text-gray-600 text-sm">
                Ask me anything about courses, admissions, facilities, and more!
              </p>
              
              {/* Suggestion Pills */}
              <div className="grid grid-cols-2 gap-3 mt-8 max-w-2xl">
                {[
                  '📚 Tell me about CS courses',
                  '🎓 Admission requirements',
                  '🏫 Campus facilities',
                  '📅 Academic calendar'
                ].map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInput(suggestion.slice(2))}
                    className="px-4 py-3 bg-[#1a1a1a] hover:bg-[#222222] border border-gray-800 rounded-xl text-sm text-gray-300 hover:text-white transition-all duration-200 text-left"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              {activeConv.messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-4 ${
                    msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                  }`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-br from-blue-500 to-cyan-500 shadow-blue-500/30'
                        : 'bg-gradient-to-br from-purple-500 to-pink-500 shadow-purple-500/30'
                    }`}
                  >
                    {msg.role === 'user' ? (
                      <User size={20} className="text-white" />
                    ) : (
                      <Bot size={20} className="text-white" />
                    )}
                  </div>

                  {/* Message Bubble */}
                  <div
                    className={`flex-1 max-w-[85%] rounded-2xl px-5 py-4 ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-br from-blue-600 to-cyan-600 text-white shadow-lg shadow-blue-500/20'
                        : 'bg-[#1a1a1a] border border-gray-800/50 shadow-lg'
                    }`}
                  >
                    <p className="whitespace-pre-wrap leading-relaxed text-[15px]">
                      {msg.content}
                    </p>
                  </div>
                </div>
              ))}
              
              {loading && (
                <div className="flex gap-4">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-purple-500/30">
                    <Bot size={20} className="text-white" />
                  </div>
                  <div className="bg-[#1a1a1a] border border-gray-800/50 rounded-2xl px-5 py-4 shadow-lg">
                    <div className="flex gap-1.5">
                      <div className="w-2.5 h-2.5 bg-purple-400 rounded-full animate-bounce" />
                      <div className="w-2.5 h-2.5 bg-pink-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                      <div className="w-2.5 h-2.5 bg-orange-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-800/50 bg-gradient-to-b from-[#0a0a0a] to-[#111111] p-4 backdrop-blur-xl">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3 items-end bg-[#1a1a1a] rounded-2xl p-2 border border-gray-800/50 shadow-xl focus-within:border-purple-500/50 focus-within:ring-2 focus-within:ring-purple-500/20 transition-all">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Ask me anything about Rizvi College..."
                rows="1"
                className="flex-1 bg-transparent px-4 py-3 outline-none resize-none max-h-32 text-gray-100 placeholder-gray-500 text-[15px]"
                disabled={loading}
              />
              <button
                onClick={handleSend}
                disabled={loading || !input.trim()}
                className="p-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:from-gray-700 disabled:to-gray-700 disabled:cursor-not-allowed rounded-xl transition-all duration-200 flex-shrink-0 shadow-lg disabled:shadow-none shadow-purple-500/30 group"
              >
                <Send size={20} className="text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </button>
            </div>
            <p className="text-xs text-gray-600 text-center mt-3 flex items-center justify-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              Powered by RAG • Press Enter to send
            </p>
          </div>
        </div>
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #333;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #444;
        }
      `}</style>
    </div>
  );
}

export default App;
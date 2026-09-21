"use client";

import React, { useState, useEffect, useRef } from "react";

interface DatasetItem {
  id: string;
  filename: string;
  summary?: any;
  assistant_report?: any;
}

interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: string;
  cleaned_file_url?: string | null;
  intent?: string;
  actions?: string[];
  data?: any;
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SAMPLE_DATASETS = [
  { id: "enterprise_hr_payroll", label: "🏢 Nhân sự Doanh nghiệp" },
  { id: "vng_zalopay_transactions", label: "💳 ZaloPay 50k FinTech" },
  { id: "flights_dirty", label: "✈️ Flights SOTA" },
  { id: "hospital_dirty", label: "🏥 Hospital SOTA" },
  { id: "v1_whitespace", label: "⚡ Khoảng trắng V1" },
  { id: "v2_date_format", label: "📅 Ngày tháng V2" },
  { id: "v3_duplicate", label: "🔄 Trùng lặp V3" },
  { id: "v4_factual_uncertainty", label: "❓ Bất định V4" },
  { id: "v5_authority", label: "🛡️ Thẩm quyền V5" },
];

export default function ChatPage() {
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const [inputMessage, setInputMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("gpt-4o-mini");
  const [showSettings, setShowSettings] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome-1",
      role: "agent",
      content:
        "👋 **Xin chào! Tôi là Trợ lý Giám sát Dữ liệu DataGuard (The Escalation Referee).**\n\n" +
        "Tôi hoạt động như một Trọng tài Dữ liệu Độc lập, sẵn sàng hỗ trợ bạn:\n" +
        "1. 📊 **Đọc hiểu & phân tích ngữ nghĩa:** Tự động nhận diện kiểu dữ liệu, khóa chính, và tính toàn vẹn.\n" +
        "2. ⚖️ **Cổng Tự Chủ (Autonomy Gate):** Tách bạch rõ ràng những gì an toàn để tự sửa (AUTO) và những ca bất định PHẢI hỏi ý kiến bạn (ESCALATE).\n" +
        "3. 🛠️ **Tự động làm sạch dữ liệu (Auto-Fix):** Chuẩn hóa khoảng trắng, sửa format ngày chuẩn ISO, sửa lỗi chính tả và xuất file sạch tức thì.\n\n" +
        "👉 **Bạn có thể bấm biểu tượng 📎 bên dưới để tải tệp lên, hoặc bấm chọn nhanh bộ dữ liệu mẫu ở trên để bắt đầu!**",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, uploading]);

  // Load available datasets
  const fetchDatasets = async () => {
    try {
      const res = await fetch(`${API}/api/datasets`);
      if (res.ok) {
        const data = await res.json();
        if (data.datasets && data.datasets.length > 0) {
          setDatasets(data.datasets);
          if (!selectedDatasetId) {
            setSelectedDatasetId(data.datasets[data.datasets.length - 1].id);
          }
        }
      }
    } catch (err) {
      console.error("Could not fetch datasets", err);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  // Handle direct file upload
  const handleUploadFile = async (file: File) => {
    if (!file) return;
    setUploading(true);

    const userUploadMsg: Message = {
      id: `user-upload-${Date.now()}`,
      role: "user",
      content: `📎 Đã nạp tệp dữ liệu: **${file.name}** (${(file.size / 1024).toFixed(1)} KB)`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, userUploadMsg]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API}/api/datasets`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Không thể tải tệp lên");

      setSelectedDatasetId(data.dataset_id);
      await fetchDatasets();

      const rep = data.assistant_report || {};
      const sum = data.summary || {};

      const agentOverviewMsg: Message = {
        id: `agent-upload-${Date.now()}`,
        role: "agent",
        content:
          `🎉 **Đã tiếp nhận và hoàn tất phân tích tệp: \`${data.filename}\`**\n\n` +
          `• **Lĩnh vực:** ${rep.domain_name || "Dữ liệu Doanh nghiệp"} (${sum.total_rows?.toLocaleString()} dòng × ${sum.total_columns} cột)\n` +
          `• **Điểm sức khỏe dữ liệu:** **${rep.cleanliness_score ?? 100}% Sạch**\n` +
          `• **Khóa chính:** \`${rep.primary_key_column || "id"}\` • **Trục thời gian:** \`${rep.temporal_column || "—"}\`\n` +
          `• **Phân định rủi ro:** Có **${sum.auto_count || 0} ô** lỗi thường quy có thể tự động sửa, và **${sum.escalate_count || 0} ca** bất định cần bạn phê duyệt.\n\n` +
          `👉 Bạn muốn tôi làm sạch ngay các lỗi thường quy hay phân tích cụ thể cột nào?`,
        actions: sum.auto_count > 0 ? ["auto_repair", "open_reviews"] : ["open_reviews"],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, agentOverviewMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "agent",
          content: `⚠️ **Lỗi tải tệp:** ${err.message}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Handle 1-click sample load
  const handleLoadSample = async (sampleId: string) => {
    setLoading(true);
    const sampleItem = SAMPLE_DATASETS.find((s) => s.id === sampleId);
    const userSampleMsg: Message = {
      id: `user-sample-${Date.now()}`,
      role: "user",
      content: `⚡ Chọn bộ dữ liệu mẫu: **${sampleItem?.label || sampleId}**`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, userSampleMsg]);

    try {
      const res = await fetch(`${API}/api/datasets/load-sample/${sampleId}`, {
        method: "POST",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Không thể nạp dữ liệu mẫu");

      setSelectedDatasetId(data.dataset_id);
      await fetchDatasets();

      const rep = data.assistant_report || {};
      const sum = data.summary || {};

      const agentMsg: Message = {
        id: `agent-sample-${Date.now()}`,
        role: "agent",
        content:
          `📊 **Đã nạp thành công bộ dữ liệu mẫu: \`${data.filename}\`**\n\n` +
          `• **Lĩnh vực:** ${rep.domain_name || "Dữ liệu Doanh nghiệp"}\n` +
          `• **Quy mô:** ${sum.total_rows?.toLocaleString()} dòng × ${sum.total_columns} cột\n` +
          `• **Chỉ số dữ liệu sạch:** **${rep.cleanliness_score ?? 100}%**\n` +
          `• **Kết quả rà soát Cổng Tự Chủ:** Có **${sum.auto_count || 0} ô** thuộc diện tự động sửa (AUTO), và **${sum.escalate_count || 0} ca** cần người duyệt (ESCALATE).\n\n` +
          `Bạn có thể yêu cầu: *'Hãy sửa các lỗi cho tôi'* hoặc bấm nút tự động sửa bên dưới.`,
        actions: sum.auto_count > 0 ? ["auto_repair", "open_reviews"] : ["open_reviews"],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "agent",
          content: `⚠️ **Lỗi nạp mẫu:** ${err.message}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (customPrompt?: string) => {
    const textToSend = customPrompt || inputMessage;
    if (!textToSend.trim() || loading || uploading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage("");
    setLoading(true);

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: textToSend,
          dataset_id: selectedDatasetId || undefined,
          api_key: apiKey.trim() || undefined,
          base_url: baseUrl.trim() || undefined,
          model: model.trim() || "gpt-4o-mini",
          history: messages.slice(-6).map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Lỗi giao tiếp với Trợ lý AI");
      }

      const agentMsg: Message = {
        id: `agent-${Date.now()}`,
        role: "agent",
        content: data.response,
        cleaned_file_url: data.cleaned_file_url,
        intent: data.intent,
        actions: data.actions || [],
        data: data.data,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, agentMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "agent",
          content: `⚠️ **Rất tiếc đã có lỗi xảy ra:** ${err.message}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-4 flex flex-col h-[calc(100vh-5.5rem)]">
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        accept=".csv,.tsv,.xlsx,.xls,.parquet"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleUploadFile(f);
        }}
      />

      {/* Top Header & Selector Bar */}
      <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-4 backdrop-blur-md shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0">
        <div className="flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-emerald-400 to-teal-500 flex items-center justify-center text-2xl shadow-lg shadow-emerald-500/20 shrink-0">
            🤖
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg md:text-xl font-black text-white">
                DataGuard AI Copilot Command Center
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono">
                The Escalation Referee
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Trợ lý Trọng tài Dữ liệu Doanh nghiệp: Tải tệp trực tiếp, đối thoại thông minh và tự động sửa lỗi
            </p>
          </div>
        </div>

        {/* Dataset selector + Settings */}
        <div className="flex items-center gap-2.5">
          <div className="flex flex-col">
            <span className="text-[10px] font-bold text-slate-400 uppercase">
              Bộ Dữ Liệu Đang Mở:
            </span>
            <select
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-white rounded-lg px-2.5 py-1.5 text-xs font-semibold focus:outline-none focus:border-emerald-500 max-w-[180px] sm:max-w-[220px] truncate"
            >
              {datasets.length === 0 ? (
                <option value="">Chưa có dữ liệu nào</option>
              ) : (
                datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    📄 {d.filename}
                  </option>
                ))
              )}
            </select>
          </div>

          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs flex items-center gap-1.5 transition-colors self-end"
            title="Cấu hình LLM Provider"
          >
            <span>⚙️</span>
            <span className="hidden sm:inline">Cấu hình</span>
          </button>
        </div>
      </div>

      {/* 1-Click Sample Datasets Bar */}
      <div className="bg-slate-900/60 rounded-xl border border-slate-800/80 p-2.5 shrink-0 flex items-center gap-2 overflow-x-auto">
        <span className="text-[11px] font-black text-slate-400 uppercase tracking-wider shrink-0 pl-1">
          ⚡ Nạp nhanh mẫu:
        </span>
        <div className="flex items-center gap-1.5">
          {SAMPLE_DATASETS.map((s) => (
            <button
              key={s.id}
              onClick={() => handleLoadSample(s.id)}
              disabled={loading || uploading}
              className="px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-800 text-slate-300 hover:text-emerald-400 border border-slate-700 hover:border-emerald-500/40 text-xs whitespace-nowrap transition-all disabled:opacity-50"
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Settings Modal Bar (Optional LLM Key) */}
      {showSettings && (
        <div className="bg-slate-900/95 rounded-xl border border-slate-700 p-4 shrink-0 space-y-3 shadow-2xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <span>⚙️</span>
              <span>Cấu Hình Mô Hình Ngôn Ngữ Lớn (LLM Provider)</span>
            </span>
            <span className="text-[11px] text-emerald-400 font-mono">
              Chỉ gửi tóm tắt metadata (~300 tokens), tiết kiệm 99% chi phí!
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
                API Key (OpenAI / DeepSeek):
              </label>
              <input
                type="password"
                placeholder="sk-..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
                Base URL (Tùy chọn, để trống nếu dùng OpenAI):
              </label>
              <input
                type="text"
                placeholder="https://api.openai.com/v1 hoặc DeepSeek..."
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
                Mô hình (Model):
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="gpt-4o-mini"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="flex-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                />
                <button
                  onClick={() => setShowSettings(false)}
                  className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shrink-0"
                >
                  Lưu
                </button>
              </div>
            </div>
          </div>
          <p className="text-[11px] text-slate-400 italic">
            *Hệ thống đã tự động nhận diện API Key trong file <code>.env</code> nếu bạn đã điền.
          </p>
        </div>
      )}

      {/* Chat Messages Flow with Drag & Drop */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setIsDragging(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          const f = e.dataTransfer.files?.[0];
          if (f) handleUploadFile(f);
        }}
        className={`flex-1 bg-slate-900/50 rounded-2xl border ${
          isDragging ? "border-emerald-400 bg-emerald-500/5" : "border-slate-800/80"
        } p-5 overflow-y-auto space-y-4 backdrop-blur-sm shadow-inner transition-all relative`}
      >
        {isDragging && (
          <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-md rounded-2xl flex flex-col items-center justify-center z-10 border-2 border-dashed border-emerald-400">
            <span className="text-5xl animate-bounce">📥</span>
            <p className="text-base font-bold text-white mt-3">Thả tệp CSV / Excel vào đây để phân tích ngay</p>
            <p className="text-xs text-slate-400 mt-1">Hệ thống sẽ tự động quét qua 11 bộ dò chuyên sâu</p>
          </div>
        )}

        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex items-start gap-3 ${
              m.role === "user" ? "flex-row-reverse" : "flex-row"
            }`}
          >
            <div
              className={`w-9 h-9 rounded-xl flex items-center justify-center text-base shrink-0 shadow-md ${
                m.role === "user"
                  ? "bg-gradient-to-tr from-emerald-500 to-teal-600 text-white font-bold"
                  : "bg-slate-800 border border-slate-700 text-emerald-400"
              }`}
            >
              {m.role === "user" ? "👤" : "🛡️"}
            </div>

            <div
              className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed space-y-3 ${
                m.role === "user"
                  ? "bg-emerald-500/20 border border-emerald-500/40 text-emerald-50 rounded-tr-none ml-auto"
                  : "bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-none shadow-xl"
              }`}
            >
              <div className="whitespace-pre-wrap font-sans text-sm">{m.content}</div>

              {/* Interactive Action Buttons */}
              {m.actions && m.actions.length > 0 && !m.cleaned_file_url && (
                <div className="pt-2 border-t border-slate-800/80 flex flex-wrap gap-2">
                  {m.actions.includes("auto_repair") && (
                    <button
                      onClick={() => handleSendMessage("Hãy sửa các lỗi cho tôi")}
                      className="px-3.5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs uppercase tracking-wider shadow-lg shadow-emerald-500/20 transition-all flex items-center gap-1.5 hover:scale-[1.02]"
                    >
                      <span>⚡</span>
                      <span>Tự Động Sửa Lỗi Ngay (Auto-Fix)</span>
                    </button>
                  )}
                  {m.actions.includes("open_reviews") && (
                    <a
                      href="/reviews"
                      className="px-3.5 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 font-bold text-xs uppercase tracking-wider transition-all flex items-center gap-1.5"
                    >
                      <span>⚖️</span>
                      <span>Xem Các Ca Cần Duyệt (/reviews)</span>
                    </a>
                  )}
                </div>
              )}

              {/* Cleaned Download Button if repair executed */}
              {m.cleaned_file_url && (
                <div className="pt-2 border-t border-slate-800/80">
                  <a
                    href={`${API}${m.cleaned_file_url}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-black text-xs uppercase tracking-wider shadow-lg shadow-emerald-500/20 transition-all hover:scale-[1.02]"
                  >
                    <span>📥</span>
                    <span>Tải Về Tệp Dữ Liệu Sạch (Cleaned CSV)</span>
                  </a>
                </div>
              )}

              <div className="text-[10px] text-slate-500 text-right font-mono">
                {m.timestamp}
              </div>
            </div>
          </div>
        ))}

        {(loading || uploading) && (
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-base shrink-0 text-emerald-400 animate-spin">
              ⚙️
            </div>
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>
                {uploading
                  ? "Đang nạp tệp và chạy 11 bộ dò chuyên sâu..."
                  : "Trợ lý DataGuard đang suy nghĩ và phản hồi..."}
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Prompts Bar */}
      <div className="flex flex-wrap items-center gap-2 shrink-0">
        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1">
          💡 Gợi ý lệnh:
        </span>
        <button
          onClick={() => handleSendMessage("Hãy kiểm tra và phân tích file này báo cáo cho tôi")}
          className="px-3 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-800 border border-slate-700 text-xs text-slate-300 hover:text-emerald-300 transition-colors"
        >
          📊 Kiểm tra & Phân tích file này
        </button>
        <button
          onClick={() => handleSendMessage("Hãy sửa các lỗi cho tôi")}
          className="px-3 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-xs text-emerald-400 font-semibold transition-colors"
        >
          🛠️ Hãy sửa các lỗi cho tôi
        </button>
        <button
          onClick={() => handleSendMessage("Tại sao có những lỗi bạn tự sửa, còn lỗi khác lại bắt tôi duyệt?")}
          className="px-3 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-800 border border-slate-700 text-xs text-slate-300 hover:text-amber-300 transition-colors"
        >
          ⚖️ Vì sao phân chia AUTO vs ESCALATE?
        </button>
      </div>

      {/* Input Message Form with 📎 Attachment Button */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendMessage();
        }}
        className="flex items-center gap-2.5 shrink-0"
      >
        {/* Attachment Button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading || uploading}
          className="p-3.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-emerald-400 transition-all flex items-center justify-center shrink-0 disabled:opacity-50"
          title="Đính kèm tệp CSV/Excel từ máy tính"
        >
          <span className="text-lg">📎</span>
        </button>

        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Nhập câu hỏi hoặc yêu cầu cho Trợ lý (ví dụ: 'Hãy kiểm tra file này', 'Hãy sửa các lỗi')..."
          disabled={loading || uploading}
          className="flex-1 px-4 py-3.5 rounded-xl bg-slate-900 border border-slate-700 text-sm text-white placeholder:text-slate-400 focus:outline-none focus:border-emerald-500 shadow-xl"
        />
        <button
          type="submit"
          disabled={loading || uploading || !inputMessage.trim()}
          className="px-6 py-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-slate-950 font-black text-sm transition-all shadow-lg shadow-emerald-500/20 flex items-center gap-2"
        >
          <span>Gửi Lệnh</span>
          <span>→</span>
        </button>
      </form>
    </div>
  );
}

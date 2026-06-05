import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  Archive,
  Check,
  Clipboard,
  Download,
  Eye,
  Filter,
  FolderSearch,
  Image as ImageIcon,
  Loader2,
  Pencil,
  Play,
  RefreshCw,
  Search,
  Settings,
  Trash2,
  X,
  Globe,
  Zap,
  ZapOff
} from "lucide-react";
import {
  exportUrl,
  getAIConfig,
  getOcrStatus,
  healthCheck,
  imageUrl,
  listItems,
  runAnalysis,
  runOcr,
  saveAIConfig,
  scan,
  thumbnailUrl,
  trashItem,
  updateItem
} from "./api";
import type { AIConfig, HealthInfo, ItemStatus, OcrStatus, PicItem } from "./types";

/* ── Provider presets ─────────────────────────────────────────────── */

const AI_PRESETS: { label: string; base_url: string; models: string[] }[] = [
  { label: "DeepSeek", base_url: "https://api.deepseek.com", models: ["deepseek-chat", "deepseek-reasoner"] },
  { label: "OpenAI", base_url: "https://api.openai.com", models: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1-nano"] },
  { label: "Kimi (月之暗面)", base_url: "https://api.moonshot.cn", models: ["moonshot-v1-8k", "moonshot-v1-32k"] },
  { label: "智谱 GLM", base_url: "https://open.bigmodel.cn/api/paas", models: ["glm-4-flash", "glm-4-plus"] },
  { label: "通义千问", base_url: "https://dashscope.aliyuncs.com/compatible-mode", models: ["qwen-turbo", "qwen-plus"] },
  { label: "硅基流动", base_url: "https://api.siliconflow.cn", models: ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-7B-Instruct"] },
  { label: "自定义", base_url: "", models: [] },
];

/* ── Translations ─────────────────────────────────────────────────── */

const translations = {
  zh: {
    subtitle: "本地截图文字整理、识别和审阅",
    imgDir: "图片目录",
    imgDirPlaceholder: "例如 H:\\photos\\screenshots",
    recursive: "递归",
    scan: "扫描",
    ocr: "OCR",
    analyze: "分析",
    searchPlaceholder: "搜索文件名、OCR 或摘要",
    status: "状态",
    suggestion: "建议",
    category: "分类",
    provider: "AI 引擎",
    refresh: "刷新",
    total: "共",
    items: "条",
    page: "第",
    pageOf: "/",
    pageUnit: "页",
    colImg: "图片",
    colFile: "文件",
    colOcr: "OCR 文字",
    colAnalysis: "分析",
    colStatus: "状态",
    colActions: "操作",
    empty: "暂无数据 — 输入图片目录并点击「扫描」开始",
    unrecognized: "未识别",
    unanalyzed: "未分析",
    topic: "话题",
    ocrQuality: "OCR",
    reason: "理由",
    exportJson: "导出 JSON",
    exportCsv: "导出 CSV",
    perPage: "每页显示",
    msgOcrDone: "✓ OCR 完成：已处理",
    msgOcrFail: "失败",
    msgNoOcr: "✓ 没有待处理的 OCR 项目",
    msgActionDone: "完成：",
    msgCopyDone: "✓ 已复制 OCR 文本",
    confirmTrash: "移入系统回收站？",
    editOcr: "编辑 OCR 文本",
    close: "关闭",
    cancel: "取消",
    save: "保存",
    all: "全部",
    ocrProgress: "OCR 处理中 —",
    ocrFail: "失败",
    actionUpdateStatus: "更新状态",
    actionTrash: "移入回收站",
    actionSaveText: "保存文字",
    tooltipZoom: "放大图片",
    tooltipView: "查看原图",
    tooltipCopy: "复制 OCR",
    tooltipEdit: "编辑 OCR",
    tooltipKeep: "保留",
    tooltipReview: "待复核",
    tooltipTrash: "移入回收站",
    settings: "AI 设置",
    settingsTitle: "AI 分析设置",
    presetLabel: "服务商预设",
    apiKeyLabel: "API Key",
    apiKeyPlaceholder: "sk-...",
    baseUrlLabel: "API 地址",
    modelLabel: "模型",
    testConn: "测试连接",
    connOk: "✓ 连接成功",
    connFail: "✗ 连接失败",
    aiConnected: "AI 已连接",
    aiNotConfigured: "AI 未配置",
    ollamaConnected: "Ollama 可用",
    providerAuto: "自动（推荐）",
    providerAI: "在线 AI",
    providerOllama: "Ollama (本地)",
    providerRules: "仅规则",
  },
  en: {
    subtitle: "Local screenshot OCR, text organizer and reviewer",
    imgDir: "Image Directory",
    imgDirPlaceholder: "e.g. H:\\photos\\screenshots",
    recursive: "Recursive",
    scan: "Scan",
    ocr: "OCR",
    analyze: "Analyze",
    searchPlaceholder: "Search filename, OCR or summary",
    status: "Status",
    suggestion: "Suggestion",
    category: "Category",
    provider: "AI Engine",
    refresh: "Refresh",
    total: "Total",
    items: "items",
    page: "Page",
    pageOf: "of",
    pageUnit: "",
    colImg: "Image",
    colFile: "File",
    colOcr: "OCR Text",
    colAnalysis: "Analysis",
    colStatus: "Status",
    colActions: "Actions",
    empty: "No data — Enter an image directory and click 'Scan' to start",
    unrecognized: "Not recognized",
    unanalyzed: "Not analyzed",
    topic: "Topic",
    ocrQuality: "OCR",
    reason: "Reason",
    exportJson: "Export JSON",
    exportCsv: "Export CSV",
    perPage: "Per Page",
    msgOcrDone: "✓ OCR Done: Processed",
    msgOcrFail: "Failed",
    msgNoOcr: "✓ No pending OCR items",
    msgActionDone: "Done:",
    msgCopyDone: "✓ Copied OCR text",
    confirmTrash: "Move to system recycle bin?",
    editOcr: "Edit OCR Text",
    close: "Close",
    cancel: "Cancel",
    save: "Save",
    all: "All",
    ocrProgress: "Processing OCR —",
    ocrFail: "failed",
    actionUpdateStatus: "Update Status",
    actionTrash: "Move to Trash",
    actionSaveText: "Save Text",
    tooltipZoom: "Zoom image",
    tooltipView: "View original",
    tooltipCopy: "Copy OCR",
    tooltipEdit: "Edit OCR",
    tooltipKeep: "Keep",
    tooltipReview: "Mark for review",
    tooltipTrash: "Move to Trash",
    settings: "AI Settings",
    settingsTitle: "AI Analysis Settings",
    presetLabel: "Provider Preset",
    apiKeyLabel: "API Key",
    apiKeyPlaceholder: "sk-...",
    baseUrlLabel: "API URL",
    modelLabel: "Model",
    testConn: "Test Connection",
    connOk: "✓ Connected",
    connFail: "✗ Connection failed",
    aiConnected: "AI Connected",
    aiNotConfigured: "AI Not Configured",
    ollamaConnected: "Ollama Available",
    providerAuto: "Auto (Recommended)",
    providerAI: "Online AI",
    providerOllama: "Ollama (Local)",
    providerRules: "Rules Only",
  },
  ja: {
    subtitle: "ローカルスクリーンショットOCR、テキスト整理・レビューツール",
    imgDir: "画像ディレクトリ",
    imgDirPlaceholder: "例: H:\\photos\\screenshots",
    recursive: "再帰的",
    scan: "スキャン",
    ocr: "OCR",
    analyze: "分析",
    searchPlaceholder: "ファイル名、OCR、概要を検索",
    status: "ステータス",
    suggestion: "提案",
    category: "カテゴリ",
    provider: "AIエンジン",
    refresh: "更新",
    total: "合計",
    items: "件",
    page: "ページ",
    pageOf: "/",
    pageUnit: "",
    colImg: "画像",
    colFile: "ファイル",
    colOcr: "OCR テキスト",
    colAnalysis: "分析",
    colStatus: "ステータス",
    colActions: "操作",
    empty: "データがありません — 画像ディレクトリを入力し「スキャン」をクリック",
    unrecognized: "未認識",
    unanalyzed: "未分析",
    topic: "トピック",
    ocrQuality: "OCR",
    reason: "理由",
    exportJson: "JSON出力",
    exportCsv: "CSV出力",
    perPage: "表示件数",
    msgOcrDone: "✓ OCR完了：処理済み",
    msgOcrFail: "失敗",
    msgNoOcr: "✓ 保留中のOCRアイテムはありません",
    msgActionDone: "完了：",
    msgCopyDone: "✓ OCRテキストをコピーしました",
    confirmTrash: "ごみ箱に移動しますか？",
    editOcr: "OCRテキストを編集",
    close: "閉じる",
    cancel: "キャンセル",
    save: "保存",
    all: "すべて",
    ocrProgress: "OCR 処理中 —",
    ocrFail: "失敗",
    actionUpdateStatus: "ステータス更新",
    actionTrash: "ごみ箱へ移動",
    actionSaveText: "テキストを保存",
    tooltipZoom: "画像を拡大",
    tooltipView: "元の画像を表示",
    tooltipCopy: "OCRをコピー",
    tooltipEdit: "OCRを編集",
    tooltipKeep: "保持",
    tooltipReview: "レビュー待ち",
    tooltipTrash: "ごみ箱へ移動",
    settings: "AI設定",
    settingsTitle: "AI分析設定",
    presetLabel: "プロバイダプリセット",
    apiKeyLabel: "APIキー",
    apiKeyPlaceholder: "sk-...",
    baseUrlLabel: "API URL",
    modelLabel: "モデル",
    testConn: "接続テスト",
    connOk: "✓ 接続成功",
    connFail: "✗ 接続失敗",
    aiConnected: "AI接続済み",
    aiNotConfigured: "AI未設定",
    ollamaConnected: "Ollama利用可能",
    providerAuto: "自動（推奨）",
    providerAI: "オンラインAI",
    providerOllama: "Ollama（ローカル）",
    providerRules: "ルールのみ",
  },
  de: {
    subtitle: "Lokaler Screenshot OCR, Textorganisator und Reviewer",
    imgDir: "Bildverzeichnis",
    imgDirPlaceholder: "z.B. H:\\photos\\screenshots",
    recursive: "Rekursiv",
    scan: "Scannen",
    ocr: "OCR",
    analyze: "Analysieren",
    searchPlaceholder: "Dateiname, OCR oder Zusammenfassung suchen",
    status: "Status",
    suggestion: "Vorschlag",
    category: "Kategorie",
    provider: "KI-Engine",
    refresh: "Aktualisieren",
    total: "Gesamt",
    items: "Einträge",
    page: "Seite",
    pageOf: "von",
    pageUnit: "",
    colImg: "Bild",
    colFile: "Datei",
    colOcr: "OCR Text",
    colAnalysis: "Analyse",
    colStatus: "Status",
    colActions: "Aktionen",
    empty: "Keine Daten — Geben Sie ein Bildverzeichnis ein und klicken Sie auf 'Scannen'",
    unrecognized: "Nicht erkannt",
    unanalyzed: "Nicht analysiert",
    topic: "Thema",
    ocrQuality: "OCR",
    reason: "Grund",
    exportJson: "JSON Export",
    exportCsv: "CSV Export",
    perPage: "Pro Seite",
    msgOcrDone: "✓ OCR Fertig: Verarbeitet",
    msgOcrFail: "Fehlgeschlagen",
    msgNoOcr: "✓ Keine ausstehenden OCR-Elemente",
    msgActionDone: "Erledigt:",
    msgCopyDone: "✓ OCR-Text kopiert",
    confirmTrash: "In den Papierkorb verschieben?",
    editOcr: "OCR-Text bearbeiten",
    close: "Schließen",
    cancel: "Abbrechen",
    save: "Speichern",
    all: "Alle",
    ocrProgress: "OCR wird verarbeitet —",
    ocrFail: "fehlgeschlagen",
    actionUpdateStatus: "Status aktualisieren",
    actionTrash: "In den Papierkorb",
    actionSaveText: "Text speichern",
    tooltipZoom: "Bild vergrößern",
    tooltipView: "Original ansehen",
    tooltipCopy: "OCR kopieren",
    tooltipEdit: "OCR bearbeiten",
    tooltipKeep: "Behalten",
    tooltipReview: "Zur Überprüfung",
    tooltipTrash: "In den Papierkorb",
    settings: "KI-Einstellungen",
    settingsTitle: "KI-Analyse Einstellungen",
    presetLabel: "Anbieter-Voreinstellung",
    apiKeyLabel: "API-Schlüssel",
    apiKeyPlaceholder: "sk-...",
    baseUrlLabel: "API-URL",
    modelLabel: "Modell",
    testConn: "Verbindung testen",
    connOk: "✓ Verbunden",
    connFail: "✗ Verbindung fehlgeschlagen",
    aiConnected: "KI verbunden",
    aiNotConfigured: "KI nicht konfiguriert",
    ollamaConnected: "Ollama verfügbar",
    providerAuto: "Auto (Empfohlen)",
    providerAI: "Online-KI",
    providerOllama: "Ollama (Lokal)",
    providerRules: "Nur Regeln",
  }
};

type LangType = keyof typeof translations;

export function App() {
  const [lang, setLang] = useState<LangType>("zh");
  const t = translations[lang];

  const [pageSize, setPageSize] = useState(20);
  const [directory, setDirectory] = useState("");
  const [recursive, setRecursive] = useState(true);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<PicItem[]>([]);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [selected, setSelected] = useState<PicItem | null>(null);
  const [editing, setEditing] = useState<PicItem | null>(null);
  const [editText, setEditText] = useState("");
  const [provider, setProvider] = useState("auto");
  const [includeImage, setIncludeImage] = useState(false);
  const [ocrProgress, setOcrProgress] = useState<OcrStatus | null>(null);
  const ocrPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Health / connection status
  const [healthInfo, setHealthInfo] = useState<HealthInfo | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    healthCheck().then(setHealthInfo).catch(() => {});
  }, []);

  const params = useMemo(() => {
    const next = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize)
    });
    if (query.trim()) next.set("q", query.trim());
    if (status) next.set("status", status);
    if (suggestion) next.set("suggestion", suggestion);
    return next;
  }, [page, pageSize, query, status, suggestion]);

  const load = useCallback(async () => {
    const data = await listItems(params);
    setItems(data.items);
    setTotal(data.total);
  }, [params]);

  useEffect(() => {
    load().catch((error) => setMessage(error.message));
  }, [load]);

  // Auto-dismiss message after 6s
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(""), 6000);
    return () => clearTimeout(timer);
  }, [message]);

  // OCR progress polling
  const stopOcrPoll = useCallback(() => {
    if (ocrPollRef.current) {
      clearInterval(ocrPollRef.current);
      ocrPollRef.current = null;
    }
  }, []);

  const startOcrPoll = useCallback(() => {
    stopOcrPoll();
    ocrPollRef.current = setInterval(async () => {
      try {
        const s = await getOcrStatus();
        setOcrProgress(s);
        if (!s.running) {
          stopOcrPoll();
          setMessage(`${t.msgOcrDone} ${s.processed}，${t.msgOcrFail} ${s.failed}`);
          setOcrProgress(null);
          setBusy("");
          await load();
        }
      } catch {
        stopOcrPoll();
        setOcrProgress(null);
        setBusy("");
      }
    }, 1500);
  }, [stopOcrPoll, load, t]);

  useEffect(() => stopOcrPoll, [stopOcrPoll]);

  async function handleOcr() {
    setBusy("OCR");
    setMessage("");
    try {
      const result = await runOcr();
      if (result.status === "started" || result.status === "already_running") {
        setOcrProgress(result);
        startOcrPoll();
      } else {
        setMessage(t.msgNoOcr);
        setBusy("");
      }
    } catch (error) {
      setMessage(`✗ ${error instanceof Error ? error.message : String(error)}`);
      setBusy("");
    }
  }

  async function runAction(label: string, action: () => Promise<unknown>) {
    setBusy(label);
    setMessage("");
    try {
      const result = await action();
      setMessage(`${t.msgActionDone} ${JSON.stringify(result)}`);
      await load();
      // Refresh health after analysis to update connection status
      healthCheck().then(setHealthInfo).catch(() => {});
    } catch (error) {
      setMessage(`✗ ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy("");
    }
  }

  async function copy(text: string) {
    await navigator.clipboard.writeText(text || "");
    setMessage(t.msgCopyDone);
  }

  async function setItemStatus(item: PicItem, nextStatus: ItemStatus) {
    await runAction(t.actionUpdateStatus, () => updateItem(item.id, { status: nextStatus }));
  }

  async function confirmTrashAction(item: PicItem) {
    const ok = window.confirm(`"${item.filename}" — ${t.confirmTrash}`);
    if (!ok) return;
    await runAction(t.actionTrash, () => trashItem(item.id));
  }

  async function saveEdit() {
    if (!editing) return;
    await runAction(t.actionSaveText, () => updateItem(editing.id, { ocr_text: editText }));
    setEditing(null);
  }

  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  // Determine AI status combining backend health and local config
  let aiStatus = "not_configured";
  try {
    const isLocalConfigured = !!localStorage.getItem("ai_config");
    const isLocalAvailable = localStorage.getItem("ai_available") === "true";
    
    if (isLocalConfigured) {
      aiStatus = isLocalAvailable ? "connected" : "error";
    } else if (healthInfo?.ai_configured) {
      aiStatus = healthInfo.ai_available ? "connected" : "error";
    }
  } catch {
    if (healthInfo?.ai_configured) {
      aiStatus = healthInfo.ai_available ? "connected" : "error";
    }
  }

  // Get local config for display and execution
  let currentModel = healthInfo?.ai_model || "";
  let localConf: any = null;
  try {
    const saved = localStorage.getItem("ai_config");
    if (saved) {
      localConf = JSON.parse(saved);
      if (localConf.model) currentModel = localConf.model;
    }
  } catch {}

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>ScreenTextOrganizer</h1>
          <p>{t.subtitle}</p>
        </div>
        <div className="topbar-actions" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {/* AI Status indicators */}
          <div className="status-indicators" style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px" }}>
            {healthInfo && (
              <>
                <span className={`status-dot ${aiStatus === "connected" ? "good" : aiStatus === "error" ? "warn" : "neutral"}`}
                  title={aiStatus === "connected" ? `${t.aiConnected} (${currentModel})` : t.aiNotConfigured}>
                  <Zap size={12} />
                  {aiStatus === "connected" ? "AI" : <ZapOff size={12} />}
                </span>
                {healthInfo.ollama_available && (
                  <span className="status-dot good" title={t.ollamaConnected}>
                    Ollama
                  </span>
                )}
              </>
            )}
          </div>

          <button className="icon-button text-button" onClick={() => setShowSettings(true)} title={t.settings}>
            <Settings size={16} />
          </button>

          <div className="lang-switcher" style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-muted)" }}>
            <Globe size={16} />
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as LangType)}
              style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer", outline: "none", fontSize: "13px", padding: 0, minHeight: "auto" }}
            >
              <option value="zh">中文</option>
              <option value="en">English</option>
              <option value="ja">日本語</option>
              <option value="de">Deutsch</option>
            </select>
          </div>
          <a className="icon-button text-button" href={exportUrl("json")} title={t.exportJson}>
            <Download size={15} /> JSON
          </a>
          <a className="icon-button text-button" href={exportUrl("csv")} title={t.exportCsv}>
            <Download size={15} /> CSV
          </a>
        </div>
      </header>

      <section className="control-band">
        <div className="scan-row">
          <label className="field wide">
            <span>{t.imgDir}</span>
            <input
              value={directory}
              placeholder={t.imgDirPlaceholder}
              onChange={(event) => setDirectory(event.target.value)}
            />
          </label>
          <label className="check-field">
            <input
              type="checkbox"
              checked={recursive}
              onChange={(event) => setRecursive(event.target.checked)}
            />
            {t.recursive}
          </label>
          <button
            className="primary-button"
            disabled={!directory || !!busy}
            onClick={() => runAction(t.scan, () => scan(directory, recursive))}
          >
            {busy === t.scan ? <Loader2 className="spin" size={16} /> : <ImageIcon size={16} />}
            {t.scan}
          </button>
          <button className="icon-button text-button" disabled={!!busy} onClick={handleOcr}>
            {busy === "OCR" ? <Loader2 className="spin" size={16} /> : <Play size={16} />}
            {t.ocr}
          </button>
          <button
            className="icon-button text-button"
            disabled={!!busy}
            onClick={() =>
              runAction(t.analyze, () =>
                runAnalysis({ 
                  provider, 
                  include_image: includeImage,
                  ai_api_key: localConf?.api_key,
                  ai_base_url: localConf?.base_url,
                  ai_model: localConf?.model
                })
              )
            }
          >
            {busy === t.analyze ? <Loader2 className="spin" size={16} /> : <Archive size={16} />}
            {t.analyze}
          </button>
        </div>

        <div className="filter-row">
          <label className="search-field">
            <Search size={16} />
            <input
              value={query}
              placeholder={t.searchPlaceholder}
              onChange={(event) => {
                setPage(1);
                setQuery(event.target.value);
              }}
            />
          </label>
          <Select label={t.status} value={status} onChange={setStatus} options={["", "unreviewed", "kept", "review", "trashed"]} allText={t.all} />
          <Select label={t.suggestion} value={suggestion} onChange={setSuggestion} options={["", "keep", "review", "delete"]} allText={t.all} />
          <label className="field compact">
            <span>{t.provider}</span>
            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
              <option value="auto">{t.providerAuto}</option>
              <option value="ai">{t.providerAI}</option>
              <option value="ollama">{t.providerOllama}</option>
              <option value="rules">{t.providerRules}</option>
            </select>
          </label>
          <button className="icon-button" title={t.refresh} onClick={() => load()} disabled={!!busy}>
            <RefreshCw size={16} />
          </button>
        </div>
      </section>

      {ocrProgress && ocrProgress.total > 0 && <OcrProgressBar progress={ocrProgress} t={t} />}

      {message && <div className="message">{message}</div>}

      <section className="table-wrap">
        <div className="table-meta">
          <span>
            <Filter size={14} /> {t.total} {total} {t.items}
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>{t.perPage}</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              style={{
                background: "var(--bg-input)",
                border: "1px solid var(--border-strong)",
                color: "var(--text-secondary)",
                borderRadius: "var(--radius-sm)",
                padding: "2px 8px",
                minHeight: "unset",
                height: "26px",
                fontSize: "12px",
                cursor: "pointer",
                outline: "none"
              }}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
          <span>
            {t.page} {page} {t.pageOf} {pageCount} {t.pageUnit}
          </span>
        </div>
        <table>
          <thead>
            <tr>
              <th>{t.colImg}</th>
              <th>{t.colFile}</th>
              <th>{t.colOcr}</th>
              <th>{t.colAnalysis}</th>
              <th>{t.colStatus}</th>
              <th>{t.colActions}</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="empty-state">
                    <FolderSearch size={42} strokeWidth={1.2} />
                    <p>{t.empty}</p>
                  </div>
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id}>
                  <td className="thumb-cell">
                    <button className="thumb-button" onClick={() => setSelected(item)} title={t.tooltipZoom}>
                      <img src={thumbnailUrl(item.id)} alt={item.filename} loading="lazy" />
                    </button>
                  </td>
                  <td className="file-cell">
                    <strong title={item.filename}>{item.filename}</strong>
                    <span>{formatBytes(item.file_size)}</span>
                    <span>{item.width || "-"} × {item.height || "-"}</span>
                    <small title={item.source_path}>{item.source_path}</small>
                  </td>
                  <td className="ocr-cell">
                    <div className="ocr-status">
                      <Badge tone={item.ocr_status === "done" ? "good" : item.ocr_status === "failed" ? "bad" : item.ocr_status === "running" ? "accent" : "neutral"}>
                        {item.ocr_status}
                      </Badge>
                      {item.ocr_confidence !== null && <span>{Math.round(item.ocr_confidence * 100)}%</span>}
                    </div>
                    {item.ocr_error ? <p className="error-text">{item.ocr_error}</p> : <p>{item.ocr_text || t.unrecognized}</p>}
                  </td>
                  <td className="analysis-cell">
                    <div className="badge-row">
                      <Badge tone={item.analysis_source === "ai" ? "accent" : item.analysis_source === "ollama" ? "accent" : "neutral"}>
                        {item.analysis_source || "none"}
                      </Badge>
                      {item.keep_suggestion && <Badge tone={item.keep_suggestion === "keep" ? "good" : item.keep_suggestion === "delete" ? "bad" : "warn"}>{item.keep_suggestion}</Badge>}
                      {item.value_score && <Badge tone="neutral">{item.value_score}/5</Badge>}
                    </div>
                    <p>{item.summary || t.unanalyzed}</p>
                    <div className="risk-line">
                      {item.staleness_risk && <span>{t.topic} {item.staleness_risk}</span>}
                      {item.distortion_risk && (
                        <span>
                          {t.ocrQuality}{" "}
                          <Badge tone={item.distortion_risk === "high" ? "good" : item.distortion_risk === "low" ? "bad" : "warn"}>
                            {item.distortion_risk}
                          </Badge>
                        </span>
                      )}
                    </div>
                    {item.category && <p className="keep-reason">{t.reason} {item.category}</p>}
                    <div className="tags">{item.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
                  </td>
                  <td className="status-cell">
                    <Badge tone={item.status === "kept" ? "good" : item.status === "trashed" ? "bad" : item.status === "review" ? "warn" : "neutral"}>
                      {item.status}
                    </Badge>
                    {item.trash_error && <p className="error-text">{item.trash_error}</p>}
                  </td>
                  <td className="action-cell">
                    <button className="icon-button" title={t.tooltipView} onClick={() => setSelected(item)}>
                      <Eye size={16} />
                    </button>
                    <button className="icon-button" title={t.tooltipCopy} onClick={() => copy(item.ocr_text)}>
                      <Clipboard size={16} />
                    </button>
                    <button
                      className="icon-button"
                      title={t.tooltipEdit}
                      onClick={() => {
                        setEditing(item);
                        setEditText(item.ocr_text || "");
                      }}
                    >
                      <Pencil size={16} />
                    </button>
                    <button className="icon-button good" title={t.tooltipKeep} onClick={() => setItemStatus(item, "kept")}>
                      <Check size={16} />
                    </button>
                    <button className="icon-button warn" title={t.tooltipReview} onClick={() => setItemStatus(item, "review")}>
                      <Archive size={16} />
                    </button>
                    <button className="icon-button danger" title={t.tooltipTrash} onClick={() => confirmTrashAction(item)}>
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
      <Pager page={page} pageCount={pageCount} onChange={setPage} />

      {selected && (
        <div className="modal" role="dialog" aria-modal="true" onClick={(e) => { if (e.target === e.currentTarget) setSelected(null); }}>
          <div className="image-dialog">
            <div className="dialog-bar">
              <strong>{selected.filename}</strong>
              <button className="icon-button" onClick={() => setSelected(null)} title={t.close} aria-label={t.close}>
                <X size={18} />
              </button>
            </div>
            <img src={imageUrl(selected.id)} alt={selected.filename} />
          </div>
        </div>
      )}

      {editing && (
        <div className="modal" role="dialog" aria-modal="true" onClick={(e) => { if (e.target === e.currentTarget) setEditing(null); }}>
          <div className="edit-dialog">
            <div className="dialog-bar">
              <strong>{t.editOcr}</strong>
              <button className="icon-button" onClick={() => setEditing(null)} title={t.close} aria-label={t.close}>
                <X size={18} />
              </button>
            </div>
            <textarea value={editText} onChange={(event) => setEditText(event.target.value)} />
            <div className="dialog-actions">
              <button onClick={() => setEditing(null)}>{t.cancel}</button>
              <button className="primary-button" onClick={saveEdit}>
                {t.save}
              </button>
            </div>
          </div>
        </div>
      )}

      {showSettings && (
        <AISettingsDialog
          t={t}
          onClose={() => {
            setShowSettings(false);
            healthCheck().then(setHealthInfo).catch(() => {});
          }}
        />
      )}
    </main>
  );
}

/* ---------- AI Settings Dialog ---------- */

function AISettingsDialog({ t, onClose }: { t: typeof translations["zh"]; onClose: () => void }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://api.deepseek.com");
  const [model, setModel] = useState("deepseek-chat");
  const [presetIdx, setPresetIdx] = useState(0);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("ai_config");
      if (saved) {
        const config = JSON.parse(saved);
        setApiKey(config.api_key || "");
        setBaseUrl(config.base_url || "https://api.deepseek.com");
        setModel(config.model || "deepseek-chat");
        const idx = AI_PRESETS.findIndex(p => p.base_url === config.base_url);
        if (idx >= 0) setPresetIdx(idx);
        else setPresetIdx(AI_PRESETS.length - 1);
      }
    } catch {
      // ignore
    }
    setLoading(false);
  }, []);

  function handlePresetChange(idx: number) {
    setPresetIdx(idx);
    const preset = AI_PRESETS[idx];
    if (preset.base_url) {
      setBaseUrl(preset.base_url);
      if (preset.models.length > 0) setModel(preset.models[0]);
    }
  }

  async function handleSave() {
    if (!apiKey && !baseUrl) return;
    setSaving(true);
    const conf = { api_key: apiKey, base_url: baseUrl, model: model };
    localStorage.setItem("ai_config", JSON.stringify(conf));
    
    try {
      const { testAIConfig } = await import("./api");
      const result = await testAIConfig(conf);
      if (result.ai_available) {
        localStorage.setItem("ai_available", "true");
        setTestResult(t.connOk);
      } else {
        localStorage.setItem("ai_available", "false");
        setTestResult(t.connFail);
      }
    } catch (err) {
      localStorage.setItem("ai_available", "false");
      setTestResult(t.connFail);
    }
    setSaving(false);
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    const conf = { api_key: apiKey, base_url: baseUrl, model: model };
    try {
      const { testAIConfig } = await import("./api");
      const result = await testAIConfig(conf);
      setTestResult(result.ai_available ? t.connOk : t.connFail);
    } catch {
      setTestResult(t.connFail);
    }
    setTesting(false);
  }

  const preset = AI_PRESETS[presetIdx];

  return (
    <div className="modal" role="dialog" aria-modal="true" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="edit-dialog settings-dialog">
        <div className="dialog-bar">
          <strong>{t.settingsTitle}</strong>
          <button className="icon-button" onClick={onClose} title={t.close} aria-label={t.close}>
            <X size={18} />
          </button>
        </div>

        {loading ? (
          <div style={{ padding: "24px", textAlign: "center" }}>
            <Loader2 className="spin" size={24} />
          </div>
        ) : (
          <div className="settings-form">
            <label className="settings-field">
              <span>{t.presetLabel}</span>
              <select value={presetIdx} onChange={(e) => handlePresetChange(Number(e.target.value))}>
                {AI_PRESETS.map((p, i) => (
                  <option key={i} value={i}>{p.label}</option>
                ))}
              </select>
            </label>

            <label className="settings-field">
              <span>{t.apiKeyLabel}</span>
              <input
                type="password"
                value={apiKey}
                placeholder={t.apiKeyPlaceholder}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </label>

            <label className="settings-field">
              <span>{t.baseUrlLabel}</span>
              <input
                value={baseUrl}
                placeholder="https://api.deepseek.com"
                onChange={(e) => setBaseUrl(e.target.value)}
                readOnly={preset.base_url !== ""}
              />
            </label>

            <label className="settings-field">
              <span>{t.modelLabel}</span>
              {preset.models.length > 0 ? (
                <select value={model} onChange={(e) => setModel(e.target.value)}>
                  {preset.models.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              ) : (
                <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="model-name" />
              )}
            </label>

            {testResult && (
              <div className={`settings-test-result ${testResult.includes("✓") ? "good" : "bad"}`}>
                {testResult}
              </div>
            )}
          </div>
        )}

        <div className="dialog-actions">
          <button onClick={handleTest} disabled={testing || !apiKey}>
            {testing ? <Loader2 className="spin" size={14} /> : null}
            {t.testConn}
          </button>
          <button className="primary-button" onClick={handleSave} disabled={saving || !apiKey}>
            {saving ? <Loader2 className="spin" size={14} /> : null}
            {t.save}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------- Sub-components ---------- */

function OcrProgressBar({ progress, t }: { progress: OcrStatus, t: typeof translations["zh"] }) {
  const done = progress.processed + progress.failed;
  const pct = progress.total > 0 ? Math.round((done / progress.total) * 100) : 0;

  return (
    <div className="ocr-progress">
      <div className="ocr-progress-header">
        <span>
          <Loader2 className="spin" size={14} />
          {t.ocrProgress} {done} / {progress.total}
          {progress.failed > 0 && <span className="ocr-progress-fail">（{progress.failed} {t.ocrFail}）</span>}
        </span>
        <span>{pct}%</span>
      </div>
      <div className="ocr-progress-track">
        <div className="ocr-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      {progress.current_file && (
        <div className="ocr-progress-file">{progress.current_file}</div>
      )}
    </div>
  );
}

function Pager({
  page,
  pageCount,
  onChange
}: {
  page: number;
  pageCount: number;
  onChange: (page: number) => void;
}) {
  const pages = useMemo(() => {
    const result: (number | "…")[] = [];
    const delta = 2;
    const left = Math.max(2, page - delta);
    const right = Math.min(pageCount - 1, page + delta);

    result.push(1);
    if (left > 2) result.push("…");
    for (let i = left; i <= right; i++) result.push(i);
    if (right < pageCount - 1) result.push("…");
    if (pageCount > 1) result.push(pageCount);
    return result;
  }, [page, pageCount]);

  return (
    <footer className="pager">
      <button disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ‹
      </button>
      {pages.map((p, idx) =>
        p === "…" ? (
          <span key={`e${idx}`} style={{ color: "var(--text-muted)", padding: "0 4px" }}>
            …
          </span>
        ) : (
          <button
            key={p}
            className={p === page ? "active" : ""}
            onClick={() => onChange(p)}
          >
            {p}
          </button>
        )
      )}
      <button disabled={page >= pageCount} onClick={() => onChange(page + 1)}>
        ›
      </button>
    </footer>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
  allText
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  allText: string;
}) {
  return (
    <label className="field compact">
      <span>{label}</span>
      <select
        value={value}
        onChange={(event) => {
          onChange(event.target.value);
        }}
      >
        {options.map((option) => (
          <option key={option || "all"} value={option}>
            {option || allText}
          </option>
        ))}
      </select>
    </label>
  );
}

function Badge({ children, tone }: { children: ReactNode; tone: "good" | "bad" | "warn" | "accent" | "neutral" }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

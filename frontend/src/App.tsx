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
  Trash2,
  X
} from "lucide-react";
import {
  exportUrl,
  getOcrStatus,
  imageUrl,
  listItems,
  runAnalysis,
  runOcr,
  scan,
  thumbnailUrl,
  trashItem,
  updateItem
} from "./api";
import type { ItemStatus, OcrStatus, PicItem } from "./types";

const PAGE_SIZE = 24;

export function App() {
  const [directory, setDirectory] = useState("");
  const [recursive, setRecursive] = useState(true);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<PicItem[]>([]);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [selected, setSelected] = useState<PicItem | null>(null);
  const [editing, setEditing] = useState<PicItem | null>(null);
  const [editText, setEditText] = useState("");
  const [useOllama, setUseOllama] = useState(false);
  const [includeImage, setIncludeImage] = useState(false);
  const [ocrProgress, setOcrProgress] = useState<OcrStatus | null>(null);
  const ocrPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const params = useMemo(() => {
    const next = new URLSearchParams({
      page: String(page),
      page_size: String(PAGE_SIZE)
    });
    if (query.trim()) next.set("q", query.trim());
    if (status) next.set("status", status);
    if (category) next.set("category", category);
    if (suggestion) next.set("suggestion", suggestion);
    return next;
  }, [page, query, status, category, suggestion]);

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
          setMessage(`✓ OCR 完成：已处理 ${s.processed}，失败 ${s.failed}`);
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
  }, [stopOcrPoll, load]);

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
        setMessage("✓ 没有待处理的 OCR 项目");
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
      setMessage(`✓ ${label} 完成：${JSON.stringify(result)}`);
      await load();
    } catch (error) {
      setMessage(`✗ ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy("");
    }
  }

  async function copy(text: string) {
    await navigator.clipboard.writeText(text || "");
    setMessage("✓ 已复制 OCR 文本");
  }

  async function setItemStatus(item: PicItem, nextStatus: ItemStatus) {
    await runAction("更新状态", () => updateItem(item.id, { status: nextStatus }));
  }

  async function confirmTrash(item: PicItem) {
    const ok = window.confirm(`把 "${item.filename}" 移入系统回收站？`);
    if (!ok) return;
    await runAction("移入回收站", () => trashItem(item.id));
  }

  async function saveEdit() {
    if (!editing) return;
    await runAction("保存文字", () => updateItem(editing.id, { ocr_text: editText }));
    setEditing(null);
  }

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>ScreenTextOrganizer</h1>
          <p>本地截图文字整理、识别和审阅</p>
        </div>
        <div className="topbar-actions">
          <a className="icon-button text-button" href={exportUrl("json")} title="导出 JSON">
            <Download size={15} /> JSON
          </a>
          <a className="icon-button text-button" href={exportUrl("csv")} title="导出 CSV">
            <Download size={15} /> CSV
          </a>
        </div>
      </header>

      <section className="control-band">
        <div className="scan-row">
          <label className="field wide">
            <span>图片目录</span>
            <input
              value={directory}
              placeholder="例如 H:\\photos\\screenshots"
              onChange={(event) => setDirectory(event.target.value)}
            />
          </label>
          <label className="check-field">
            <input
              type="checkbox"
              checked={recursive}
              onChange={(event) => setRecursive(event.target.checked)}
            />
            递归
          </label>
          <button
            className="primary-button"
            disabled={!directory || !!busy}
            onClick={() => runAction("扫描", () => scan(directory, recursive))}
          >
            {busy === "扫描" ? <Loader2 className="spin" size={16} /> : <ImageIcon size={16} />}
            扫描
          </button>
          <button className="icon-button text-button" disabled={!!busy} onClick={handleOcr}>
            {busy === "OCR" ? <Loader2 className="spin" size={16} /> : <Play size={16} />}
            OCR
          </button>
          <button
            className="icon-button text-button"
            disabled={!!busy}
            onClick={() =>
              runAction("分析", () =>
                runAnalysis({ use_ollama: useOllama, include_image: includeImage })
              )
            }
          >
            {busy === "分析" ? <Loader2 className="spin" size={16} /> : <Archive size={16} />}
            分析
          </button>
        </div>

        <div className="filter-row">
          <label className="search-field">
            <Search size={16} />
            <input
              value={query}
              placeholder="搜索文件名、OCR 或摘要"
              onChange={(event) => {
                setPage(1);
                setQuery(event.target.value);
              }}
            />
          </label>
          <Select label="状态" value={status} onChange={setStatus} options={["", "unreviewed", "kept", "review", "trashed"]} />
          <Select label="建议" value={suggestion} onChange={setSuggestion} options={["", "keep", "review", "delete"]} />
          <label className="field compact">
            <span>分类</span>
            <input
              value={category}
              placeholder="frontend_interview"
              onChange={(event) => {
                setPage(1);
                setCategory(event.target.value);
              }}
            />
          </label>
          <label className="check-field">
            <input type="checkbox" checked={useOllama} onChange={(event) => setUseOllama(event.target.checked)} />
            Ollama
          </label>
          <label className="check-field">
            <input
              type="checkbox"
              checked={includeImage}
              disabled={!useOllama}
              onChange={(event) => setIncludeImage(event.target.checked)}
            />
            带图
          </label>
          <button className="icon-button" title="刷新" onClick={() => load()} disabled={!!busy}>
            <RefreshCw size={16} />
          </button>
        </div>
      </section>

      {ocrProgress && ocrProgress.total > 0 && <OcrProgressBar progress={ocrProgress} />}

      {message && <div className="message">{message}</div>}

      <section className="table-wrap">
        <div className="table-meta">
          <span>
            <Filter size={14} /> 共 {total} 条
          </span>
          <span>
            第 {page} / {pageCount} 页
          </span>
        </div>
        <table>
          <thead>
            <tr>
              <th>图片</th>
              <th>文件</th>
              <th>OCR 文字</th>
              <th>分析</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="empty-state">
                    <FolderSearch size={42} strokeWidth={1.2} />
                    <p>暂无数据 — 输入图片目录并点击「扫描」开始</p>
                  </div>
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id}>
                  <td className="thumb-cell">
                    <button className="thumb-button" onClick={() => setSelected(item)} title="放大图片">
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
                    {item.ocr_error ? <p className="error-text">{item.ocr_error}</p> : <p>{item.ocr_text || "未识别"}</p>}
                  </td>
                  <td className="analysis-cell">
                    <div className="badge-row">
                      <Badge tone={item.analysis_source === "ollama" ? "accent" : "neutral"}>
                        {item.analysis_source || "none"}
                      </Badge>
                      {item.keep_suggestion && <Badge tone={item.keep_suggestion === "keep" ? "good" : item.keep_suggestion === "delete" ? "bad" : "warn"}>{item.keep_suggestion}</Badge>}
                      {item.value_score && <Badge tone="neutral">{item.value_score}/5</Badge>}
                    </div>
                    <p>{item.summary || "未分析"}</p>
                    <div className="risk-line">
                      <span>过时 {item.staleness_risk || "-"}</span>
                      <span>失真 {item.distortion_risk || "-"}</span>
                    </div>
                    <div className="tags">{item.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
                  </td>
                  <td className="status-cell">
                    <Badge tone={item.status === "kept" ? "good" : item.status === "trashed" ? "bad" : item.status === "review" ? "warn" : "neutral"}>
                      {item.status}
                    </Badge>
                    {item.trash_error && <p className="error-text">{item.trash_error}</p>}
                  </td>
                  <td className="action-cell">
                    <button className="icon-button" title="查看原图" onClick={() => setSelected(item)}>
                      <Eye size={16} />
                    </button>
                    <button className="icon-button" title="复制 OCR" onClick={() => copy(item.ocr_text)}>
                      <Clipboard size={16} />
                    </button>
                    <button
                      className="icon-button"
                      title="编辑 OCR"
                      onClick={() => {
                        setEditing(item);
                        setEditText(item.ocr_text || "");
                      }}
                    >
                      <Pencil size={16} />
                    </button>
                    <button className="icon-button good" title="保留" onClick={() => setItemStatus(item, "kept")}>
                      <Check size={16} />
                    </button>
                    <button className="icon-button warn" title="待复核" onClick={() => setItemStatus(item, "review")}>
                      <Archive size={16} />
                    </button>
                    <button className="icon-button danger" title="移入回收站" onClick={() => confirmTrash(item)}>
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
              <button className="icon-button" onClick={() => setSelected(null)} title="关闭" aria-label="关闭预览">
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
              <strong>编辑 OCR 文本</strong>
              <button className="icon-button" onClick={() => setEditing(null)} title="关闭" aria-label="关闭编辑">
                <X size={18} />
              </button>
            </div>
            <textarea value={editText} onChange={(event) => setEditText(event.target.value)} />
            <div className="dialog-actions">
              <button onClick={() => setEditing(null)}>取消</button>
              <button className="primary-button" onClick={saveEdit}>
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

/* ---------- Sub-components ---------- */

function OcrProgressBar({ progress }: { progress: OcrStatus }) {
  const done = progress.processed + progress.failed;
  const pct = progress.total > 0 ? Math.round((done / progress.total) * 100) : 0;

  return (
    <div className="ocr-progress">
      <div className="ocr-progress-header">
        <span>
          <Loader2 className="spin" size={14} />
          OCR 处理中 — {done} / {progress.total}
          {progress.failed > 0 && <span className="ocr-progress-fail">（{progress.failed} 失败）</span>}
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
  options
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
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
            {option || "全部"}
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

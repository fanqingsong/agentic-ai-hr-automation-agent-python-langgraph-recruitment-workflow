/**
 * Batch import page (HR): drag & drop or select multiple CV files to import into the
 * candidate pool (decoupled from any job). After import, score all candidates against a
 * JD from the job detail page ("Refresh rankings").
 */

import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { batchAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';

const ACCEPT = '.pdf,.doc,.docx';
const ALLOWED_RE = /\.(pdf|doc|docx)$/i;

type UploadResult = {
  batch_id: string;
  summary: {
    total: number;
    successful: number;
    duplicates: number;
    failed: number;
    skipped: number;
  };
  skipped_files: string[];
  duplicate_files: {
    candidate_name?: string;
    source_folder?: string;
    relative_path?: string;
    existing_candidate_id?: string;
    existing_candidate_name?: string;
  }[];
};

/** Relative path within the picked/dropped folder (for source_folder + dedup display). */
function fileRelativePath(f: File): string {
  return (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name;
}

// ---- Recursive drag & drop of folders via the HTML5 Entries API (webkitGetAsEntry) ----

/** readEntries() returns results in batches; call repeatedly until it returns empty. */
function readAllEntries(reader: any): Promise<any[]> {
  return new Promise((resolve, reject) => {
    const all: any[] = [];
    const readBatch = () => {
      reader.readEntries((batch: any[]) => {
        if (batch.length === 0) {
          resolve(all);
        } else {
          all.push(...batch);
          readBatch();
        }
      }, reject);
    };
    readBatch();
  });
}

/** Recursively collect all files under a FileSystemEntry (file or directory). */
async function entryToFiles(entry: any): Promise<File[]> {
  if (!entry) return [];
  if (entry.isFile) {
    const file: File = await new Promise((res, rej) => entry.file(res, rej));
    // Attach the tree-relative path (entry.fullPath) so dedup/display show subfolders.
    try {
      Object.defineProperty(file, 'webkitRelativePath', {
        value: (entry.fullPath || file.name).replace(/^\//, ''),
        configurable: true,
      });
    } catch {
      /* some browsers disallow redefining; fall back to file.name */
    }
    return [file];
  }
  if (entry.isDirectory) {
    const entries = await readAllEntries(entry.createReader());
    const nested = await Promise.all(entries.map((e) => entryToFiles(e)));
    return nested.flat();
  }
  return [];
}

export function BatchPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [maxConcurrent, setMaxConcurrent] = useState(5);
  const [processing, setProcessing] = useState(false);
  const [uploadPhase, setUploadPhase] = useState<'idle' | 'uploading' | 'parsing'>('idle');
  const [progress, setProgress] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [importingCount, setImportingCount] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);
  const processingStartedAt = useRef<number | null>(null);

  useEffect(() => {
    if (!processing) {
      setUploadPhase('idle');
      setElapsedSec(0);
      processingStartedAt.current = null;
      return;
    }
    processingStartedAt.current = Date.now();
    const timer = window.setInterval(() => {
      if (processingStartedAt.current) {
        setElapsedSec(Math.floor((Date.now() - processingStartedAt.current) / 1000));
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [processing]);

  // React doesn't reliably pass through the non-standard `webkitdirectory` attribute.
  // Set it directly on the DOM node the moment it mounts (ref callback) so the picker
  // opens in folder (directory) mode.
  const attachFolderInput = (el: HTMLInputElement | null) => {
    folderInputRef.current = el;
    if (el) {
      el.setAttribute('webkitdirectory', '');
      el.setAttribute('directory', '');
      el.setAttribute('mozdirectory', '');
    }
  };

  const fileKey = (f: File) => `${(f as any).webkitRelativePath || f.name}:${f.size}`;

  const addFiles = (incoming: FileList | File[]) => {
    const list = Array.from(incoming);
    const valid = list.filter((f) => ALLOWED_RE.test(f.name));
    const rejected = list.length - valid.length;
    if (rejected > 0) {
      setError(`已忽略 ${rejected} 个不支持的文件（仅保留 PDF / DOC / DOCX）。`);
    } else {
      setError(null);
    }
    setFiles((prev) => {
      const seen = new Set(prev.map(fileKey));
      const merged = [...prev];
      for (const f of valid) {
        const key = fileKey(f);
        if (!seen.has(key)) {
          seen.add(key);
          merged.push(f);
        }
      }
      return merged;
    });
  };

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);

    const items = e.dataTransfer.items;
    // Prefer the Entries API so dropped folders are traversed recursively (incl. subfolders).
    if (items && items.length && typeof (items[0] as any).webkitGetAsEntry === 'function') {
      // Must grab entries synchronously before any await (DataTransfer is cleared afterwards).
      const entries = Array.from(items)
        .map((it) => (it as any).webkitGetAsEntry?.())
        .filter(Boolean);
      if (entries.length) {
        const collected = (await Promise.all(entries.map((en) => entryToFiles(en)))).flat();
        addFiles(collected);
        return;
      }
    }
    // Fallback: plain files (no directory recursion available)
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('请先选择至少一个简历文件。');
      return;
    }
    setError(null);
    setResult(null);
    setProcessing(true);
    setUploadPhase('uploading');
    setProgress(0);
    setImportingCount(files.length);
    const fileCount = files.length;
    // ~90s per CV for LLM extraction; allow headroom for large folders.
    const timeoutMs = Math.max(600_000, fileCount * 90_000);
    try {
      const form = new FormData();
      files.forEach((f) => form.append('files', f));
      files.forEach((f) => form.append('relative_paths', fileRelativePath(f)));
      form.append('max_concurrent', String(maxConcurrent));
      const res = await batchAPI.uploadBatch(form, {
        timeout: timeoutMs,
        onUploadProgress: (e) => {
          if (!e.total) return;
          const pct = Math.round((e.loaded / e.total) * 100);
          setProgress(pct);
          if (pct >= 100 || e.loaded >= e.total) setUploadPhase('parsing');
        },
      });
      const data = res.data;
      if (data.success && data.batch_id) {
        setResult(data);
        setFiles([]);
      } else {
        setError('服务器返回了非预期的响应。');
      }
    } catch (err: any) {
      const data = err.response?.data;
      const detail =
        (typeof data?.detail === 'string' && data.detail) ||
        (typeof data?.error === 'string' && data.error) ||
        (Array.isArray(data?.detail) && data.detail.map((d: any) => d.msg).join('; '));
      const isTimeout = err.code === 'ECONNABORTED';
      setError(
        isTimeout
          ? `导入超时（已等待 ${Math.floor(timeoutMs / 1000)} 秒）。后端可能仍在处理 ${fileCount} 份简历，请稍后刷新候选人列表查看结果。`
          : detail || err.message || '批量导入失败。',
      );
    } finally {
      setProcessing(false);
    }
  };

  const handleExportBatch = async () => {
    if (!result?.batch_id) return;
    setExporting(true);
    setExportError(null);
    try {
      const res = await batchAPI.export(result.batch_id);
      const blob = res.data as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `batch_${result.batch_id}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      setExportError(
        typeof detail === 'string'
          ? detail
          : result.summary.successful === 0 && (result.summary.duplicates ?? 0) > 0
            ? '本批次全部为重复简历，暂无可导出记录。请重新导入一次后再试导出。'
            : '导出失败，请稍后重试。',
      );
      console.error(e);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Batch Import (批量导入简历)</h1>
      <p className="text-gray-600 mb-6">
        上传多份简历导入候选人库。导入与岗位解耦：导入完成后，到某个岗位的详情页点「Refresh rankings」，
        即可用该 JD 对全库简历打分排序并生成评语，可切换不同 JD 分别打分。
      </p>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Upload CV files</CardTitle>
          <CardDescription>
            拖拽文件或整个文件夹到下方区域、点击选择多个文件，或用「选择文件夹」——均会
            <span className="font-medium">递归导入所有子文件夹</span>中的简历。支持 PDF / DOC / DOCX。
            系统按文件内容 hash 自动跳过已导入的重复简历，并记录简历所在父文件夹（如日期目录）。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={`flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center cursor-pointer transition-colors ${
              dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <p className="text-sm font-medium text-gray-700">拖拽简历或文件夹到这里，或点击选择文件</p>
            <p className="text-xs text-gray-500">PDF / DOC / DOCX，支持多选与子文件夹递归</p>
          </div>

          {/* Hidden inputs live OUTSIDE the drop area so their programmatic .click() does
              not bubble into the drop area's onClick (which would open the file picker). */}
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPT}
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.length) addFiles(e.target.files);
              e.target.value = '';
            }}
          />
          {/* Folder picker: webkitdirectory (set via ref callback) returns all files under
              the chosen folder recursively */}
          <input
            ref={attachFolderInput}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.length) addFiles(e.target.files);
              e.target.value = '';
            }}
          />

          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => inputRef.current?.click()}
              disabled={processing}
            >
              选择文件
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => folderInputRef.current?.click()}
              disabled={processing}
            >
              选择文件夹
            </Button>
          </div>

          {files.length > 0 && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <Label>已选择 {files.length} 个文件</Label>
                <button
                  type="button"
                  className="text-xs text-gray-500 hover:text-red-600"
                  onClick={() => setFiles([])}
                  disabled={processing}
                >
                  清空
                </button>
              </div>
              <ul className="max-h-48 overflow-auto divide-y divide-gray-100 rounded border border-gray-200">
                {files.map((f, idx) => (
                  <li key={fileKey(f)} className="flex items-center justify-between px-3 py-2 text-sm">
                    <span className="truncate mr-2" title={fileRelativePath(f)}>
                      {fileRelativePath(f)}
                    </span>
                    <span className="flex items-center gap-3 shrink-0">
                      <span className="text-xs text-gray-400">{(f.size / 1024).toFixed(0)} KB</span>
                      <button
                        type="button"
                        className="text-xs text-gray-400 hover:text-red-600"
                        onClick={() => removeFile(idx)}
                        disabled={processing}
                      >
                        移除
                      </button>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-4 space-y-2">
            <Label>Max concurrent (1–20)</Label>
            <Input
              type="number"
              min={1}
              max={20}
              value={maxConcurrent}
              onChange={(e) => setMaxConcurrent(parseInt(e.target.value, 10) || 5)}
              disabled={processing}
            />
            <p className="text-xs text-gray-500">同时解析的简历数量。批量抽取由 LLM 完成，导入可能需要较长时间。</p>
          </div>

          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
              {error}
            </div>
          )}

          {processing && uploadPhase === 'uploading' && progress > 0 && progress < 100 && (
            <div className="mt-4">
              <div className="h-2 w-full rounded bg-gray-200 overflow-hidden">
                <div className="h-full bg-blue-500 transition-all" style={{ width: `${progress}%` }} />
              </div>
              <p className="mt-1 text-xs text-gray-500">上传中 {progress}%</p>
            </div>
          )}

          {processing && uploadPhase === 'parsing' && (
            <div className="mt-4 rounded border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
              <p className="font-medium">服务器正在解析简历…</p>
              <p className="mt-1 text-xs text-blue-800">
                共 {importingCount} 份，并发 {maxConcurrent} 路 LLM 抽取，预计约 {Math.max(1, Math.ceil(importingCount / maxConcurrent))} 分钟。
                已等待 {elapsedSec} 秒 — 上传已完成，请勿关闭页面。
              </p>
              <div className="mt-2 h-1.5 w-full rounded bg-blue-200 overflow-hidden">
                <div className="h-full w-1/3 bg-blue-500 animate-pulse rounded" />
              </div>
            </div>
          )}

          <Button type="button" className="mt-4" onClick={handleUpload} disabled={processing || files.length === 0}>
            {processing
              ? uploadPhase === 'parsing'
                ? `解析中… (${elapsedSec}s)`
                : progress > 0 && progress < 100
                  ? `上传中… ${progress}%`
                  : '导入中…'
              : `导入 ${files.length || ''} 份简历`}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Import result</CardTitle>
            <CardDescription>Batch ID: {result.batch_id}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p>Total: {result.summary.total}</p>
            <p>Successful: {result.summary.successful}</p>
            {(result.summary.duplicates ?? 0) > 0 && (
              <p className="text-amber-700">
                Duplicates (已跳过重复): {result.summary.duplicates}
              </p>
            )}
            <p>Failed: {result.summary.failed}</p>
            {result.summary.skipped > 0 && (
              <p className="text-gray-500">
                Skipped (格式不支持): {result.summary.skipped}
                {result.skipped_files.length > 0 && (
                  <span className="block text-xs">{result.skipped_files.join(', ')}</span>
                )}
              </p>
            )}
            {(result.duplicate_files?.length ?? 0) > 0 && (
              <div className="mt-2 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                <p className="font-medium mb-1">重复文件（内容 hash 已存在，未重新导入）</p>
                <ul className="max-h-40 overflow-auto text-xs space-y-1">
                  {result.duplicate_files.map((d, i) => (
                    <li key={i}>
                      {d.relative_path || d.candidate_name}
                      {d.source_folder ? ` · 文件夹: ${d.source_folder}` : ''}
                      {d.existing_candidate_name
                        ? ` · 已有: ${d.existing_candidate_name}`
                        : d.existing_candidate_id
                          ? ` · ID: ${d.existing_candidate_id}`
                          : ''}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex flex-wrap gap-3 pt-2">
              <Button variant="outline" onClick={handleExportBatch} disabled={exporting}>
                {exporting ? 'Exporting...' : 'Export batch (CSV)'}
              </Button>
              <Button asChild>
                <Link to="/jobs">去岗位页按 JD 打分排序 →</Link>
              </Button>
            </div>
            {exportError && (
              <p className="text-sm text-red-600 pt-1">{exportError}</p>
            )}
            {(result.summary.successful === 0 && (result.summary.duplicates ?? 0) > 0) && (
              <p className="text-xs text-amber-700 pt-1">
                本批次未新增候选人（全部为重复）。导出 CSV 将包含已存在的对应候选人资料。
              </p>
            )}
            <p className="text-xs text-gray-500 pt-1">
              提示：打开一个岗位详情页，点「Refresh rankings」即可对包含本次导入在内的全库候选人打分排序。
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

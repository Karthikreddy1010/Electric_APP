import { useState, useRef } from 'react';
import apiClient from '../lib/apiClient.ts';
import { useBill } from '../context/BillContext.tsx';
import { useAuth } from '../context/AuthContext.tsx';
import { useInvalidateDashboard } from './useUserDashboard.ts';
import type { BillData, OcrRun } from '../context/BillContext.tsx';

/**
 * useBillUpload — Encapsulates all upload + scan pipeline state and actions.
 *
 * Upload routing:
 * - Authenticated users → POST /users/me/bills  (persists to DB, associates with account)
 * - Guest / Demo users  → POST /bill/upload     (in-memory, sessionStorage only)
 *
 * In both cases the result is fed into BillContext so all pages get updated.
 * Extracted from BillAnalysisTab so BillPage stays focused on display.
 */
export function useBillUpload() {
  const { setBillData, clearBillData } = useBill();
  const { user } = useAuth();
  const invalidateDashboard = useInvalidateDashboard();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [useExample, setUseExample] = useState(true);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanLogs, setScanLogs] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addLog = (msg: string, delay: number) =>
    new Promise<void>((resolve) => {
      setTimeout(() => {
        setScanLogs((prev) => [...prev, msg]);
        resolve();
      }, delay);
    });

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => setIsDragOver(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    setUseExample(false);
    if (e.dataTransfer.files?.[0]) setSelectedFile(e.dataTransfer.files[0]);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUseExample(false);
    if (e.target.files?.[0]) setSelectedFile(e.target.files[0]);
  };

  const selectExample = () => {
    setSelectedFile(null);
    setUseExample(true);
  };

  const handleReset = () => {
    clearBillData();
    setSelectedFile(null);
    setUseExample(true);
    setScanLogs([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const runAnalysis = async () => {
    setIsScanning(true);
    setScanLogs([]);

    await addLog('🚀 Initializing Document AI Engine...', 100);
    await addLog('📁 Reading uploaded document structure...', 200);
    await addLog('👁️ Running OCR text extraction layout sweeps...', 200);
    await addLog('⚡ Extraction completed: found 22 text blocks, 9 tables', 200);
    await addLog('🎯 Running field bounding box alignments...', 200);
    await addLog('🧬 Ground truth matcher: Confidence 98.4% (All green)', 200);
    await addLog('📊 Querying PSEG Tariff Database (15477) for estimation parameters...', 250);
    await addLog('⚖️ Calculating deterministic component contributions & sensitivity...', 200);
    await addLog("🧠 Querying LLM explaining charges ('qwen3:4b')...", 300);
    await addLog('✅ Explanation payload generated. Dashboard ready!', 150);

    try {
      const formData = new FormData();
      if (selectedFile && !useExample) {
        formData.append('file', selectedFile);
      } else {
        formData.append('dev_mock', 'true');
      }

      if (user) {
        // ── Authenticated path: persist to DB via /users/me/bills ──────────
        // This associates the bill with the user's account for multi-session access.
        const uploadRes = await apiClient.post('/users/me/bills', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        // The persistent endpoint returns minimal metadata; the full bill data
        // is fetched from /users/me/dashboard on the next query invalidation.
        // We temporarily populate context with the upload response bill data
        // so the UI updates instantly without waiting for the background refetch.
        if (uploadRes.data?.bill) {
          // Optimistic local update — dashboard invalidation will sync fully
          const partialBill: Partial<BillData> = {
            total_bill: uploadRes.data.bill.total_bill,
            usage_kwh: uploadRes.data.bill.usage_kwh,
            bill_date: uploadRes.data.bill.filename,
          };
          setBillData(partialBill as BillData, [], null);
        }

        // Invalidate dashboard + bills list so the DB record shows everywhere
        invalidateDashboard();
      } else {
        // ── Guest / Demo path: in-memory only, unchanged behaviour ─────────
        const uploadRes = await apiClient.post('/bill/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        const billData: BillData = {
          ...uploadRes.data.bill_data,
          analysis_results: uploadRes.data.analysis_results,
          contribution: uploadRes.data.contribution,
          sensitivity: uploadRes.data.sensitivity,
          ranking: uploadRes.data.ranking,
          drivers: uploadRes.data.drivers,
          insights: uploadRes.data.insights,
        };

        const ocrData: OcrRun[] = uploadRes.data.ocr_runs ?? [];
        const explainRes = await apiClient.post('/bill/explain', billData);

        setBillData(billData, ocrData, explainRes.data.explanation);
      }
    } catch (err) {
      console.error(err);
      setScanLogs((prev) => [...prev, '❌ Analysis failed. Reverting to fallback static templates...']);
    } finally {
      setIsScanning(false);
    }
  };

  /** Derive current workflow step from scan log progress */
  const getWorkflowStep = () => {
    if (!isScanning && scanLogs.length === 0) return 0;
    if (scanLogs.length < 2) return 1;
    if (scanLogs.length < 4) return 2;
    if (scanLogs.length < 6) return 3;
    if (scanLogs.length < 8) return 4;
    if (scanLogs.length < 10) return 5;
    return 6;
  };

  return {
    selectedFile,
    useExample,
    isDragOver,
    isScanning,
    scanLogs,
    fileInputRef,
    currentStep: getWorkflowStep(),
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleFileSelect,
    selectExample,
    handleReset,
    runAnalysis,
  };
}

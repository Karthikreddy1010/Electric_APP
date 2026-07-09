/**
 * Bill Analysis Page
 *
 * Architecture rule: Bill Analysis ingests.
 * This page owns: file upload, OCR pipeline, field validation, AI explanation,
 * bill history, and export.
 *
 * It does NOT own: sensitivity analysis, driver analysis, component breakdown,
 * or what-if simulation. Those live in Impact & Simulation.
 */
import {
  Upload, FileText, RefreshCw,
  Terminal, ShieldCheck, Play, Download
} from 'lucide-react';
import { useBill } from '../context/BillContext.tsx';
import { useBillUpload } from '../hooks/useBillUpload.ts';
import RecentBillsCard from '../components/shared/RecentBillsCard.tsx';
import { useNavigation } from '../context/NavigationContext.tsx';

// ─── Upload Interface ─────────────────────────────────────────────────────────

const UploadView = () => {
  const upload = useBillUpload();

  const WORKFLOW_STEPS = [
    { step: 1, label: 'Upload bill',       desc: 'Select file' },
    { step: 2, label: 'OCR extraction',    desc: 'Scan layout text' },
    { step: 3, label: 'Bill parsing',      desc: 'Match fields' },
    { step: 4, label: 'Component mapping', desc: 'Identify vectors' },
    { step: 5, label: 'Tariff matching',   desc: 'Est. tariff rates' },
    { step: 6, label: 'AI explanation',    desc: 'Generate report' },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500 pb-16">

      {/* Title */}
      <div>
        <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px]">
          AI utility bill ingestion
        </span>
        <h1 className="text-3xl font-bold text-text-primary tracking-tight mt-2 font-sans">
          Upload & explain electricity bill
        </h1>
        <p className="text-text-secondary text-sm mt-1">
          Analyze any PDF or scanned image bill. Our models extract line item fees, estimate hidden components from the tariff, and provide plain-language AI explanations.
        </p>
      </div>

      {/* Workflow Steps */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4 p-5 bg-bg-surface border border-border-hairline rounded-md shadow-sm">
        {WORKFLOW_STEPS.map((s) => {
          const isCompleted = upload.currentStep > s.step;
          const isActive = upload.currentStep === s.step;
          return (
            <div key={s.step} className="flex flex-col text-xs font-sans">
              <div className="flex items-center gap-2">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center font-bold border transition-colors ${
                  isCompleted ? 'bg-savings-green text-white border-savings-green'
                  : isActive   ? 'bg-primary-blue text-white border-primary-blue animate-pulse'
                  :              'bg-bg-primary text-text-secondary border-border-hairline'
                }`}>
                  {s.step}
                </div>
                <span className={`font-semibold ${isActive ? 'text-primary-blue font-bold' : 'text-text-primary'}`}>
                  {s.label}
                </span>
              </div>
              <span className="text-[10px] text-text-secondary mt-1 pl-8">{s.desc}</span>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Drop Zone + Actions */}
        <div className="lg:col-span-7 space-y-6">
          <div
            onDragOver={upload.handleDragOver}
            onDragLeave={upload.handleDragLeave}
            onDrop={upload.handleDrop}
            onClick={() => upload.fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-md p-8 text-center cursor-pointer transition-all duration-300 flex flex-col items-center justify-center min-h-[300px] relative overflow-hidden group bg-bg-surface ${
              upload.isDragOver
                ? 'border-primary-blue bg-primary-blue/5 shadow-inner'
                : 'border-border-hairline hover:border-primary-blue/50 hover:bg-bg-primary/50'
            }`}
          >
            <input
              type="file"
              ref={upload.fileInputRef}
              onChange={upload.handleFileSelect}
              accept=".pdf,.png,.jpg,.jpeg"
              className="hidden"
            />
            {upload.isScanning && (
              <div className="absolute inset-0 z-10 pointer-events-none">
                <div className="w-full h-0.5 bg-primary-blue/50 absolute left-0" style={{ animation: 'sweep 2.5s infinite linear' }} />
              </div>
            )}
            <div className="w-12 h-12 bg-primary-blue/10 text-primary-blue rounded-md flex items-center justify-center mb-4 border border-primary-blue/20">
              <Upload size={22} />
            </div>
            <h3 className="text-sm font-semibold text-text-primary">
              {upload.selectedFile ? upload.selectedFile.name : 'Drag and drop your electricity bill PDF here'}
            </h3>
            <p className="text-[10px] text-text-secondary mt-1 font-mono-numbers">Supports PDF, PNG, JPG, JPEG</p>
            <button type="button" className="mt-6 bg-bg-surface border border-border-hairline hover:border-text-secondary px-4 py-2 rounded-md text-xs font-semibold text-text-primary transition-all shadow-sm">
              Choose file
            </button>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={upload.runAnalysis}
              disabled={upload.isScanning || (!upload.selectedFile && !upload.useExample)}
              className="flex-1 bg-primary-blue text-white hover:bg-primary-blue/90 font-semibold px-6 py-3.5 rounded-md shadow-sm active:scale-[0.99] disabled:bg-bg-primary disabled:text-text-secondary disabled:border disabled:border-border-hairline disabled:pointer-events-none transition-all flex items-center justify-center gap-2 text-xs"
            >
              {upload.isScanning
                ? <><RefreshCw size={14} className="animate-spin" /> Extracting bill telemetry...</>
                : <><Play size={14} fill="currentColor" /> Analyze bill</>
              }
            </button>
            {!upload.useExample && (
              <button
                onClick={upload.selectExample}
                className="bg-bg-surface border border-border-hairline hover:bg-bg-primary text-text-primary font-semibold px-5 py-3.5 rounded-md text-xs transition-all shadow-sm"
              >
                Use sample bill
              </button>
            )}
          </div>
        </div>

        {/* OCR Processing Console */}
        <div className="lg:col-span-5 flex flex-col">
          <div className="panel-operational flex-1 flex flex-col justify-between min-h-[300px]">
            <div>
              <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider flex items-center gap-1.5 border-b border-border-hairline pb-3">
                <Terminal size={14} className="text-primary-blue" /> Processing telemetry logs
              </h3>
              <div className="mt-4 font-mono text-[10px] space-y-2 text-text-primary max-h-[220px] overflow-y-auto pr-1">
                {upload.scanLogs.map((log: string, idx: number) => (
                  <div key={idx} className="flex gap-2">
                    <span className="text-text-secondary shrink-0">&gt;</span>
                    <span>{log}</span>
                  </div>
                ))}
                {upload.isScanning && (
                  <div className="flex gap-2 text-primary-blue items-center">
                    <span className="shrink-0">&gt;</span>
                    <RefreshCw size={8} className="animate-spin" />
                    <span>Processing matrix pipelines...</span>
                  </div>
                )}
                {!upload.isScanning && upload.scanLogs.length === 0 && (
                  <div className="text-text-secondary italic">Awaiting document feed to launch analysis logs...</div>
                )}
              </div>
            </div>

            {/* Sample bill preview */}
            <div className="border-t border-border-hairline pt-4 mt-6">
              {upload.useExample && !upload.selectedFile && !upload.isScanning ? (
                <div className="bg-bg-primary border border-border-hairline rounded-md p-4 space-y-3">
                  <div className="flex justify-between items-start border-b border-border-hairline pb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-primary-blue text-white rounded-[4px] flex items-center justify-center font-bold text-xs">PS</div>
                      <div>
                        <h4 className="text-xs font-bold text-text-primary leading-tight">PSE&G</h4>
                        <p className="text-[8px] text-text-secondary leading-none">Public Service Electric & Gas</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[8px] text-text-secondary uppercase block">Bill Date</span>
                      <span className="text-xs font-semibold text-text-primary font-mono-numbers">2026-06-30</span>
                    </div>
                  </div>
                  <div className="space-y-1.5 font-mono-numbers text-[11px] border-t border-border-hairline pt-2">
                    <div className="flex justify-between"><span className="text-text-secondary font-sans">Supply:</span><span>$81.00</span></div>
                    <div className="flex justify-between"><span className="text-text-secondary font-sans">Delivery:</span><span>$41.25</span></div>
                    <div className="flex justify-between"><span className="text-text-secondary font-sans">Tax:</span><span>$8.41</span></div>
                    <div className="flex justify-between items-baseline border-t border-border-hairline pt-2 text-xs font-bold mt-1">
                      <span className="font-sans text-text-primary">Total Due:</span>
                      <span className="text-base text-primary-blue">$138.90</span>
                    </div>
                  </div>
                </div>
              ) : upload.selectedFile ? (
                <div className="border border-border-hairline bg-bg-primary rounded-md p-6 flex flex-col items-center justify-center text-center">
                  <FileText size={32} className="text-primary-blue mb-2" />
                  <h4 className="text-xs font-bold text-text-primary truncate max-w-[200px]">{upload.selectedFile.name}</h4>
                  <p className="text-[10px] text-text-secondary mt-1 font-mono-numbers">
                    {(upload.selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <div className="mt-3 bg-savings-green/10 text-savings-green border border-savings-green/20 px-2.5 py-1 rounded-[4px] text-[10px] font-bold flex items-center gap-1.5">
                    <ShieldCheck size={12} /> Ready for secure ingestion scan
                  </div>
                </div>
              ) : null}
              <div className="text-[8px] text-text-secondary font-medium text-center pt-4">
                Our secure parser complies with PII standards. No files are stored permanently.
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes sweep { 0% { top: 0%; } 50% { top: 100%; } 100% { top: 0%; } }
      `}</style>
    </div>
  );
};

// ─── Analysis View (bill loaded) ──────────────────────────────────────────────

const AnalysisView = () => {
  const { uploadedBill, ocrRuns, billExplanation } = useBill();
  const upload = useBillUpload();
  const navigate = useNavigation();

  if (!uploadedBill) return null;

  const handleExportJson = () => {
    const blob = new Blob([JSON.stringify(uploadedBill, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `electricai-bill-${uploadedBill.bill_date}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500 pb-16 font-sans">

      {/* Header bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-bg-surface p-5 rounded-md border border-border-hairline shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px]">
              {uploadedBill.utility} · ingestion complete
            </span>
            <span className="bg-savings-green/10 text-savings-green text-xs font-bold px-2.5 py-1 rounded-full flex items-center gap-1">
              <ShieldCheck size={12} /> Bill validated
            </span>
          </div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight mt-2">
            Bill ingestion results
          </h1>
          <p className="text-text-secondary text-xs mt-1">
            {uploadedBill.billing_period} · {uploadedBill.utility} · Rate schedule: {uploadedBill.rate_schedule}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('Impact & Simulation')}
            className="bg-primary-blue text-white hover:bg-primary-blue/90 px-4 py-2.5 rounded-md text-xs font-semibold transition-all shadow-sm flex items-center gap-2 border border-transparent"
          >
            View impact analysis →
          </button>
          <button
            onClick={upload.handleReset}
            className="bg-bg-surface hover:bg-bg-primary text-text-primary px-4 py-2.5 rounded-md text-xs font-semibold transition-all shadow-sm flex items-center gap-2 border border-border-hairline"
          >
            <Upload size={14} /> Upload another
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

        {/* LEFT COLUMN: Bill preview + OCR + AI explanation */}
        <div className="lg:col-span-4 space-y-8">

          {/* Bill Preview */}
          <div className="panel-operational space-y-4">
            <div className="flex items-center justify-between border-b border-border-hairline pb-3">
              <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
                <FileText size={14} /> Bill preview
              </h3>
              <span className="text-[10px] bg-bg-primary px-2 py-0.5 rounded font-mono font-bold text-text-primary border border-border-hairline">
                {uploadedBill.utility} {uploadedBill.rate_schedule}
              </span>
            </div>
            <div className="bg-bg-primary border border-border-hairline rounded-md p-4 space-y-3 font-mono-numbers text-xs">
              <div className="flex justify-between items-baseline border-b border-border-hairline pb-2">
                <span className="text-text-secondary font-sans">Usage (kWh)</span>
                <span className="text-base font-bold text-text-primary">{uploadedBill.usage_kwh} kWh</span>
              </div>
              <div className="flex justify-between items-baseline border-b border-border-hairline pb-2">
                <span className="text-text-secondary font-sans">Supply</span>
                <span className="font-semibold">${uploadedBill.supply_charge?.toFixed(2)}</span>
              </div>
              <div className="flex justify-between items-baseline border-b border-border-hairline pb-2">
                <span className="text-text-secondary font-sans">Delivery</span>
                <span className="font-semibold">${uploadedBill.delivery_charge?.toFixed(2)}</span>
              </div>
              <div className="flex justify-between items-baseline border-b border-border-hairline pb-2">
                <span className="text-text-secondary font-sans">Sales tax</span>
                <span className="font-semibold">${uploadedBill.tax?.toFixed(2)}</span>
              </div>
              <div className="flex justify-between items-baseline pt-2">
                <span className="font-bold text-text-primary font-sans">Total</span>
                <span className="text-lg font-bold text-primary-blue">${uploadedBill.total_bill?.toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* OCR Extraction Results */}
          <div className="panel-operational space-y-4 overflow-hidden">
            <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider flex items-center gap-1.5 border-b border-border-hairline pb-3">
              <Terminal size={14} className="text-primary-blue" /> OCR field validation
            </h3>
            <div className="overflow-x-auto max-h-[280px]">
              <table className="w-full text-left text-xs">
                <thead className="text-[10px] uppercase text-text-secondary border-b border-border-hairline sticky top-0 bg-bg-surface z-10">
                  <tr>
                    <th className="py-2">Field</th>
                    <th className="py-2">Extracted</th>
                    <th className="py-2 text-right">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-hairline font-mono-numbers text-text-primary">
                  {ocrRuns?.map((run, idx: number) => (
                    <tr key={idx} className="hover:bg-bg-primary/50 transition-colors">
                      <td className="py-2 font-bold text-[11px] capitalize font-sans">{run.field_name?.replace('_', ' ')}</td>
                      <td className="py-2 text-text-secondary truncate max-w-[110px]">{run.extracted_value}</td>
                      <td className="py-2 text-right font-bold">{(run.confidence * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* AI Explanation */}
          <div className="panel-operational space-y-4">
            <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider flex items-center gap-1.5 border-b border-border-hairline pb-3">
              <Terminal size={14} className="text-primary-blue" /> AI bill explanation
            </h3>
            <div className="text-xs text-text-primary space-y-3 max-h-[300px] overflow-y-auto leading-relaxed whitespace-pre-wrap font-medium pr-1">
              {billExplanation ? (
                <div dangerouslySetInnerHTML={{ __html: billExplanation.replace(/\n/g, '<br />') }} />
              ) : (
                <span className="italic text-text-secondary">Loading AI explanation...</span>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Bill history + Export */}
        <div className="lg:col-span-8 space-y-8">

          {/* Bill History */}
          <RecentBillsCard />

          {/* Export Panel */}
          <div className="panel-operational space-y-4">
            <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider flex items-center gap-1.5 border-b border-border-hairline pb-3">
              <Download size={14} className="text-primary-blue" /> Export bill data
            </h3>
            <p className="text-[11px] text-text-secondary font-semibold">
              Download your parsed bill data for use in external tools or record-keeping.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleExportJson}
                className="flex items-center gap-2 px-4 py-2.5 bg-bg-surface border border-border-hairline rounded-md text-xs font-semibold hover:bg-bg-primary transition-all shadow-sm"
              >
                <Download size={13} /> Export as JSON
              </button>
              <button
                onClick={() => {
                  const fields = ['bill_date', 'utility', 'usage_kwh', 'supply_charge', 'delivery_charge', 'tax', 'total_bill', 'effective_rate'];
                  const header = fields.join(',');
                  const row = fields.map(f => (uploadedBill as any)[f] ?? '').join(',');
                  const blob = new Blob([`${header}\n${row}`], { type: 'text/csv' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `electricai-bill-${uploadedBill.bill_date}.csv`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                className="flex items-center gap-2 px-4 py-2.5 bg-bg-surface border border-border-hairline rounded-md text-xs font-semibold hover:bg-bg-primary transition-all shadow-sm"
              >
                <Download size={13} /> Export as CSV
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

// ─── Page Shell ───────────────────────────────────────────────────────────────

const BillPage = () => {
  const { hasBill } = useBill();
  return hasBill ? <AnalysisView /> : <UploadView />;
};

export default BillPage;

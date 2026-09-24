/**
 * LedgerUpload.jsx - Digital Ledger CSV Ingestion Component
 * Allows users to upload a company transaction ledger CSV, load sample demo data,
 * and immediately trigger grounded AI analysis.
 */

import { useState } from 'react';
import {
  FileSpreadsheet, Upload, Download, CheckCircle, AlertTriangle,
  Loader2, ArrowRight, Sparkles, RefreshCw, Database, DollarSign,
  TrendingUp, TrendingDown, Clock, ShieldCheck
} from 'lucide-react';
import { uploadLedger, loadDemoLedger, getDemoLedgerUrl } from '../services/api';

const fmt = (n) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

export default function LedgerUpload({ onNavigate, onLedgerLoaded }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [runAnalysis, setRunAnalysis] = useState(true);
  const [replaceExisting, setReplaceExisting] = useState(true);
  const [dragActive, setDragActive] = useState(false);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = () => {
    setDragActive(false);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a CSV ledger file to upload.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await uploadLedger(file, replaceExisting, runAnalysis);
      setResult(data);
      if (onLedgerLoaded) onLedgerLoaded(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to upload ledger CSV.');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await loadDemoLedger(runAnalysis);
      setResult(data);
      if (onLedgerLoaded) onLedgerLoaded(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load demo ledger.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-blue-900/40 via-slate-800 to-indigo-900/40 border border-blue-500/20 rounded-2xl p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="bg-blue-500/20 text-blue-400 text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1 border border-blue-500/30">
                <FileSpreadsheet className="w-3.5 h-3.5" /> Digital Ledger Ingestion
              </span>
              <span className="text-xs text-slate-400">CSV Standard format</span>
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Load Company Digital Ledger
            </h2>
            <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
              Upload your company&apos;s transaction dataset or load the synthetic digital ledger.
              FinVisor&apos;s AI agent processes each line item to uncover anomalies, idle inventory,
              recurring/hidden charges, and constructs an evidence-grounded financial plan.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch gap-2.5">
            <a
              href={getDemoLedgerUrl()}
              download="company_digital_ledger_demo.csv"
              className="flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium px-4 py-2.5 rounded-xl border border-slate-600 transition-colors shadow-sm"
              title="Download pre-built synthetic ledger CSV"
            >
              <Download className="w-3.5 h-3.5 text-blue-400" />
              Download Sample CSV
            </a>
            <button
              onClick={handleLoadDemo}
              disabled={loading}
              className="flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-lg shadow-blue-500/20 transition-all disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              Load Pre-Built Demo Ledger
            </button>
          </div>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-400 flex items-center gap-2.5">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Upload Dropzone */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-4">
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer ${
              dragActive
                ? 'border-blue-500 bg-blue-500/10'
                : 'border-slate-700 bg-slate-800/60 hover:border-slate-600 hover:bg-slate-800'
            }`}
            onClick={() => document.getElementById('ledger-file-input').click()}
          >
            <input
              id="ledger-file-input"
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={handleFileChange}
            />
            <div className="w-14 h-14 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded-2xl flex items-center justify-center mx-auto mb-3.5 shadow-inner">
              <Upload className="w-6 h-6" />
            </div>

            {file ? (
              <div>
                <p className="font-semibold text-white text-base">{file.name}</p>
                <p className="text-xs text-slate-400 mt-1">
                  {(file.size / 1024).toFixed(1)} KB · Ready to ingest
                </p>
                <span className="inline-block mt-3 text-xs bg-blue-500/20 text-blue-300 border border-blue-500/30 px-3 py-1 rounded-full font-medium">
                  Click or drag another file to replace
                </span>
              </div>
            ) : (
              <div>
                <p className="font-semibold text-white text-base">
                  Choose a CSV Ledger or Drag &amp; Drop here
                </p>
                <p className="text-xs text-slate-400 mt-1.5 max-w-md mx-auto">
                  Accepts standard transaction columns: <code className="text-blue-300 font-mono">id, timestamp, amount, type, category, description, account_balance, tags</code>
                </p>
              </div>
            )}
          </div>

          {/* Upload Configuration */}
          <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-5 text-xs text-slate-300">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={runAnalysis}
                  onChange={(e) => setRunAnalysis(e.target.checked)}
                  className="rounded border-slate-600 text-blue-600 focus:ring-blue-500 w-4 h-4 bg-slate-900"
                />
                <span>Run Mistral AI Analysis immediately</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={replaceExisting}
                  onChange={(e) => setReplaceExisting(e.target.checked)}
                  className="rounded border-slate-600 text-blue-600 focus:ring-blue-500 w-4 h-4 bg-slate-900"
                />
                <span>Replace existing ledger</span>
              </label>
            </div>

            <button
              onClick={handleUpload}
              disabled={!file || loading}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition-all shadow-md ml-auto"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              {loading ? 'Ingesting Ledger…' : 'Ingest & Analyze CSV'}
            </button>
          </div>
        </div>

        {/* Ledger Guide & Format Spec */}
        <div className="bg-slate-800/70 border border-slate-700 rounded-2xl p-5 space-y-4">
          <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Digital Ledger Schema</span>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            FinVisor evaluates small business cash flow using debit and credit entries:
          </p>

          <div className="space-y-2.5 text-xs">
            <div className="bg-slate-900/80 border border-emerald-500/20 rounded-lg p-2.5">
              <span className="font-semibold text-emerald-400 block mb-0.5">🟢 Good Transactions</span>
              <p className="text-slate-300 text-[11px] leading-snug">
                Orders with subsequent customer sales within 7 days, indicating swift inventory turnover and profit.
              </p>
            </div>

            <div className="bg-slate-900/80 border border-rose-500/20 rounded-lg p-2.5">
              <span className="font-semibold text-rose-400 block mb-0.5">🔴 Bad Transactions (Idle Inventory)</span>
              <p className="text-slate-300 text-[11px] leading-snug">
                Stock orders sitting unfulfilled for 14+ days with zero matching sales, trapping working capital.
              </p>
            </div>

            <div className="bg-slate-900/80 border border-amber-500/20 rounded-lg p-2.5">
              <span className="font-semibold text-amber-400 block mb-0.5">⚠️ Anomalies &amp; Hidden Costs</span>
              <p className="text-slate-300 text-[11px] leading-snug">
                Duplicate payments, 2 AM off-hours debits, SaaS creep, and feast/famine revenue volatility.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Ingestion Success Result Card */}
      {result && (
        <div className="bg-slate-800 border border-emerald-500/30 rounded-2xl p-6 space-y-5 animate-fade-in shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-700 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <CheckCircle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">
                  Digital Ledger Ingested Successfully
                </h3>
                <p className="text-xs text-slate-400">
                  {result.filename} · Profile: <span className="capitalize text-slate-200 font-medium">{result.business_type}</span>
                </p>
              </div>
            </div>

            <span className="text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-3 py-1 rounded-full font-medium">
              {result.total_transactions?.toLocaleString()} Transactions Stored
            </span>
          </div>

          {/* Quick Metrics from Uploaded Ledger */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            <div className="bg-slate-900/80 border border-slate-700 rounded-xl p-3.5">
              <span className="text-xs text-slate-400 block mb-1">Total Revenue (Credits)</span>
              <p className="text-lg font-bold text-emerald-400">{fmt(result.total_revenue || 0)}</p>
              <span className="text-[11px] text-slate-500">{result.credit_count} sales entries</span>
            </div>

            <div className="bg-slate-900/80 border border-slate-700 rounded-xl p-3.5">
              <span className="text-xs text-slate-400 block mb-1">Total Expenses (Debits)</span>
              <p className="text-lg font-bold text-rose-400">{fmt(result.total_expenses || 0)}</p>
              <span className="text-[11px] text-slate-500">{result.debit_count} expense entries</span>
            </div>

            <div className="bg-slate-900/80 border border-slate-700 rounded-xl p-3.5">
              <span className="text-xs text-slate-400 block mb-1">Net Cash Flow</span>
              <p className={`text-lg font-bold ${(result.net_cash_flow || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {fmt(result.net_cash_flow || 0)}
              </p>
              <span className="text-[11px] text-slate-500">During ledger period</span>
            </div>

            <div className="bg-slate-900/80 border border-slate-700 rounded-xl p-3.5">
              <span className="text-xs text-slate-400 block mb-1">Analysis Status</span>
              <p className="text-lg font-bold text-blue-400">
                {result.report ? 'Grounded Plan Ready' : 'Ready'}
              </p>
              <span className="text-[11px] text-slate-500">Citing exact transaction IDs</span>
            </div>
          </div>

          {/* Navigation Action Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <p className="text-xs text-slate-400">
              The company&apos;s digital ledger is now loaded into the FinVisor engine.
            </p>

            <div className="flex flex-wrap items-center gap-2.5">
              <button
                onClick={() => onNavigate && onNavigate('transactions')}
                className="flex items-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs px-3.5 py-2 rounded-lg font-medium transition-colors"
              >
                <span>View Ledger Feed</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => onNavigate && onNavigate('anomalies')}
                className="flex items-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs px-3.5 py-2 rounded-lg font-medium transition-colors"
              >
                <span>View Detected Anomalies</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => onNavigate && onNavigate('report')}
                className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs px-4 py-2 rounded-lg font-semibold transition-colors shadow-md"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>View AI Financial Plan</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

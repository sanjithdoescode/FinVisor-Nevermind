/**
 * FinancialReport.jsx - AI-Generated Financial Health Report
 * Shows executive summary, analysis sections, action items, transaction evidence.
 */

import { useState, useEffect } from 'react';
import {
  FileText, RefreshCw, Download, CheckCircle, AlertTriangle,
  Clock, TrendingUp, Loader2, Shield, DollarSign, Activity, Sparkles
} from 'lucide-react';
import { getReport, generateReport } from '../services/api';

const URGENCY_CONFIG = {
  critical: { color: 'text-red-400',    bg: 'bg-red-500/10',    border: 'border-red-500/30',    label: 'Critical' },
  high:     { color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30', label: 'High' },
  medium:   { color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', label: 'Medium' },
  low:      { color: 'text-blue-400',   bg: 'bg-blue-500/10',   border: 'border-blue-500/30',   label: 'Low' },
};

const SCORE_COLOR = (score) => {
  if (score >= 80) return 'text-green-400';
  if (score >= 60) return 'text-yellow-400';
  return 'text-red-400';
};

const fmt = (n) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

function ScoreRing({ score }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';

  return (
    <div className="relative w-28 h-28 flex items-center justify-center">
      <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#1e293b" strokeWidth="8" />
        <circle
          cx="50" cy="50" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-bold ${SCORE_COLOR(score)}`}>{score}</span>
        <span className="text-xs text-slate-400">/100</span>
      </div>
    </div>
  );
}

export default function FinancialReport({ initialReport, onNavigate }) {
  const [report, setReport] = useState(initialReport || null);
  const [loading, setLoading] = useState(!initialReport);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (initialReport) {
      setReport(initialReport);
      setLoading(false);
      return;
    }
    let isMounted = true;
    const fetchReport = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getReport();
        if (isMounted && data) {
          setReport(data);
        }
      } catch (err) {
        // If no report found yet, generate it from the database
        try {
          const fresh = await generateReport();
          if (isMounted && fresh) setReport(fresh);
        } catch (genErr) {
          if (isMounted) setError(genErr.response?.data?.detail || 'Could not load financial report. Please ensure digital ledger is loaded.');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchReport();
    return () => { isMounted = false; };
  }, [initialReport]);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await generateReport();
      setReport(data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Analysis generation failed. Check API key and database.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    window.print();
  };

  const fmtTime = (iso) => {
    if (!iso) return 'Just now';
    return new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
  };

  return (
    <div className="space-y-6">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-white">AI Financial Report</h2>
          {report && (
            <span className="text-xs text-slate-400 flex items-center gap-1">
              <Clock className="w-3 h-3" /> Generated: {fmtTime(report.generatedAt)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm px-4 py-2 rounded-lg transition-colors"
          >
            <Download className="w-4 h-4" />
            Download PDF
          </button>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white text-sm px-4 py-2 rounded-lg transition-colors font-medium"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            {loading ? 'Analyzing…' : 'Generate Report'}
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-3 text-sm text-amber-400 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Loading overlay */}
      {loading && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-12 text-center">
          <Loader2 className="w-10 h-10 text-blue-400 animate-spin mx-auto mb-4" />
          <p className="text-slate-300 font-medium">AI is analyzing your financial data…</p>
          <p className="text-slate-400 text-sm mt-1">This usually takes 10–30 seconds</p>
        </div>
      )}

      {/* Report Content */}
      {report && !loading && (
        <div className="space-y-6">
          {/* Grounded Ledger Metrics Ribbon */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
              <span className="text-xs text-slate-400 block mb-1">Total Ledger Revenue</span>
              <p className="text-xl font-bold text-emerald-400">{fmt(report.total_revenue || 0)}</p>
              <span className="text-[11px] text-slate-500 capitalize">{report.business_type || 'Retail'} Business</span>
            </div>

            <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
              <span className="text-xs text-slate-400 block mb-1">Total Operating Expenses</span>
              <p className="text-xl font-bold text-rose-400">{fmt(report.total_expenses || 0)}</p>
              <span className="text-[11px] text-slate-500">{report.recurring_cost_count || 0} recurring costs</span>
            </div>

            <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
              <span className="text-xs text-slate-400 block mb-1">Net Cash Flow</span>
              <p className={`text-xl font-bold ${(report.net_profit || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {fmt(report.net_profit || 0)}
              </p>
              <span className="text-[11px] text-slate-500">Margin: {report.profit_margin_pct || 0}%</span>
            </div>

            <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
              <span className="text-xs text-slate-400 block mb-1">Cash Runway</span>
              <p className="text-xl font-bold text-blue-400">
                {report.cash_runway_days ?? 'N/A'} {typeof report.cash_runway_days === 'number' ? 'days' : ''}
              </p>
              <span className="text-[11px] text-slate-500">Burn: ₹{Math.round(report.burn_rate_daily || 0).toLocaleString()}/day</span>
            </div>
          </div>

          {/* Executive Summary Card */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
            <div className="flex flex-wrap items-start gap-6">
              {/* Score ring */}
              <div className="text-center">
                <ScoreRing score={report.overallScore ?? report.health_score ?? 70} />
                <p className="text-xs text-slate-400 mt-2">Health Score</p>
              </div>
              {/* Summary */}
              <div className="flex-1 min-w-52">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-blue-400" />
                    <h3 className="font-semibold text-slate-200">Executive Summary</h3>
                  </div>
                  {report.period_start && (
                    <span className="text-xs text-slate-400 bg-slate-900 border border-slate-700 px-2.5 py-1 rounded-full">
                      Ledger: {String(report.period_start).slice(0, 10)} → {String(report.period_end).slice(0, 10)} ({report.total_transactions} txns)
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">{report.executiveSummary}</p>
              </div>
            </div>
          </div>

          {/* Analysis Sections */}
          <div className="space-y-4">
            {report.sections.map((section, i) => (
              <div key={i} className="bg-slate-800 border border-slate-700 rounded-xl p-5">
                <h3 className="font-semibold text-slate-200 mb-3">{section.title}</h3>
                <p className="text-sm text-slate-300 leading-relaxed mb-3">{section.content}</p>
                {section.references.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs text-slate-500">Referenced transactions:</span>
                    {section.references.map(txId => (
                      <button
                        key={txId}
                        className="text-xs bg-blue-500/10 text-blue-300 border border-blue-500/20 px-2 py-0.5 rounded font-mono hover:bg-blue-500/20 transition-colors"
                        title={`View transaction ${txId}`}
                      >
                        {txId}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Action Items */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-4 h-4 text-green-400" />
              <h3 className="font-semibold text-slate-200">Recommended Action Plan</h3>
            </div>
            <div className="space-y-3">
              {report.actionItems.map((item) => {
                const urgency = URGENCY_CONFIG[item.urgency] || URGENCY_CONFIG.low;
                return (
                  <div
                    key={item.priority}
                    className={`flex items-start gap-4 bg-slate-900 border rounded-lg p-4 ${urgency.border}`}
                  >
                    <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${urgency.bg} ${urgency.color}`}>
                      {item.priority}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-200">{item.action}</p>
                      <p className={`text-xs mt-0.5 ${urgency.color}`}>Impact: {item.impact}</p>
                      {item.transaction_refs && item.transaction_refs.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 mt-2">
                          <span className="text-[11px] text-slate-500">Refs:</span>
                          {item.transaction_refs.map(ref => (
                            <span key={ref} className="text-[11px] bg-slate-800 text-blue-300 font-mono px-1.5 py-0.5 rounded border border-slate-700">
                              {ref}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      {item.potential_saving > 0 && (
                        <div className="text-right">
                          <span className="text-[10px] text-slate-400 block">Est. Impact</span>
                          <span className="text-xs font-bold text-emerald-400">+{fmt(item.potential_saving)}</span>
                        </div>
                      )}
                      <span className={`text-xs font-medium px-2 py-1 rounded border ${urgency.bg} ${urgency.color} ${urgency.border}`}>
                        {urgency.label}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

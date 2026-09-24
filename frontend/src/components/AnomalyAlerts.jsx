/**
 * AnomalyAlerts.jsx - Anomaly Detection Panel
 * Lists all detected anomalies with severity badges, evidence, and acknowledge button.
 */

import { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Filter, Eye, Loader2, ArrowRight } from 'lucide-react';
import { getAnomalies, acknowledgeAnomaly } from '../services/api';

const SEVERITY_CONFIG = {
  critical: { label: 'CRITICAL', bg: 'bg-red-500', text: 'text-red-400', border: 'border-red-500/30', badge: 'bg-red-500/10 text-red-400' },
  high:     { label: 'HIGH',     bg: 'bg-orange-500', text: 'text-orange-400', border: 'border-orange-500/30', badge: 'bg-orange-500/10 text-orange-400' },
  medium:   { label: 'MEDIUM',   bg: 'bg-yellow-500', text: 'text-yellow-400', border: 'border-yellow-500/30', badge: 'bg-yellow-500/10 text-yellow-400' },
  low:      { label: 'LOW',      bg: 'bg-blue-500', text: 'text-blue-400', border: 'border-blue-500/30', badge: 'bg-blue-500/10 text-blue-400' },
};

const SEVERITIES = ['All', 'critical', 'high', 'medium', 'low'];

const fmtAmt = (n) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);
const fmtDate = (iso) => {
  if (!iso) return '-';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
};

export default function AnomalyAlerts({ onNavigate }) {
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterSeverity, setFilterSeverity] = useState('All');
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const fetchAnomalies = async () => {
      setLoading(true);
      try {
        const data = await getAnomalies();
        if (isMounted && data && Array.isArray(data.anomalies)) {
          const norm = data.anomalies.map((a) => {
            const rawEv = a.evidence || '';
            const evidenceList = a.transaction_id
              ? [a.transaction_id]
              : (rawEv.match(/TXN-[A-F0-9]+/g) || []);
            return {
              id: a.id,
              type: a.type ? a.type.replace(/_/g, ' ').toUpperCase() : 'ANOMALY',
              severity: a.severity || 'medium',
              description: a.description,
              amount: a.metadata?.amount || a.metadata?.order_amount || 0,
              date: a.detected_at || new Date().toISOString(),
              evidence: evidenceList,
              recommendedAction: a.evidence || 'Verify vendor invoice and payment authorization.',
              acknowledged: false,
            };
          });
          setAnomalies(norm);
        }
      } catch (err) {
        console.warn('Could not load anomalies from API:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchAnomalies();
    return () => { isMounted = false; };
  }, []);

  const handleAcknowledge = async (id) => {
    try {
      await acknowledgeAnomaly(id);
    } catch (_) {}
    setAnomalies(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true } : a));
  };

  const filtered = anomalies.filter(a => {
    if (filterSeverity !== 'All' && a.severity !== filterSeverity) return false;
    return true;
  });

  const activeCount = anomalies.filter(a => !a.acknowledged).length;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-white">Anomaly Alerts</h2>
          {activeCount > 0 && (
            <span className="bg-red-500 text-white text-xs rounded-full px-2 py-0.5 font-bold animate-pulse">
              {activeCount} Active
            </span>
          )}
        </div>
        <p className="text-sm text-slate-400">{anomalies.filter(a => a.acknowledged).length} acknowledged · {activeCount} pending</p>
      </div>

      {/* Severity summary chips */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {(['critical', 'high', 'medium', 'low']).map(sev => {
          const count = anomalies.filter(a => a.severity === sev && !a.acknowledged).length;
          const cfg = SEVERITY_CONFIG[sev];
          return (
            <div key={sev} className={`bg-slate-800 border ${cfg.border} rounded-xl p-4 text-center`}>
              <p className={`text-2xl font-bold ${cfg.text}`}>{count}</p>
              <p className="text-xs text-slate-400 mt-1">{cfg.label}</p>
            </div>
          );
        })}
      </div>

      {/* Filter bar */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 flex items-center gap-3">
        <Filter className="w-4 h-4 text-slate-400" />
        <span className="text-sm text-slate-400">Filter by severity:</span>
        <div className="flex gap-2 flex-wrap">
          {SEVERITIES.map(sev => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className={`text-xs px-3 py-1 rounded-full border transition-colors font-medium ${
                filterSeverity === sev
                  ? 'bg-blue-600 border-blue-500 text-white'
                  : 'bg-slate-900 border-slate-600 text-slate-300 hover:border-slate-400'
              }`}
            >
              {sev === 'All' ? 'All' : SEVERITY_CONFIG[sev].label}
            </button>
          ))}
        </div>
      </div>

      {/* Anomaly Cards */}
      <div className="space-y-4">
        {filtered.length === 0 && (
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-12 text-center">
            <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-3" />
            <p className="text-slate-300 font-medium">All clear!</p>
            <p className="text-slate-400 text-sm mt-1">No anomalies match your current filter.</p>
          </div>
        )}

        {filtered.map((anomaly) => {
          const cfg = SEVERITY_CONFIG[anomaly.severity];
          const isExpanded = expandedId === anomaly.id;
          const isAcknowledged = anomaly.acknowledged;

          return (
            <div
              key={anomaly.id}
              className={`bg-slate-800 border rounded-xl overflow-hidden transition-all ${
                isAcknowledged
                  ? 'border-slate-700 opacity-60'
                  : `border-slate-700 hover:border-slate-600 border-l-4 border-l-current ${cfg.text}`
              }`}
            >
              {/* Main row */}
              <div className="p-5">
                <div className="flex items-start gap-4">
                  {/* Severity badge */}
                  <span className={`flex-shrink-0 mt-0.5 text-xs font-bold text-white px-2.5 py-1 rounded ${cfg.bg}`}>
                    {cfg.label}
                  </span>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-semibold text-slate-100">{anomaly.type}</p>
                      {isAcknowledged && (
                        <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded">Acknowledged</span>
                      )}
                    </div>
                    <p className="text-sm text-slate-400 mt-1 leading-relaxed">{anomaly.description}</p>

                    {/* Meta */}
                    <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-slate-500">
                      <span>Detected: {fmtDate(anomaly.date)}</span>
                      <span className={`font-semibold ${cfg.text}`}>Amount: {fmtAmt(anomaly.amount)}</span>
                    </div>

                    {/* Evidence */}
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                      <span className="text-xs text-slate-500">Evidence:</span>
                      {anomaly.evidence.map((txId, idx) => (
                        <span key={`${txId}-${idx}`} className="text-xs bg-slate-700 text-blue-300 px-2 py-0.5 rounded font-mono border border-blue-500/20">
                          {txId}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : anomaly.id)}
                      className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-700 rounded-lg transition-colors"
                      title="View recommended action"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    {!isAcknowledged && (
                      <button
                        onClick={() => handleAcknowledge(anomaly.id)}
                        className="flex items-center gap-1.5 text-xs bg-slate-700 hover:bg-green-600 text-slate-300 hover:text-white px-3 py-1.5 rounded-lg transition-colors font-medium"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        Acknowledge
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Expanded: Recommended Action */}
              {isExpanded && (
                <div className="border-t border-slate-700 bg-slate-900 px-5 py-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className={`w-4 h-4 flex-shrink-0 mt-0.5 ${cfg.text}`} />
                    <div>
                      <p className="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-1">Recommended Action</p>
                      <p className="text-sm text-slate-300 leading-relaxed">{anomaly.recommendedAction}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

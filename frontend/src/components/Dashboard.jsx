/**
 * Dashboard.jsx - Main KPI Dashboard
 * Shows KPI cards, cash flow chart, category breakdown, anomaly panel, live ticker.
 */

import { useMemo } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import {
  TrendingUp, TrendingDown, DollarSign, Activity,
  AlertTriangle, ArrowUpRight, ArrowDownRight,
  FileSpreadsheet, Sparkles, ArrowRight
} from 'lucide-react';

import {
  MOCK_SUMMARY, MOCK_CASHFLOW, MOCK_SPENDING_BY_CATEGORY, MOCK_ANOMALIES, MOCK_TRANSACTIONS
} from '../data/mockData';

// ── Helpers ──────────────────────────────────
const fmt = (n) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
const fmtSmall = (n) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);

const SEVERITY_COLORS = { critical: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-yellow-500', low: 'bg-blue-500' };

// ── KPI Card ─────────────────────────────────
function KPICard({ title, value, change, positive, icon: Icon, prefix = '$' }) {
  const isPositive = change >= 0;
  const trendColor = positive ? (isPositive ? 'text-green-400' : 'text-red-400') : (isPositive ? 'text-red-400' : 'text-green-400');
  const TrendIcon = isPositive ? ArrowUpRight : ArrowDownRight;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 hover:border-slate-600 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <p className="text-sm text-slate-400 font-medium">{title}</p>
        <div className="p-2 bg-slate-700 rounded-lg">
          <Icon className="w-4 h-4 text-blue-400" />
        </div>
      </div>
      <p className="text-2xl font-bold text-white mb-1">{value}</p>
      <div className={`flex items-center gap-1 text-sm ${trendColor}`}>
        <TrendIcon className="w-3.5 h-3.5" />
        <span>{Math.abs(change)}% vs last month</span>
      </div>
    </div>
  );
}

// ── Custom Tooltip ────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-sm shadow-xl">
      <p className="text-slate-300 font-medium mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: {fmt(p.value)}
        </p>
      ))}
    </div>
  );
}

// ── Live Transaction Ticker ───────────────────
function LiveTicker({ transactions }) {
  const items = transactions.length > 0 ? transactions : MOCK_TRANSACTIONS;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <div className="relative">
          <div className="w-2 h-2 bg-green-400 rounded-full" />
          <div className="absolute inset-0 w-2 h-2 bg-green-400 rounded-full animate-ping" />
        </div>
        <span className="text-sm font-medium text-slate-300">Live Transaction Feed</span>
      </div>
      <div className="flex gap-4 overflow-x-auto pb-1 scrollbar-thin">
        {items.slice(0, 8).map((tx, i) => (
          <div
            key={`${tx.id}-${i}`}
            className={`flex-shrink-0 bg-slate-900 border rounded-lg px-3 py-2 min-w-48 ${
              tx.anomalous ? 'border-orange-500/50' : 'border-slate-700'
            }`}
            style={{ animation: 'fadeIn 0.3s ease' }}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-400 truncate max-w-32">{tx.description.split(' - ')[0]}</span>
              {tx.anomalous && <AlertTriangle className="w-3 h-3 text-orange-400 flex-shrink-0" />}
            </div>
            <p className={`text-sm font-semibold ${tx.type === 'CREDIT' ? 'text-green-400' : 'text-red-400'}`}>
              {tx.type === 'CREDIT' ? '+' : '-'}{fmtSmall(tx.amount)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Dashboard ────────────────────────────
export default function Dashboard({ transactions, isConnected, onNavigate }) {
  const summary = MOCK_SUMMARY;
  const cashflow = MOCK_CASHFLOW;
  const categories = MOCK_SPENDING_BY_CATEGORY;
  const anomalies = MOCK_ANOMALIES.filter(a => !a.acknowledged);

  return (
    <div className="space-y-6">
      {/* Digital Ledger Quick Actions Banner */}
      <div className="bg-gradient-to-r from-blue-950/60 via-slate-800 to-indigo-950/60 border border-blue-500/20 rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 flex-shrink-0">
            <FileSpreadsheet className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-white font-semibold text-sm">Digital Ledger Pipeline</span>
              <span className="bg-blue-500/20 text-blue-300 text-[10px] px-2 py-0.5 rounded-full font-medium border border-blue-500/30">
                CSV Data Demo Ready
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-0.5">
              Load your company&apos;s digital ledger or ingest the pre-generated 2,560 synthetic transaction dataset for grounded AI analysis.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => onNavigate && onNavigate('ledger')}
            className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all shadow-md shadow-blue-500/20"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Load / Upload Ledger</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onNavigate && onNavigate('report')}
            className="flex items-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium px-3.5 py-2 rounded-xl transition-colors border border-slate-600"
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            <span>AI Financial Plan</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KPICard
          title="Total Revenue"
          value={fmt(summary.totalRevenue)}
          change={summary.revenueChange}
          positive={true}
          icon={TrendingUp}
        />
        <KPICard
          title="Total Expenses"
          value={fmt(summary.totalExpenses)}
          change={summary.expensesChange}
          positive={false}
          icon={DollarSign}
        />
        <KPICard
          title="Net Cash Flow"
          value={fmt(summary.netCashFlow)}
          change={summary.cashFlowChange}
          positive={true}
          icon={Activity}
        />
        <KPICard
          title="Profit Margin"
          value={`${summary.profitMargin}%`}
          change={summary.marginChange}
          positive={true}
          icon={TrendingDown}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Cash Flow Line Chart */}
        <div className="xl:col-span-2 bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Cash Flow Over Time</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={cashflow} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
              <Line type="monotone" dataKey="cashflow" stroke="#3b82f6" strokeWidth={2} dot={false} name="Balance" />
              <Line type="monotone" dataKey="revenue" stroke="#10b981" strokeWidth={1.5} dot={false} name="Revenue" />
              <Line type="monotone" dataKey="expenses" stroke="#ef4444" strokeWidth={1.5} dot={false} name="Expenses" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Spending by Category Bar Chart */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Spending by Category</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={categories} layout="vertical" margin={{ top: 0, right: 10, bottom: 0, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 10 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
              <YAxis type="category" dataKey="category" tick={{ fill: '#94a3b8', fontSize: 10 }} width={80} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="amount" name="Spent" radius={[0, 4, 4, 0]}>
                {categories.map((entry, index) => (
                  <rect key={`bar-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Anomaly Alerts Panel */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <h3 className="text-sm font-semibold text-slate-300">Recent Anomaly Alerts</h3>
            <span className="bg-red-500 text-white text-xs rounded-full px-2 py-0.5">{anomalies.length}</span>
          </div>
        </div>
        <div className="space-y-3">
          {anomalies.map((anomaly) => (
            <div
              key={anomaly.id}
              className="flex items-start gap-3 bg-slate-900 border border-slate-700 rounded-lg p-4 hover:border-slate-600 transition-colors"
            >
              <span className={`flex-shrink-0 text-xs font-bold text-white px-2 py-1 rounded ${SEVERITY_COLORS[anomaly.severity]}`}>
                {anomaly.severity.toUpperCase()}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-200">{anomaly.type}</p>
                <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{anomaly.description}</p>
                <div className="flex flex-wrap gap-1 mt-2">
                  {anomaly.evidence.map((txId, idx) => (
                    <span key={`${txId}-${idx}`} className="text-xs bg-slate-700 text-blue-300 px-1.5 py-0.5 rounded font-mono">{txId}</span>
                  ))}
                </div>
              </div>
              <p className="flex-shrink-0 text-sm font-semibold text-red-400">−{fmtSmall(anomaly.amount)}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Live Transaction Ticker */}
      <LiveTicker transactions={transactions} />
    </div>
  );
}

/**
 * WhatIfSimulator.jsx - Financial Scenario Simulator
 * Lets users model financial scenarios and see AI-projected outcomes.
 */

import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { FlaskConical, Play, Loader2, TrendingUp, TrendingDown, DollarSign, AlertTriangle } from 'lucide-react';
import { runSimulation } from '../services/api';
import { MOCK_SIMULATION_RESULT } from '../data/mockData';

const SCENARIO_TYPES = [
  { value: 'reduce_spending',       label: 'Reduce Spending',         desc: 'Model the impact of cutting costs in a specific category' },
  { value: 'increase_sales',        label: 'Increase Revenue',        desc: 'Project outcomes if sales/revenue grows by a percentage' },
  { value: 'eliminate_subscription',label: 'Eliminate Subscriptions', desc: 'Simulate removing SaaS subscriptions entirely' },
  { value: 'hire_employee',         label: 'Hire an Employee',        desc: 'Model the cost impact of adding headcount' },
];

const CATEGORIES = ['Subscriptions', 'Infrastructure', 'Marketing', 'Payroll', 'Rent', 'Utilities', 'Office', 'All Categories'];
const HORIZONS = [1, 3, 6, 12];

const fmtAmt = (n) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-sm shadow-xl">
      <p className="text-slate-300 font-medium mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: {fmtAmt(p.value)}
        </p>
      ))}
    </div>
  );
}

export default function WhatIfSimulator() {
  const [scenarioType, setScenarioType] = useState('reduce_spending');
  const [category, setCategory] = useState('Subscriptions');
  const [percentage, setPercentage] = useState(30);
  const [months, setMonths] = useState(6);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const selectedScenario = SCENARIO_TYPES.find(s => s.value === scenarioType);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runSimulation({ type: scenarioType, category, percentage, months });
      setResult(data);
    } catch {
      // Generate dynamic mock result based on inputs
      const saving = 1347 * (percentage / 100);
      const mockResult = {
        scenario: `${selectedScenario.label} — ${category} by ${percentage}%`,
        currentMonthly: 1347,
        projectedMonthly: 1347 * (1 - percentage / 100),
        monthlySaving: saving,
        annualSaving: saving * 12,
        projectedCashflow: Array.from({ length: months }, (_, i) => ({
          month: `Month ${i + 1}`,
          current: -5122,
          projected: -5122 + saving,
        })),
        aiCommentary: `Reducing ${category.toLowerCase()} by ${percentage}% over ${months} month(s) is projected to save ${fmtAmt(saving)}/month (${fmtAmt(saving * 12)}/year). Based on historical spending patterns, this adjustment appears ${percentage > 50 ? 'aggressive but achievable with careful planning' : 'realistic and achievable within 30 days'}. The cash flow deficit would ${saving > 5122 ? 'turn positive' : 'narrow significantly'}, improving your financial runway by approximately ${Math.round((saving * months) / 5000)} months.`,
      };
      setResult(mockResult);
      setError('Backend not connected — showing estimated projection.');
    } finally {
      setLoading(false);
    }
  };

  const isPositive = result && result.monthlySaving > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <FlaskConical className="w-5 h-5 text-blue-400" />
        <h2 className="text-lg font-semibold text-white">What-If Simulator</h2>
        <span className="text-xs text-slate-400 bg-slate-800 border border-slate-700 px-2 py-1 rounded">AI-Powered</span>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* ── Scenario Builder ── */}
        <div className="xl:col-span-2 space-y-5">
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Build Your Scenario</h3>

            {/* Scenario Type */}
            <div className="mb-4">
              <label className="block text-xs text-slate-400 mb-2 font-medium uppercase tracking-wide">Scenario Type</label>
              <div className="space-y-2">
                {SCENARIO_TYPES.map((s) => (
                  <button
                    key={s.value}
                    onClick={() => setScenarioType(s.value)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      scenarioType === s.value
                        ? 'border-blue-500 bg-blue-500/10 text-blue-300'
                        : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500'
                    }`}
                  >
                    <p className="text-sm font-medium">{s.label}</p>
                    <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{s.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Category */}
            <div className="mb-4">
              <label className="block text-xs text-slate-400 mb-2 font-medium uppercase tracking-wide">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 transition-colors"
              >
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            {/* Percentage */}
            <div className="mb-4">
              <label className="block text-xs text-slate-400 mb-2 font-medium uppercase tracking-wide">
                Change Magnitude: <span className="text-blue-400">{percentage}%</span>
              </label>
              <input
                type="range"
                min={5}
                max={100}
                step={5}
                value={percentage}
                onChange={(e) => setPercentage(Number(e.target.value))}
                className="w-full accent-blue-500"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>5%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>

            {/* Time Horizon */}
            <div className="mb-6">
              <label className="block text-xs text-slate-400 mb-2 font-medium uppercase tracking-wide">Time Horizon</label>
              <div className="grid grid-cols-4 gap-2">
                {HORIZONS.map(m => (
                  <button
                    key={m}
                    onClick={() => setMonths(m)}
                    className={`py-2 text-sm font-medium rounded-lg border transition-colors ${
                      months === m
                        ? 'border-blue-500 bg-blue-500/10 text-blue-300'
                        : 'border-slate-700 bg-slate-900 text-slate-400 hover:border-slate-500'
                    }`}
                  >
                    {m}mo
                  </button>
                ))}
              </div>
            </div>

            {/* Run button */}
            <button
              onClick={handleRun}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white font-medium py-3 rounded-lg transition-colors"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {loading ? 'Simulating…' : 'Run Simulation'}
            </button>
          </div>
        </div>

        {/* ── Results Panel ── */}
        <div className="xl:col-span-3 space-y-5">
          {/* Error banner */}
          {error && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-3 text-sm text-amber-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {!result && !loading && (
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-12 text-center">
              <FlaskConical className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400 font-medium">Configure a scenario and click Run Simulation</p>
              <p className="text-slate-500 text-sm mt-1">The AI will project financial outcomes based on your inputs</p>
            </div>
          )}

          {loading && (
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-12 text-center">
              <Loader2 className="w-10 h-10 text-blue-400 animate-spin mx-auto mb-4" />
              <p className="text-slate-300 font-medium">Running simulation…</p>
            </div>
          )}

          {result && !loading && (
            <>
              {/* Scenario label */}
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
                <p className="text-xs text-blue-400 uppercase tracking-wide font-semibold mb-1">Scenario</p>
                <p className="text-slate-200 font-medium">{result.scenario}</p>
              </div>

              {/* Before vs After KPIs */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-400 mb-1">Current Monthly</p>
                  <p className="text-xl font-bold text-red-400">{fmtAmt(result.currentMonthly)}</p>
                </div>
                <div className="bg-slate-800 border border-green-500/30 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-400 mb-1">Projected Monthly</p>
                  <p className="text-xl font-bold text-green-400">{fmtAmt(result.projectedMonthly)}</p>
                </div>
                <div className="bg-slate-800 border border-blue-500/30 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-400 mb-1">Annual Saving</p>
                  <div className="flex items-center justify-center gap-1">
                    {isPositive ? <TrendingUp className="w-4 h-4 text-green-400" /> : <TrendingDown className="w-4 h-4 text-red-400" />}
                    <p className={`text-xl font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                      {fmtAmt(result.annualSaving)}
                    </p>
                  </div>
                </div>
              </div>

              {/* Projected Cash Flow Chart */}
              <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-slate-300 mb-4">Current vs Projected Cash Flow</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={result.projectedCashflow} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                    <Bar dataKey="current" fill="#ef4444" name="Current" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="projected" fill="#10b981" name="Projected" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* AI Commentary */}
              <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                    <DollarSign className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <p className="text-xs text-blue-400 font-semibold uppercase tracking-wide mb-1">AI Commentary</p>
                    <p className="text-sm text-slate-300 leading-relaxed">{result.aiCommentary}</p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

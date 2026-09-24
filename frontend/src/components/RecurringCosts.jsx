/**
 * RecurringCosts.jsx - Recurring Cost Analysis
 * Table of recurring expenses, pie chart breakdown, hidden costs panel.
 */

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { RefreshCw, AlertTriangle, CheckCircle, TrendingDown } from 'lucide-react';
import { MOCK_RECURRING_COSTS, MOCK_RECURRING_SUMMARY } from '../data/mockData';

const fmtAmt = (n) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);

const PIE_DATA = [
  { name: 'Necessary Recurring', value: 714236, color: '#3b82f6' },
  { name: 'Suspicious Subscriptions', value: 5940, color: '#f59e0b' },
  { name: 'Hidden / Idle Costs', value: 7382, color: '#ef4444' },
  { name: 'One-Time Expenses', value: 145146, color: '#64748b' },
];

const TAG_CONFIG = {
  necessary:  { label: 'Necessary',  bg: 'bg-green-500/10',  text: 'text-green-400',  border: 'border-green-500/20',  icon: CheckCircle },
  suspicious: { label: 'Suspicious', bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/20', icon: AlertTriangle },
};

function CustomPieTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-sm shadow-xl">
      <p className="text-slate-200 font-medium">{payload[0].name}</p>
      <p style={{ color: payload[0].payload.color }} className="font-bold">
        {fmtAmt(payload[0].value)}/year
      </p>
      <p className="text-slate-400 text-xs">{payload[0].payload.percent?.toFixed(1)}% of total</p>
    </div>
  );
}

export default function RecurringCosts() {
  const costs = MOCK_RECURRING_COSTS;
  const summary = MOCK_RECURRING_SUMMARY;

  const suspiciousCosts = costs.filter(c => c.tag === 'suspicious');
  const totalSuspiciousAnnual = suspiciousCosts.reduce((sum, c) => sum + c.annualCost, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Recurring Cost Analysis</h2>
        <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2">
          <RefreshCw className="w-4 h-4 text-blue-400" />
          <span className="text-sm text-slate-300">Monthly Burden: <strong className="text-white">{fmtAmt(summary.totalMonthlyRecurring)}</strong></span>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <p className="text-xs text-slate-400 mb-1">Annual Recurring Burden</p>
          <p className="text-2xl font-bold text-white">{fmtAmt(summary.totalAnnualRecurring)}</p>
          <p className="text-xs text-slate-500 mt-1">10 recurring items</p>
        </div>
        <div className="bg-slate-800 border border-orange-500/30 rounded-xl p-5">
          <p className="text-xs text-slate-400 mb-1">Suspicious Subscriptions</p>
          <p className="text-2xl font-bold text-orange-400">{fmtAmt(totalSuspiciousAnnual)}/yr</p>
          <p className="text-xs text-orange-400/70 mt-1">{suspiciousCosts.length} subscriptions flagged</p>
        </div>
        <div className="bg-slate-800 border border-red-500/30 rounded-xl p-5">
          <p className="text-xs text-slate-400 mb-1">Potential Annual Savings</p>
          <p className="text-2xl font-bold text-green-400">+{fmtAmt(totalSuspiciousAnnual * 0.7)}</p>
          <p className="text-xs text-slate-500 mt-1">If suspicious items eliminated</p>
        </div>
      </div>

      {/* Chart + Hidden Costs */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* Pie Chart */}
        <div className="xl:col-span-2 bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Cost Breakdown</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={PIE_DATA}
                cx="50%"
                cy="50%"
                innerRadius={65}
                outerRadius={100}
                paddingAngle={3}
                dataKey="value"
              >
                {PIE_DATA.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomPieTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: 11, color: '#94a3b8' }}
                iconType="circle"
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Hidden Costs Panel */}
        <div className="xl:col-span-3 bg-slate-800 border border-red-500/30 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <h3 className="text-sm font-semibold text-red-400">Hidden Cost Spotlight</h3>
            <span className="text-xs text-slate-400">— small charges that add up</span>
          </div>
          <div className="space-y-3">
            {summary.hiddenCosts.map((hc, i) => (
              <div key={i} className="flex items-start justify-between bg-slate-900 border border-slate-700 rounded-lg p-3">
                <div>
                  <p className="text-sm font-medium text-slate-200">{hc.name}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{hc.note}</p>
                </div>
                <div className="text-right flex-shrink-0 ml-4">
                  <p className="text-sm font-semibold text-red-400">−{fmtAmt(hc.monthly)}/mo</p>
                  <p className="text-xs text-slate-500">{fmtAmt(hc.monthly * 12)}/yr</p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-3 border-t border-slate-700 flex items-center justify-between">
            <span className="text-sm text-slate-400">Total hidden cost</span>
            <span className="text-sm font-bold text-red-400">
              −{fmtAmt(summary.hiddenCosts.reduce((s, h) => s + h.monthly, 0) * 12)}/yr
            </span>
          </div>
        </div>
      </div>

      {/* Recurring Costs Table */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-700">
          <h3 className="text-sm font-semibold text-slate-300">Recurring Cost Register</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-900">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Merchant / Service</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Category</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Frequency</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Per Occurrence</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Annual Cost</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Tag</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {costs.map((cost) => {
                const tagCfg = TAG_CONFIG[cost.tag];
                const TagIcon = tagCfg.icon;
                return (
                  <tr key={cost.id} className={`hover:bg-slate-700/40 transition-colors ${cost.tag === 'suspicious' ? 'bg-orange-500/5' : ''}`}>
                    <td className="px-4 py-3 font-medium text-slate-200">{cost.merchant}</td>
                    <td className="px-4 py-3 text-slate-400">
                      <span className="text-xs bg-slate-700 px-2 py-0.5 rounded">{cost.category}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{cost.frequency}</td>
                    <td className="px-4 py-3 text-right text-slate-300">{fmtAmt(cost.amount)}</td>
                    <td className="px-4 py-3 text-right font-semibold text-slate-100">{fmtAmt(cost.annualCost)}</td>
                    <td className="px-4 py-3">
                      <span className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded border w-fit ${tagCfg.bg} ${tagCfg.text} ${tagCfg.border}`}>
                        <TagIcon className="w-3 h-3" />
                        {tagCfg.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">{cost.notes}</td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-slate-600 bg-slate-900">
                <td colSpan={4} className="px-4 py-3 text-sm font-semibold text-slate-300">Total Annual Recurring</td>
                <td className="px-4 py-3 text-right text-base font-bold text-white">
                  {fmtAmt(costs.reduce((s, c) => s + c.annualCost, 0))}
                </td>
                <td colSpan={2} />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}

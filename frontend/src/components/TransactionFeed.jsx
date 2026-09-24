/**
 * TransactionFeed.jsx - Live Transaction Table
 * Full paginated table with filters, search, and live indicators.
 */

import { useState, useMemo, useEffect, useRef } from 'react';
import { Search, Filter, ChevronLeft, ChevronRight, AlertTriangle, Zap, Loader2 } from 'lucide-react';
import { getTransactions } from '../services/api';
import { MOCK_TRANSACTIONS } from '../data/mockData';

const fmtAmt = (n) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

const fmtDate = (iso) => {
  if (!iso) return '-';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const PAGE_SIZE = 15;

const CATEGORIES = ['All', 'salaries', 'rent', 'logistics', 'marketing', 'utilities', 'subscriptions', 'pos_fees', 'inventory_purchase', 'sales', 'Revenue', 'Infrastructure'];
const TYPES = ['All', 'CREDIT', 'DEBIT'];

export default function TransactionFeed({ transactions = [], latestTx, isConnected }) {
  const [dbTransactions, setDbTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('All');
  const [filterCategory, setFilterCategory] = useState('All');
  const [page, setPage] = useState(1);
  const [flashId, setFlashId] = useState(null);
  const prevLatestRef = useRef(null);

  // Fetch digital ledger transactions from backend
  useEffect(() => {
    let isMounted = true;
    const fetchLedger = async () => {
      setLoading(true);
      try {
        const res = await getTransactions({ page: 1, page_size: 500 });
        if (isMounted && res && Array.isArray(res.items) && res.items.length > 0) {
          setDbTransactions(res.items);
        }
      } catch (err) {
        console.warn('Could not load ledger transactions:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchLedger();
    return () => { isMounted = false; };
  }, []);

  // Flash animation when new live tx arrives
  useEffect(() => {
    if (latestTx && latestTx.id !== prevLatestRef.current) {
      prevLatestRef.current = latestTx.id;
      setFlashId(latestTx.id);
      const t = setTimeout(() => setFlashId(null), 2000);
      return () => clearTimeout(t);
    }
  }, [latestTx]);

  // Merge database ledger transactions + live incoming feed
  const allTxns = useMemo(() => {
    const map = new Map();
    // 1. Digital ledger database rows
    const base = dbTransactions.length > 0 ? dbTransactions : MOCK_TRANSACTIONS;
    base.forEach((tx) => {
      map.set(tx.id, {
        ...tx,
        date: tx.date || tx.timestamp || new Date().toISOString(),
        balance: tx.balance ?? tx.account_balance ?? 0,
      });
    });
    // 2. Real / live feed takes precedence
    transactions.forEach((tx) => {
      if (tx && tx.id) {
        map.set(tx.id, {
          ...tx,
          date: tx.date || tx.timestamp || new Date().toISOString(),
          balance: tx.balance ?? tx.account_balance ?? 0,
        });
      }
    });
    const list = Array.from(map.values());
    return list.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  }, [dbTransactions, transactions]);

  const filtered = useMemo(() => {
    return allTxns.filter((tx) => {
      if (filterType !== 'All' && tx.type !== filterType) return false;
      if (filterCategory !== 'All' && tx.category !== filterCategory) return false;
      if (search && !tx.description.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [allTxns, filterType, filterCategory, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleSearchChange = (e) => { setSearch(e.target.value); setPage(1); };
  const handleTypeChange = (e) => { setFilterType(e.target.value); setPage(1); };
  const handleCategoryChange = (e) => { setFilterCategory(e.target.value); setPage(1); };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-white">All Transactions</h2>
          <span className="bg-slate-700 text-slate-300 text-xs px-2 py-1 rounded-full">{filtered.length} records</span>
          {isConnected && (
            <div className="flex items-center gap-1.5 bg-green-500/10 border border-green-500/30 rounded-full px-2 py-1">
              <Zap className="w-3 h-3 text-green-400" />
              <span className="text-xs text-green-400">Live</span>
            </div>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 flex flex-wrap gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-52">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search description..."
            value={search}
            onChange={handleSearchChange}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>

        {/* Type filter */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <select
            value={filterType}
            onChange={handleTypeChange}
            className="bg-slate-900 border border-slate-700 rounded-lg pl-8 pr-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 transition-colors appearance-none cursor-pointer"
          >
            {TYPES.map(t => <option key={t} value={t}>{t === 'All' ? 'All Types' : t}</option>)}
          </select>
        </div>

        {/* Category filter */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <select
            value={filterCategory}
            onChange={handleCategoryChange}
            className="bg-slate-900 border border-slate-700 rounded-lg pl-8 pr-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 transition-colors appearance-none cursor-pointer"
          >
            {CATEGORIES.map(c => <option key={c} value={c}>{c === 'All' ? 'All Categories' : c}</option>)}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-900">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">ID</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Date</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Description</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Category</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Type</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Amount</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Balance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {paginated.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-400">No transactions match your filters</td>
                </tr>
              ) : (
                paginated.map((tx, idx) => {
                  const isFlashing = flashId === tx.id;
                  const isAnomaly = tx.anomalous;
                  const rowKey = `${tx.id || 'tx'}-${(page - 1) * PAGE_SIZE + idx}`;
                  return (
                    <tr
                      key={rowKey}
                      className={`hover:bg-slate-700/50 transition-colors ${
                        isFlashing ? 'bg-blue-500/10' : ''
                      } ${isAnomaly ? 'border-l-2 border-l-orange-500' : ''}`}
                    >
                      <td className="px-4 py-3">
                        <code className="text-xs text-blue-300 bg-slate-900 px-1.5 py-0.5 rounded">{tx.id}</code>
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">{fmtDate(tx.date || tx.timestamp)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {isAnomaly && <AlertTriangle className="w-3.5 h-3.5 text-orange-400 flex-shrink-0" />}
                          <span className={`text-slate-200 ${isAnomaly ? 'text-orange-300' : ''}`}>
                            {tx.description}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded">{tx.category}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-bold px-2 py-1 rounded ${
                          tx.type === 'CREDIT'
                            ? 'bg-green-500/10 text-green-400 border border-green-500/30'
                            : 'bg-red-500/10 text-red-400 border border-red-500/30'
                        }`}>
                          {tx.type}
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-right font-semibold ${tx.type === 'CREDIT' ? 'text-green-400' : 'text-red-400'}`}>
                        {tx.type === 'CREDIT' ? '+' : '−'}{fmtAmt(tx.amount)}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-300">{fmtAmt(tx.balance ?? tx.account_balance ?? 0)}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="border-t border-slate-700 px-4 py-3 flex items-center justify-between">
          <p className="text-xs text-slate-400">
            Showing {Math.min((page - 1) * PAGE_SIZE + 1, filtered.length)}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded bg-slate-700 text-slate-300 hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs text-slate-300 px-2">Page {page} of {totalPages}</span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded bg-slate-700 text-slate-300 hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

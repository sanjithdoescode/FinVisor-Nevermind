/**
 * App.jsx - FinVisor 2.0 Root Component
 * Main app shell with sidebar navigation and routing.
 */

import { useState } from 'react';
import './App.css';
import {
  LayoutDashboard,
  ArrowLeftRight,
  AlertTriangle,
  RefreshCw,
  FileText,
  FlaskConical,
  TrendingUp,
  Wifi,
  WifiOff,
  ChevronLeft,
  ChevronRight,
  Shield,
} from 'lucide-react';

import Dashboard from './components/Dashboard';
import TransactionFeed from './components/TransactionFeed';
import AnomalyAlerts from './components/AnomalyAlerts';
import RecurringCosts from './components/RecurringCosts';
import FinancialReport from './components/FinancialReport';
import WhatIfSimulator from './components/WhatIfSimulator';
import { useLiveTransactions } from './hooks/useLiveTransactions';

const NAV_ITEMS = [
  { id: 'dashboard',    label: 'Dashboard',         icon: LayoutDashboard },
  { id: 'transactions', label: 'Transactions',       icon: ArrowLeftRight },
  { id: 'anomalies',    label: 'Anomaly Alerts',     icon: AlertTriangle },
  { id: 'recurring',    label: 'Recurring Costs',    icon: RefreshCw },
  { id: 'report',       label: 'AI Report',          icon: FileText },
  { id: 'simulator',    label: 'What-If Simulator',  icon: FlaskConical },
];

export default function App() {
  const [activeView, setActiveView] = useState('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { transactions, isConnected, latestTx } = useLiveTransactions();

  const renderView = () => {
    switch (activeView) {
      case 'dashboard':    return <Dashboard transactions={transactions} isConnected={isConnected} />;
      case 'transactions': return <TransactionFeed transactions={transactions} latestTx={latestTx} isConnected={isConnected} />;
      case 'anomalies':    return <AnomalyAlerts />;
      case 'recurring':    return <RecurringCosts />;
      case 'report':       return <FinancialReport />;
      case 'simulator':    return <WhatIfSimulator />;
      default:             return <Dashboard transactions={transactions} isConnected={isConnected} />;
    }
  };

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100 overflow-hidden">
      {/* ── Sidebar ── */}
      <aside
        className={`flex flex-col bg-slate-800 border-r border-slate-700 transition-all duration-300 ${
          sidebarCollapsed ? 'w-16' : 'w-64'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-slate-700">
          <div className="flex-shrink-0 w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-white" />
          </div>
          {!sidebarCollapsed && (
            <div>
              <span className="font-bold text-white tracking-tight">FinVisor</span>
              <span className="text-blue-400 font-bold"> 2.0</span>
              <p className="text-xs text-slate-400 leading-none mt-0.5">AI Financial Advisor</p>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 overflow-y-auto">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
            const isActive = activeView === id;
            return (
              <button
                key={id}
                onClick={() => setActiveView(id)}
                title={sidebarCollapsed ? label : undefined}
                className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-blue-600 text-white border-r-2 border-blue-400'
                    : 'text-slate-400 hover:bg-slate-700 hover:text-slate-100'
                }`}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {!sidebarCollapsed && <span>{label}</span>}
                {/* Anomaly badge */}
                {id === 'anomalies' && !sidebarCollapsed && (
                  <span className="ml-auto bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">3</span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Connection Status */}
        <div className={`px-4 py-3 border-t border-slate-700 flex items-center gap-2 ${sidebarCollapsed ? 'justify-center' : ''}`}>
          {isConnected ? (
            <>
              <div className="relative flex-shrink-0">
                <div className="w-2 h-2 bg-green-400 rounded-full" />
                <div className="absolute inset-0 w-2 h-2 bg-green-400 rounded-full animate-ping" />
              </div>
              {!sidebarCollapsed && <span className="text-xs text-green-400">Live Connected</span>}
            </>
          ) : (
            <>
              <div className="w-2 h-2 bg-amber-400 rounded-full flex-shrink-0" />
              {!sidebarCollapsed && <span className="text-xs text-amber-400">Demo Mode</span>}
            </>
          )}
        </div>

        {/* Collapse Toggle */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="flex items-center justify-center py-3 border-t border-slate-700 text-slate-400 hover:text-slate-100 hover:bg-slate-700 transition-colors"
        >
          {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </aside>

      {/* ── Main Content ── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="bg-slate-800 border-b border-slate-700 px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div>
            <h1 className="text-lg font-semibold text-white">
              {NAV_ITEMS.find(n => n.id === activeView)?.label ?? 'Dashboard'}
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
            </p>
          </div>

          <div className="flex items-center gap-4">
            {/* Live feed badge */}
            {isConnected ? (
              <div className="flex items-center gap-2 bg-green-500/10 border border-green-500/30 rounded-full px-3 py-1">
                <Wifi className="w-3.5 h-3.5 text-green-400" />
                <span className="text-xs text-green-400 font-medium">Live Feed Active</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 rounded-full px-3 py-1">
                <WifiOff className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-xs text-amber-400 font-medium">Demo Mode</span>
              </div>
            )}

            <div className="flex items-center gap-2 bg-slate-700 rounded-full px-3 py-1">
              <Shield className="w-3.5 h-3.5 text-blue-400" />
              <span className="text-xs text-slate-300 font-medium">FinVisor AI</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {renderView()}
        </div>
      </main>
    </div>
  );
}

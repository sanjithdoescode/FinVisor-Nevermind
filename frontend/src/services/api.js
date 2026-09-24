/**
 * FinVisor 2.0 - API Service Layer
 * Handles all HTTP requests to the FastAPI backend at http://localhost:8000
 */

import axios from 'axios';

const BASE_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000';

// Configure axios defaults
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─────────────────────────────────────────────
// Transactions
// ─────────────────────────────────────────────

/** Fetch all transactions with optional filters */
export const getTransactions = async (params = {}) => {
  const response = await api.get('/transactions', { params });
  return response.data;
};

/** Fetch a single transaction by ID */
export const getTransaction = async (id) => {
  const response = await api.get(`/transactions/${id}`);
  return response.data;
};

// ─────────────────────────────────────────────
// Anomalies
// ─────────────────────────────────────────────

/** Fetch all detected anomalies */
export const getAnomalies = async () => {
  const response = await api.get('/anomalies');
  return response.data;
};

/** Acknowledge (dismiss) an anomaly */
export const acknowledgeAnomaly = async (id) => {
  const response = await api.post(`/anomalies/${id}/acknowledge`);
  return response.data;
};

// ─────────────────────────────────────────────
// Dashboard / Summary
// ─────────────────────────────────────────────

/** Fetch dashboard KPI summary */
export const getSummary = async () => {
  const response = await api.get('/summary');
  return response.data;
};

/** Fetch cash flow time-series data */
export const getCashFlow = async (period = '30d') => {
  const response = await api.get('/cashflow', { params: { period } });
  return response.data;
};
export const getCashflow = getCashFlow;

/** Fetch spending by category */
export const getSpendingByCategory = async () => {
  const response = await api.get('/spending-by-category');
  return response.data;
};

// ─────────────────────────────────────────────
// Recurring Costs
// ─────────────────────────────────────────────

/** Fetch recurring costs analysis */
export const getRecurringCosts = async () => {
  const response = await api.get('/recurring-costs');
  return response.data;
};

// ─────────────────────────────────────────────
// AI Report
// ─────────────────────────────────────────────

/** Trigger AI financial report generation */
export const generateReport = async () => {
  const response = await api.post('/analyze');
  return response.data;
};

/** Fetch last generated report */
export const getReport = async () => {
  const response = await api.get('/report');
  return response.data;
};

// ─────────────────────────────────────────────
// What-If Simulator
// ─────────────────────────────────────────────

/**
 * Run a what-if scenario simulation
 * @param {Object} scenario - { type, category, percentage, months }
 */
export const runSimulation = async (scenario) => {
  const response = await api.post('/simulate', scenario);
  return response.data;
};

// ─────────────────────────────────────────────
// Digital Ledger (CSV)
// ─────────────────────────────────────────────

/** Upload a custom company digital ledger CSV file */
export const uploadLedger = async (file, replaceAll = true, runAnalysis = true) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/upload-ledger?replace_all=${replaceAll}&run_analysis=${runAnalysis}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/** Load the pre-built synthetic company digital ledger */
export const loadDemoLedger = async (runAnalysis = true) => {
  const response = await api.post(`/load-demo-ledger?run_analysis=${runAnalysis}`);
  return response.data;
};

/** URL to download the demo digital ledger CSV */
export const getDemoLedgerUrl = () => `${BASE_URL}/demo-ledger`;

// ─────────────────────────────────────────────
// WebSocket Manager
// ─────────────────────────────────────────────

/**
 * Creates and manages a WebSocket connection to the live transaction feed.
 * Returns a controller object with { socket, close }.
 */
export const createTransactionWebSocket = (onMessage, onOpen, onClose, onError) => {
  let ws = null;
  let reconnectTimer = null;
  let isClosed = false;

  const handlePageHide = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  const handlePageShow = (event) => {
    if (event.persisted && !isClosed) {
      if (!ws || ws.readyState === WebSocket.CLOSED) {
        connect();
      }
    }
  };

  if (typeof window !== 'undefined') {
    window.addEventListener('pagehide', handlePageHide);
    window.addEventListener('pageshow', handlePageShow);
  }

  const connect = () => {
    if (isClosed) return;
    try {
      ws = new WebSocket(`${WS_URL}/ws/transactions`);

      ws.onopen = () => {
        if (!isClosed && onOpen) onOpen();
      };

      ws.onmessage = (event) => {
        if (isClosed) return;
        try {
          const data = JSON.parse(event.data);
          if (onMessage) onMessage(data);
        } catch (e) {
          console.warn('WS message parse error:', e);
        }
      };

      ws.onclose = () => {
        if (!isClosed && onClose) onClose();
        // Auto-reconnect unless explicitly closed or page is frozen
        if (!isClosed && (typeof document === 'undefined' || document.visibilityState !== 'hidden')) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };

      ws.onerror = (err) => {
        if (!isClosed && onError) onError(err);
      };
    } catch (e) {
      console.warn('WebSocket connection failed:', e);
      if (!isClosed && (typeof document === 'undefined' || document.visibilityState !== 'hidden')) {
        reconnectTimer = setTimeout(connect, 3000);
      }
    }
  };

  connect();

  return {
    close: () => {
      isClosed = true;
      if (typeof window !== 'undefined') {
        window.removeEventListener('pagehide', handlePageHide);
        window.removeEventListener('pageshow', handlePageShow);
      }
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (ws) {
        ws.onopen = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null;

        if (ws.readyState === WebSocket.OPEN) {
          try {
            ws.close(1000, 'Normal Closure');
          } catch (_) {}
        } else if (ws.readyState === WebSocket.CONNECTING) {
          // Defer closing until open to prevent browser "closed before connection is established" warning
          const pendingWs = ws;
          pendingWs.onopen = () => {
            try {
              pendingWs.close(1000, 'Normal Closure');
            } catch (_) {}
          };
          pendingWs.onerror = () => {};
        }
        ws = null;
      }
    },
    get readyState() {
      return ws ? ws.readyState : (typeof WebSocket !== 'undefined' ? WebSocket.CLOSED : 3);
    },
  };
};

export default api;

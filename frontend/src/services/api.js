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

  const connect = () => {
    try {
      ws = new WebSocket(`${WS_URL}/ws/transactions`);

      ws.onopen = () => {
        if (onOpen) onOpen();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (onMessage) onMessage(data);
        } catch (e) {
          console.warn('WS message parse error:', e);
        }
      };

      ws.onclose = () => {
        if (onClose) onClose();
        // Auto-reconnect unless explicitly closed
        if (!isClosed) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };

      ws.onerror = (err) => {
        if (onError) onError(err);
      };
    } catch (e) {
      console.warn('WebSocket connection failed:', e);
      if (!isClosed) {
        reconnectTimer = setTimeout(connect, 3000);
      }
    }
  };

  connect();

  return {
    close: () => {
      isClosed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    },
    get readyState() {
      return ws ? ws.readyState : WebSocket.CLOSED;
    },
  };
};

export default api;

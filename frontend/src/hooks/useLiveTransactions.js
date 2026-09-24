/**
 * useLiveTransactions - Custom React hook
 * Manages a WebSocket connection to the live transaction feed.
 * - Auto-reconnects on disconnect (every 3 seconds)
 * - Maintains a rolling buffer of the last 50 live transactions
 * - Exposes connection status
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { createTransactionWebSocket } from '../services/api';
import { MOCK_TRANSACTIONS } from '../data/mockData';

const BUFFER_SIZE = 50;
const WS_URL = 'ws://localhost:8000/ws/transactions';

export function useLiveTransactions() {
  const [transactions, setTransactions] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [latestTx, setLatestTx] = useState(null);
  const wsController = useRef(null);
  const mockTimerRef = useRef(null);
  const mockIndexRef = useRef(0);

  // ── Push a new transaction into the rolling buffer ──
  const pushTransaction = useCallback((tx) => {
    if (!tx || !tx.id) return;
    const normalized = {
      ...tx,
      date: tx.date || tx.timestamp || new Date().toISOString(),
      balance: tx.balance ?? tx.account_balance ?? 0,
    };
    setLatestTx(normalized);
    setTransactions((prev) => {
      const filtered = prev.filter((t) => t.id !== normalized.id);
      return [normalized, ...filtered].slice(0, BUFFER_SIZE);
    });
  }, []);

  // ── Start demo mock feed when backend is unavailable ──
  const startMockFeed = useCallback(() => {
    if (mockTimerRef.current) return;
    mockTimerRef.current = setInterval(() => {
      const base = MOCK_TRANSACTIONS[mockIndexRef.current % MOCK_TRANSACTIONS.length];
      const tx = {
        ...base,
        id: `MOCK-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
        date: new Date().toISOString(),
      };
      pushTransaction(tx);
      mockIndexRef.current += 1;
    }, 3000);
  }, [pushTransaction]);

  const stopMockFeed = useCallback(() => {
    if (mockTimerRef.current) {
      clearInterval(mockTimerRef.current);
      mockTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    let mockFallbackTimer = null;

    // Try real WebSocket first
    wsController.current = createTransactionWebSocket(
      (data) => {
        // Handle both single tx and batch
        if (Array.isArray(data)) {
          data.forEach(pushTransaction);
        } else if (data && data.type !== 'heartbeat') {
          pushTransaction(data);
        }
      },
      () => {
        // onOpen
        setIsConnected(true);
        if (mockFallbackTimer) clearTimeout(mockFallbackTimer);
        stopMockFeed();
      },
      () => {
        // onClose
        setIsConnected(false);
        startMockFeed();
      },
      () => {
        // onError - switch to mock mode
        setIsConnected(false);
        startMockFeed();
      }
    );

    // Give real connection 1.5s before falling back to mock feed
    mockFallbackTimer = setTimeout(() => {
      if (!wsController.current || wsController.current.readyState !== 1) {
        startMockFeed();
      }
    }, 1500);

    return () => {
      if (mockFallbackTimer) clearTimeout(mockFallbackTimer);
      if (wsController.current) wsController.current.close();
      stopMockFeed();
    };
  }, [pushTransaction, startMockFeed, stopMockFeed]);

  return { transactions, isConnected, latestTx };
}

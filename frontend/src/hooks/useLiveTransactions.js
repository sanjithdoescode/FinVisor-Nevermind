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
    setLatestTx(tx);
    setTransactions((prev) => {
      const updated = [tx, ...prev];
      return updated.slice(0, BUFFER_SIZE);
    });
  }, []);

  // ── Start demo mock feed when backend is unavailable ──
  const startMockFeed = useCallback(() => {
    mockTimerRef.current = setInterval(() => {
      const tx = { ...MOCK_TRANSACTIONS[mockIndexRef.current % MOCK_TRANSACTIONS.length] };
      tx.id = `LIVE-${Date.now()}`;
      tx.date = new Date().toISOString();
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
    let useMock = false;

    // Try real WebSocket first
    wsController.current = createTransactionWebSocket(
      (data) => {
        // Handle both single tx and batch
        if (Array.isArray(data)) {
          data.forEach(pushTransaction);
        } else {
          pushTransaction(data);
        }
      },
      () => {
        // onOpen
        setIsConnected(true);
        stopMockFeed();
        useMock = false;
      },
      () => {
        // onClose
        setIsConnected(false);
        // Fall back to mock if not already running
        if (!mockTimerRef.current) {
          useMock = true;
          startMockFeed();
        }
      },
      () => {
        // onError - switch to mock mode
        setIsConnected(false);
        if (!mockTimerRef.current) {
          useMock = true;
          startMockFeed();
        }
      }
    );

    // Start mock immediately; will be stopped if WS connects
    startMockFeed();

    return () => {
      if (wsController.current) wsController.current.close();
      stopMockFeed();
    };
  }, [pushTransaction, startMockFeed, stopMockFeed]);

  return { transactions, isConnected, latestTx };
}

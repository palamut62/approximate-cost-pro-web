"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api from '@/lib/api';

interface LLMUsageData {
  provider: string;
  usage: number | null;
  usage_monthly: number | null;
  usage_daily: number | null;
  usage_weekly: number | null;
  total_credits: number | null;
  total_usage: number | null;
  remaining: number | null;
  is_low_balance: boolean;
  has_credits: boolean;
}

interface LLMUsageContextType {
  usageData: LLMUsageData;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

const LLMUsageContext = createContext<LLMUsageContextType | undefined>(undefined);

export function LLMUsageProvider({ children }: { children: ReactNode }) {
  const [usageData, setUsageData] = useState<LLMUsageData>({
    provider: "OpenRouter",
    usage: null,
    usage_monthly: null,
    usage_daily: null,
    usage_weekly: null,
    total_credits: null,
    total_usage: null,
    remaining: null,
    is_low_balance: false,
    has_credits: false,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsage = async () => {
    try {
      const response = await api.get('/usage/llm');
      setUsageData(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch LLM usage:', err);
      setError('Failed to fetch usage data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsage();

    // Poll every 5 minutes
    const interval = setInterval(fetchUsage, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <LLMUsageContext.Provider value={{ usageData, loading, error, refetch: fetchUsage }}>
      {children}
    </LLMUsageContext.Provider>
  );
}

export function useLLMUsage() {
  const context = useContext(LLMUsageContext);
  if (context === undefined) {
    throw new Error('useLLMUsage must be used within a LLMUsageProvider');
  }
  return context;
}

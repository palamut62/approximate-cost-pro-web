"use client";

import { useLLMUsage } from '@/context/LLMUsageContext';

export default function LLMUsageWarning() {
  const { usageData, loading } = useLLMUsage();

  if (loading || !usageData.is_low_balance || usageData.remaining === null) {
    return null;
  }

  return (
    <div className="bg-red-500 text-white px-4 py-2 text-center flex items-center justify-center space-x-2">
      <span>
        ⚠️ {usageData.provider} kredi bakiyeniz tükenmek üzere! Kalan: ${usageData.remaining.toFixed(2)}
      </span>
    </div>
  );
}

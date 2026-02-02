"use client";

import { useLLMUsage } from '@/context/LLMUsageContext';
import { AlertCircle, XCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function LLMUsageWarning() {
  const { usageData, loading } = useLLMUsage();

  if (loading || !usageData.is_low_balance || usageData.remaining === null) {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 z-[100] w-auto pointer-events-none">
      <motion.div
        initial={{ x: 20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        className="bg-[#09090b]/90 backdrop-blur-md border border-red-500/30 rounded-2xl p-2.5 pr-4 shadow-[0_8px_32px_rgba(0,0,0,0.5)] border-l-4 border-l-red-500 flex items-center gap-4 pointer-events-auto"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center text-red-500 shrink-0">
            <AlertCircle className="w-4 h-4" />
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-bold text-red-500 uppercase tracking-widest leading-none mb-1">Düşük Kredi Uyarısı</span>
            <p className="text-xs text-[#fafafa] font-medium leading-none">
              {usageData.provider} bakiyeniz tükenmek üzere.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 px-3 py-1.5 bg-red-500/10 rounded-xl border border-red-500/20">
          <span className="text-[10px] font-black text-red-500 font-mono">
            KALAN: ${usageData.remaining.toFixed(2)}
          </span>
        </div>
      </motion.div>
    </div>
  );
}

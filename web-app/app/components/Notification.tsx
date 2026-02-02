"use client";

import React from 'react';
import { useNotification } from '@/context/NotificationContext';
import { CheckCircle2, AlertCircle, Info, X, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function Notification() {
    const { notifications, removeNotification, confirmState, closeConfirm } = useNotification();

    return (
        <>
            {/* Toasts - Bottom Right, Dark Theme, Glassmorphism */}
            <div className="fixed bottom-4 right-4 z-[9999] flex flex-col-reverse gap-3 max-w-md w-full sm:w-[400px]">
                {notifications.map((n) => (
                    <div
                        key={n.id}
                        className={cn(
                            "animate-in slide-in-from-right-full duration-300 p-4 rounded-xl shadow-2xl border flex items-start gap-3",
                            "backdrop-blur-xl bg-[#18181b]/80",
                            n.type === 'success' ? "border-green-500/30" :
                                n.type === 'error' ? "border-red-500/30" :
                                    n.type === 'warning' ? "border-amber-500/30" :
                                        "border-blue-500/30"
                        )}
                    >
                        <div className="flex-shrink-0 mt-0.5">
                            {n.type === 'success' && <CheckCircle2 className="w-5 h-5 text-green-400" />}
                            {n.type === 'error' && <AlertCircle className="w-5 h-5 text-red-400" />}
                            {n.type === 'warning' && <AlertTriangle className="w-5 h-5 text-amber-400" />}
                            {n.type === 'info' && <Info className="w-5 h-5 text-blue-400" />}
                        </div>

                        <div className="flex-grow">
                            <p className={cn(
                                "text-sm font-medium",
                                n.type === 'success' ? "text-green-300" :
                                    n.type === 'error' ? "text-red-300" :
                                        n.type === 'warning' ? "text-amber-300" :
                                            "text-blue-300"
                            )}>
                                {n.message}
                            </p>
                        </div>

                        <button
                            onClick={() => removeNotification(n.id)}
                            className="flex-shrink-0 text-[#71717a] hover:text-[#fafafa] transition-colors"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                ))}
            </div>

            {/* Confirm Dialog */}
            {confirmState && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[10000] flex items-center justify-center p-4 animate-in fade-in duration-200" onClick={() => { confirmState.onCancel?.(); closeConfirm(); }}>
                    <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full overflow-hidden animate-in zoom-in-95 duration-200" onClick={e => e.stopPropagation()}>
                        <div className="p-6">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="p-2 bg-amber-100 rounded-full">
                                    <AlertTriangle className="w-6 h-6 text-amber-600" />
                                </div>
                                <h3 className="text-lg font-bold text-slate-800">
                                    {confirmState.title || 'Onay Gerekiyor'}
                                </h3>
                            </div>
                            <p className="text-slate-600">
                                {confirmState.message}
                            </p>
                        </div>
                        <div className="p-4 bg-slate-50 flex justify-end gap-3 border-t border-slate-100">
                            <button
                                onClick={() => {
                                    confirmState.onCancel?.();
                                    closeConfirm();
                                }}
                                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors font-medium text-sm"
                            >
                                Vazgeç
                            </button>
                            <button
                                onClick={() => {
                                    confirmState.onConfirm();
                                    closeConfirm();
                                }}
                                className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium text-sm shadow-sm"
                            >
                                Onayla
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

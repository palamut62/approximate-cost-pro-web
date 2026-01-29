"use client";

import { useState, useEffect } from 'react';
import { Search, X, Loader2, Plus, Box, FileText } from 'lucide-react';
import api from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';

type Poz = {
    poz_no: string;
    description: string;
    unit: string;
    unit_price: string | number;
    institution?: string;
}

interface PozSelectorModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSelect: (poz: Poz) => void;
}

export default function PozSelectorModal({ isOpen, onClose, onSelect }: PozSelectorModalProps) {
    const [searchTerm, setSearchTerm] = useState("");
    const [results, setResults] = useState<Poz[]>([]);
    const [loading, setLoading] = useState(false);
    const [debouncedTerm, setDebouncedTerm] = useState(searchTerm);

    // Debounce search term
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedTerm(searchTerm);
        }, 500);

        return () => clearTimeout(timer);
    }, [searchTerm]);

    // Perform search
    useEffect(() => {
        if (debouncedTerm.length >= 2) {
            setLoading(true);
            api.get(`/data/search?q=${encodeURIComponent(debouncedTerm)}`)
                .then(res => {
                    setResults(res.data);
                })
                .catch(err => {
                    console.error("Search error:", err);
                })
                .finally(() => {
                    setLoading(false);
                });
        } else {
            setResults([]);
        }
    }, [debouncedTerm]);

    // Reset when closed
    useEffect(() => {
        if (!isOpen) {
            setSearchTerm("");
            setResults([]);
        }
    }, [isOpen]);

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 transition-all"
                    />

                    {/* Modal Content */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none p-4"
                    >
                        <div className="w-full max-w-3xl bg-white rounded-2xl shadow-2xl border border-slate-100 overflow-hidden pointer-events-auto flex flex-col max-h-[85vh]">
                            {/* Header */}
                            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-white bg-opacity-90 backdrop-blur-md sticky top-0">
                                <div>
                                    <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                                        <Box className="w-6 h-6 text-blue-600" />
                                        Kayıtlı Poz Seçimi
                                    </h2>
                                    <p className="text-sm text-slate-500 mt-1">
                                        Veritabanında kayıtlı pozlar arasında arama yapın ve ekleyin.
                                    </p>
                                </div>
                                <button
                                    onClick={onClose}
                                    className="p-2 hover:bg-slate-100 rounded-full text-slate-400 hover:text-slate-600 transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            {/* Search Bar */}
                            <div className="p-4 bg-slate-50/50">
                                <div className="relative">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                                    <input
                                        type="text"
                                        placeholder="Poz No veya Açıklama ile arayın (örn: 15.120, Beton...)"
                                        value={searchTerm}
                                        onChange={(e) => setSearchTerm(e.target.value)}
                                        className="w-full pl-10 pr-4 py-3 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all placeholder:text-slate-400 text-slate-700"
                                        autoFocus
                                    />
                                    {loading && (
                                        <div className="absolute right-3 top-1/2 -translate-y-1/2">
                                            <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Results List */}
                            <div className="flex-1 overflow-y-auto p-4 space-y-2 bg-slate-50/30">
                                {results.length === 0 ? (
                                    <div className="h-64 flex flex-col items-center justify-center text-slate-400">
                                        {searchTerm.length < 2 ? (
                                            <>
                                                <Search className="w-12 h-12 mb-3 text-slate-200" />
                                                <p className="font-medium">Arama yapmak için en az 2 karakter girin.</p>
                                            </>
                                        ) : !loading && (
                                            <>
                                                <FileText className="w-12 h-12 mb-3 text-slate-200" />
                                                <p className="font-medium">Sonuç bulunamadı.</p>
                                            </>
                                        )}
                                    </div>
                                ) : (
                                    <div className="grid gap-2">
                                        {results.map((poz, index) => (
                                            <div
                                                key={`${poz.poz_no}-${index}`}
                                                className="group bg-white p-4 rounded-xl border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-default"
                                            >
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs font-bold rounded-md font-mono">
                                                            {poz.poz_no}
                                                        </span>
                                                        <span className="text-xs text-slate-400 font-medium px-2 py-0.5 bg-slate-100 rounded-md">
                                                            {poz.unit}
                                                        </span>
                                                        {poz.institution && (
                                                            <span className="text-xs text-slate-400">
                                                                {poz.institution}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="text-slate-700 font-medium text-sm leading-snug line-clamp-2" title={poz.description}>
                                                        {poz.description}
                                                    </p>
                                                </div>

                                                <div className="flex items-center gap-4 pl-4 border-l border-slate-100 min-w-fit">
                                                    <div className="text-right">
                                                        <div className="text-lg font-bold text-slate-900 font-mono">
                                                            {typeof poz.unit_price === 'string' ? poz.unit_price : poz.unit_price?.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                                        </div>
                                                        <div className="text-xs text-slate-400">Birim Fiyat</div>
                                                    </div>
                                                    <button
                                                        onClick={() => {
                                                            onSelect(poz);
                                                            onClose();
                                                        }}
                                                        className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm active:scale-95 flex items-center gap-2 px-4"
                                                    >
                                                        <Plus className="w-4 h-4" />
                                                        <span className="font-medium">Ekle</span>
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Footer */}
                            <div className="p-3 bg-slate-50 border-t border-slate-200 text-xs text-center text-slate-400">
                                Toplam {results.length} sonuç görüntülendi
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}

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
                        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 transition-all"
                    />

                    {/* Modal Content */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.98, y: 10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.98, y: 10 }}
                        className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none p-4"
                    >
                        <div className="w-full max-w-3xl bg-[#09090b] rounded-2xl shadow-[0_0_50px_-12px_rgba(0,0,0,0.5)] border border-[#27272a] overflow-hidden pointer-events-auto flex flex-col max-h-[85vh] ring-1 ring-white/10">
                            {/* Header */}
                            <div className="p-6 border-b border-[#27272a] flex items-center justify-between bg-black/40 backdrop-blur-md sticky top-0 z-10">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <Box className="w-5 h-5 text-blue-500" />
                                        <h2 className="text-xl font-bold text-[#fafafa] tracking-tight">
                                            Kayıtlı Poz Seçimi
                                        </h2>
                                    </div>
                                    <p className="text-sm text-[#71717a] font-medium leading-relaxed">
                                        Veritabanında kayıtlı pozlar arasında arama yapın ve ekleyin.
                                    </p>
                                </div>
                                <button
                                    onClick={onClose}
                                    className="p-2 hover:bg-[#18181b] rounded-lg text-[#71717a] hover:text-[#fafafa] transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            {/* Search Bar */}
                            <div className="p-6 bg-[#09090b] border-b border-[#18181b]">
                                <div className="relative group">
                                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#52525b] group-focus-within:text-blue-500 transition-colors" />
                                    <input
                                        type="text"
                                        placeholder="Poz No veya Açıklama ile arayın (örn: 15.120, Beton...)"
                                        value={searchTerm}
                                        onChange={(e) => setSearchTerm(e.target.value)}
                                        className="w-full pl-12 pr-12 py-3.5 bg-[#18181b] border border-[#27272a] rounded-xl focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all placeholder:text-[#3f3f46] text-[#fafafa] text-base"
                                        autoFocus
                                    />
                                    {loading && (
                                        <div className="absolute right-4 top-1/2 -translate-y-1/2">
                                            <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Results List */}
                            <div className="flex-1 overflow-y-auto p-2 space-y-2 bg-black/20 custom-scrollbar">
                                {results.length === 0 ? (
                                    <div className="h-64 flex flex-col items-center justify-center text-[#52525b]">
                                        {searchTerm.length < 2 ? (
                                            <>
                                                <Search className="w-12 h-12 mb-4 text-[#18181b]" />
                                                <p className="font-bold text-sm uppercase tracking-widest">Arama Bekleniyor</p>
                                                <p className="text-xs mt-1">En az 2 karakter girin.</p>
                                            </>
                                        ) : !loading && (
                                            <>
                                                <FileText className="w-12 h-12 mb-4 text-[#18181b]" />
                                                <p className="font-bold text-sm uppercase tracking-widest">Sonuç Bulunamadı</p>
                                                <p className="text-xs mt-1">Farklı anahtar kelimeler deneyin.</p>
                                            </>
                                        )}
                                    </div>
                                ) : (
                                    <div className="grid gap-2 p-2">
                                        {results.map((poz, index) => (
                                            <div
                                                key={`${poz.poz_no}-${index}`}
                                                className="group bg-[#18181b]/50 hover:bg-[#18181b] p-4 rounded-xl border border-[#27272a] hover:border-blue-500/50 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-default overflow-hidden relative"
                                            >
                                                <div className="flex-1 min-w-0 z-10">
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <span className="px-2 py-0.5 bg-blue-600/10 text-blue-500 text-[11px] font-bold rounded border border-blue-500/20 font-mono">
                                                            {poz.poz_no}
                                                        </span>
                                                        <span className="text-[10px] font-bold text-[#71717a] px-2 py-0.5 bg-[#09090b] rounded uppercase tracking-tighter border border-[#27272a]">
                                                            {poz.unit}
                                                        </span>
                                                        {poz.institution && (
                                                            <span className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">
                                                                {poz.institution}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="text-[#fafafa] font-medium text-sm leading-relaxed line-clamp-2 pr-4 transition-colors group-hover:text-white" title={poz.description}>
                                                        {poz.description}
                                                    </p>
                                                </div>

                                                <div className="flex items-center gap-6 pl-6 border-l border-[#27272a] min-w-fit z-10">
                                                    <div className="text-right">
                                                        <div className="text-lg font-bold text-[#fafafa] font-mono tracking-tighter group-hover:text-blue-400 transition-colors">
                                                            {typeof poz.unit_price === 'string' ? poz.unit_price : poz.unit_price?.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} <span className="text-xs font-bold text-[#71717a]">TL</span>
                                                        </div>
                                                        <div className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">Birim Fiyat</div>
                                                    </div>
                                                    <button
                                                        onClick={() => {
                                                            onSelect(poz);
                                                            onClose();
                                                        }}
                                                        className="p-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-all shadow-lg active:scale-95 flex items-center gap-2 px-6 font-bold text-sm"
                                                    >
                                                        <Plus className="w-4 h-4" />
                                                        Ekle
                                                    </button>
                                                </div>

                                                {/* Subtle highlight effect */}
                                                <div className="absolute top-0 right-0 w-32 h-32 bg-blue-600/5 blur-[60px] pointer-events-none group-hover:bg-blue-500/10 transition-colors" />
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Footer */}
                            <div className="p-4 bg-black/40 border-t border-[#27272a] text-[10px] font-bold text-[#52525b] uppercase tracking-[0.2em] text-center">
                                Toplam {results.length} kayıt listelendi
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}

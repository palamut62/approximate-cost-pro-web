"use client";

import { useEffect, useState } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { DataTable } from '@/components/ui/data-table';
import api from '@/lib/api';
import { Search, Plus, Check, X, Info, FileText, Table, Box, ExternalLink, Sparkles, Loader2, Archive } from 'lucide-react';
import AnalysisTable, { AnalysisData } from '@/components/AnalysisTable';
import { useCart } from '@/context/CartContext';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

// Poz Tipi Tanımı
type Poz = {
    poz_no: string;
    description: string;
    unit: string;
    unit_price: string;
    institution: string;
    source_file: string;
    technical_description?: string;
    analysis_data?: AnalysisData;
}

export default function DataExplorerPage() {
    const [data, setData] = useState<Poz[]>([]);
    const [loading, setLoading] = useState(false);
    const [query, setQuery] = useState("");
    const [selectedPoz, setSelectedPoz] = useState<Poz | null>(null);
    const { addItem, items: cartItems } = useCart();

    const columns: ColumnDef<Poz>[] = [
        {
            accessorKey: "poz_no",
            header: "Poz No",
            cell: ({ row }) => <span className="font-mono font-bold text-blue-500">{row.getValue("poz_no")}</span>
        },
        {
            accessorKey: "description",
            header: "Açıklama",
            cell: ({ row }) => <span className="text-[#fafafa] font-medium block max-w-lg truncate leading-relaxed" title={row.getValue("description")}>{row.getValue("description")}</span>
        },
        {
            accessorKey: "unit",
            header: "Birim",
            cell: ({ row }) => <span className="text-[#71717a] text-[10px] font-bold px-2 py-0.5 bg-[#09090b] rounded border border-[#27272a] uppercase">{row.getValue("unit")}</span>
        },
        {
            accessorKey: "unit_price",
            header: "Birim Fiyat",
            cell: ({ row }) => <span className="font-mono font-bold text-[#fafafa] tracking-tighter">{row.getValue("unit_price")} <span className="text-[10px] text-[#52525b]">TL</span></span>
        },
        {
            accessorKey: "institution",
            header: "Kurum",
            cell: ({ row }) => <span className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">{row.getValue("institution")}</span>
        },
        {
            id: "actions",
            header: "İşlem",
            cell: ({ row }) => {
                const poz = row.original;
                const isAdded = cartItems.some(item => item.poz_no === poz.poz_no);
                return (
                    <button
                        onClick={() => addItem(poz)}
                        disabled={isAdded}
                        className={cn(
                            "p-2.5 rounded-lg transition-all active:scale-95",
                            isAdded
                                ? "bg-green-500/10 text-green-500 cursor-default border border-green-500/20"
                                : "bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-900/20"
                        )}
                        title={isAdded ? "Projede mevcut" : "Projeye ekle"}
                    >
                        {isAdded ? <Check className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
                    </button>
                )
            }
        }
    ]

    // Initial load? maybe not needed if we search
    useEffect(() => {
        handleSearch("10."); // Load some initial data or empty? Let's load ÇŞB items
    }, []);

    const handleSearch = async (q: string) => {
        setLoading(true);
        try {
            const res = await api.get(`/data/search?q=${q}`);
            setData(res.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Page Title & Stats Bar */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#27272a]/50">
                <div className="space-y-1">
                    <div className="flex items-center gap-2 mb-2">
                        <FileText className="w-4 h-4 text-blue-500" />
                        <span className="text-[10px] font-bold text-[#71717a] uppercase tracking-[0.2em]">Kütüphane</span>
                    </div>
                    <h1 className="text-3xl font-bold text-[#fafafa] tracking-tight">Veri Gezgini</h1>
                    <p className="text-sm text-[#71717a]">Resmi poz veritabanında teknik arama yapın ve analizleri inceleyin.</p>
                </div>
            </div>

            {/* Search Bar - High Fidelity */}
            <div className="relative group">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                    <Search className="h-5 w-5 text-[#52525b] group-focus-within:text-blue-500 transition-colors" />
                </div>
                <input
                    type="text"
                    className="block w-full pl-12 pr-28 py-4 border border-[#27272a] rounded-xl bg-[#18181b] text-[#fafafa] placeholder-[#3f3f46] focus:outline-none focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500/50 text-base shadow-2xl transition-all"
                    placeholder="Poz No, Açıklama veya Kurum ara..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSearch(query);
                    }}
                />
                <button
                    onClick={() => handleSearch(query)}
                    className="absolute inset-y-2 right-2 px-6 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-500 transition-all shadow-lg active:scale-95 flex items-center gap-2"
                >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                    ARA
                </button>
            </div>

            {/* Main Content Table */}
            <div className="bg-[#18181b] rounded-2xl shadow-2xl border border-[#27272a] overflow-hidden">
                <div className="p-1">
                    <DataTable
                        columns={columns}
                        data={data}
                        loading={loading}
                        onRowDoubleClick={async (row) => {
                            // Detayları çekmek için yeni endpoint'i kullan
                            try {
                                const res = await api.get(`/data/poz/${row.poz_no}`);
                                setSelectedPoz(res.data);
                            } catch (e) {
                                console.error("Detay yükleme hatası:", e);
                                setSelectedPoz(row); // Hata olursa temel veriyle devam et
                            }
                        }}
                    />
                </div>
            </div>

            {/* Poz Detay Overlay Modal */}
            <AnimatePresence>
                {selectedPoz && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                            onClick={() => setSelectedPoz(null)}
                        />

                        <motion.div
                            initial={{ opacity: 0, scale: 0.98, y: 10 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.98, y: 10 }}
                            className="bg-[#09090b] rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden border border-[#27272a] ring-1 ring-white/10 relative z-10 flex flex-col"
                            onClick={e => e.stopPropagation()}
                        >
                            {/* Modal Header */}
                            <div className="px-6 py-5 border-b border-[#27272a] flex justify-between items-center bg-black/40">
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-500">
                                        <Box className="w-5 h-5" />
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <div className="font-mono text-lg font-bold text-blue-500 tracking-tight">{selectedPoz.poz_no}</div>
                                            <span className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">{selectedPoz.institution}</span>
                                        </div>
                                        <div className="text-xs text-[#71717a] font-medium leading-tight">İmalat Teknik Detayları</div>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setSelectedPoz(null)}
                                    className="p-2 rounded-lg hover:bg-[#18181b] text-[#52525b] hover:text-[#fafafa] transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            {/* Modal Content */}
                            <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar flex-1">
                                {/* Description Box */}
                                <div className="p-4 bg-[#18181b]/50 rounded-xl border border-[#27272a] space-y-2">
                                    <div className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest flex items-center gap-2">
                                        <Info className="w-3 h-3" />
                                        Açıklama
                                    </div>
                                    <p className="text-[#fafafa] text-sm leading-relaxed font-medium">
                                        {selectedPoz.description}
                                    </p>
                                </div>

                                {/* Price & Unit Stats Row */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="px-5 py-4 bg-blue-600/5 rounded-xl border border-blue-500/20 group hover:border-blue-500/40 transition-colors">
                                        <div className="flex items-center justify-between mb-1">
                                            <div className="text-[10px] text-blue-500 font-bold uppercase tracking-widest">Birim Fiyat</div>
                                            <Sparkles className="w-3 h-3 text-blue-500/30 group-hover:text-blue-500 transition-colors" />
                                        </div>
                                        <div className="text-2xl font-black text-[#fafafa] tracking-tighter">
                                            {selectedPoz.unit_price} <span className="text-xs font-bold text-blue-500">TL</span>
                                        </div>
                                    </div>
                                    <div className="px-5 py-4 bg-[#18181b] rounded-xl border border-[#27272a]">
                                        <div className="text-[10px] text-[#71717a] font-bold uppercase tracking-widest mb-1">Ölçü Birimi</div>
                                        <div className="text-2xl font-black text-[#fafafa] tracking-tighter uppercase">{selectedPoz.unit}</div>
                                    </div>
                                </div>

                                {/* Analysis Data or Technical Description Sections */}
                                {selectedPoz.analysis_data && selectedPoz.analysis_data.components && selectedPoz.analysis_data.components.length > 0 ? (
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center text-[10px] font-bold text-[#71717a] uppercase tracking-widest">
                                                <Table className="w-3 h-3 mr-2 text-blue-500" />
                                                Resmi Analiz Kalemleri
                                            </div>
                                            <div className="text-[10px] font-bold text-blue-500 flex items-center gap-1">
                                                <Box className="w-3 h-3" /> VERİ TABANLI
                                            </div>
                                        </div>
                                        <div className="rounded-xl border border-[#27272a] overflow-hidden bg-black/20">
                                            <AnalysisTable data={selectedPoz.analysis_data} className="max-h-[300px] overflow-y-auto" />
                                        </div>
                                    </div>
                                ) : selectedPoz.technical_description ? (
                                    <div className="space-y-3">
                                        <div className="flex items-center text-[10px] font-bold text-[#71717a] uppercase tracking-widest">
                                            <FileText className="w-3 h-3 mr-2 text-blue-500" />
                                            Teknik Tarif & İmalat Şartları
                                        </div>
                                        <div className="text-sm text-[#a1a1aa] leading-relaxed bg-black/40 p-4 rounded-xl border border-[#27272a] max-h-48 overflow-y-auto custom-scrollbar font-normal whitespace-pre-wrap">
                                            {selectedPoz.technical_description}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="py-12 border border-dashed border-[#27272a] rounded-xl flex flex-col items-center justify-center text-[#52525b] space-y-2">
                                        <Archive className="w-8 h-8 opacity-20" />
                                        <p className="text-xs font-bold uppercase tracking-widest">Ek teknik veri bulunmuyor</p>
                                    </div>
                                )}

                                {/* Source Footnote */}
                                <div className="pt-2 border-t border-[#27272a] flex items-center justify-between text-[10px] font-bold text-[#52525b] uppercase tracking-[0.15em]">
                                    <div className="flex items-center gap-2">
                                        <Box className="w-3 h-3" />
                                        KAYNAK: {selectedPoz.source_file}
                                    </div>
                                    <div className="flex items-center gap-1 text-blue-500/50">
                                        GÜNCEL VERİ <Check className="w-3 h-3" />
                                    </div>
                                </div>
                            </div>

                            {/* Modal Footer */}
                            <div className="px-6 py-6 bg-black/60 border-t border-[#27272a] flex justify-end gap-3">
                                <button
                                    onClick={() => setSelectedPoz(null)}
                                    className="px-6 py-2.5 text-[#71717a] hover:text-[#fafafa] hover:bg-[#18181b] rounded-lg transition-all font-bold text-sm"
                                >
                                    Vazgeç
                                </button>
                                <button
                                    onClick={() => {
                                        addItem(selectedPoz);
                                        setSelectedPoz(null);
                                    }}
                                    className="px-8 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-all text-sm font-bold flex items-center shadow-xl shadow-blue-900/40 active:scale-95"
                                >
                                    <Plus className="w-4 h-4 mr-2" />
                                    PROJEYE EKLE
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    )
}

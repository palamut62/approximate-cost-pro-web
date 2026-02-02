"use client";

import { useState, useEffect } from 'react';
import { FileText, Trash2, Eye, Loader2, Calendar, Calculator, Sparkles, Plus, ArrowRight, Box, Trash, ExternalLink } from 'lucide-react';
import api from '@/lib/api';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCart } from '@/context/CartContext';
import { useNotification } from '@/context/NotificationContext';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

type Analysis = {
    id: number;
    poz_no: string;
    name: string;
    unit: string;
    total_price: number;
    created_date: string;
    is_ai_generated: boolean;
    score?: number;
}

export default function SavedAnalysesPage() {
    const [analyses, setAnalyses] = useState<Analysis[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedAnalysis, setSelectedAnalysis] = useState<any>(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const { addItem } = useCart();
    const { showNotification, confirm } = useNotification();
    const router = useRouter();

    useEffect(() => {
        fetchAnalyses();
    }, []);

    const handleAddToCost = (analysis: Analysis) => {
        addItem({
            poz_no: analysis.poz_no,
            description: analysis.name,
            unit: analysis.unit,
            unit_price: analysis.total_price.toString(),
            institution: "Özel Analiz",
            source_file: "Kayıtlı Analiz"
        });
        showNotification(`"${analysis.name}" maliyet hesabına eklendi!`, "success");
    };

    const handleAddAndGo = (analysis: Analysis) => {
        handleAddToCost(analysis);
        router.push('/cost');
    };

    const fetchAnalyses = async () => {
        try {
            const res = await api.get('/analyses');
            setAnalyses(res.data);
            if (res.data.length > 0 && !selectedAnalysis) {
                handleViewDetail(res.data[0].id);
            }
        } catch (e) {
            console.error("Analizler yüklenemedi:", e);
        } finally {
            setLoading(false);
        }
    };

    const handleViewDetail = async (id: number) => {
        setDetailLoading(true);
        try {
            const res = await api.get(`/analyses/${id}`);
            setSelectedAnalysis(res.data);
        } catch (e) {
            console.error("Analiz detayı yüklenemedi:", e);
            showNotification("Analiz detayı yüklenirken hata oluştu.", "error");
        } finally {
            setDetailLoading(false);
        }
    };

    const handleDelete = (id: number) => {
        confirm({
            title: "Analizi Sil",
            message: "Bu analizi silmek istediğinize emin misiniz? Bu işlem geri alınamaz.",
            onConfirm: async () => {
                try {
                    await api.delete(`/analyses/${id}`);
                    setAnalyses(analyses.filter(a => a.id !== id));
                    if (selectedAnalysis?.id === id) {
                        setSelectedAnalysis(null);
                    }
                    showNotification("Analiz silindi.", "success");
                } catch (e) {
                    console.error("Analiz silinemedi:", e);
                    showNotification("Analiz silinirken hata oluştu.", "error");
                }
            }
        });
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] text-[#71717a]">
                <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
                <p className="animate-pulse font-medium">Arşiv taranıyor...</p>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Header Section */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#27272a]/50">
                <div className="space-y-1">
                    <div className="flex items-center gap-2 mb-2">
                        <Box className="w-4 h-4 text-purple-500" />
                        <span className="text-[10px] font-bold text-[#71717a] uppercase tracking-[0.2em]">Koleksiyon</span>
                    </div>
                    <h1 className="text-3xl font-bold text-[#fafafa] tracking-tight">Kayıtlı Analizler</h1>
                    <p className="text-sm text-[#71717a]">Daha önce oluşturulmuş tüm projeler ve AI sonuçları.</p>
                </div>
                <Link
                    href="/analysis"
                    className="flex items-center px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 transition-all font-bold shadow-lg shadow-purple-900/40 text-sm"
                >
                    <Plus className="w-4 h-4 mr-2" />
                    YENİ ANALİZ
                </Link>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Analiz Listesi (Sol Kolon) */}
                <div className="lg:col-span-1 border-r border-[#27272a]/50 pr-4">
                    {analyses.length === 0 ? (
                        <div className="bg-[#18181b]/50 rounded-2xl border border-dashed border-[#27272a] p-12 text-center space-y-4">
                            <div className="w-16 h-16 bg-[#18181b] rounded-full flex items-center justify-center mx-auto text-[#27272a] border border-[#27272a]">
                                <FileText className="w-8 h-8" />
                            </div>
                            <div className="space-y-1">
                                <p className="text-[#fafafa] font-bold">Arşiviniz Boş</p>
                                <p className="text-[#52525b] text-xs">Henüz kayıtlı bir analiz bulunmuyor.</p>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-3 max-h-[70vh] overflow-y-auto pr-2 custom-scrollbar">
                            {analyses.map(analysis => (
                                <div
                                    key={analysis.id}
                                    className={cn(
                                        "group rounded-xl border p-4 cursor-pointer transition-all relative overflow-hidden",
                                        selectedAnalysis?.id === analysis.id
                                            ? 'bg-[#18181b] border-purple-500/50 shadow-lg shadow-purple-900/20'
                                            : 'bg-transparent border-[#27272a] hover:bg-[#18181b]/50 hover:border-[#3f3f46]'
                                    )}
                                    onClick={() => handleViewDetail(analysis.id)}
                                >
                                    <div className="flex justify-between items-start z-10 relative">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-2">
                                                {analysis.is_ai_generated ? (
                                                    <span className="px-2 py-0.5 bg-purple-600/10 text-purple-500 text-[9px] font-black uppercase rounded border border-purple-500/20 tracking-tighter">
                                                        AI ANALİZ
                                                    </span>
                                                ) : (
                                                    <span className="px-2 py-0.5 bg-blue-600/10 text-blue-500 text-[9px] font-black uppercase rounded border border-blue-500/20 tracking-tighter">
                                                        MANUEL
                                                    </span>
                                                )}
                                                <span className="text-[10px] font-mono font-bold text-[#52525b]">
                                                    {analysis.poz_no}
                                                </span>
                                            </div>
                                            <h3 className={cn(
                                                "font-bold text-sm truncate transition-colors",
                                                selectedAnalysis?.id === analysis.id ? "text-white" : "text-[#fafafa]/80 group-hover:text-white"
                                            )}>
                                                {analysis.name}
                                            </h3>
                                            <div className="flex items-center gap-4 mt-3">
                                                <div className="flex items-center text-[10px] font-bold text-[#52525b] uppercase tracking-widest">
                                                    <Calendar className="w-3 h-3 mr-1 text-zinc-700" />
                                                    {analysis.created_date}
                                                </div>
                                                <div className="flex items-center text-[10px] font-mono font-bold text-blue-500 tracking-tighter">
                                                    {analysis.total_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                                </div>
                                            </div>
                                        </div>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleDelete(analysis.id);
                                            }}
                                            className="p-2 text-[#27272a] hover:text-red-500 transition-colors"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                    {selectedAnalysis?.id === analysis.id && (
                                        <div className="absolute top-0 right-0 w-32 h-32 bg-purple-600/5 blur-[50px] -z-0" />
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Analiz Detayı (Sağ Kolon) */}
                <div className="lg:col-span-2">
                    <AnimatePresence mode="wait">
                        {detailLoading ? (
                            <motion.div
                                key="loader"
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                className="bg-[#18181b]/30 rounded-2xl border border-[#27272a] p-12 flex flex-col items-center justify-center min-h-[500px]"
                            >
                                <Loader2 className="w-10 h-10 animate-spin text-purple-500 mb-4" />
                                <p className="text-[#52525b] font-bold uppercase tracking-widest text-xs">Teknik Veriler Alınıyor</p>
                            </motion.div>
                        ) : selectedAnalysis ? (
                            <motion.div
                                key={selectedAnalysis.id}
                                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                                className="bg-[#18181b] rounded-2xl shadow-2xl border border-[#27272a] overflow-hidden flex flex-col ring-1 ring-white/5"
                            >
                                {/* Detail Header Box */}
                                <div className="p-8 border-b border-[#27272a] bg-black/40 relative overflow-hidden">
                                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2">
                                                <span className="text-[10px] font-mono font-bold text-blue-500 tracking-tight uppercase px-2 py-1 bg-blue-500/10 rounded border border-blue-500/20">{selectedAnalysis.poz_no}</span>
                                                <span className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">Özel Analiz Raporu</span>
                                            </div>
                                            <h2 className="font-black text-2xl text-white tracking-tight leading-tight">{selectedAnalysis.name}</h2>
                                        </div>
                                        <div className="text-left md:text-right">
                                            <div className="text-4xl font-black text-white tracking-tighter mb-1">
                                                {selectedAnalysis.total_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} <span className="text-sm font-bold text-purple-500">TL</span>
                                            </div>
                                            <div className="text-[10px] font-bold text-[#52525b] uppercase tracking-[0.2em]">1 {selectedAnalysis.unit} Yaklaşık Maliyet</div>
                                        </div>
                                    </div>

                                    {/* Action Row */}
                                    <div className="flex flex-wrap gap-3 mt-8 relative z-10">
                                        <button
                                            onClick={() => handleAddToCost(selectedAnalysis)}
                                            className="flex items-center px-6 py-2.5 bg-[#09090b] border border-[#27272a] text-[#fafafa] rounded-lg hover:border-green-500/50 hover:bg-green-500/5 transition-all font-bold text-sm shadow-xl"
                                        >
                                            <Plus className="w-4 h-4 mr-2" />
                                            Projeye Dahil Et
                                        </button>
                                        <button
                                            onClick={() => handleAddAndGo(selectedAnalysis)}
                                            className="flex items-center px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-all font-bold text-sm shadow-xl shadow-blue-900/40 active:scale-95"
                                        >
                                            <ArrowRight className="w-4 h-4 mr-2" />
                                            Ekle ve Git
                                        </button>
                                    </div>

                                    <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/5 blur-[80px] -z-0" />
                                </div>

                                {/* Explanation Banner */}
                                {selectedAnalysis.ai_explanation && (
                                    <div className="p-6 bg-blue-600/5 border-b border-blue-500/10">
                                        <div className="flex gap-4">
                                            <Sparkles className="w-5 h-5 text-blue-500/50 shrink-0 mt-1" />
                                            <p className="text-sm text-[#a1a1aa] leading-relaxed italic font-medium">
                                                "{selectedAnalysis.ai_explanation}"
                                            </p>
                                        </div>
                                    </div>
                                )}

                                {/* Component Table */}
                                <div className="overflow-x-auto bg-[#09090b]/50">
                                    <table className="w-full text-sm border-collapse">
                                        <thead>
                                            <tr className="bg-black/20 text-[10px] font-bold uppercase text-[#52525b] tracking-widest border-b border-[#27272a]">
                                                <th className="px-6 py-4 text-left">Sınıf</th>
                                                <th className="px-6 py-4 text-left">Kod</th>
                                                <th className="px-6 py-4 text-left">Bileşen Adı</th>
                                                <th className="px-6 py-4 text-left">Birim</th>
                                                <th className="px-6 py-4 text-right">Miktar</th>
                                                <th className="px-6 py-4 text-right">Fiyat</th>
                                                <th className="px-6 py-4 text-right">Tutar</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-[#18181b]">
                                            {selectedAnalysis.components?.map((comp: any, idx: number) => (
                                                <tr key={idx} className="group hover:bg-[#18181b]/80 transition-colors">
                                                    <td className="px-6 py-4">
                                                        <span className={cn(
                                                            "text-[9px] font-black uppercase px-2 py-0.5 rounded tracking-tighter border",
                                                            comp.type === 'Malzeme' ? 'bg-blue-600/10 text-blue-400 border-blue-500/20' :
                                                                comp.type === 'İşçilik' ? 'bg-orange-600/10 text-orange-400 border-orange-500/20' :
                                                                    comp.type === 'Nakliye' ? 'bg-green-600/10 text-green-400 border-green-500/20' :
                                                                        'bg-[#111111] text-zinc-500 border-[#27272a]'
                                                        )}>
                                                            {comp.type}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 font-mono text-[11px] text-[#52525b] group-hover:text-[#71717a]">{comp.code}</td>
                                                    <td className="px-6 py-4 text-[#fafafa] font-medium text-sm">{comp.name}</td>
                                                    <td className="px-6 py-4 text-[10px] font-bold text-[#52525b] uppercase">{comp.unit}</td>
                                                    <td className="px-6 py-4 text-right font-mono text-zinc-400 text-xs">{comp.quantity?.toFixed(4)}</td>
                                                    <td className="px-6 py-4 text-right font-mono text-zinc-400 text-xs">{comp.unit_price?.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</td>
                                                    <td className="px-6 py-4 text-right font-mono font-bold text-[#fafafa] text-sm tabular-nums">
                                                        {comp.total_price?.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                        <tfoot className="bg-black/60 border-t border-[#27272a]">
                                            <tr className="border-b border-[#27272a]/30">
                                                <td colSpan={6} className="px-6 py-4 text-right font-bold text-[#52525b] text-[10px] uppercase tracking-widest">Çıplak Maliyet</td>
                                                <td className="px-6 py-4 text-right font-mono font-bold text-[#fafafa] text-sm">
                                                    {(selectedAnalysis.total_price / 1.25).toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                                </td>
                                            </tr>
                                            <tr>
                                                <td colSpan={6} className="px-6 py-6 text-right font-bold text-[#71717a] text-[10px] uppercase tracking-[0.2em]">Birim Fiyat (Kâr Dahil)</td>
                                                <td className="px-6 py-6 text-right font-mono font-black text-white text-2xl tracking-tighter">
                                                    {selectedAnalysis.total_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} <span className="text-xs font-bold text-purple-500">TL</span>
                                                </td>
                                            </tr>
                                        </tfoot>
                                    </table>
                                </div>
                            </motion.div>
                        ) : (
                            <motion.div
                                key="empty"
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                className="bg-[#18181b]/30 rounded-2xl border border-dashed border-[#27272a] p-12 flex flex-col items-center justify-center min-h-[500px] text-center space-y-4"
                            >
                                <div className="w-16 h-16 bg-[#18181b] rounded-full flex items-center justify-center mx-auto text-[#27272a] border border-[#27272a]">
                                    <Eye className="w-8 h-8 opacity-20" />
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[#52525b] font-bold text-sm uppercase tracking-widest">Önizleme Bekleniyor</p>
                                    <p className="text-[#52525b] text-xs">Detayları incelemek için listeden bir analiz seçin.</p>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}


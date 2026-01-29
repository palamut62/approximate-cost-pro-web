"use client";

import { useState, useEffect } from 'react';
import { FileText, Trash2, Eye, Loader2, Calendar, Calculator, Sparkles, Plus, ArrowRight } from 'lucide-react';
import api from '@/lib/api';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCart } from '@/context/CartContext';
import { useNotification } from '@/context/NotificationContext';

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
        // Analizi poz olarak sepete ekle
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
            <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-400">
                <Loader2 className="w-8 h-8 animate-spin mb-4" />
                <p>Analizler yükleniyor...</p>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-slate-800 flex items-center">
                    <FileText className="w-6 h-6 mr-2 text-blue-600" />
                    Kayıtlı Analizler
                </h1>
                <p className="text-slate-500">Daha önce oluşturulmuş ve kaydedilmiş tüm analizleriniz.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Analiz Listesi */}
                <div className="lg:col-span-1 space-y-4">
                    {analyses.length === 0 ? (
                        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center">
                            <div className="p-3 bg-slate-50 rounded-full inline-block mb-4">
                                <FileText className="w-8 h-8 text-slate-300" />
                            </div>
                            <p className="text-slate-500 mb-4">Henüz kayıtlı analiz bulunmuyor.</p>
                            <Link
                                href="/analysis"
                                className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium"
                            >
                                <Sparkles className="w-4 h-4 mr-2" />
                                Yeni Analiz Oluştur
                            </Link>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {analyses.map(analysis => (
                                <div
                                    key={analysis.id}
                                    className={`bg-white rounded-xl shadow-sm border p-4 cursor-pointer transition-all ${selectedAnalysis?.id === analysis.id
                                        ? 'border-purple-400 ring-2 ring-purple-100'
                                        : 'border-slate-200 hover:border-slate-300'
                                        }`}
                                    onClick={() => handleViewDetail(analysis.id)}
                                >
                                    <div className="flex justify-between items-start">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                {analysis.is_ai_generated && (
                                                    <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 text-[10px] font-bold rounded">
                                                        AI
                                                    </span>
                                                )}
                                                <span className="text-xs text-slate-400 font-mono">
                                                    {analysis.poz_no}
                                                </span>
                                            </div>
                                            <h3 className="font-medium text-slate-800 truncate">
                                                {analysis.name}
                                            </h3>
                                            <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                                                <span className="flex items-center">
                                                    <Calendar className="w-3 h-3 mr-1" />
                                                    {analysis.created_date}
                                                </span>
                                                <span className="flex items-center">
                                                    <Calculator className="w-3 h-3 mr-1" />
                                                    {analysis.total_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL/{analysis.unit}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleAddToCost(analysis);
                                                }}
                                                className="p-2 text-slate-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                                                title="Maliyet Hesabına Ekle"
                                            >
                                                <Plus className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleDelete(analysis.id);
                                                }}
                                                className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                                title="Sil"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Analiz Detayı */}
                <div className="lg:col-span-2">
                    {detailLoading ? (
                        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 flex flex-col items-center justify-center min-h-[400px]">
                            <Loader2 className="w-8 h-8 animate-spin text-purple-600 mb-4" />
                            <p className="text-slate-500">Detaylar yükleniyor...</p>
                        </div>
                    ) : selectedAnalysis ? (
                        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                            <div className="p-4 border-b border-slate-100 bg-slate-50">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h2 className="font-bold text-slate-800 text-lg">{selectedAnalysis.name}</h2>
                                        <p className="text-sm text-slate-500 font-mono">{selectedAnalysis.poz_no}</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-2xl font-bold text-purple-600">
                                            {selectedAnalysis.total_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                        </p>
                                        <p className="text-sm text-slate-500">1 {selectedAnalysis.unit} Birim Fiyatı</p>
                                    </div>
                                </div>
                                {/* Maliyet Hesabına Ekle Butonları */}
                                <div className="flex gap-2 mt-4">
                                    <button
                                        onClick={() => handleAddToCost(selectedAnalysis)}
                                        className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                                    >
                                        <Plus className="w-4 h-4 mr-2" />
                                        Maliyet Hesabına Ekle
                                    </button>
                                    <button
                                        onClick={() => handleAddAndGo(selectedAnalysis)}
                                        className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                                    >
                                        <ArrowRight className="w-4 h-4 mr-2" />
                                        Ekle ve Git
                                    </button>
                                </div>
                            </div>

                            {selectedAnalysis.ai_explanation && (
                                <div className="p-4 bg-blue-50 border-b border-blue-100">
                                    <p className="text-sm text-blue-800">{selectedAnalysis.ai_explanation}</p>
                                </div>
                            )}

                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-medium">
                                        <tr>
                                            <th className="px-4 py-3 text-left">Tür</th>
                                            <th className="px-4 py-3 text-left">Kod</th>
                                            <th className="px-4 py-3 text-left">Açıklama</th>
                                            <th className="px-4 py-3 text-left">Birim</th>
                                            <th className="px-4 py-3 text-right">Miktar</th>
                                            <th className="px-4 py-3 text-right">B.Fiyat</th>
                                            <th className="px-4 py-3 text-right">Tutar</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100">
                                        {selectedAnalysis.components?.map((comp: any, idx: number) => (
                                            <tr key={idx} className="hover:bg-slate-50">
                                                <td className="px-4 py-3">
                                                    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${comp.type === 'Malzeme' ? 'bg-blue-100 text-blue-700' :
                                                        comp.type === 'İşçilik' ? 'bg-orange-100 text-orange-700' :
                                                            comp.type === 'Nakliye' ? 'bg-green-100 text-green-700' :
                                                                'bg-slate-100 text-slate-700'
                                                        }`}>
                                                        {comp.type}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 font-mono text-xs text-slate-500">{comp.code}</td>
                                                <td className="px-4 py-3 text-slate-800">{comp.name}</td>
                                                <td className="px-4 py-3 text-slate-500">{comp.unit}</td>
                                                <td className="px-4 py-3 text-right">{comp.quantity?.toFixed(4)}</td>
                                                <td className="px-4 py-3 text-right">{comp.unit_price?.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL</td>
                                                <td className="px-4 py-3 text-right font-medium">{comp.total_price?.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                    <tfoot className="bg-slate-50 border-t border-slate-200">
                                        <tr>
                                            <td colSpan={6} className="px-4 py-3 text-right font-medium text-slate-600">
                                                Malzeme + İşçilik + Nakliye
                                            </td>
                                            <td className="px-4 py-3 text-right font-bold">
                                                {(selectedAnalysis.total_price / 1.25).toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                            </td>
                                        </tr>
                                        <tr>
                                            <td colSpan={6} className="px-4 py-3 text-right text-slate-500">
                                                Yüklenici Kârı ve Genel Giderler (%25)
                                            </td>
                                            <td className="px-4 py-3 text-right font-medium">
                                                {(selectedAnalysis.total_price - selectedAnalysis.total_price / 1.25).toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                            </td>
                                        </tr>
                                        <tr className="border-t-2 border-slate-300">
                                            <td colSpan={6} className="px-4 py-3 text-right font-bold text-slate-800">
                                                1 {selectedAnalysis.unit} Birim Fiyatı
                                            </td>
                                            <td className="px-4 py-3 text-right font-bold text-lg text-purple-600">
                                                {selectedAnalysis.total_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                            </td>
                                        </tr>
                                    </tfoot>
                                </table>
                            </div>
                        </div>
                    ) : (
                        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 flex flex-col items-center justify-center min-h-[400px] text-center">
                            <div className="p-3 bg-slate-50 rounded-full mb-4">
                                <Eye className="w-8 h-8 text-slate-300" />
                            </div>
                            <p className="text-slate-500">Detayları görüntülemek için bir analiz seçin.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

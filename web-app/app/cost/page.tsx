"use client";

import { useState, useEffect, Suspense } from 'react';
import { Plus, Trash2, Save, FileDown, Loader2, Search, Calculator, Archive, X } from 'lucide-react';
import { useCart } from '@/context/CartContext';
import { useNotification } from '@/context/NotificationContext';
import { useSearchParams } from 'next/navigation';
import api from '@/lib/api';
import * as XLSX from 'xlsx';
import PozSelectorModal from '@/components/PozSelectorModal';
import { cn } from '@/lib/utils';

type CostItem = {
    id: string; // Temporary ID for frontend
    poz_no: string;
    description: string;
    unit: string;
    quantity: number;
    unit_price: number;
    total_price: number;
}

function CostEstimatorContent() {
    const searchParams = useSearchParams();
    const projectId = searchParams.get('id');
    const { items: cartItems, clearCart } = useCart();
    const { showNotification } = useNotification();
    const [items, setItems] = useState<CostItem[]>([]);
    const [projectName, setProjectName] = useState("Yeni Proje");
    const [loading, setLoading] = useState(false);
    const [saveLoading, setSaveLoading] = useState(false);
    const [isPozModalOpen, setPozModalOpen] = useState(false);

    // Load existing project if ID is provided
    useEffect(() => {
        if (projectId) {
            setLoading(true);
            api.get(`/projects/${projectId}`)
                .then(res => {
                    const project = res.data;
                    setProjectName(project.name);
                    const mappedItems = project.items.map((item: any) => ({
                        id: item.id.toString(),
                        poz_no: item.poz_no,
                        description: item.description,
                        unit: item.unit,
                        quantity: item.quantity,
                        unit_price: item.unit_price,
                        total_price: item.total_price
                    }));
                    setItems(mappedItems);
                })
                .catch(err => {
                    console.error("Project load error:", err);
                    showNotification("Proje yüklenirken hata oluştu.", "error");
                })
                .finally(() => setLoading(false));
        }
    }, [projectId]);

    // Sync from cart on mount (only for new projects)
    useEffect(() => {
        if (!projectId && cartItems.length > 0 && items.length === 0) {
            const mapped = cartItems.map((poz: any) => ({
                id: Math.random().toString(36).substr(2, 9),
                poz_no: poz.poz_no,
                description: poz.description,
                unit: poz.unit,
                quantity: 1,
                unit_price: parseFloat(poz.unit_price?.replace(/\./g, '').replace(',', '.') || '0'),
                total_price: parseFloat(poz.unit_price?.replace(/\./g, '').replace(',', '.') || '0')
            }));
            setItems(mapped);
        }
    }, [cartItems, projectId]);

    const handleSave = async () => {
        setSaveLoading(true);
        try {
            const payload = {
                name: projectName,
                items: items.map(i => ({
                    poz_no: i.poz_no,
                    description: i.description,
                    unit: i.unit,
                    quantity: i.quantity,
                    unit_price: i.unit_price
                }))
            };

            if (projectId) {
                await api.put(`/projects/${projectId}`, payload);
            } else {
                await api.post('/projects', payload);
            }

            showNotification("Proje başarıyla kaydedildi!", "success");
        } catch (e) {
            console.error(e);
            showNotification("Kaydetme sırasında hata oluştu.", "error");
        } finally {
            setSaveLoading(false);
        }
    }

    const handleExportExcel = () => {
        const data = items.map(item => ({
            "Poz No": item.poz_no,
            "Açıklama": item.description,
            "Birim": item.unit,
            "Miktar": item.quantity,
            "Birim Fiyat": item.unit_price,
            "Tutar": item.total_price
        }));

        const ws = XLSX.utils.json_to_sheet(data);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Maliyet Cetveli");
        XLSX.writeFile(wb, `${projectName}_Maliyet_Hesabi.xlsx`);
    };

    // Calculate totals
    const totalAmount = items.reduce((sum, item) => sum + item.total_price, 0);

    const handleAddItem = (poz: any) => {
        const newItem: CostItem = {
            id: Math.random().toString(36).substr(2, 9),
            poz_no: poz.poz_no || "",
            description: poz.description || "Yeni Kalem",
            unit: poz.unit || "adet",
            quantity: 1,
            unit_price: typeof poz.unit_price === 'number'
                ? poz.unit_price
                : parseFloat(String(poz.unit_price || '0').replace(/\./g, '').replace(',', '.')),
            total_price: 0
        };
        newItem.total_price = newItem.quantity * newItem.unit_price;
        setItems([...items, newItem]);
    }

    const updateItem = (id: string, field: keyof CostItem, value: any) => {
        setItems(items.map(item => {
            if (item.id === id) {
                const updated = { ...item, [field]: value };
                if (field === 'quantity' || field === 'unit_price') {
                    updated.total_price = updated.quantity * updated.unit_price;
                }
                return updated;
            }
            return item;
        }));
    }

    const removeItem = (id: string) => {
        setItems(items.filter(item => item.id !== id));
    }

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] text-[#71717a]">
                <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
                <p className="font-medium animate-pulse">Proje yükleniyor...</p>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Header Section */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-2 border-b border-[#27272a]/50">
                <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2 mb-2">
                        <Calculator className="w-4 h-4 text-blue-500" />
                        <span className="text-[10px] font-bold text-[#71717a] uppercase tracking-[0.2em]">Maliyet Hesabı</span>
                    </div>
                    <input
                        type="text"
                        value={projectName}
                        onChange={(e) => setProjectName(e.target.value)}
                        className="text-3xl font-bold text-[#fafafa] bg-transparent border-none focus:ring-0 p-0 w-full placeholder-[#27272a] tracking-tight"
                        placeholder="Proje Adı Girin..."
                    />
                    <p className="text-[#71717a] text-sm">Proje maliyet cetveli oluşturun ve yönetin.</p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => { setItems([]); clearCart(); }}
                        className="px-4 py-2 text-[#71717a] hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-all font-bold text-sm"
                    >
                        Temizle
                    </button>
                    <button
                        onClick={handleExportExcel}
                        disabled={items.length === 0}
                        className="flex items-center px-4 py-2 bg-[#18181b] border border-[#27272a] text-[#fafafa] rounded-lg hover:border-[#3f3f46] hover:bg-[#27272a] disabled:opacity-30 transition-all font-bold text-sm"
                    >
                        <FileDown className="w-4 h-4 mr-2" />
                        Excel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saveLoading || items.length === 0}
                        className="flex items-center px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 transition-all font-bold shadow-lg shadow-blue-900/40 text-sm"
                    >
                        {saveLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                        Kaydet
                    </button>
                </div>
            </div>

            {/* Main Table Area */}
            <div className="bg-[#18181b] rounded-xl shadow-2xl border border-[#27272a] overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left border-collapse">
                        <thead>
                            <tr className="bg-black/40 text-[10px] font-bold uppercase text-[#71717a] tracking-[0.1em] border-b border-[#27272a]">
                                <th className="px-6 py-4 w-40">Poz No</th>
                                <th className="px-6 py-4">Açıklama</th>
                                <th className="px-6 py-4 w-24">Birim</th>
                                <th className="px-6 py-4 w-32 text-right">Miktar</th>
                                <th className="px-6 py-4 w-40 text-right">Birim Fiyat</th>
                                <th className="px-6 py-4 w-40 text-right">Tutar</th>
                                <th className="px-6 py-4 w-12"></th>
                            </tr>
                        </thead>
                        <tbody className="bg-[#09090b]/50">
                            {items.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="h-64 text-center">
                                        <div className="flex flex-col items-center justify-center space-y-4">
                                            <div className="p-4 bg-[#18181b] rounded-full text-[#27272a] border border-[#27272a]">
                                                <Archive className="w-8 h-8" />
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-[#fafafa] font-bold">Liste Henüz Boş</p>
                                                <p className="text-[#52525b] text-xs">Aşağıdaki butonları kullanarak kalem ekleyin.</p>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                items.map((item, index) => (
                                    <tr key={item.id} className="group border-b border-[#18181b] hover:bg-[#18181b]/50 transition-colors">
                                        <td className="px-6 py-3">
                                            <input
                                                type="text"
                                                value={item.poz_no}
                                                onChange={(e) => updateItem(item.id, 'poz_no', e.target.value)}
                                                className="w-full bg-transparent border-none focus:ring-0 p-0 font-mono text-[11px] font-bold text-blue-500 placeholder-[#27272a]"
                                                placeholder="POZ NO"
                                            />
                                        </td>
                                        <td className="px-6 py-3">
                                            <input
                                                type="text"
                                                value={item.description}
                                                onChange={(e) => updateItem(item.id, 'description', e.target.value)}
                                                className="w-full bg-transparent border-none focus:ring-0 p-0 text-sm text-[#fafafa] font-medium placeholder-[#3f3f46]"
                                                placeholder="İmalat Açıklaması"
                                            />
                                        </td>
                                        <td className="px-6 py-3">
                                            <input
                                                type="text"
                                                value={item.unit}
                                                onChange={(e) => updateItem(item.id, 'unit', e.target.value)}
                                                className="w-full bg-transparent border-none focus:ring-0 p-0 text-xs font-bold text-[#71717a] uppercase placeholder-[#27272a]"
                                                placeholder="BİRİM"
                                            />
                                        </td>
                                        <td className="px-6 py-3">
                                            <input
                                                type="number"
                                                value={item.quantity}
                                                onChange={(e) => updateItem(item.id, 'quantity', parseFloat(e.target.value) || 0)}
                                                className="w-full bg-[#18181b] border border-[#27272a] rounded px-2 py-1 text-right focus:ring-1 focus:ring-blue-500/50 outline-none text-[#fafafa] font-mono text-xs transition-all"
                                            />
                                        </td>
                                        <td className="px-6 py-3 text-right font-mono text-[#a1a1aa] text-sm tabular-nums">
                                            {item.unit_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                        </td>
                                        <td className="px-6 py-3 text-right font-mono font-bold text-white text-sm tabular-nums">
                                            {item.total_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                        </td>
                                        <td className="px-6 py-3 text-center">
                                            <button
                                                onClick={() => removeItem(item.id)}
                                                className="text-[#3f3f46] hover:text-red-500 transition-colors p-2"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                        <tfoot className="bg-black/60 sticky bottom-0">
                            <tr>
                                <td colSpan={5} className="px-6 py-6 text-right font-bold text-[#71717a] text-[10px] uppercase tracking-[0.2em] border-t border-[#27272a]">Genel Yaklaşık Maliyet</td>
                                <td className="px-6 py-6 text-right font-mono font-black text-white text-2xl tracking-tighter border-t border-[#27272a]">
                                    {totalAmount.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} <span className="text-sm font-bold text-[#71717a]">TL</span>
                                </td>
                                <td className="border-t border-[#27272a]"></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>

            {/* Quick Action Footer Boxes */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <button
                    onClick={() => setPozModalOpen(true)}
                    className="group p-8 rounded-2xl border border-[#27272a] bg-[#18181b] hover:border-blue-500/50 transition-all text-center space-y-3 relative overflow-hidden"
                >
                    <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                        <Search className="w-24 h-24 text-white" />
                    </div>
                    <div className="w-12 h-12 bg-blue-600/10 rounded-xl flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
                        <Search className="w-6 h-6 text-blue-500" />
                    </div>
                    <div className="space-y-1">
                        <h3 className="text-lg font-bold text-white">Poz Veritabanı</h3>
                        <p className="text-sm text-[#71717a]">Yüz binlerce resmi poz arasından seçim yapın.</p>
                    </div>
                </button>

                <button
                    onClick={() => handleAddItem({})}
                    className="group p-8 rounded-2xl border border-dashed border-[#27272a] bg-transparent hover:border-[#3f3f46] hover:bg-[#18181b]/30 transition-all text-center space-y-3"
                >
                    <div className="w-12 h-12 bg-zinc-800 rounded-xl flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
                        <Plus className="w-6 h-6 text-[#71717a]" />
                    </div>
                    <div className="space-y-1">
                        <h3 className="text-lg font-bold text-[#fafafa]">Manuel Kalem</h3>
                        <p className="text-sm text-[#52525b]">Listeye özel imalat veya piyasa fiyatı ekleyin.</p>
                    </div>
                </button>
            </div>

            <PozSelectorModal
                isOpen={isPozModalOpen}
                onClose={() => setPozModalOpen(false)}
                onSelect={(poz) => handleAddItem(poz)}
            />
        </div>
    );
}

export default function CostEstimatorPage() {
    return (
        <div className="min-h-screen bg-[#09090b] p-6 lg:p-10 font-inter antialiased">
            <Suspense fallback={
                <div className="flex flex-col items-center justify-center min-h-[400px] text-[#71717a]">
                    <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
                    <p className="animate-pulse">Modüller hazırlanıyor...</p>
                </div>
            }>
                <CostEstimatorContent />
            </Suspense>
        </div>
    );
}


"use client";

import { useState, useEffect, Suspense } from 'react';
import { Plus, Trash2, Save, FileDown, Loader2, Search } from 'lucide-react';
import { useCart } from '@/context/CartContext';
import { useSearchParams } from 'next/navigation';
import api from '@/lib/api';
import * as XLSX from 'xlsx';
import PozSelectorModal from '@/components/PozSelectorModal';

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
                    alert("Proje yüklenirken hata oluştu.");
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
                unit_price: parseFloat(poz.unit_price?.replace('.', '').replace(',', '.') || '0'),
                total_price: parseFloat(poz.unit_price?.replace('.', '').replace(',', '.') || '0')
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

            alert("Proje başarıyla kaydedildi!");
        } catch (e) {
            console.error(e);
            alert("Kaydetme sırasında hata oluştu.");
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
        // This will be connected to a Poz Selector Modal later
        const newItem: CostItem = {
            id: Math.random().toString(36).substr(2, 9),
            poz_no: poz.poz_no || "Yeni Poz",
            description: poz.description || "",
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
            <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-400">
                <Loader2 className="w-8 h-8 animate-spin mb-4" />
                <p>Proje yükleniyor...</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex-1">
                    <input
                        type="text"
                        value={projectName}
                        onChange={(e) => setProjectName(e.target.value)}
                        className="text-2xl font-bold text-slate-800 bg-transparent border-none focus:ring-0 p-0 w-full"
                        placeholder="Proje Adı Girin..."
                    />
                    <p className="text-slate-500">Proje maliyet cetveli oluşturun.</p>
                </div>
                <div className="flex space-x-2">
                    <button
                        onClick={() => { setItems([]); clearCart(); }}
                        className="flex items-center px-4 py-2 bg-white border border-slate-200 text-red-600 rounded-lg hover:bg-red-50"
                    >
                        Temizle
                    </button>
                    <button
                        onClick={handleExportExcel}
                        disabled={items.length === 0}
                        className="flex items-center px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg hover:bg-slate-50 disabled:opacity-50"
                    >
                        <FileDown className="w-4 h-4 mr-2" />
                        Excel İndir
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saveLoading || items.length === 0}
                        className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                        {saveLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                        Kaydet
                    </button>
                </div>
            </div>

            {/* Calculations Table */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                <table className="w-full text-sm text-left">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-medium">
                        <tr>
                            <th className="px-4 py-3 w-32">Poz No</th>
                            <th className="px-4 py-3">Açıklama</th>
                            <th className="px-4 py-3 w-24">Birim</th>
                            <th className="px-4 py-3 w-32 text-right">Miktar</th>
                            <th className="px-4 py-3 w-32 text-right">Birim Fiyat</th>
                            <th className="px-4 py-3 w-32 text-right">Tutar</th>
                            <th className="px-4 py-3 w-12"></th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {items.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="h-48 text-center text-slate-400">
                                    <div className="flex flex-col items-center">
                                        <div className="p-3 bg-slate-50 rounded-full mb-3">
                                            <Plus className="w-6 h-6 text-slate-300" />
                                        </div>
                                        <p>Henüz poz eklenmedi.</p>
                                        <div className="flex gap-3 mt-4">
                                            <button
                                                onClick={() => setPozModalOpen(true)}
                                                className="px-4 py-2 bg-blue-50 text-blue-600 rounded-lg font-medium hover:bg-blue-100 transition-colors flex items-center"
                                            >
                                                <Search className="w-4 h-4 mr-2" />
                                                Kayıtlı Pozlardan Ekle
                                            </button>
                                            <button
                                                onClick={() => handleAddItem({})}
                                                className="px-4 py-2 text-slate-600 hover:text-slate-900 font-medium hover:underline"
                                            >
                                                Manuel Poz Ekle
                                            </button>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            items.map(item => (
                                <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                                    <td className="px-4 py-2">
                                        <input
                                            type="text"
                                            value={item.poz_no}
                                            onChange={(e) => updateItem(item.id, 'poz_no', e.target.value)}
                                            className="w-full bg-transparent border-none focus:ring-0 p-0 font-medium text-slate-900"
                                        />
                                    </td>
                                    <td className="px-4 py-2">
                                        <input
                                            type="text"
                                            value={item.description}
                                            onChange={(e) => updateItem(item.id, 'description', e.target.value)}
                                            className="w-full bg-transparent border-none focus:ring-0 p-0 text-slate-600"
                                        />
                                    </td>
                                    <td className="px-4 py-2">
                                        <input
                                            type="text"
                                            value={item.unit}
                                            onChange={(e) => updateItem(item.id, 'unit', e.target.value)}
                                            className="w-full bg-transparent border-none focus:ring-0 p-0 text-slate-500"
                                        />
                                    </td>
                                    <td className="px-4 py-2">
                                        <input
                                            type="number"
                                            value={item.quantity}
                                            onChange={(e) => updateItem(item.id, 'quantity', parseFloat(e.target.value) || 0)}
                                            className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-right focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                                        />
                                    </td>
                                    <td className="px-4 py-2 text-right font-mono text-slate-600">
                                        {item.unit_price.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} TL
                                    </td>
                                    <td className="px-4 py-2 text-right font-mono font-medium text-slate-900">
                                        {item.total_price.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} TL
                                    </td>
                                    <td className="px-4 py-2 text-center">
                                        <button
                                            onClick={() => removeItem(item.id)}
                                            className="text-slate-400 hover:text-red-600 transition-colors p-1"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                    <tfoot className="bg-slate-50 border-t border-slate-200">
                        <tr>
                            <td colSpan={5} className="px-4 py-4 text-right font-bold text-slate-600">GENEL TOPLAM</td>
                            <td className="px-4 py-4 text-right font-bold text-slate-900 text-lg">
                                {totalAmount.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} TL
                            </td>
                            <td></td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <div className="grid grid-cols-2 gap-4">
                <button
                    onClick={() => setPozModalOpen(true)}
                    className="w-full py-3 border-2 border-dashed border-blue-200 bg-blue-50/50 rounded-xl text-blue-600 hover:bg-blue-50 hover:border-blue-300 transition-all flex items-center justify-center font-medium"
                >
                    <Search className="w-5 h-5 mr-2" />
                    Kayıtlı Pozlardan Ekle
                </button>
                <button
                    onClick={() => handleAddItem({})}
                    className="w-full py-3 border-2 border-dashed border-slate-200 rounded-xl text-slate-500 hover:border-slate-300 hover:text-slate-700 transition-all flex items-center justify-center font-medium"
                >
                    <Plus className="w-5 h-5 mr-1" />
                    Manuel Poz Ekle
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
        <Suspense fallback={
            <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-400">
                <Loader2 className="w-8 h-8 animate-spin mb-4" />
                <p>Sayfa yükleniyor...</p>
            </div>
        }>
            <CostEstimatorContent />
        </Suspense>
    );
}

"use client";

import { useState } from 'react';
import { Sparkles, Loader2, Plus, Save, FileDown, Trash2, Info, Calculator, GraduationCap, X } from 'lucide-react';
import api from '@/lib/api';
import { useCart } from '@/context/CartContext';
import { useNotification } from '@/context/NotificationContext';
import { cn } from '@/lib/utils';
import * as XLSX from 'xlsx';

type AIComponent = {
    id: string;
    type: string;
    code: string;
    name: string;
    unit: string;
    quantity: number;
    unit_price: number;
    total_price: number;
    price_source?: string;
}

type AIResult = {
    suggested_unit?: string;
    unit?: string;
    explanation: string;
    components: AIComponent[];
}

export default function AnalysisPage() {
    const [description, setDescription] = useState("");
    const [displayUnit, setDisplayUnit] = useState("m2");
    const [loading, setLoading] = useState(false);
    const [saveLoading, setSaveLoading] = useState(false);
    const [result, setResult] = useState<AIResult | null>(null);
    const [analysisName, setAnalysisName] = useState("");
    const { addItem } = useCart();
    const { showNotification } = useNotification();

    // Feedback modal states
    const [showFeedbackModal, setShowFeedbackModal] = useState(false);
    const [feedbackLoading, setFeedbackLoading] = useState(false);
    const [correctionType, setCorrectionType] = useState("wrong_method");
    const [correctionDescription, setCorrectionDescription] = useState("");
    const [refineLoading, setRefineLoading] = useState(false);
    const [selectedCompForDetail, setSelectedCompForDetail] = useState<AIComponent | null>(null);

    const handleAnalyze = async () => {
        if (!description) return;
        setLoading(true);
        setResult(null);
        try {
            const res = await api.post('/ai/analyze', {
                description,
                unit: "m2"  // AI bu bilgiyi referans alacak, kendi önerdiği birimi döndürecek
            });
            // Her component'a benzersiz ID ekle
            const components = res.data.components.map((comp: any, idx: number) => ({
                ...comp,
                id: `comp-${Date.now()}-${idx}`
            }));
            setResult({ ...res.data, components });
            setDisplayUnit(res.data.unit || res.data.suggested_unit || "m2");
            setAnalysisName(description);
        } catch (e: any) {
            console.error(e);
            showNotification("Analiz sırasında bir hata oluştu: " + (e.response?.data?.detail || e.message), "error");
        } finally {
            setLoading(false);
        }
    };

    const updateComponent = (id: string, field: keyof AIComponent, value: any) => {
        if (!result) return;

        const updatedComponents = result.components.map(comp => {
            if (comp.id === id) {
                const updated = { ...comp, [field]: value };
                // Tutarı yeniden hesapla
                if (field === 'quantity' || field === 'unit_price') {
                    updated.total_price = updated.quantity * updated.unit_price;
                }
                return updated;
            }
            return comp;
        });

        setResult({ ...result, components: updatedComponents });
    };

    const removeComponent = (id: string) => {
        if (!result) return;
        const updatedComponents = result.components.filter(comp => comp.id !== id);
        setResult({ ...result, components: updatedComponents });
    };

    const addNewComponent = () => {
        if (!result) return;
        const newComponent: AIComponent = {
            id: `comp-${Date.now()}`,
            type: 'Malzeme',
            code: '',
            name: 'Yeni Kalem',
            unit: 'adet',
            quantity: 1,
            unit_price: 0,
            total_price: 0
        };
        setResult({ ...result, components: [...result.components, newComponent] });
    };

    const handleSaveAsProject = async () => {
        if (!result) return;
        setSaveLoading(true);
        try {
            const payload = {
                name: analysisName || description,
                description: result.explanation,
                items: result.components.map(comp => ({
                    poz_no: comp.code,
                    description: comp.name,
                    unit: comp.unit,
                    quantity: comp.quantity,
                    unit_price: comp.unit_price
                }))
            };

            await api.post('/projects', payload);
            showNotification("Analiz proje olarak kaydedildi!", "success");
        } catch (e) {
            console.error(e);
            showNotification("Kaydetme sırasında hata oluştu.", "error");
        } finally {
            setSaveLoading(false);
        }
    };

    const handleSaveAnalysis = async () => {
        if (!result) return;
        setSaveLoading(true);
        try {
            const payload = {
                name: analysisName || description,
                description: description,
                unit: displayUnit,
                explanation: result.explanation,
                components: result.components.map(comp => ({
                    type: comp.type,
                    code: comp.code,
                    name: comp.name,
                    unit: comp.unit,
                    quantity: comp.quantity,
                    unit_price: comp.unit_price
                }))
            };

            await api.post('/analyses', payload);
            showNotification("Analiz kaydedildi!", "success");
        } catch (e) {
            console.error(e);
            showNotification("Kaydetme sırasında hata oluştu.", "error");
        } finally {
            setSaveLoading(false);
        }
    };

    const handleExportExcel = () => {
        if (!result) return;

        const data = result.components.map(comp => ({
            "Tür": comp.type,
            "Kod": comp.code,
            "Açıklama": comp.name,
            "Birim": comp.unit,
            "Miktar": comp.quantity,
            "Birim Fiyat": comp.unit_price,
            "Tutar": comp.total_price
        }));

        const ws = XLSX.utils.json_to_sheet(data);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Analiz");
        XLSX.writeFile(wb, `${analysisName || 'Analiz'}_Detay.xlsx`);
    };

    const handleRefineDescription = async () => {
        if (!correctionDescription.trim()) return;
        setRefineLoading(true);
        try {
            const res = await api.post('/ai/refine-feedback', { text: correctionDescription });
            if (res.data.refined_text) {
                setCorrectionDescription(res.data.refined_text);
            }
        } catch (e) {
            console.error(e);
            showNotification("İyileştirme sırasında hata oluştu.", "error");
        } finally {
            setRefineLoading(false);
        }
    };

    const handleAddAllToProject = () => {
        if (!result) return;
        result.components.forEach(comp => {
            addItem({
                poz_no: comp.code,
                description: comp.name,
                unit: comp.unit,
                unit_price: comp.unit_price.toString(),
                institution: "AI Generated",
                source_file: "AI Analysis"
            });
        });
        showNotification("Tüm kalemler projeye eklendi!", "success");
    };

    const handleSubmitFeedback = async () => {
        if (!result || !correctionDescription.trim()) {
            showNotification("Lütfen düzeltme açıklamasını girin.", "warning");
            return;
        }

        setFeedbackLoading(true);
        try {
            await api.post('/feedback', {
                original_prompt: description,
                original_unit: displayUnit,
                correction_type: correctionType,
                correction_description: correctionDescription,
                correct_components: result.components.map(comp => ({
                    type: comp.type,
                    code: comp.code,
                    name: comp.name,
                    unit: comp.unit,
                    quantity: comp.quantity,
                    unit_price: comp.unit_price
                })),
                keywords: description.toLowerCase().split(' ').filter(w => w.length > 2)
            });

            showNotification("Düzeltmeniz kaydedildi! AI bundan sonraki benzer sorgularda bu bilgiyi kullanacak.", "success");
            setShowFeedbackModal(false);
            setCorrectionDescription("");
        } catch (e: any) {
            console.error(e);
            showNotification("Kaydetme sırasında hata oluştu: " + (e.response?.data?.detail || e.message), "error");
        } finally {
            setFeedbackLoading(false);
        }
    };

    // Hesaplamalar
    const totalMaterial = result?.components
        .filter(c => c.type === 'Malzeme')
        .reduce((sum, c) => sum + c.total_price, 0) || 0;

    const totalLabor = result?.components
        .filter(c => c.type === 'İşçilik')
        .reduce((sum, c) => sum + c.total_price, 0) || 0;

    const totalTransport = result?.components
        .filter(c => c.type === 'Nakliye')
        .reduce((sum, c) => sum + c.total_price, 0) || 0;

    const subtotal = totalMaterial + totalLabor + totalTransport;
    const overhead = subtotal * 0.25; // %25 Yüklenici kârı ve genel giderler
    const grandTotal = subtotal + overhead;

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-slate-800 flex items-center">
                    <Sparkles className="w-6 h-6 mr-2 text-purple-600" />
                    AI Analiz Sihirbazı
                </h1>
                <p className="text-slate-500">Poz tanımı girin, AI sizin için detaylı analiz ve birim fiyat oluştursun.</p>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                    <div className="md:col-span-2 space-y-2">
                        <label className="text-sm font-medium text-slate-700">Poz Tanımı</label>
                        <input
                            type="text"
                            placeholder="Örn: 20 cm Gazbeton Duvar Örülmesi"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
                        />
                    </div>
                    <button
                        onClick={handleAnalyze}
                        disabled={loading || !description}
                        className="h-10 flex items-center justify-center px-6 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Analiz Et"}
                    </button>
                </div>
            </div>

            {result && (
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">
                    {/* Analiz Adı */}
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                        <label className="text-sm font-medium text-slate-700">Analiz Adı</label>
                        <input
                            type="text"
                            value={analysisName}
                            onChange={(e) => setAnalysisName(e.target.value)}
                            placeholder="Analiz adı girin..."
                            className="w-full mt-2 px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none text-lg font-medium"
                        />
                    </div>

                    {/* Explanation */}
                    <div className="bg-blue-50 border border-blue-100 rounded-xl p-6">
                        <div className="flex items-start">
                            <Info className="w-5 h-5 text-blue-600 mr-3 mt-0.5 flex-shrink-0" />
                            <div className="text-blue-800 text-sm leading-relaxed whitespace-pre-wrap">
                                {result.explanation}
                            </div>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-wrap gap-2">
                        <button
                            onClick={handleSaveAnalysis}
                            disabled={saveLoading}
                            className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors font-medium"
                        >
                            {saveLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                            Analizi Kaydet
                        </button>
                        <button
                            onClick={handleSaveAsProject}
                            disabled={saveLoading}
                            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors font-medium"
                        >
                            <Calculator className="w-4 h-4 mr-2" />
                            Proje Olarak Kaydet
                        </button>
                        <button
                            onClick={handleExportExcel}
                            className="flex items-center px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors font-medium"
                        >
                            <FileDown className="w-4 h-4 mr-2" />
                            Excel İndir
                        </button>
                        <button
                            onClick={handleAddAllToProject}
                            className="flex items-center px-4 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors font-medium"
                        >
                            <Plus className="w-4 h-4 mr-2" />
                            Maliyet Hesabına Ekle
                        </button>
                        <button
                            onClick={() => setShowFeedbackModal(true)}
                            className="flex items-center px-4 py-2 bg-amber-50 text-amber-700 rounded-lg hover:bg-amber-100 transition-colors font-medium border border-amber-200"
                        >
                            <GraduationCap className="w-4 h-4 mr-2" />
                            AI'ya Öğret
                        </button>
                    </div>

                    {/* Components Table */}
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                        <div className="p-4 border-b border-slate-100 flex justify-between items-center">
                            <h3 className="font-bold text-slate-800">Analiz Detayı</h3>
                            <button
                                onClick={addNewComponent}
                                className="text-sm flex items-center px-3 py-1.5 bg-slate-50 text-slate-700 rounded-lg hover:bg-slate-100 transition-colors font-medium"
                            >
                                <Plus className="w-4 h-4 mr-1" />
                                Kalem Ekle
                            </button>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm text-left">
                                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-medium">
                                    <tr>
                                        <th className="px-4 py-3 w-24">Tür</th>
                                        <th className="px-4 py-3 w-32">Kod</th>
                                        <th className="px-4 py-3">Adı</th>
                                        <th className="px-4 py-3 w-20">Birim</th>
                                        <th className="px-4 py-3 w-28 text-right">Miktar</th>
                                        <th className="px-4 py-3 w-32 text-right">B.Fiyat</th>
                                        <th className="px-4 py-3 w-32 text-right">Tutar</th>
                                        <th className="px-4 py-3 w-20"></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    {result.components.map((comp) => (
                                        <tr
                                            key={comp.id}
                                            onDoubleClick={() => setSelectedCompForDetail(comp)}
                                            className="hover:bg-slate-50 transition-colors cursor-pointer select-none"
                                            title="Detaylar için çift tıklayın"
                                        >
                                            <td className="px-4 py-3">
                                                <select
                                                    value={comp.type}
                                                    onChange={(e) => updateComponent(comp.id, 'type', e.target.value)}
                                                    className={cn(
                                                        "text-[10px] font-bold uppercase px-2 py-1 rounded border-none focus:ring-2 focus:ring-purple-500 outline-none cursor-pointer",
                                                        comp.type === 'Malzeme' ? 'bg-blue-100 text-blue-700' :
                                                            comp.type === 'İşçilik' ? 'bg-orange-100 text-orange-700' :
                                                                comp.type === 'Nakliye' ? 'bg-green-100 text-green-700' :
                                                                    'bg-slate-100 text-slate-700'
                                                    )}
                                                >
                                                    <option value="Malzeme">MALZEME</option>
                                                    <option value="İşçilik">İŞÇİLİK</option>
                                                    <option value="Nakliye">NAKLİYE</option>
                                                    <option value="Diğer">DİĞER</option>
                                                </select>
                                            </td>
                                            <td className="px-4 py-3">
                                                <input
                                                    type="text"
                                                    value={comp.code}
                                                    onChange={(e) => updateComponent(comp.id, 'code', e.target.value)}
                                                    className="w-full bg-transparent border-none focus:ring-0 p-0 text-slate-500 font-mono text-xs"
                                                    placeholder="Kod girin"
                                                />
                                            </td>
                                            <td className="px-4 py-3">
                                                <input
                                                    type="text"
                                                    value={comp.name}
                                                    onChange={(e) => updateComponent(comp.id, 'name', e.target.value)}
                                                    className="w-full bg-transparent border-none focus:ring-0 p-0 text-slate-800 font-medium"
                                                    placeholder="Açıklama girin"
                                                />
                                            </td>
                                            <td className="px-4 py-3">
                                                <input
                                                    type="text"
                                                    value={comp.unit}
                                                    onChange={(e) => updateComponent(comp.id, 'unit', e.target.value)}
                                                    className="w-full bg-transparent border-none focus:ring-0 p-0 text-slate-500"
                                                    placeholder="Birim"
                                                />
                                            </td>
                                            <td className="px-4 py-3">
                                                <input
                                                    type="number"
                                                    step="0.0001"
                                                    value={comp.quantity}
                                                    onChange={(e) => updateComponent(comp.id, 'quantity', parseFloat(e.target.value) || 0)}
                                                    className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-right focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
                                                />
                                            </td>
                                            <td className="px-4 py-3">
                                                <input
                                                    type="number"
                                                    step="0.01"
                                                    value={comp.unit_price}
                                                    onChange={(e) => updateComponent(comp.id, 'unit_price', parseFloat(e.target.value) || 0)}
                                                    className="w-full bg-white border border-slate-200 rounded px-2 py-1 text-right focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none"
                                                />
                                            </td>
                                            <td className="px-4 py-3 text-right font-medium text-slate-900">
                                                {comp.total_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                <button
                                                    onClick={() => removeComponent(comp.id)}
                                                    className="text-slate-400 hover:text-red-600 transition-colors p-1"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Yaklaşık Maliyet Özeti */}
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                        <div className="p-4 border-b border-slate-100">
                            <h3 className="font-bold text-slate-800 flex items-center">
                                <Calculator className="w-5 h-5 mr-2 text-blue-600" />
                                Yaklaşık Maliyet Özeti
                            </h3>
                        </div>
                        <div className="p-4 space-y-3">
                            <div className="flex justify-between items-center py-2">
                                <span className="text-slate-600">Malzeme Toplamı</span>
                                <span className="font-medium text-slate-800">
                                    {totalMaterial.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                </span>
                            </div>
                            <div className="flex justify-between items-center py-2">
                                <span className="text-slate-600">İşçilik Toplamı</span>
                                <span className="font-medium text-slate-800">
                                    {totalLabor.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                </span>
                            </div>
                            <div className="flex justify-between items-center py-2">
                                <span className="text-slate-600">Nakliye Toplamı</span>
                                <span className="font-medium text-slate-800">
                                    {totalTransport.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                </span>
                            </div>
                            <div className="border-t border-slate-200 pt-3 flex justify-between items-center py-2">
                                <span className="text-slate-700 font-medium">Malzeme + İşçilik + Nakliye</span>
                                <span className="font-bold text-slate-800">
                                    {subtotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                </span>
                            </div>
                            <div className="flex justify-between items-center py-2 text-slate-600">
                                <span>Yüklenici Kârı ve Genel Giderler (%25)</span>
                                <span className="font-medium">
                                    {overhead.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                </span>
                            </div>
                            <div className="border-t-2 border-slate-300 pt-3 flex justify-between items-center py-2">
                                <span className="text-lg font-bold text-slate-800">1 {displayUnit} Birim Fiyatı</span>
                                <span className="text-xl font-bold text-purple-600">
                                    {grandTotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* AI'ya Öğret Modal */}
            {showFeedbackModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                        {/* Modal Header */}
                        <div className="p-6 border-b border-slate-200 flex justify-between items-center">
                            <div className="flex items-center">
                                <GraduationCap className="w-6 h-6 text-amber-600 mr-3" />
                                <h2 className="text-xl font-bold text-slate-800">AI'ya Öğret</h2>
                            </div>
                            <button
                                onClick={() => setShowFeedbackModal(false)}
                                className="text-slate-400 hover:text-slate-600 transition-colors"
                            >
                                <X className="w-6 h-6" />
                            </button>
                        </div>

                        {/* Modal Content */}
                        <div className="p-6 space-y-6">
                            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                                <p className="text-amber-800 text-sm">
                                    <strong>Neden kullanılır?</strong> AI hatalı bir analiz yaptığında, doğru sonuçları manuel düzelttikten sonra buradan gönderirsiniz.
                                    AI, gelecekteki benzer sorgularda bu düzeltmeyi referans alacaktır.
                                </p>
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium text-slate-700">Düzeltme Türü</label>
                                <select
                                    value={correctionType}
                                    onChange={(e) => setCorrectionType(e.target.value)}
                                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent outline-none"
                                >
                                    <option value="wrong_method">Yanlış Yöntem (örn. elle yerine makine)</option>
                                    <option value="missing_item">Eksik Kalem (örn. nakliye eklenmemiş)</option>
                                    <option value="wrong_price">Yanlış Fiyat</option>
                                    <option value="wrong_quantity">Yanlış Miktar</option>
                                    <option value="other">Diğer</option>
                                </select>
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium text-slate-700">Düzeltme Açıklaması</label>
                                <div className="relative group">
                                    <textarea
                                        value={correctionDescription}
                                        onChange={(e) => setCorrectionDescription(e.target.value)}
                                        placeholder="Örn: Beton santrali ile taş duvar demek, beton döküm işçiliği ve hazır beton malzemesi demektir, taş duvar malzemeleri değil..."
                                        rows={4}
                                        className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent outline-none resize-none pr-12"
                                    />
                                    <button
                                        onClick={handleRefineDescription}
                                        disabled={refineLoading || !correctionDescription.trim()}
                                        className="absolute right-3 top-3 p-2 bg-amber-50 text-amber-600 rounded-lg hover:bg-amber-100 transition-all border border-amber-200 shadow-sm disabled:opacity-50"
                                        title="AI ile profesyonelce düzenle"
                                    >
                                        {refineLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                                    </button>
                                </div>
                                <p className="text-xs text-slate-500">
                                    AI'nın hatasını açıkça belirtin. Bu açıklama gelecekteki sorgularda referans olarak kullanılacak.
                                </p>
                            </div>

                            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                                <h3 className="font-medium text-slate-700 mb-2">Gönderilecek Bileşenler ({result?.components.length || 0}):</h3>
                                <div className="max-h-40 overflow-y-auto space-y-1 text-sm">
                                    {result?.components.map((comp) => (
                                        <div key={comp.id} className="flex items-center justify-between text-slate-600">
                                            <span>
                                                <span className={cn(
                                                    "text-[10px] font-bold uppercase px-1.5 py-0.5 rounded mr-2",
                                                    comp.type === 'Malzeme' ? 'bg-blue-100 text-blue-700' :
                                                        comp.type === 'İşçilik' ? 'bg-orange-100 text-orange-700' :
                                                            comp.type === 'Nakliye' ? 'bg-green-100 text-green-700' :
                                                                'bg-slate-100 text-slate-700'
                                                )}>
                                                    {comp.type}
                                                </span>
                                                {comp.name}
                                            </span>
                                            <span className="text-slate-500">
                                                {comp.quantity} {comp.unit} × {comp.unit_price.toFixed(2)} TL
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <h3 className="font-medium text-blue-800 mb-1">Orijinal Sorgu</h3>
                                <p className="text-blue-700 font-mono text-sm">{description}</p>
                                <p className="text-blue-600 text-xs mt-1">Birim: {displayUnit}</p>
                            </div>
                        </div>

                        {/* Modal Footer */}
                        <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
                            <button
                                onClick={() => setShowFeedbackModal(false)}
                                disabled={feedbackLoading}
                                className="px-4 py-2 text-slate-700 hover:bg-slate-100 rounded-lg transition-colors font-medium"
                            >
                                İptal
                            </button>
                            <button
                                onClick={handleSubmitFeedback}
                                disabled={feedbackLoading || !correctionDescription.trim()}
                                className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center"
                            >
                                {feedbackLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <GraduationCap className="w-4 h-4 mr-2" />}
                                AI'ya Öğret
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* Poz Detay Modal */}
            {selectedCompForDetail && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedCompForDetail(null)}>
                    <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden animate-in zoom-in-95 duration-200" onClick={e => e.stopPropagation()}>
                        <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                            <div className="flex items-center">
                                <Info className="w-5 h-5 text-blue-600 mr-2" />
                                <h2 className="text-lg font-bold text-slate-800">Poz Detayı</h2>
                            </div>
                            <button onClick={() => setSelectedCompForDetail(null)} className="text-slate-400 hover:text-slate-600 transition-colors">
                                <X className="w-6 h-6" />
                            </button>
                        </div>

                        <div className="p-6 space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Poz Kodu</label>
                                    <div className="font-mono text-sm text-slate-700 bg-slate-50 px-2 py-1 rounded border border-slate-100">
                                        {selectedCompForDetail.code || 'Kodsuz'}
                                    </div>
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Tür</label>
                                    <div className="text-sm">
                                        <span className={cn(
                                            "px-2 py-0.5 rounded text-[10px] font-bold uppercase",
                                            selectedCompForDetail.type === 'Malzeme' ? 'bg-blue-100 text-blue-700' :
                                                selectedCompForDetail.type === 'İşçilik' ? 'bg-orange-100 text-orange-700' :
                                                    selectedCompForDetail.type === 'Nakliye' ? 'bg-green-100 text-green-700' :
                                                        'bg-slate-100 text-slate-700'
                                        )}>
                                            {selectedCompForDetail.type}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-1">
                                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Açıklama</label>
                                <div className="text-slate-800 font-medium leading-relaxed">
                                    {selectedCompForDetail.name}
                                </div>
                            </div>

                            <div className="grid grid-cols-3 gap-4 py-4 border-y border-slate-50">
                                <div className="text-center">
                                    <div className="text-xs text-slate-400 mb-1">Miktar</div>
                                    <div className="font-bold text-slate-700">{selectedCompForDetail.quantity} {selectedCompForDetail.unit}</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-xs text-slate-400 mb-1">Birim Fiyat</div>
                                    <div className="font-bold text-slate-700">{selectedCompForDetail.unit_price.toLocaleString('tr-TR')} TL</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-xs text-slate-400 mb-1">Tutar</div>
                                    <div className="font-bold text-purple-600">{selectedCompForDetail.total_price.toLocaleString('tr-TR')} TL</div>
                                </div>
                            </div>

                            {/* Fiyat Kaynağı Bilgisi */}
                            {selectedCompForDetail.price_source && (
                                <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
                                    <div className="flex items-center text-blue-800 text-xs font-semibold mb-2">
                                        <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                                        FİYAT KAYNAĞI
                                    </div>
                                    <p className="text-blue-700 text-xs leading-normal">
                                        {selectedCompForDetail.price_source === 'exact_code_validated' && "Fiyat, veritabanındaki tam kod eşleşmesi ve açıklama doğrulaması ile getirilmiştir."}
                                        {selectedCompForDetail.price_source === 'description' && "Fiyat, benzer açıklama metinleri üzerinden AI destekli eşleştirme ile getirilmiştir."}
                                        {selectedCompForDetail.price_source === 'similar_code' && "Fiyat, benzer kod hiyerarşisi üzerinden tahmin edilerek getirilmiştir."}
                                        {selectedCompForDetail.price_source === 'ai_generated' && "Bu kalem için veritabanında kesin eşleşme bulunamadı, fiyat AI tarafından piyasa ortalamasına göre tahmin edildi."}
                                        {selectedCompForDetail.price_source === 'not_found' && "Veritabanında uygun fiyat bulunamadı."}
                                    </p>
                                </div>
                            )}
                        </div>

                        <div className="p-6 bg-slate-50 border-t border-slate-100 flex justify-end">
                            <button
                                onClick={() => setSelectedCompForDetail(null)}
                                className="px-6 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition-colors font-medium text-sm shadow-sm"
                            >
                                Kapat
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

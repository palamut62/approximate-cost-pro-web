"use client";

import { useState, useEffect, useRef } from 'react';
import { ChevronDown, Sparkles, Loader2, Plus, Save, FileDown, Trash2, Info, Calculator, GraduationCap, X, ArrowRight, AlertTriangle, FileText, Table, XCircle, Box, Copy, Search } from 'lucide-react';
import { motion } from 'framer-motion';
import api from '@/lib/api';
import AnalysisTable, { AnalysisData } from '@/components/AnalysisTable';
import { useCart } from '@/context/CartContext';
import { useNotification } from '@/context/NotificationContext';
import { useLLMUsage } from '@/context/LLMUsageContext';
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
    metadata?: {
        analysis_score: number;
        confidence_level: string;
        warnings: string[];
    };
    technical_description?: string;
    analysis_data?: AnalysisData;
    critic_review?: {
        status: string;
        issues: Array<{
            severity: string;
            category: string;
            message: string;
            suggestion: string;
        }>;
        suggestions: string[];
    };
    technical_specification?: string;
    advanced_metrics?: {
        consensus_score?: number;
        model_count?: number;
        consistency_score?: number;
        sample_count?: number;
        consistency_warning?: string;
        cot_enabled?: boolean;
    };
}

export default function AnalysisPage() {
    const [description, setDescription] = useState("");
    const [displayUnit, setDisplayUnit] = useState("otomatik");
    const [loading, setLoading] = useState(false);
    const [saveLoading, setSaveLoading] = useState(false);
    const [result, setResult] = useState<AIResult | null>(null);
    const [analysisName, setAnalysisName] = useState("");
    const { addItem } = useCart();
    const { showNotification } = useNotification();
    const { usageData, loading: usageLoading, refetch: refetchLLMUsage } = useLLMUsage();

    // Feedback modal states
    const [showFeedbackModal, setShowFeedbackModal] = useState(false);
    const [feedbackLoading, setFeedbackLoading] = useState(false);
    const [correctionType, setCorrectionType] = useState("wrong_method");
    const [correctionDescription, setCorrectionDescription] = useState("");
    const [refineLoading, setRefineLoading] = useState(false);
    const [selectedCompForDetail, setSelectedCompForDetail] = useState<AIComponent | null>(null);
    const [aiReviewLoading, setAiReviewLoading] = useState(false);
    const [feedbackModalTab, setFeedbackModalTab] = useState<'ai' | 'manual'>('ai');

    // AI request refinement
    const [refineRequestLoading, setRefineRequestLoading] = useState(false);

    // Textarea ref for auto-resize
    // State for sections visibility
    const [sections, setSections] = useState({ spec: true, analysis: true, cost: true });

    const toggleSection = (key: keyof typeof sections) => {
        setSections(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea based on content
    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 300) + 'px';
        }
    }, [description]);

    const handleAnalyze = async () => {
        if (!description) return;
        setLoading(true);
        setResult(null);
        try {
            const res = await api.post('/ai/analyze', {
                description,
                unit: "otomatik"  // AI imalat türüne göre otomatik birim belirleyecek
            });
            // Her component'a benzersiz ID ekle
            const components = res.data.components.map((comp: any, idx: number) => ({
                ...comp,
                id: `comp-${Date.now()}-${idx}`
            }));
            setResult({ ...res.data, components });
            setDisplayUnit(res.data.unit || res.data.suggested_unit || "m2");
            setAnalysisName(description);
            // AI isteğinden sonra kullanım verilerini güncelle
            refetchLLMUsage();
        } catch (e: any) {
            console.error("AI Analyze Error:", e);
            console.error("Error details:", {
                message: e.message,
                code: e.code,
                response: e.response?.data,
                status: e.response?.status,
                config: e.config
            });
            showNotification("Analiz sırasında bir hata oluştu: " + (e.response?.data?.detail || e.message || e.code), "error");
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
            // AI isteğinden sonra kullanım verilerini güncelle
            refetchLLMUsage();
        } catch (e) {
            console.error(e);
            showNotification("İyileştirme sırasında hata oluştu.", "error");
        } finally {
            setRefineLoading(false);
        }
    };

    const handleRefineRequest = async () => {
        if (!description.trim()) {
            showNotification("Lütfen önce bir talep yazın.", "warning");
            return;
        }
        setRefineRequestLoading(true);
        try {
            const res = await api.post('/ai/refine-request', { text: description });
            if (res.data.refined_text) {
                setDescription(res.data.refined_text);
                showNotification("Talebiniz profesyonel bir ifadeye dönüştürüldü!", "success");
            }
            // AI isteğinden sonra kullanım verilerini güncelle
            refetchLLMUsage();
        } catch (e) {
            console.error(e);
            showNotification("Profesyonelleştirme sırasında hata oluştu.", "error");
        } finally {
            setRefineRequestLoading(false);
        }
    };

    const generateMarkdown = (): string => {
        if (!result) return '';

        let md = `# ${analysisName || description}\n\n`;
        md += `**Birim:** ${displayUnit}\n\n`;
        md += `## Açıklama\n${result.explanation}\n\n`;

        if (result.technical_description) {
            md += `## Teknik Tarif\n${result.technical_description}\n\n`;
        }

        md += `## Analiz Detay Tablosu\n\n`;
        md += `| Tür | Kod | Açıklama | Birim | Miktar | B.Fiyat | Tutar |\n`;
        md += `|-----|-----|----------|-------|--------|---------|-------|\n`;

        result.components.forEach(c => {
            md += `| ${c.type} | ${c.code || '-'} | ${c.name} | ${c.unit} | ${c.quantity.toFixed(3)} | ${c.unit_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} | ${c.total_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} |\n`;
        });

        md += `\n## Maliyet Özeti\n\n`;
        md += `- **Malzeme Toplamı:** ${totalMaterial.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL\n`;
        md += `- **İşçilik Toplamı:** ${totalLabor.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL\n`;
        md += `- **Nakliye Toplamı:** ${totalTransport.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL\n`;
        md += `- **Ara Toplam:** ${subtotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL\n`;
        md += `- **Genel Gider (%25):** ${overhead.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL\n`;
        md += `- **Birim Fiyat (1 ${displayUnit}):** ${grandTotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL\n`;

        if (result.metadata?.warnings?.length) {
            md += `\n## Uyarılar\n\n`;
            result.metadata.warnings.forEach(w => {
                md += `- ⚠️ ${w}\n`;
            });
        }

        if (result.critic_review?.issues?.length) {
            md += `\n## Eleştirmen Analizi\n\n`;
            result.critic_review.issues.forEach(issue => {
                md += `### ${issue.category}\n`;
                md += `- **Durum:** ${issue.severity === 'critical' ? '🔴 Kritik' : '🟡 Uyarı'}\n`;
                md += `- **Mesaj:** ${issue.message}\n`;
                if (issue.suggestion) md += `- **Öneri:** ${issue.suggestion}\n`;
                md += `\n`;
            });
        }

        return md;
    };

    const handleCopyAsMarkdown = async () => {
        const md = generateMarkdown();
        try {
            await navigator.clipboard.writeText(md);
            showNotification("Analiz Markdown olarak kopyalandı!", "success");
        } catch (e) {
            console.error(e);
            showNotification("Kopyalama başarısız oldu.", "error");
        }
    };

    const handleLearnRule = async (issue: any) => {
        if (!description) return;

        try {
            // Basit bir kural çıkarımı:
            // "Malzeme var ama işçilik bulunamadı" -> Eksik olan şey "işçilik"
            let requiredItem = "Bilinmeyen Öğe";

            if (issue.message.toLowerCase().includes("işçilik")) requiredItem = "İşçilik";
            else if (issue.message.toLowerCase().includes("demir")) requiredItem = "Demir/Donatı";
            else if (issue.message.toLowerCase().includes("kalıp")) requiredItem = "Kalıp";
            else if (issue.message.toLowerCase().includes("harç")) requiredItem = "Harç";
            else if (issue.category === "Eksik Kalem") {
                // Mesajdan çekmeye çalış: "X bulunamadı"
                const match = issue.message.match(/([\w\sçğıöşüÇĞİÖŞÜ]+)\s+(bulunamadı|eksik|yok)/i);
                if (match) requiredItem = match[1].trim();
            }

            await api.post('/ai/learn-rule', {
                trigger_keywords: description.split(" ").filter((w: string) => w.length > 3),
                required_item_name: requiredItem,
                condition_text: `"${description}" benzeri işlerde ${requiredItem} olmalı`
            });

            showNotification("Kural kaydedildi! AI artık bunu hatırlayacak.", "success");

        } catch (e) {
            console.error(e);
            showNotification("Kural kaydedilemedi.", "error");
        }
    };

    const handleAIReview = async () => {
        if (!result) return;
        setAiReviewLoading(true);
        try {
            const payload = {
                description: description,
                components: result.components.map(c => ({
                    type: c.type,
                    code: c.code,
                    name: c.name,
                    unit: c.unit,
                    quantity: c.quantity,
                    unit_price: c.unit_price,
                    total_price: c.total_price
                })),
                totals: { subtotal, overhead, grandTotal },
                unit: displayUnit
            };

            const res = await api.post('/ai/review-analysis', payload);

            // Update result with new critic review
            setResult(prev => prev ? {
                ...prev,
                critic_review: res.data.critic_review,
                metadata: {
                    analysis_score: res.data.updated_score || prev.metadata?.analysis_score || 70,
                    confidence_level: prev.metadata?.confidence_level || 'medium',
                    warnings: [...(prev.metadata?.warnings || []), ...(res.data.new_warnings || [])]
                }
            } : null);

            refetchLLMUsage();
            showNotification("AI analiz tamamlandı! Sonuçlar güncellendi.", "success");
        } catch (e: any) {
            console.error(e);
            showNotification("AI analiz sırasında hata: " + (e.response?.data?.detail || e.message), "error");
        } finally {
            setAiReviewLoading(false);
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
        <div className="flex flex-col h-full relative">
            {/* Usage Stats Card */}
            <div className="absolute top-4 right-4 z-50 hidden md:block">
                <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-4 shadow-2xl flex flex-col gap-2 min-w-[200px]">
                    <div className="flex items-center gap-2 mb-1">
                        <div className="p-1.5 bg-purple-500/10 rounded-lg">
                            <Sparkles className="w-3 h-3 text-purple-500" />
                        </div>
                        <span className="text-[10px] font-bold text-[#fafafa] uppercase tracking-widest">AI Limitleri</span>
                    </div>
                    {usageLoading ? (
                        <div className="space-y-2 py-1">
                            <div className="h-3 w-full bg-[#27272a] animate-pulse rounded"></div>
                            <div className="h-3 w-3/4 bg-[#27272a] animate-pulse rounded"></div>
                        </div>
                    ) : (
                        <div className="space-y-1">
                            <div className="flex justify-between items-end">
                                <span className="text-xs text-[#a1a1aa]">Kalan</span>
                                <span className={cn("text-sm font-bold font-mono", (usageData.remaining ?? 0) < 5 ? "text-red-500" : "text-green-500")}>
                                    ${(usageData.remaining ?? 0).toFixed(2)}
                                </span>
                            </div>
                            <div className="flex justify-between items-end">
                                <span className="text-xs text-[#a1a1aa]">Harcanan</span>
                                <span className="text-sm font-bold text-[#fafafa] font-mono">${(usageData.total_usage ?? 0).toFixed(2)}</span>
                            </div>
                            <div className="w-full h-px bg-[#27272a] my-1" />
                            <div className="flex justify-between items-end">
                                <span className="text-xs text-[#a1a1aa]">Limit</span>
                                <span className="text-sm font-bold text-[#71717a] font-mono">${(usageData.total_credits ?? 0).toFixed(2)}</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>
            {!result ? (
                // Initial State - Centered Search (Refined Bolt Aesthetic)
                <div className="flex-1 flex flex-col items-center justify-start pt-20 px-4 max-w-4xl mx-auto w-full">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, ease: "easeOut" }}
                        className="w-full space-y-10"
                    >
                        <div className="text-center space-y-4">
                            <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-blue-500 text-[10px] font-bold uppercase tracking-widest mb-2">
                                <Sparkles className="w-3 h-3" />
                                Yapay Zeka Destekli Analiz
                            </div>
                            <h1 className="text-5xl md:text-7xl font-bold text-[#fafafa] tracking-tight leading-[1.1]">
                                Ne inşa etmek <br /> <span className="text-blue-500">istersiniz?</span>
                            </h1>
                            <p className="text-lg text-[#71717a] max-w-xl mx-auto leading-relaxed">
                                Saniyeler içinde detaylı poz analizi ve birim fiyat oluşturun.
                                Teknik tanımları girin, gerisini AI halletsin.
                            </p>
                        </div>

                        <div className="relative max-w-2xl mx-auto">
                            {/* Glow Effect */}
                            <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-10 group-focus-within:opacity-25 transition duration-1000 group-focus-within:duration-200"></div>

                            <div className="relative bg-[#18181b] p-2 rounded-2xl shadow-3xl border border-[#27272a] group focus-within:border-blue-500/50 transition-all duration-300">
                                <textarea
                                    ref={textareaRef}
                                    placeholder="Örn: C30/37 betonarme perde duvar yapılması..."
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.shiftKey && !loading && description) {
                                            e.preventDefault();
                                            handleAnalyze();
                                        }
                                    }}
                                    rows={1}
                                    className="w-full bg-transparent text-[#fafafa] text-lg placeholder-[#3f3f46] border-none outline-none resize-none min-h-[80px] max-h-[300px] p-4 pr-16 custom-scrollbar"
                                />

                                <div className="absolute right-4 bottom-4 flex items-center gap-2">
                                    <button
                                        onClick={handleRefineRequest}
                                        disabled={refineRequestLoading || !description.trim()}
                                        className="p-2.5 text-[#71717a] hover:text-[#fafafa] hover:bg-[#27272a] rounded-xl transition-all border border-transparent hover:border-[#3f3f46]"
                                        title="AI ile profesyonel ifadeye dönüştür"
                                    >
                                        {refineRequestLoading ? (
                                            <Loader2 className="w-5 h-5 animate-spin" />
                                        ) : (
                                            <Sparkles className="w-5 h-5" />
                                        )}
                                    </button>
                                    <button
                                        onClick={handleAnalyze}
                                        disabled={loading || !description.trim()}
                                        className="p-3 bg-blue-600 text-white rounded-xl hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-[0_0_20px_rgba(37,99,235,0.3)] active:scale-95 flex items-center justify-center min-w-[48px]"
                                    >
                                        {loading ? (
                                            <Loader2 className="w-5 h-5 animate-spin" />
                                        ) : (
                                            <ArrowRight className="w-5 h-5" />
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Suggestions / Quick Chips - DSI Odaklı */}
                        <div className="flex flex-wrap items-center justify-center gap-3">
                            <div className="w-full text-center text-[10px] font-bold text-[#52525b] uppercase tracking-widest mb-2">Popüler Aramalar (DSİ)</div>
                            <button onClick={() => setDescription("Taşkın koruma duvarı yapılması (C30 beton, kalıp, demir dahil)")} className="px-5 py-2.5 bg-[#18181b]/50 border border-[#27272a] rounded-xl text-sm text-[#71717a] hover:text-[#fafafa] hover:border-blue-500/50 hover:bg-blue-500/5 transition-all active:scale-95">
                                Taşkın Koruma Duvarı
                            </button>
                            <button onClick={() => setDescription("Betonarme istinat duvarı yapılması (Barbakan, drenaj ve geri dolgu dahil)")} className="px-5 py-2.5 bg-[#18181b]/50 border border-[#27272a] rounded-xl text-sm text-[#71717a] hover:text-[#fafafa] hover:border-blue-500/50 hover:bg-blue-500/5 transition-all active:scale-95">
                                İstinat Duvarı
                            </button>
                            <button onClick={() => setDescription("Harçlı taş duvar örülmesi (60 cm kalınlıkta, derzli)")} className="px-5 py-2.5 bg-[#18181b]/50 border border-[#27272a] rounded-xl text-sm text-[#71717a] hover:text-[#fafafa] hover:border-blue-500/50 hover:bg-blue-500/5 transition-all active:scale-95">
                                Taş Duvar
                            </button>
                            <button onClick={() => setDescription("Trapez kesitli sulama kanalı betonu dökülmesi (C20, perdahlı)")} className="px-5 py-2.5 bg-[#18181b]/50 border border-[#27272a] rounded-xl text-sm text-[#71717a] hover:text-[#fafafa] hover:border-blue-500/50 hover:bg-blue-500/5 transition-all active:scale-95">
                                Trapez Kanal
                            </button>
                            <button onClick={() => setDescription("Kutu menfez yapılması (Kazı, betonarme, yalıtım dahil)")} className="px-5 py-2.5 bg-[#18181b]/50 border border-[#27272a] rounded-xl text-sm text-[#71717a] hover:text-[#fafafa] hover:border-blue-500/50 hover:bg-blue-500/5 transition-all active:scale-95">
                                Kutu Menfez
                            </button>
                            <button onClick={() => setDescription("Taşkın koruma tesisi için brit yapılması (Grobeton, taş dolgu)")} className="px-5 py-2.5 bg-[#18181b]/50 border border-[#27272a] rounded-xl text-sm text-[#71717a] hover:text-[#fafafa] hover:border-blue-500/50 hover:bg-blue-500/5 transition-all active:scale-95">
                                Brit Yapısı
                            </button>
                        </div>
                    </motion.div>
                </div>
            ) : (
                // Result View
                <div className="max-w-5xl mx-auto w-full space-y-10 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-700">
                    <div className="bg-[#18181b] rounded-2xl border border-[#27272a] p-8 shadow-2xl relative overflow-hidden group">
                        {/* Abstract Background Detail */}
                        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/5 rounded-full blur-3xl -mr-32 -mt-32 group-hover:bg-blue-600/10 transition-colors duration-1000"></div>

                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
                            <div className="flex items-start gap-5">
                                <div className="p-4 bg-blue-600/10 text-blue-500 rounded-2xl border border-blue-500/20 shadow-inner">
                                    <Sparkles className="w-8 h-8" />
                                </div>
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <span className="text-[10px] font-bold text-blue-500 uppercase tracking-widest px-2 py-0.5 bg-blue-600/10 border border-blue-500/20 rounded">Analiz Tamamlandı</span>
                                        <span className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">{new Date().toLocaleDateString('tr-TR')}</span>
                                    </div>
                                    <h2 className="text-2xl md:text-3xl font-bold text-[#fafafa] tracking-tight leading-tight">
                                        {description}
                                    </h2>
                                </div>
                            </div>
                            <div className="flex items-center gap-3 self-end md:self-center">
                                <button
                                    onClick={() => setResult(null)}
                                    className="p-3 bg-[#27272a] text-[#71717a] hover:text-[#fafafa] rounded-xl border border-[#3f3f46] transition-all hover:bg-[#3f3f46] shadow-lg active:scale-95"
                                    title="Yeni Analiz"
                                >
                                    <Plus className="w-5 h-5" />
                                </button>
                                <button
                                    onClick={() => setResult(null)}
                                    className="p-3 bg-[#27272a] text-[#71717a] hover:text-[#fafafa] rounded-xl border border-[#3f3f46] transition-all hover:bg-[#3f3f46] shadow-lg active:scale-95"
                                    title="Kapat"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                        </div>

                        {/* Technical Specification Block (New) */}
                        {result.technical_specification && (
                            <div className="bg-[#18181b]/50 border border-[#27272a] rounded-xl overflow-hidden">
                                <button
                                    onClick={() => toggleSection('spec')}
                                    className="w-full flex items-center justify-between p-4 bg-[#27272a]/30 hover:bg-[#27272a]/50 transition-colors"
                                >
                                    <div className="flex items-center gap-3">
                                        <FileText className="w-5 h-5 text-amber-500" />
                                        <h3 className="text-sm font-bold text-[#fafafa] uppercase tracking-widest">Yapım Şartları ve Teknik Tarif</h3>
                                    </div>
                                    <ChevronDown className={cn("w-5 h-5 text-[#71717a] transition-transform", sections.spec ? "rotate-180" : "")} />
                                </button>

                                {sections.spec && (
                                    <div className="p-6 text-[#a1a1aa] text-sm leading-relaxed border-t border-[#27272a] whitespace-pre-line font-mono bg-[#09090b]">
                                        {result.technical_specification}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        {/* Left Column: Stats & Technical Data */}
                        <div className="lg:col-span-2 space-y-8">
                            {/* Analiz Adı Editor */}
                            <div className="bg-[#18181b] rounded-2xl shadow-xl border border-[#27272a] p-6 group focus-within:border-blue-500/30 transition-colors">
                                <div className="flex items-center gap-2 mb-4">
                                    <FileText className="w-4 h-4 text-[#52525b]" />
                                    <label className="text-[10px] font-bold text-[#71717a] uppercase tracking-widest italic">Dosya Adı / Kayıt Başlığı</label>
                                </div>
                                <input
                                    type="text"
                                    value={analysisName}
                                    onChange={(e) => setAnalysisName(e.target.value)}
                                    placeholder="Analiz adı girin..."
                                    className="w-full px-0 bg-transparent border-none outline-none text-xl font-bold text-[#fafafa] placeholder-[#3f3f46] transition-colors"
                                />
                            </div>

                            {/* Trust Score & Warnings */}
                            {result.metadata && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {/* Analysis Score */}
                                    <div className="bg-[#18181b] rounded-2xl shadow-xl border border-[#27272a] p-8 space-y-6">
                                        <div className="flex justify-between items-center">
                                            <div className="space-y-1">
                                                <h3 className="text-[10px] font-bold text-[#71717a] uppercase tracking-widest leading-none">AI Güven Skoru</h3>
                                                <p className="text-sm text-white font-medium">Analiz hassasiyeti ve veri doğruluğu</p>
                                            </div>
                                            <div className={cn(
                                                "text-4xl font-black tracking-tighter transition-colors",
                                                result.metadata.analysis_score >= 85 ? "text-green-500" :
                                                    result.metadata.analysis_score >= 60 ? "text-amber-500" : "text-red-500"
                                            )}>
                                                %{result.metadata.analysis_score}
                                            </div>
                                        </div>
                                        <div className="w-full bg-[#09090b] rounded-full h-3 border border-[#27272a] p-0.5">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: `${result.metadata.analysis_score}%` }}
                                                transition={{ duration: 1.5, ease: "circOut" }}
                                                className={cn(
                                                    "h-full rounded-full shadow-[0_0_10px_-2px_rgba(0,0,0,0.5)]",
                                                    result.metadata.analysis_score >= 85 ? "bg-gradient-to-r from-green-600 to-green-400" :
                                                        result.metadata.analysis_score >= 60 ? "bg-gradient-to-r from-amber-600 to-amber-400" : "bg-gradient-to-r from-red-600 to-red-400"
                                                )}
                                            ></motion.div>
                                        </div>
                                        <div className="flex items-start gap-3 p-4 bg-[#09090b] rounded-xl border border-[#27272a]">
                                            <Info className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                                            <p className="text-xs text-[#71717a] leading-relaxed">
                                                {result.metadata.analysis_score >= 85 ? "Bu analiz yüksek düzeyde veri doğruluğu içermektedir. Veriler resmi poz veritabanı ile tam uyumludur." :
                                                    result.metadata.analysis_score >= 60 ? "Analiz verileri benzer imalat türleri üzerinden türetilmiştir. Kalem fiyatlarını gözden geçirmeniz önerilir." :
                                                        "Düşük güvenirlik düzeyi. Lütfen tüm kalemleri manuel olarak doğrulayın."}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Advanced Metrics (Consensus/Consistency/CoT) */}
                            {result.advanced_metrics && (
                                <div className="bg-[#18181b] rounded-2xl shadow-xl border border-[#27272a] p-6 space-y-4">
                                    <div className="flex items-center gap-2">
                                        <Sparkles className="w-4 h-4 text-purple-500" />
                                        <h3 className="text-[10px] font-bold text-[#71717a] uppercase tracking-widest leading-none">Gelişmiş Analiz Metrikleri</h3>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        {/* Consensus Score */}
                                        {result.advanced_metrics.consensus_score !== undefined && (
                                            <div className="p-4 bg-[#09090b] rounded-xl border border-[#27272a] space-y-2">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-[10px] font-bold text-[#71717a] uppercase tracking-widest">Konsensüs Skoru</span>
                                                    <span className="text-xs text-[#52525b]">{result.advanced_metrics.model_count} model</span>
                                                </div>
                                                <div className={cn(
                                                    "text-2xl font-black tracking-tight",
                                                    result.advanced_metrics.consensus_score >= 0.7 ? "text-green-500" :
                                                        result.advanced_metrics.consensus_score >= 0.4 ? "text-amber-500" : "text-red-500"
                                                )}>
                                                    %{Math.round(result.advanced_metrics.consensus_score * 100)}
                                                </div>
                                                <p className="text-[10px] text-[#52525b]">
                                                    {result.advanced_metrics.consensus_score >= 0.7 ? "Modeller güçlü uyum gösteriyor" :
                                                        result.advanced_metrics.consensus_score >= 0.4 ? "Kısmi uyum mevcut" : "Modeller arası farklılıklar var"}
                                                </p>
                                            </div>
                                        )}

                                        {/* Consistency Score */}
                                        {result.advanced_metrics.consistency_score !== undefined && (
                                            <div className="p-4 bg-[#09090b] rounded-xl border border-[#27272a] space-y-2">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-[10px] font-bold text-[#71717a] uppercase tracking-widest">Tutarlılık Skoru</span>
                                                    <span className="text-xs text-[#52525b]">{result.advanced_metrics.sample_count} örnek</span>
                                                </div>
                                                <div className={cn(
                                                    "text-2xl font-black tracking-tight",
                                                    result.advanced_metrics.consistency_score >= 0.7 ? "text-green-500" :
                                                        result.advanced_metrics.consistency_score >= 0.4 ? "text-amber-500" : "text-red-500"
                                                )}>
                                                    %{Math.round(result.advanced_metrics.consistency_score * 100)}
                                                </div>
                                                {result.advanced_metrics.consistency_warning ? (
                                                    <p className="text-[10px] text-amber-500 flex items-center gap-1">
                                                        <AlertTriangle className="w-3 h-3" />
                                                        {result.advanced_metrics.consistency_warning}
                                                    </p>
                                                ) : (
                                                    <p className="text-[10px] text-[#52525b]">
                                                        {result.advanced_metrics.consistency_score >= 0.7 ? "Sonuçlar yüksek tutarlılık gösteriyor" : "Sonuçları gözden geçirin"}
                                                    </p>
                                                )}
                                            </div>
                                        )}

                                        {/* CoT Mode */}
                                        {result.advanced_metrics.cot_enabled && (
                                            <div className="p-4 bg-[#09090b] rounded-xl border border-purple-500/20 space-y-2">
                                                <span className="text-[10px] font-bold text-[#71717a] uppercase tracking-widest">Chain-of-Thought</span>
                                                <div className="flex items-center gap-2">
                                                    <div className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
                                                    <span className="text-sm font-semibold text-purple-400">Aktif</span>
                                                </div>
                                                <p className="text-[10px] text-[#52525b]">
                                                    Adım adım düşünme modu ile analiz yapıldı
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Critic Review (AI Feedback Loop) */}
                            {result.critic_review && result.critic_review.status !== 'ok' && (
                                <div className={cn(
                                    "p-8 rounded-2xl border-2 shadow-2xl space-y-6",
                                    result.critic_review.status === 'error' ? "bg-red-500/5 border-red-500/20" : "bg-amber-500/5 border-amber-500/20"
                                )}>
                                    <div className="flex items-center gap-4">
                                        <div className={cn(
                                            "p-3 rounded-xl border mb-2",
                                            result.critic_review.status === 'error' ? "bg-red-500/10 border-red-500/20 text-red-500" : "bg-amber-500/10 border-amber-500/20 text-amber-500"
                                        )}>
                                            <GraduationCap className="w-6 h-6" />
                                        </div>
                                        <div>
                                            <h4 className={cn("text-lg font-bold tracking-tight mb-1", result.critic_review.status === 'error' ? "text-red-500" : "text-amber-500")}>
                                                {result.critic_review.status === 'error' ? "Eleştirmen AI: Kritik Sorunlar" : "Eleştirmen AI: İyileştirme Önerileri"}
                                            </h4>
                                            <p className="text-xs text-[#71717a] font-medium leading-none">Analiz süreci denetlendi ve iyileştirme kalemleri belirlendi.</p>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {result.critic_review.issues.map((issue, idx) => (
                                            <div key={idx} className="p-4 bg-[#09090b]/50 rounded-xl border border-[#27272a] space-y-2 group hover:border-blue-500/30 transition-colors">
                                                <div className="flex items-center justify-between">
                                                    <span className={cn(
                                                        "text-[9px] font-bold px-2 py-0.5 rounded uppercase tracking-widest",
                                                        issue.severity === 'critical' ? "bg-red-500/20 text-red-500 border border-red-500/30" : "bg-amber-500/20 text-amber-500 border border-amber-500/30"
                                                    )}>
                                                        {issue.category}
                                                    </span>
                                                    {issue.severity === 'critical' && <XCircle className="w-3 h-3 text-red-500" />}
                                                </div>
                                                <p className="text-sm text-[#fafafa] font-medium leading-relaxed">{issue.message}</p>
                                                {issue.suggestion && (
                                                    <div className="pt-2 flex items-center gap-2 text-[11px] text-[#71717a] italic">
                                                        <Sparkles className="w-3 h-3 text-blue-500 shrink-0" />
                                                        <span className="flex-1">💡 {issue.suggestion}</span>
                                                        {["Eksik Kalem", "Eksik Malzeme", "Öğrenilmiş Kural"].includes(issue.category) && (
                                                            <button
                                                                onClick={() => handleLearnRule(issue)}
                                                                className="not-italic bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 rounded-lg px-2.5 py-1 text-[10px] whitespace-nowrap transition-colors shrink-0"
                                                                title="Bu düzeltmeyi kural olarak kaydet"
                                                            >
                                                                + Kural Yap
                                                            </button>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Explanation */}
                            <div className="bg-blue-900/10 border border-blue-500/20 rounded-xl p-6">
                                <div className="flex items-start">
                                    <Info className="w-5 h-5 text-blue-500 mr-3 mt-0.5 flex-shrink-0" />
                                    <div className="text-blue-400 text-sm leading-relaxed whitespace-pre-wrap">
                                        {result.explanation}
                                    </div>
                                </div>
                            </div>

                            {/* Technical Description (Tarif) */}
                            {result.technical_description && (
                                <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-6">
                                    <div className="flex items-start">
                                        <FileText className="w-5 h-5 text-[#a1a1aa] mr-3 mt-0.5 flex-shrink-0" />
                                        <div className="space-y-2">
                                            <h4 className="text-sm font-bold text-white uppercase tracking-tight">Teknik Tarif / Yapım Şartları</h4>
                                            <div className="text-[#a1a1aa] text-sm leading-relaxed italic whitespace-pre-wrap">
                                                {result.technical_description}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Detail Table */}
                            <div className="bg-[#18181b] rounded-2xl shadow-xl border border-[#27272a] overflow-hidden">
                                <div className="p-6 border-b border-[#27272a] flex items-center justify-between bg-black/20">
                                    <div className="flex items-center gap-3">
                                        <Table className="w-5 h-5 text-blue-500" />
                                        <h3 className="text-sm font-bold text-[#fafafa] uppercase tracking-widest leading-none">Analiz Detay Cetveli</h3>
                                    </div>
                                    <button
                                        onClick={addNewComponent}
                                        className="px-4 py-2 bg-[#27272a] text-[#fafafa] rounded-xl border border-[#3f3f46] hover:bg-[#3f3f46] transition-all text-xs font-bold flex items-center gap-2 group active:scale-95"
                                    >
                                        <Plus className="w-3 h-3 text-blue-500 group-hover:scale-125 transition-transform" />
                                        KALEM EKLE
                                    </button>
                                </div>
                                <div className="p-1">
                                    <AnalysisTable
                                        data={(result.analysis_data && result.analysis_data.components && result.analysis_data.components.length > 0)
                                            ? result.analysis_data
                                            : {
                                                poz_no: "Y.ANALİZ",
                                                name: analysisName || description,
                                                unit: displayUnit,
                                                components: result.components.map(c => ({
                                                    type: c.type,
                                                    code: c.code,
                                                    name: c.name,
                                                    unit: c.unit,
                                                    quantity: c.quantity.toString(),
                                                    price: c.unit_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 }),
                                                    total: c.total_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })
                                                })),
                                                totals: {
                                                    subtotal: subtotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 }),
                                                    profit: overhead.toLocaleString('tr-TR', { minimumFractionDigits: 2 }),
                                                    grand_total: grandTotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 }),
                                                    label: `1 ${displayUnit} Fiyatı`
                                                }
                                            }}
                                        description={result.technical_description || result.explanation}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Right Column: Actions & Summary */}
                        <div className="space-y-8">
                            {/* Quick Actions Card */}
                            <div className="bg-[#18181b] rounded-2xl shadow-xl border border-[#27272a] p-8 space-y-6 sticky top-24">
                                <div className="flex items-center gap-2">
                                    <Calculator className="w-4 h-4 text-blue-500" />
                                    <h3 className="text-[10px] font-bold text-[#71717a] uppercase tracking-widest leading-none">İşlem Merkezi</h3>
                                </div>

                                <div className="space-y-4">
                                    <button
                                        onClick={handleSaveAnalysis}
                                        disabled={saveLoading}
                                        className="w-full flex items-center justify-between px-6 py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl transition-all font-bold shadow-xl shadow-blue-900/20 group active:scale-[0.98]"
                                    >
                                        <div className="flex items-center gap-3">
                                            {saveLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                                            Analizi Kaydet
                                        </div>
                                        <ArrowRight className="w-4 h-4 opacity-50 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                                    </button>

                                    <button
                                        onClick={handleSaveAsProject}
                                        disabled={saveLoading}
                                        className="w-full flex items-center justify-between px-6 py-4 bg-[#27272a] hover:bg-[#3f3f46] text-[#fafafa] rounded-2xl transition-all font-bold border border-[#3f3f46] group active:scale-[0.98]"
                                    >
                                        <div className="flex items-center gap-3">
                                            <Box className="w-5 h-5 text-blue-500" />
                                            Proje Olarak Aktar
                                        </div>
                                        <ArrowRight className="w-4 h-4 opacity-30 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                                    </button>

                                    <div className="grid grid-cols-3 gap-3">
                                        <button
                                            onClick={handleExportExcel}
                                            className="flex flex-col items-center justify-center p-4 bg-[#18181b] hover:bg-[#27272a] text-[#71717a] hover:text-[#fafafa] rounded-2xl border border-[#27272a] transition-all gap-2 group active:scale-[0.98]"
                                        >
                                            <FileDown className="w-5 h-5 group-hover:scale-110 transition-transform" />
                                            <span className="text-[10px] font-bold uppercase tracking-widest">Excel</span>
                                        </button>
                                        <button
                                            onClick={handleCopyAsMarkdown}
                                            className="flex flex-col items-center justify-center p-4 bg-[#18181b] hover:bg-[#27272a] text-[#71717a] hover:text-[#fafafa] rounded-2xl border border-[#27272a] transition-all gap-2 group active:scale-[0.98]"
                                        >
                                            <Copy className="w-5 h-5 group-hover:scale-110 transition-transform" />
                                            <span className="text-[10px] font-bold uppercase tracking-widest">Kopyala</span>
                                        </button>
                                        <button
                                            onClick={() => { setFeedbackModalTab('ai'); setShowFeedbackModal(true); }}
                                            className="flex flex-col items-center justify-center p-4 bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 hover:text-purple-300 rounded-2xl border border-purple-500/20 transition-all gap-2 group active:scale-[0.98]"
                                        >
                                            <Sparkles className="w-5 h-5 group-hover:scale-110 transition-transform" />
                                            <span className="text-[10px] font-bold uppercase tracking-widest">Öneriler</span>
                                        </button>
                                    </div>
                                </div>

                                <div className="pt-6 border-t border-[#27272a] space-y-4">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Calculator className="w-4 h-4 text-[#52525b]" />
                                        <h3 className="text-[10px] font-bold text-[#71717a] uppercase tracking-widest leading-none italic">Fiyat Özeti</h3>
                                    </div>

                                    <div className="space-y-3">
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-[#71717a]">Gider Toplamı</span>
                                            <span className="text-[#fafafa] font-mono leading-none tracking-tighter">
                                                {subtotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} <span className="text-[9px] opacity-50 italic">TL</span>
                                            </span>
                                        </div>
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-[#71717a]">Genel Gider (%25)</span>
                                            <span className="text-[#71717a] font-mono leading-none tracking-tighter text-blue-500/70">
                                                {overhead.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} <span className="text-[9px] opacity-50 italic">TL</span>
                                            </span>
                                        </div>
                                        <div className="pt-3 border-t border-dashed border-[#27272a] flex flex-col gap-1">
                                            <div className="text-[10px] font-bold text-blue-500 uppercase tracking-[0.2em] leading-none mb-1">Birim Fiyat ({displayUnit})</div>
                                            <div className="text-3xl font-black text-[#fafafa] tracking-tighter leading-none">
                                                {grandTotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} <span className="text-sm font-bold text-blue-500">TL</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Öneriler Modal - Sekmeli (AI Analiz / Manuel Düzeltme) */}
            {
                showFeedbackModal && (
                    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-300">
                        <div className="bg-[#09090b] border border-[#27272a] rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto ring-1 ring-white/10">
                            {/* Modal Header */}
                            <div className="p-6 border-b border-[#27272a] flex justify-between items-center bg-black/40">
                                <div className="flex items-center">
                                    <Sparkles className="w-6 h-6 text-purple-500 mr-3" />
                                    <h2 className="text-xl font-bold text-[#fafafa] tracking-tight">Analiz Önerileri</h2>
                                </div>
                                <button
                                    onClick={() => setShowFeedbackModal(false)}
                                    className="text-[#71717a] hover:text-[#fafafa] transition-colors"
                                >
                                    <X className="w-6 h-6" />
                                </button>
                            </div>

                            {/* Tabs */}
                            <div className="flex border-b border-[#27272a]">
                                <button
                                    onClick={() => setFeedbackModalTab('ai')}
                                    className={cn(
                                        "flex-1 px-6 py-4 text-sm font-bold uppercase tracking-widest transition-all flex items-center justify-center gap-2",
                                        feedbackModalTab === 'ai'
                                            ? "text-purple-400 border-b-2 border-purple-500 bg-purple-500/5"
                                            : "text-[#71717a] hover:text-[#fafafa] hover:bg-[#18181b]"
                                    )}
                                >
                                    <Search className="w-4 h-4" />
                                    AI Analiz
                                </button>
                                <button
                                    onClick={() => setFeedbackModalTab('manual')}
                                    className={cn(
                                        "flex-1 px-6 py-4 text-sm font-bold uppercase tracking-widest transition-all flex items-center justify-center gap-2",
                                        feedbackModalTab === 'manual'
                                            ? "text-amber-400 border-b-2 border-amber-500 bg-amber-500/5"
                                            : "text-[#71717a] hover:text-[#fafafa] hover:bg-[#18181b]"
                                    )}
                                >
                                    <GraduationCap className="w-4 h-4" />
                                    Manuel Düzeltme
                                </button>
                            </div>

                            {/* Tab Content */}
                            <div className="p-6 space-y-6">
                                {feedbackModalTab === 'ai' ? (
                                    <>
                                        {/* AI Analysis Tab */}
                                        <div className="bg-purple-600/10 border border-purple-500/20 rounded-lg p-4">
                                            <p className="text-purple-400 text-sm leading-relaxed">
                                                <span className="font-bold">AI Analiz:</span> Mevcut analizi yapay zeka ile inceleyin. Eksik kalemleri, mantık hatalarını ve fiyat anomalilerini tespit eder.
                                            </p>
                                        </div>

                                        {/* Current Analysis Summary */}
                                        <div className="bg-[#18181b] border border-[#27272a] rounded-lg p-5">
                                            <h3 className="text-xs font-bold text-[#71717a] uppercase tracking-widest mb-3">Mevcut Analiz</h3>
                                            <p className="text-[#fafafa] font-medium text-sm leading-relaxed italic mb-2">"{description}"</p>
                                            <div className="flex items-center gap-4 text-xs text-[#71717a]">
                                                <span>Birim: <strong className="text-[#fafafa]">{displayUnit}</strong></span>
                                                <span>Kalem: <strong className="text-[#fafafa]">{result?.components.length || 0}</strong></span>
                                                <span>Toplam: <strong className="text-blue-400">{grandTotal.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL</strong></span>
                                            </div>
                                        </div>

                                        {/* Action Button - Restored */}
                                        <button
                                            onClick={handleAIReview}
                                            disabled={aiReviewLoading}
                                            className="w-full py-4 bg-purple-600 hover:bg-purple-500 text-white rounded-xl transition-all font-bold shadow-lg shadow-purple-900/20 active:scale-[0.98] flex items-center justify-center gap-2"
                                        >
                                            {aiReviewLoading ? (
                                                <>
                                                    <Loader2 className="w-5 h-5 animate-spin" />
                                                    AI Analiz Yapılıyor...
                                                </>
                                            ) : (
                                                <>
                                                    <Sparkles className="w-5 h-5" />
                                                    AI ile Analiz Et
                                                </>
                                            )}
                                        </button>

                                        {/* AI Review Result Preview */}
                                        {result?.critic_review && (
                                            <div className="bg-[#18181b] border border-[#27272a] rounded-lg p-5 space-y-3">
                                                <h3 className="text-xs font-bold text-[#71717a] uppercase tracking-widest">Son AI İnceleme Sonucu</h3>

                                                {result.critic_review.status === 'ok' ? (
                                                    <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg flex items-center gap-3">
                                                        <div className="p-2 bg-green-500/20 rounded-full">
                                                            <Sparkles className="w-4 h-4 text-green-500" />
                                                        </div>
                                                        <div>
                                                            <div className="text-sm font-bold text-green-500">Mükemmel!</div>
                                                            <div className="text-xs text-green-400/80">Analizde herhangi bir sorun tespit edilmedi.</div>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
                                                        {result.critic_review.issues.slice(0, 3).map((issue, idx) => (
                                                            <div key={idx} className={cn(
                                                                "p-3 rounded-lg border text-xs",
                                                                issue.severity === 'critical'
                                                                    ? "bg-red-500/10 border-red-500/20 text-red-400"
                                                                    : "bg-amber-500/10 border-amber-500/20 text-amber-400"
                                                            )}>
                                                                <div className="font-bold flex items-center gap-2">
                                                                    {issue.severity === 'critical' && <XCircle className="w-3 h-3" />}
                                                                    {issue.category}
                                                                </div>
                                                                <div className="opacity-80 mt-1 leading-relaxed">{issue.message}</div>
                                                                {issue.suggestion && (
                                                                    <div className="mt-2 flex items-center gap-2">
                                                                        <div className="text-[10px] bg-white/5 p-1.5 rounded border border-white/5 opacity-70 flex-1">
                                                                            💡 {issue.suggestion}
                                                                        </div>
                                                                        {["Eksik Kalem", "Eksik Malzeme", "Öğrenilmiş Kural"].includes(issue.category) && (
                                                                            <button
                                                                                onClick={() => handleLearnRule(issue)}
                                                                                className="bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 rounded p-1.5 text-[10px] whitespace-nowrap transition-colors"
                                                                                title="Bu düzeltmeyi kural olarak kaydet"
                                                                            >
                                                                                + Kural Yap
                                                                            </button>
                                                                        )}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </>
                                ) : (
                                    <>
                                        {/* Manual Correction Tab */}
                                        <div className="bg-amber-600/10 border border-amber-500/20 rounded-lg p-4">
                                            <p className="text-amber-400 text-sm leading-relaxed">
                                                <span className="font-bold">Manuel Düzeltme:</span> AI hatalı bir analiz yaptığında, doğru sonuçları buradan öğretebilirsiniz. AI, gelecekteki benzer sorgularda bu düzeltmeyi referans alacaktır.
                                            </p>
                                        </div>

                                        <div className="space-y-2">
                                            <label className="text-xs font-bold text-[#71717a] uppercase tracking-widest">Düzeltme Türü</label>
                                            <select
                                                value={correctionType}
                                                onChange={(e) => setCorrectionType(e.target.value)}
                                                className="w-full px-4 py-2.5 bg-[#18181b] border border-[#27272a] text-[#fafafa] rounded-lg focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50 outline-none transition-all"
                                            >
                                                <option value="wrong_method">Yanlış Yöntem (örn. elle yerine makine)</option>
                                                <option value="missing_item">Eksik Kalem (örn. nakliye eklenmemiş)</option>
                                                <option value="wrong_price">Yanlış Fiyat</option>
                                                <option value="wrong_quantity">Yanlış Miktar</option>
                                                <option value="other">Diğer</option>
                                            </select>
                                        </div>

                                        <div className="space-y-2">
                                            <label className="text-xs font-bold text-[#71717a] uppercase tracking-widest">Düzeltme Açıklaması</label>
                                            <div className="relative group">
                                                <textarea
                                                    value={correctionDescription}
                                                    onChange={(e) => setCorrectionDescription(e.target.value)}
                                                    placeholder="Örn: Beton santrali ile taş duvar demek, beton döküm işçiliği ve hazır beton malzemesi demektir, taş duvar malzemeleri değil..."
                                                    rows={4}
                                                    className="w-full px-4 py-3 bg-[#18181b] border border-[#27272a] text-[#fafafa] rounded-lg focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50 outline-none resize-none pr-12 text-sm leading-relaxed"
                                                />
                                                <button
                                                    onClick={handleRefineDescription}
                                                    disabled={refineLoading || !correctionDescription.trim()}
                                                    className="absolute right-3 top-3 p-2 bg-[#27272a] text-amber-500 rounded-lg hover:bg-[#3f3f46] transition-all border border-[#3f3f46] shadow-sm disabled:opacity-50"
                                                    title="AI ile profesyonelce düzenle"
                                                >
                                                    {refineLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                                                </button>
                                            </div>
                                            <p className="text-[11px] text-[#71717a]">
                                                AI'nın hatasını açıkça belirtin. Bu açıklama gelecekteki sorgularda referans olarak kullanılacak.
                                            </p>
                                        </div>

                                        <div className="bg-black/40 border border-[#27272a] rounded-lg p-5">
                                            <h3 className="text-xs font-bold text-[#71717a] uppercase tracking-widest mb-4">Gönderilecek Bileşenler ({result?.components.length || 0})</h3>
                                            <div className="max-h-32 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                                                {result?.components.slice(0, 5).map((comp) => (
                                                    <div key={comp.id} className="flex items-center justify-between text-sm py-1 border-b border-[#18181b] last:border-0">
                                                        <span className="flex items-center">
                                                            <span className={cn(
                                                                "text-[9px] font-black uppercase px-2 py-0.5 rounded mr-3 tracking-tighter",
                                                                comp.type === 'Malzeme' ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' :
                                                                    comp.type === 'İşçilik' ? 'bg-orange-600/20 text-orange-400 border border-orange-500/30' :
                                                                        comp.type === 'Nakliye' ? 'bg-green-600/20 text-green-400 border border-green-500/30' :
                                                                            'bg-zinc-800 text-zinc-400 border border-zinc-700'
                                                            )}>
                                                                {comp.type}
                                                            </span>
                                                            <span className="text-[#fafafa] font-medium truncate max-w-[200px]">{comp.name}</span>
                                                        </span>
                                                    </div>
                                                ))}
                                                {(result?.components.length || 0) > 5 && (
                                                    <div className="text-xs text-[#71717a] italic">... ve {(result?.components.length || 0) - 5} kalem daha</div>
                                                )}
                                            </div>
                                        </div>
                                    </>
                                )}
                            </div>

                            {/* Modal Footer */}
                            <div className="p-6 border-t border-[#27272a] flex justify-end gap-3 bg-black/40">
                                <button
                                    onClick={() => setShowFeedbackModal(false)}
                                    disabled={feedbackLoading || aiReviewLoading}
                                    className="px-5 py-2 text-[#a1a1aa] hover:text-[#fafafa] hover:bg-[#18181b] rounded-lg transition-all font-bold text-sm"
                                >
                                    Kapat
                                </button>
                                {feedbackModalTab === 'manual' && (
                                    <button
                                        onClick={handleSubmitFeedback}
                                        disabled={feedbackLoading || !correctionDescription.trim()}
                                        className="px-6 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-bold text-sm flex items-center shadow-lg shadow-amber-900/40 active:scale-95"
                                    >
                                        {feedbackLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <GraduationCap className="w-4 h-4 mr-2" />}
                                        AI'ya Öğret
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                )
            }
            {/* Poz Detay Modal - High Fidelity Dark */}
            {
                selectedCompForDetail && (
                    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[60] p-4" onClick={() => setSelectedCompForDetail(null)}>
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="bg-[#09090b] rounded-2xl shadow-3xl border border-[#27272a] max-w-sm w-full overflow-hidden ring-1 ring-white/10"
                            onClick={e => e.stopPropagation()}
                        >
                            {/* Header */}
                            <div className="px-5 py-4 border-b border-[#27272a] flex justify-between items-center bg-black/40">
                                <div className="flex items-center gap-3">
                                    <div className={cn(
                                        "p-2 rounded-lg border",
                                        selectedCompForDetail.type === 'Malzeme' ? 'bg-blue-600/10 border-blue-500/20 text-blue-500' :
                                            selectedCompForDetail.type === 'İşçilik' ? 'bg-orange-600/10 border-orange-500/20 text-orange-500' :
                                                selectedCompForDetail.type === 'Nakliye' ? 'bg-green-600/10 border-green-500/20 text-green-500' :
                                                    'bg-[#18181b] border-[#27272a] text-[#71717a]'
                                    )}>
                                        <Box className="w-4 h-4" />
                                    </div>
                                    <div>
                                        <div className="text-[10px] font-bold text-[#71717a] uppercase tracking-widest leading-none mb-1">{selectedCompForDetail.type}</div>
                                        <div className="font-mono text-xs text-blue-500 font-bold leading-none">{selectedCompForDetail.code || '-'}</div>
                                    </div>
                                </div>
                                <button onClick={() => setSelectedCompForDetail(null)} className="p-2 rounded-lg hover:bg-[#18181b] text-[#52525b] hover:text-[#fafafa] transition-colors">
                                    <X className="w-4 h-4" />
                                </button>
                            </div>

                            {/* Content */}
                            <div className="p-5 space-y-5">
                                <div className="text-sm font-medium text-[#fafafa] leading-relaxed">
                                    {selectedCompForDetail.name}
                                </div>

                                <div className="grid grid-cols-3 gap-3">
                                    <div className="p-3 bg-[#18181b] rounded-xl border border-[#27272a] text-center">
                                        <div className="text-[9px] text-[#71717a] font-bold uppercase tracking-widest mb-1">Miktar</div>
                                        <div className="text-sm font-black text-[#fafafa]">{selectedCompForDetail.quantity} <span className="text-[9px] font-normal text-[#52525b] uppercase">{selectedCompForDetail.unit}</span></div>
                                    </div>
                                    <div className="p-3 bg-[#18181b] rounded-xl border border-[#27272a] text-center">
                                        <div className="text-[9px] text-[#71717a] font-bold uppercase tracking-widest mb-1">Birim</div>
                                        <div className="text-sm font-black text-[#fafafa]">{selectedCompForDetail.unit_price.toLocaleString('tr-TR')}</div>
                                    </div>
                                    <div className="p-3 bg-blue-600/5 rounded-xl border border-blue-500/20 text-center">
                                        <div className="text-[9px] text-blue-500 font-bold uppercase tracking-widest mb-1">Tutar</div>
                                        <div className="text-sm font-black text-blue-400">{selectedCompForDetail.total_price.toLocaleString('tr-TR')}</div>
                                    </div>
                                </div>

                                {selectedCompForDetail.price_source && (
                                    <div className="flex items-start gap-3 text-[11px] text-blue-400 bg-blue-600/5 px-4 py-3 rounded-xl border border-blue-500/10">
                                        <Sparkles className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                                        <span className="leading-relaxed">
                                            {selectedCompForDetail.price_source === 'exact_code_validated' && "Resmi poz veritabanı ile tam kod eşleşmesi sağlandı."}
                                            {selectedCompForDetail.price_source === 'description' && "Benzer iş kalemleri üzerinden fiyatlandırıldı."}
                                            {selectedCompForDetail.price_source === 'similar_code' && "Poz grubu analizi ile fiyat tahmini yapıldı."}
                                            {selectedCompForDetail.price_source === 'ai_generated' && "Yapay zeka piyasa verileri ile hesaplandı."}
                                            {selectedCompForDetail.price_source === 'not_found' && "Özel imalat kapsamında fiyatlandırıldı."}
                                        </span>
                                    </div>
                                )}
                            </div>

                            {/* Footer */}
                            <div className="px-5 py-4 bg-black/40 border-t border-[#27272a] flex justify-end">
                                <button
                                    onClick={() => setSelectedCompForDetail(null)}
                                    className="px-6 py-2 bg-[#27272a] text-[#fafafa] hover:bg-[#3f3f46] rounded-xl transition-all text-xs font-bold border border-[#3f3f46] active:scale-95"
                                >
                                    KAPAT
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )
            }
        </div>
    );
}

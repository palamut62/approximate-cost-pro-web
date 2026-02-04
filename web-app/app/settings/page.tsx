"use client";

import React, { useEffect, useState } from 'react';
import { Settings, RefreshCw, Save, Check, AlertTriangle, Shield, Cpu, MessageSquare, Truck, FileSignature, Layers } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';
import FileManager from '@/components/FileManager';

interface Model {
    id: string;
    name: string;
    context_length: number;
    is_free: boolean;
    pricing: {
        prompt: string;
        completion: string;
    };
}

interface SettingsData {
    // Model Settings
    selected_models: {
        analyze: string;
        refine: string;
        critic: string;
    };
    cached_models: Model[];
    last_models_refresh: number | null;
    filter_free_only: boolean;

    // General Settings (Assumptions)
    profit_margin?: string; // Kar Oranı
    overhead?: string;      // Genel Gider
    transport_distance_cement?: string;
    transport_distance_sand?: string;
    transport_distance_other?: string;

    // Densities
    density_sand?: string;
    density_gravel?: string; // Moloz/Taş
    density_concrete?: string;
    density_cement?: string;
    density_iron?: string;

    // API Limits
    llm_warning_threshold?: string;

    // Signatories
    preparer_name?: string;
    preparer_title?: string;
    controller_name?: string;
    controller_title?: string;
    approver_name?: string;
    approver_title?: string;

    // Allow dynamic keys
    [key: string]: any;
}

export default function SettingsPage() {
    const [settings, setSettings] = useState<SettingsData | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [activeTab, setActiveTab] = useState<'models' | 'general' | 'signatories' | 'data'>('models');

    useEffect(() => {
        fetchSettings();
    }, []);

    const fetchSettings = async () => {
        try {
            const res = await api.get('/settings');
            // Ensure default structure for some fields if missing
            const data = res.data;
            if (!data.selected_models) {
                data.selected_models = { analyze: "moonshotai/kimi-k2.5", refine: "moonshotai/kimi-k2.5", critic: "moonshotai/kimi-k2.5" };
            }
            if (!data.cached_models) data.cached_models = [];

            setSettings(data);
        } catch (err) {
            console.error(err);
            setMessage({ type: 'error', text: 'Ayarlar sunucudan alınamadı.' });
        } finally {
            setLoading(false);
        }
    };

    const refreshModels = async () => {
        setRefreshing(true);
        setMessage(null);
        try {
            const res = await api.post('/settings/refresh-models');
            const data = res.data;

            if (settings) {
                setSettings({
                    ...settings,
                    cached_models: data.models,
                    last_models_refresh: Date.now() / 1000
                });
            }
            setMessage({ type: 'success', text: `${data.count} model başarıyla güncellendi.` });
        } catch (err) {
            console.error(err);
            setMessage({ type: 'error', text: 'Modeller yenilenirken hata oluştu.' });
        } finally {
            setRefreshing(false);
        }
    };

    const saveSettings = async () => {
        if (!settings) return;
        setSaving(true);
        setMessage(null);

        try {
            await api.post('/settings', settings);
            setMessage({ type: 'success', text: 'Ayarlar başarıyla kaydedildi.' });
        } catch (err) {
            console.error(err);
            setMessage({ type: 'error', text: 'Ayarlar kaydedilemedi.' });
        } finally {
            setSaving(false);
        }
    };

    const handleModelChange = (task: 'analyze' | 'refine' | 'critic', modelId: string) => {
        if (!settings) return;
        setSettings({
            ...settings,
            selected_models: {
                ...settings.selected_models,
                [task]: modelId
            }
        });
    };

    const handleSettingChange = (key: string, value: string | boolean) => {
        if (!settings) return;
        setSettings({ ...settings, [key]: value });
    };

    const toggleFilter = () => {
        if (!settings) return;
        setSettings({
            ...settings,
            filter_free_only: !settings.filter_free_only
        });
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-[#09090b]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!settings) {
        return (
            <div className="p-8 text-center bg-[#09090b] min-h-screen text-[#a1a1aa]">
                <h1 className="text-2xl font-bold text-red-600">Hata</h1>
                <p className="mt-2 text-[#a1a1aa]">Ayarlar verisi yüklenemedi. Backend çalışıyor mu?</p>
                <div className="mt-4">
                    <Link href="/" className="text-blue-500 hover:text-blue-400">Ana Sayfaya Dön</Link>
                </div>
            </div>
        );
    }

    // Filter models for display
    const availableModels = settings.cached_models.filter(m =>
        !settings.filter_free_only || m.is_free
    );

    return (
        <div className="min-h-screen bg-[#09090b] text-[#a1a1aa] p-6 md:p-12 font-inter">
            <div className="max-w-5xl mx-auto bg-[#18181b] border border-[#27272a] rounded-xl shadow-lg overflow-hidden flex flex-col md:flex-row min-h-[600px]">

                {/* Sidebar Navigation */}
                <div className="w-full md:w-64 border-b md:border-b-0 md:border-r border-[#27272a] bg-[#09090b]/30 p-4 space-y-2">
                    <div className="flex items-center gap-2 mb-6 px-2">
                        <Settings className="w-5 h-5 text-blue-500" />
                        <h1 className="font-bold text-[#fafafa]">Ayarlar</h1>
                    </div>

                    <button
                        onClick={() => setActiveTab('models')}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${activeTab === 'models' ? 'bg-[#27272a] text-white' : 'text-[#a1a1aa] hover:bg-[#27272a]/50 hover:text-[#fafafa]'}`}
                    >
                        <Cpu className="w-4 h-4" />
                        Model Yönetimi
                    </button>
                    <button
                        onClick={() => setActiveTab('general')}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${activeTab === 'general' ? 'bg-[#27272a] text-white' : 'text-[#a1a1aa] hover:bg-[#27272a]/50 hover:text-[#fafafa]'}`}
                    >
                        <Layers className="w-4 h-4" />
                        Genel Kabuller
                    </button>
                    <button
                        onClick={() => setActiveTab('signatories')}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${activeTab === 'signatories' ? 'bg-[#27272a] text-white' : 'text-[#a1a1aa] hover:bg-[#27272a]/50 hover:text-[#fafafa]'}`}
                    >
                        <FileSignature className="w-4 h-4" />
                        Imza Ayarları
                    </button>
                    <button
                        onClick={() => setActiveTab('data')}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${activeTab === 'data' ? 'bg-[#27272a] text-white' : 'text-[#a1a1aa] hover:bg-[#27272a]/50 hover:text-[#fafafa]'}`}
                    >
                        <Settings className="w-4 h-4" />
                        Veri Yönetimi
                    </button>

                    <div className="mt-auto pt-6">
                        <Link href="/" className="block w-full text-center px-4 py-2 border border-[#27272a] hover:bg-[#27272a] rounded-lg transition text-xs font-medium text-[#fafafa]">
                            Ana Sayfaya Dön
                        </Link>
                    </div>
                </div>

                {/* Content Area */}
                <div className="flex-1 p-8 overflow-y-auto max-h-[800px]">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-xl font-bold text-[#fafafa]">
                            {activeTab === 'models' && 'Yapay Zeka Modelleri'}
                            {activeTab === 'general' && 'Genel Hesaplama Kabulleri'}
                            {activeTab === 'models' && 'Yapay Zeka Modelleri'}
                            {activeTab === 'general' && 'Genel Hesaplama Kabulleri'}
                            {activeTab === 'signatories' && 'Rapor İmza Ayarları'}
                            {activeTab === 'data' && 'Veri Yönetimi'}
                        </h2>
                        {/* Save Button (Top Right) */}
                        <button
                            onClick={saveSettings}
                            disabled={saving}
                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg shadow transition disabled:opacity-70 disabled:cursor-not-allowed text-xs"
                        >
                            <Save className="w-4 h-4" />
                            {saving ? 'Kaydediliyor...' : 'Kaydet'}
                        </button>
                    </div>

                    {message && (
                        <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 border text-sm ${message.type === 'success' ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-red-500/10 text-red-500 border-red-500/20'}`}>
                            {message.type === 'success' ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                            {message.text}
                        </div>
                    )}

                    {/* --- TAB CONTENT: MODELS --- */}
                    {activeTab === 'models' && (
                        <div className="space-y-8 animate-in fade-in duration-500">
                            <div className="bg-[#09090b] p-6 rounded-xl border border-[#27272a]">
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h3 className="font-semibold text-[#fafafa] mb-1">Model Havuzu</h3>
                                        <p className="text-xs text-[#71717a]">OpenRouter üzerinden erişilebilen modeller.</p>
                                    </div>
                                    <button
                                        onClick={refreshModels}
                                        disabled={refreshing}
                                        className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium bg-[#27272a] border border-[#3f3f46] text-[#fafafa] rounded-md hover:bg-[#3f3f46] transition disabled:opacity-50"
                                    >
                                        <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
                                        {refreshing ? 'Yenileniyor...' : 'Listeyi Yenile'}
                                    </button>
                                </div>
                                <div className="flex items-center gap-3 mb-2">
                                    <div
                                        onClick={toggleFilter}
                                        className={`relative w-9 h-5 rounded-full cursor-pointer transition-colors duration-200 ${settings.filter_free_only ? 'bg-green-600' : 'bg-[#3f3f46]'}`}
                                    >
                                        <div className={`absolute top-1 left-1 w-3 h-3 bg-white rounded-full shadow transition-transform duration-200 ${settings.filter_free_only ? 'translate-x-4' : ''}`} />
                                    </div>
                                    <span className="text-xs font-medium text-[#fafafa] cursor-pointer" onClick={toggleFilter}>
                                        Sadece Ücretsiz Modelleri Göster
                                    </span>
                                </div>
                            </div>

                            <div className="space-y-4">
                                {['analyze', 'refine', 'critic'].map((task) => (
                                    <div key={task} className={`p-4 rounded-lg border flex flex-col md:flex-row md:items-center gap-4 ${task === 'analyze' ? 'bg-blue-500/5 border-blue-500/10' :
                                        task === 'refine' ? 'bg-green-500/5 border-green-500/10' :
                                            'bg-red-500/5 border-red-500/10'
                                        }`}>
                                        <div className="min-w-[140px]">
                                            <div className="flex items-center gap-2 font-medium text-[#fafafa] text-sm capitalize">
                                                {task === 'analyze' && <Shield className="w-4 h-4 text-blue-500" />}
                                                {task === 'refine' && <MessageSquare className="w-4 h-4 text-green-500" />}
                                                {task === 'critic' && <AlertTriangle className="w-4 h-4 text-red-500" />}
                                                {task === 'analyze' ? 'Analiz Motoru' : task === 'refine' ? 'İyileştirici' : 'Denetleyici'}
                                            </div>
                                        </div>
                                        <select
                                            value={settings.selected_models[task as keyof typeof settings.selected_models]}
                                            onChange={(e) => handleModelChange(task as any, e.target.value)}
                                            className="flex-1 p-2 bg-[#09090b] border border-[#27272a] text-[#fafafa] rounded-lg focus:ring-1 focus:ring-blue-500 outline-none text-xs"
                                        >
                                            {availableModels.map(model => (
                                                <option key={model.id} value={model.id}>
                                                    {model.name} {model.is_free ? '(Ücretsiz)' : `($${model.pricing.prompt})`}
                                                </option>
                                            ))}
                                            {!availableModels.some(m => m.id === settings.selected_models[task as keyof typeof settings.selected_models]) && (
                                                <option value={settings.selected_models[task as keyof typeof settings.selected_models]}>
                                                    {settings.selected_models[task as keyof typeof settings.selected_models]} (Mevcut, Listede Yok)
                                                </option>
                                            )}
                                        </select>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* --- TAB CONTENT: GENERAL --- */}
                    {activeTab === 'general' && (
                        <div className="space-y-8 animate-in fade-in duration-500">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div className="space-y-4">
                                    <h3 className="text-sm font-bold text-[#fafafa] uppercase tracking-wider flex items-center gap-2 border-b border-[#27272a] pb-2">
                                        <Layers className="w-4 h-4 text-amber-500" />
                                        Fiyat ve Kâr
                                    </h3>
                                    <Input label="Yüklenici Kârı (%)" value={settings.profit_margin || '25'} onChange={v => handleSettingChange('profit_margin', v)} type="number" />
                                    <Input label="Genel Giderler (%)" value={settings.overhead || '0'} onChange={v => handleSettingChange('overhead', v)} type="number" />
                                </div>

                                <div className="space-y-4">
                                    <h3 className="text-sm font-bold text-[#fafafa] uppercase tracking-wider flex items-center gap-2 border-b border-[#27272a] pb-2">
                                        <Truck className="w-4 h-4 text-blue-500" />
                                        Nakliye Mesafeleri (km)
                                    </h3>
                                    <Input label="Çimento Mesafesi" value={settings.transport_distance_cement || '20'} onChange={v => handleSettingChange('transport_distance_cement', v)} type="number" />
                                    <Input label="Kum/Çakıl Mesafesi" value={settings.transport_distance_sand || '20'} onChange={v => handleSettingChange('transport_distance_sand', v)} type="number" />
                                    <Input label="Diğer Malzemeler" value={settings.transport_distance_other || '20'} onChange={v => handleSettingChange('transport_distance_other', v)} type="number" />
                                </div>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-sm font-bold text-[#fafafa] uppercase tracking-wider flex items-center gap-2 border-b border-[#27272a] pb-2">
                                    <Layers className="w-4 h-4 text-purple-500" />
                                    Malzeme Yoğunlukları (ton/m³)
                                </h3>
                                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                    <Input label="Kum" value={settings.density_sand || '1.60'} onChange={v => handleSettingChange('density_sand', v)} type="number" step="0.01" />
                                    <Input label="Çakıl/Moloz" value={settings.density_gravel || '1.80'} onChange={v => handleSettingChange('density_gravel', v)} type="number" step="0.01" />
                                    <Input label="Demir" value={settings.density_iron || '7.85'} onChange={v => handleSettingChange('density_iron', v)} type="number" step="0.01" />
                                    <Input label="Çimento" value={settings.density_cement || '1.50'} onChange={v => handleSettingChange('density_cement', v)} type="number" step="0.01" />
                                    <Input label="Beton" value={settings.density_concrete || '2.40'} onChange={v => handleSettingChange('density_concrete', v)} type="number" step="0.01" />
                                </div>
                            </div>
                            <div className="space-y-4 pt-4 border-t border-[#27272a]">
                                <h3 className="text-sm font-bold text-[#fafafa] uppercase tracking-wider flex items-center gap-2 border-b border-[#27272a] pb-2">
                                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                                    API Limit & Uyarılar
                                </h3>
                                <div className="bg-[#18181b] border border-[#27272a] rounded-lg p-4">
                                    <p className="text-sm text-[#a1a1aa] mb-4">
                                        OpenRouter API krediniz bu tutarın altına düştüğünde sistem uyarı ve kırmızı gösterge ile sizi bilgilendirecektir.
                                    </p>
                                    <div className="max-w-xs">
                                        <Input
                                            label="Düşük Bakiye Uyarısı ($)"
                                            value={settings.llm_warning_threshold || '5.00'}
                                            onChange={v => handleSettingChange('llm_warning_threshold', v)}
                                            type="number"
                                            step="0.01"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* --- TAB CONTENT: SIGNATORIES --- */}
                    {activeTab === 'signatories' && (
                        <div className="space-y-8 animate-in fade-in duration-500">
                            <p className="text-xs text-[#71717a] bg-[#27272a]/50 p-3 rounded-lg border border-[#27272a]">
                                Bu bilgiler oluşturulan yaklaşık maliyet cetvellerinin ve analiz raporlarının altındaki imza bloğunda görünecektir.
                            </p>

                            <div className="grid grid-cols-1 gap-6">
                                <div className="p-4 rounded-xl border border-[#27272a] bg-[#09090b]/50">
                                    <h4 className="text-sm font-bold text-[#fafafa] mb-4">Hazırlayan</h4>
                                    <div className="grid grid-cols-2 gap-4">
                                        <Input label="Ad Soyad" value={settings.preparer_name || ''} onChange={v => handleSettingChange('preparer_name', v)} />
                                        <Input label="Unvan" value={settings.preparer_title || ''} onChange={v => handleSettingChange('preparer_title', v)} />
                                    </div>
                                </div>

                                <div className="p-4 rounded-xl border border-[#27272a] bg-[#09090b]/50">
                                    <h4 className="text-sm font-bold text-[#fafafa] mb-4">Kontrol Eden</h4>
                                    <div className="grid grid-cols-2 gap-4">
                                        <Input label="Ad Soyad" value={settings.controller_name || ''} onChange={v => handleSettingChange('controller_name', v)} />
                                        <Input label="Unvan" value={settings.controller_title || ''} onChange={v => handleSettingChange('controller_title', v)} />
                                    </div>
                                </div>

                                <div className="p-4 rounded-xl border border-[#27272a] bg-[#09090b]/50">
                                    <h4 className="text-sm font-bold text-[#fafafa] mb-4">Onaylayan</h4>
                                    <div className="grid grid-cols-2 gap-4">
                                        <Input label="Ad Soyad" value={settings.approver_name || ''} onChange={v => handleSettingChange('approver_name', v)} />
                                        <Input label="Unvan" value={settings.approver_title || ''} onChange={v => handleSettingChange('approver_title', v)} />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* --- TAB CONTENT: DATA --- */}
                    {activeTab === 'data' && (
                        <FileManager />
                    )}

                </div>
            </div>
        </div>
    );
}

// Reusable Input Component
function Input({ label, value, onChange, type = 'text', step }: { label: string, value: string, onChange: (v: string) => void, type?: string, step?: string }) {
    return (
        <div className="space-y-1.5">
            <label className="text-xs font-medium text-[#a1a1aa] block">{label}</label>
            <input
                type={type}
                step={step}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-full px-3 py-2 bg-[#09090b] border border-[#27272a] rounded-lg text-sm text-[#fafafa] focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors placeholder-[#3f3f46]"
            />
        </div>
    );
}

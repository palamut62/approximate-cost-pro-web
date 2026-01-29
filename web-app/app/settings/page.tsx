"use client";

import { useState, useEffect } from 'react';
import { Save, RefreshCw, Eye, EyeOff } from 'lucide-react';
import api from '@/lib/api';

export default function SettingsPage() {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [activeTab, setActiveTab] = useState('constants');

    // Settings State
    const [settings, setSettings] = useState<Record<string, string>>({});

    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            const res = await api.get('/settings');
            setSettings(res.data);
        } catch (e) {
            console.error("Settings load error:", e);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async (key: string, value: string) => {
        // Optimistic update
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    const saveAll = async () => {
        setSaving(true);
        try {
            await api.post('/settings/batch', { settings });
            // Show success toast/alert
        } catch (e) {
            console.error("Save error:", e);
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="p-8">Yükleniyor...</div>;

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-slate-800">Ayarlar</h1>
                <button
                    onClick={saveAll}
                    disabled={saving}
                    className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                    <Save className="w-4 h-4 mr-2" />
                    {saving ? 'Kaydediliyor...' : 'Kaydet'}
                </button>
            </div>

            {/* Tabs */}
            <div className="flex space-x-1 bg-slate-100 p-1 rounded-lg">
                <TabButton id="constants" label="Sabitler (Nakliye/Malzeme)" activeById={activeTab} onClick={setActiveTab} />
                <TabButton id="ai" label="Yapay Zeka" activeById={activeTab} onClick={setActiveTab} />
                <TabButton id="signatories" label="İmza Sahipleri" activeById={activeTab} onClick={setActiveTab} />
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                {activeTab === 'constants' && (
                    <div className="space-y-8">
                        {/* Nakliye Params */}
                        <Section title="Nakliye Parametreleri (KGM 2025)">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <Input
                                    label="Taşıma Katsayısı (K) - TL"
                                    value={settings['nakliye_k'] || '1750.00'}
                                    onChange={(v) => handleSave('nakliye_k', v)}
                                    type="number"
                                />
                                <Input
                                    label="A Katsayısı (Zorluk: 1-3)"
                                    value={settings['nakliye_a'] || '1.0'}
                                    onChange={(v) => handleSave('nakliye_a', v)}
                                    type="number" step="0.1"
                                />
                                <div className="col-span-1 md:col-span-2 space-y-4 pt-2 border-t border-slate-100">
                                    <h4 className="text-sm font-semibold text-slate-700">Varsayılan Mesafeler (m)</h4>
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        <Input
                                            label="Demir Nakli"
                                            value={settings['nakliye_mesafe_demir'] || '20000'}
                                            onChange={(v) => handleSave('nakliye_mesafe_demir', v)}
                                            type="number"
                                        />
                                        <Input
                                            label="Çimento Nakli"
                                            value={settings['nakliye_mesafe_cimento'] || '20000'}
                                            onChange={(v) => handleSave('nakliye_mesafe_cimento', v)}
                                            type="number"
                                        />
                                        <Input
                                            label="Diğer Malzemeler"
                                            value={settings['nakliye_mesafe_diger'] || '20000'}
                                            onChange={(v) => handleSave('nakliye_mesafe_diger', v)}
                                            type="number"
                                        />
                                    </div>
                                </div>
                            </div>
                        </Section>

                        {/* Densities */}
                        <Section title="Malzeme Yoğunlukları (ton/m³)">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <Input label="Kum / Çakıl" value={settings['yogunluk_kum'] || '1.60'} onChange={v => handleSave('yogunluk_kum', v)} type="number" step="0.01" />
                                <Input label="Moloz / Taş" value={settings['yogunluk_moloz'] || '1.80'} onChange={v => handleSave('yogunluk_moloz', v)} type="number" step="0.01" />
                                <Input label="Beton" value={settings['yogunluk_beton'] || '2.40'} onChange={v => handleSave('yogunluk_beton', v)} type="number" step="0.01" />
                                <Input label="Çimento" value={settings['yogunluk_cimento'] || '1.50'} onChange={v => handleSave('yogunluk_cimento', v)} type="number" step="0.01" />
                                <Input label="Demir" value={settings['yogunluk_demir'] || '7.85'} onChange={v => handleSave('yogunluk_demir', v)} type="number" step="0.01" />
                            </div>
                        </Section>
                    </div>
                )}

                {activeTab === 'ai' && (
                    <div className="space-y-8">
                        <Section title="AI Sağlayıcı">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-slate-700">Varsayılan Sağlayıcı</label>
                                <select
                                    value={settings['ai_provider'] || 'OpenRouter'}
                                    onChange={(e) => handleSave('ai_provider', e.target.value)}
                                    className="w-full p-2 border border-slate-300 rounded-lg"
                                >
                                    <option value="OpenRouter">OpenRouter</option>
                                    <option value="Google Gemini">Google Gemini</option>
                                </select>
                            </div>
                        </Section>

                        <Section title="OpenRouter Ayarları">
                            <Input
                                label="API Key"
                                value={settings['openrouter_api_key'] || ''}
                                onChange={v => handleSave('openrouter_api_key', v)}
                                type="password"
                            />
                            <Input
                                label="Model"
                                value={settings['openrouter_model'] || 'google/gemini-pro'}
                                onChange={v => handleSave('openrouter_model', v)}
                            />
                        </Section>

                        <Section title="Google Gemini Ayarları">
                            <Input
                                label="API Key"
                                value={settings['gemini_api_key'] || ''}
                                onChange={v => handleSave('gemini_api_key', v)}
                                type="password"
                            />
                            <Input
                                label="Model"
                                value={settings['gemini_model'] || 'gemini-pro'}
                                onChange={v => handleSave('gemini_model', v)}
                            />
                        </Section>
                    </div>
                )}

                {activeTab === 'signatories' && (
                    <div className="space-y-8">
                        <p className="text-sm text-slate-500 bg-blue-50 p-3 rounded">Raporlarda görünecek imza sahipleri.</p>

                        <Section title="Hazırlayan">
                            <div className="grid grid-cols-2 gap-4">
                                <Input label="Ad Soyad" value={settings['hazirlayan_name'] || ''} onChange={v => handleSave('hazirlayan_name', v)} />
                                <Input label="Unvan" value={settings['hazirlayan_title'] || ''} onChange={v => handleSave('hazirlayan_title', v)} />
                            </div>
                        </Section>
                        <Section title="Kontrol Eden">
                            <div className="grid grid-cols-2 gap-4">
                                <Input label="Ad Soyad" value={settings['kontrol1_name'] || ''} onChange={v => handleSave('kontrol1_name', v)} />
                                <Input label="Unvan" value={settings['kontrol1_title'] || ''} onChange={v => handleSave('kontrol1_title', v)} />
                            </div>
                        </Section>
                        <Section title="Onaylayan">
                            <div className="grid grid-cols-2 gap-4">
                                <Input label="Ad Soyad" value={settings['onaylayan_name'] || ''} onChange={v => handleSave('onaylayan_name', v)} />
                                <Input label="Unvan" value={settings['onaylayan_title'] || ''} onChange={v => handleSave('onaylayan_title', v)} />
                            </div>
                        </Section>
                    </div>
                )}
            </div>
        </div>
    );
}

interface SectionProps {
    title: string;
    children: React.ReactNode;
}

interface InputProps {
    label: string;
    value: string;
    onChange: (value: string) => void;
    type?: string;
    step?: string;
}

interface TabButtonProps {
    id: string;
    label: string;
    activeById: string;
    onClick: (id: string) => void;
}

function Section({ title, children }: SectionProps) {
    return (
        <div className="space-y-4">
            <h3 className="text-lg font-bold text-slate-800 border-b pb-2">{title}</h3>
            {children}
        </div>
    );
}

function Input({ label, value, onChange, type = 'text', step }: InputProps) {
    return (
        <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">{label}</label>
            <input
                type={type}
                step={step}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
        </div>
    );
}

function TabButton({ id, label, activeById, onClick }: TabButtonProps) {
    const active = id === activeById;
    return (
        <button
            onClick={() => onClick(id)}
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${active ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                }`}
        >
            {label}
        </button>
    );
}

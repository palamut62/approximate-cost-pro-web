"use client";

import { useState, useEffect } from 'react';
import { Save, RefreshCw, Eye, EyeOff, Settings, Truck, Box, FileText, ShieldCheck, AlertCircle, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

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
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    const saveAll = async () => {
        setSaving(true);
        try {
            await api.post('/settings/batch', { settings });
            showSuccessEffect();
        } catch (e) {
            console.error("Save error:", e);
        } finally {
            setSaving(false);
        }
    };

    const showSuccessEffect = () => {
        // Simple success handling here
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] text-[#71717a]">
                <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
                <p className="animate-pulse font-medium">Sistem parametreleri yükleniyor...</p>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#27272a]/50">
                <div className="space-y-1">
                    <div className="flex items-center gap-2 mb-2">
                        <Settings className="w-4 h-4 text-blue-500" />
                        <span className="text-[10px] font-bold text-[#71717a] uppercase tracking-[0.2em]">Konfigürasyon</span>
                    </div>
                    <h1 className="text-3xl font-bold text-[#fafafa] tracking-tight">Sistem Ayarları</h1>
                    <p className="text-sm text-[#71717a]">Analiz katsayılarını ve rapor parametrelerini yönetin.</p>
                </div>
                <button
                    onClick={saveAll}
                    disabled={saving}
                    className="flex items-center px-8 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-all font-bold shadow-lg shadow-blue-900/40 text-sm active:scale-95 disabled:opacity-50"
                >
                    {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                    {saving ? 'KAYDEDİLİYOR...' : 'DEĞİŞİKLİKLERİ KAYDET'}
                </button>
            </div>

            {/* Tabs - High Fidelity Segment Controls */}
            <div className="flex p-1 bg-[#18181b] rounded-xl border border-[#27272a] shadow-inner max-w-lg">
                <TabButton id="constants" label="Maliyet Katsayıları" activeById={activeTab} onClick={setActiveTab} icon={<Truck className="w-3.5 h-3.5" />} />
                <TabButton id="signatories" label="İmza Paneli" activeById={activeTab} onClick={setActiveTab} icon={<ShieldCheck className="w-3.5 h-3.5" />} />
            </div>

            <div className="bg-[#18181b] rounded-2xl shadow-2xl border border-[#27272a] overflow-hidden">
                <AnimatePresence mode="wait">
                    {activeTab === 'constants' ? (
                        <motion.div
                            key="constants"
                            initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 10 }}
                            className="p-8 space-y-12"
                        >
                            {/* Nakliye Params */}
                            <Section title="Nakliye Parametreleri (KGM 2025)" subtitle="Birim taşıma maliyeti hesaplama değişkenleri">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <Input
                                        label="Taşıma Katsayısı (K) - TL"
                                        value={settings['nakliye_k'] || '1750.00'}
                                        onChange={(v) => handleSave('nakliye_k', v)}
                                        type="number"
                                    />
                                    <Input
                                        label="Zorluk Katsayısı (A)"
                                        value={settings['nakliye_a'] || '1.0'}
                                        onChange={(v) => handleSave('nakliye_a', v)}
                                        type="number" step="0.1"
                                    />
                                </div>

                                <div className="p-6 bg-[#09090b]/50 rounded-xl border border-[#27272a] space-y-6">
                                    <h4 className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest flex items-center gap-2">
                                        <Truck className="w-3 h-3" /> Varsayılan Taşıma Mesafeleri (m)
                                    </h4>
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                        <Input
                                            label="Profil Demir Nakli"
                                            value={settings['nakliye_mesafe_demir'] || '20000'}
                                            onChange={(v) => handleSave('nakliye_mesafe_demir', v)}
                                            type="number"
                                        />
                                        <Input
                                            label="Torbalı Çimento Nakli"
                                            value={settings['nakliye_mesafe_cimento'] || '20000'}
                                            onChange={(v) => handleSave('nakliye_mesafe_cimento', v)}
                                            type="number"
                                        />
                                        <Input
                                            label="Standart Malzemeler"
                                            value={settings['nakliye_mesafe_diger'] || '20000'}
                                            onChange={(v) => handleSave('nakliye_mesafe_diger', v)}
                                            type="number"
                                        />
                                    </div>
                                </div>
                            </Section>

                            {/* Densities */}
                            <Section title="Yoğunluk Sabitleri" subtitle="Hacim → Ağırlık dönüşümü için ton/m³ değerleri">
                                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                                    <Input label="Kum / Çakıl" value={settings['yogunluk_kum'] || '1.60'} onChange={v => handleSave('yogunluk_kum', v)} type="number" step="0.01" compact />
                                    <Input label="Moloz / Taş" value={settings['yogunluk_moloz'] || '1.80'} onChange={v => handleSave('yogunluk_moloz', v)} type="number" step="0.01" compact />
                                    <Input label="Standart Beton" value={settings['yogunluk_beton'] || '2.40'} onChange={v => handleSave('yogunluk_beton', v)} type="number" step="0.01" compact />
                                    <Input label="Cem I-II PÇ" value={settings['yogunluk_cimento'] || '1.50'} onChange={v => handleSave('yogunluk_cimento', v)} type="number" step="0.01" compact />
                                    <Input label="İnşaat Çeliği" value={settings['yogunluk_demir'] || '7.85'} onChange={v => handleSave('yogunluk_demir', v)} type="number" step="0.01" compact />
                                </div>
                            </Section>

                            {/* LLM Usage Warning */}
                            <Section title="AI Servis Limitleri" subtitle="Model kullanımı ve bütçe uyarıları">
                                <div className="max-w-md p-6 bg-blue-600/[0.03] rounded-xl border border-blue-500/10 flex gap-4">
                                    <AlertCircle className="w-5 h-5 text-blue-500 shrink-0" />
                                    <div className="space-y-3">
                                        <Input
                                            label="Bütçe Uyarı Eşiği (USD)"
                                            value={settings['llm_warning_threshold'] || '1.00'}
                                            onChange={v => handleSave('llm_warning_threshold', v)}
                                            type="number"
                                            step="0.01"
                                        />
                                        <p className="text-[10px] text-[#71717a] font-medium leading-relaxed">
                                            LLM kullanım paneli bu tutarın altına düştüğünde sistem genelinde düşük bakiy uyarısı görüntülenir.
                                        </p>
                                    </div>
                                </div>
                            </Section>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="signatories"
                            initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }}
                            className="p-8 space-y-12"
                        >
                            <div className="p-4 bg-purple-600/5 rounded-xl border border-purple-500/10 flex items-center gap-3">
                                <ShieldCheck className="w-5 h-5 text-purple-500" />
                                <p className="text-xs text-[#a1a1aa] font-medium">Bu bilgiler oluşturulacak resmi raporların imza bloğunda otomatik olarak kullanılacaktır.</p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
                                <Section title="Hazırlayan">
                                    <div className="space-y-4">
                                        <Input label="Ad Soyad" value={settings['hazirlayan_name'] || ''} onChange={v => handleSave('hazirlayan_name', v)} />
                                        <Input label="Unvan" value={settings['hazirlayan_title'] || ''} onChange={v => handleSave('hazirlayan_title', v)} />
                                    </div>
                                </Section>
                                <Section title="Kontrol Eden">
                                    <div className="space-y-4">
                                        <Input label="Ad Soyad" value={settings['kontrol1_name'] || ''} onChange={v => handleSave('kontrol1_name', v)} />
                                        <Input label="Unvan" value={settings['kontrol1_title'] || ''} onChange={v => handleSave('kontrol1_title', v)} />
                                    </div>
                                </Section>
                                <Section title="Onaylayan">
                                    <div className="space-y-4">
                                        <Input label="Ad Soyad" value={settings['onaylayan_name'] || ''} onChange={v => handleSave('onaylayan_name', v)} />
                                        <Input label="Unvan" value={settings['onaylayan_title'] || ''} onChange={v => handleSave('onaylayan_title', v)} />
                                    </div>
                                </Section>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

interface SectionProps {
    title: string;
    subtitle?: string;
    children: React.ReactNode;
}

interface InputProps {
    label: string;
    value: string;
    onChange: (value: string) => void;
    type?: string;
    step?: string;
    compact?: boolean;
}

interface TabButtonProps {
    id: string;
    label: string;
    activeById: string;
    onClick: (id: string) => void;
    icon?: React.ReactNode;
}

function Section({ title, subtitle, children }: SectionProps) {
    return (
        <div className="space-y-6">
            <div className="space-y-1">
                <h3 className="text-xl font-bold text-[#fafafa] tracking-tight">{title}</h3>
                {subtitle && <p className="text-xs text-[#71717a]">{subtitle}</p>}
            </div>
            {children}
        </div>
    );
}

function Input({ label, value, onChange, type = 'text', step, compact }: InputProps) {
    return (
        <div className="space-y-2">
            <label className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">{label}</label>
            <input
                type={type}
                step={step}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className={cn(
                    "w-full bg-[#09090b] border border-[#27272a] rounded-xl text-[#fafafa] focus:outline-none focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all font-medium",
                    compact ? "px-3 py-2 text-sm" : "px-4 py-3 text-base"
                )}
            />
        </div>
    );
}

function TabButton({ id, label, activeById, onClick, icon }: TabButtonProps) {
    const active = id === activeById;
    return (
        <button
            onClick={() => onClick(id)}
            className={cn(
                "flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-bold rounded-lg transition-all",
                active
                    ? "bg-[#27272a] text-[#fafafa] shadow-lg ring-1 ring-white/5"
                    : "text-[#71717a] hover:text-[#a1a1aa] hover:bg-[#27272a]/50"
            )}
        >
            {icon}
            {label.toUpperCase()}
        </button>
    );
}

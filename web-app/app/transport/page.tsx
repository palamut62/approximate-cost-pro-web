"use client";

import { useState, useEffect } from 'react';
import { Truck, Calculator, Info, RotateCcw, ArrowLeft, Loader2, Gauge, Scale, MapPin, Sparkles, Box, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

// Malzeme yoğunlukları (ton/m³)
const MATERIAL_DENSITIES: Record<string, number> = {
    "Beton / Prefabrik": 2.40,
    "Betonarme Demiri": 7.85,
    "Çimento": 1.50,
    "Kum / Çakıl / Stabilize": 1.60,
    "Moloz / Anroşman / Taş": 1.80,
    "Kireç": 1.00,
    "Tuğla": 1.80,
    "Asfalt": 2.30,
    "Toprak": 1.70,
    "Diğer (Manuel Gir)": 0.0
};

const DEFAULT_DENSITIES: Record<string, number> = {
    "Beton / Prefabrik": 2.40,
    "Betonarme Demiri": 7.85,
    "Çimento": 1.50,
    "Kum / Çakıl / Stabilize": 1.60,
    "Moloz / Anroşman / Taş": 1.80,
    "Kireç": 1.00,
    "Tuğla": 1.80,
    "Asfalt": 2.30,
    "Toprak": 1.70,
    "Diğer (Manuel Gir)": 0.0
};

export default function TransportPage() {
    // State
    const [densities, setDensities] = useState<Record<string, number>>(DEFAULT_DENSITIES);
    const [material, setMaterial] = useState("Beton / Prefabrik");
    const [density, setDensity] = useState(2.40);
    const [quantity, setQuantity] = useState(10.0);
    const [unit, setUnit] = useState("m³");
    // Distance State
    const [distances, setDistances] = useState({
        demir: 20000,
        cimento: 20000,
        diger: 20000
    });

    const [distance, setDistance] = useState(20000); // meters
    const [kCoeff, setKCoeff] = useState(1750.00);
    const [aCoeff, setACoeff] = useState(1.0);
    const [formulaChoice, setFormulaChoice] = useState("auto"); // auto, 005, 006

    // Results
    const [results, setResults] = useState<{
        f_ton: number;
        f_m3: number;
        total_ton: number;
        total_m3: number;
        formula_used: string;
    } | null>(null);

    const [loading, setLoading] = useState(true);

    // Load defaults from API
    useEffect(() => {
        const loadSettings = async () => {
            try {
                const res = await api.get('/settings');
                const s = res.data;

                setDensities(prev => ({
                    ...prev,
                    "Beton / Prefabrik": parseFloat(s['yogunluk_beton']) || prev["Beton / Prefabrik"],
                    "Kum / Çakıl / Stabilize": parseFloat(s['yogunluk_kum']) || prev["Kum / Çakıl / Stabilize"],
                    "Moloz / Anroşman / Taş": parseFloat(s['yogunluk_moloz']) || prev["Moloz / Anroşman / Taş"],
                    "Çimento": parseFloat(s['yogunluk_cimento']) || prev["Çimento"],
                    "Betonarme Demiri": parseFloat(s['yogunluk_demir']) || prev["Betonarme Demiri"],
                }));

                if (s['nakliye_k']) setKCoeff(parseFloat(s['nakliye_k']));
                if (s['nakliye_a']) setACoeff(parseFloat(s['nakliye_a']));

                const d_demir = parseFloat(s['nakliye_mesafe_demir']) || 20000;
                const d_cimento = parseFloat(s['nakliye_mesafe_cimento']) || 20000;
                const d_diger = parseFloat(s['nakliye_mesafe_diger']) || 20000;

                setDistances({ demir: d_demir, cimento: d_cimento, diger: d_diger });
                setDistance(d_diger);

            } catch (e) {
                console.error("Settings load error:", e);
            } finally {
                setLoading(false);
            }
        };
        loadSettings();
    }, []);

    // Update density and distance when material changes
    useEffect(() => {
        const d = densities[material];
        if (d !== undefined && d > 0) {
            setDensity(d);
        }

        if (material === "Betonarme Demiri") {
            setDistance(distances.demir);
        } else if (material === "Çimento") {
            setDistance(distances.cimento);
        } else {
            setDistance(distances.diger);
        }
    }, [material, densities, distances]);

    const handleCalculate = () => {
        let formula = "";
        if (formulaChoice === "auto") {
            formula = distance <= 10000 ? "07.005/K" : "07.006/K";
        } else if (formulaChoice === "005") {
            formula = "07.005/K";
        } else {
            formula = "07.006/K";
        }

        let f_ton = 0;
        let f_m3 = 0;

        if (formula === "07.005/K") {
            f_ton = 1.25 * 0.00017 * kCoeff * Math.sqrt(distance) * aCoeff;
            f_m3 = f_ton * density;
        } else {
            const distanceKm = distance / 1000.0;
            f_ton = 1.25 * kCoeff * (0.0007 * distanceKm + 0.01) * aCoeff;
            f_m3 = f_ton * density;
        }

        let total_ton = 0;
        let total_m3 = 0;

        if (unit === "m³") {
            const quantity_m3 = quantity;
            const quantity_ton = quantity * density;
            total_ton = f_ton * quantity_ton;
            total_m3 = f_m3 * quantity_m3;
        } else {
            const quantity_ton = quantity;
            const quantity_m3 = density > 0 ? quantity / density : 0;
            total_ton = f_ton * quantity_ton;
            total_m3 = f_m3 * quantity_m3;
        }

        setResults({ f_ton, f_m3, total_ton, total_m3, formula_used: formula });
    };

    const handleClear = () => {
        setResults(null);
        setMaterial("Beton / Prefabrik");
        setDensity(2.40);
        setQuantity(10.0);
        setDistance(distances.diger);
        setKCoeff(1750.00);
        setACoeff(1.0);
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] text-[#71717a]">
                <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
                <p className="animate-pulse font-medium">Birim fiyatlar hesaplanıyor...</p>
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-5xl mx-auto animate-in fade-in duration-500 pb-12">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#27272a]/50">
                <div className="flex items-center gap-4">
                    <Link href="/" className="p-2 hover:bg-[#18181b] rounded-xl transition-all border border-transparent hover:border-[#27272a] text-[#52525b] hover:text-[#fafafa]">
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div className="space-y-1">
                        <div className="flex items-center gap-2 mb-2">
                            <Truck className="w-4 h-4 text-blue-500" />
                            <span className="text-[10px] font-bold text-[#71717a] uppercase tracking-[0.2em]">KGM Formülleri</span>
                        </div>
                        <h1 className="text-3xl font-bold text-[#fafafa] tracking-tight">Nakliye Hesabı</h1>
                        <p className="text-sm text-[#71717a]">Karayolları Genel Müdürlüğü analitik formülleriyle taşıma maliyeti.</p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                {/* Input Panel */}
                <div className="space-y-8">
                    <div className="bg-[#18181b] rounded-2xl shadow-2xl border border-[#27272a] p-8 space-y-8 ring-1 ring-white/5">
                        <div className="flex items-center justify-between">
                            <h2 className="font-bold text-lg text-white flex items-center gap-2">
                                <Calculator className="w-5 h-5 text-blue-500" />
                                Girdi Parametreleri
                            </h2>
                            <button onClick={handleClear} className="text-[10px] font-black uppercase text-[#52525b] hover:text-red-500 transition-colors flex items-center gap-1 mt-1 font-mono">
                                <RotateCcw className="w-3 h-3" /> TEMİZLE
                            </button>
                        </div>

                        {/* Formula Selection - Segmented Control style */}
                        <div className="space-y-3">
                            <label className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest flex items-center gap-2">
                                <Gauge className="w-3 h-3" /> Nakliye Formülü
                            </label>
                            <div className="flex p-1 bg-[#09090b] rounded-xl border border-[#27272a]">
                                {[
                                    { id: "auto", label: "OTOMATİK" },
                                    { id: "005", label: "07.005/K" },
                                    { id: "006", label: "07.006/K" },
                                ].map((opt) => (
                                    <button
                                        key={opt.id}
                                        onClick={() => setFormulaChoice(opt.id)}
                                        className={cn(
                                            "flex-1 py-2 text-[10px] font-black rounded-lg transition-all",
                                            formulaChoice === opt.id
                                                ? "bg-[#27272a] text-white shadow-lg ring-1 ring-white/5"
                                                : "text-[#52525b] hover:text-[#71717a]"
                                        )}
                                    >
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Material & Density Row */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">Malzeme Sınıfı</label>
                                <select
                                    value={material}
                                    onChange={(e) => setMaterial(e.target.value)}
                                    className="w-full bg-[#09090b] border border-[#27272a] rounded-xl px-4 py-3 text-[#fafafa] font-medium focus:ring-1 focus:ring-blue-500/50 outline-none appearance-none"
                                >
                                    {Object.keys(densities).map((m) => (
                                        <option key={m} value={m}>{m}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="space-y-2 relative">
                                <label className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">Özgül Ağırlık</label>
                                <div className="relative">
                                    <input
                                        type="number"
                                        value={density}
                                        onChange={(e) => setDensity(parseFloat(e.target.value) || 0)}
                                        disabled={densities[material] > 0}
                                        className="w-full bg-[#09090b] border border-[#27272a] rounded-xl px-4 py-3 text-[#fafafa] font-mono focus:ring-1 focus:ring-blue-500/50 outline-none disabled:opacity-50"
                                    />
                                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] font-bold text-[#52525b]">TON/M³</span>
                                </div>
                            </div>
                        </div>

                        {/* Quantities Row */}
                        <div className="grid grid-cols-3 gap-4">
                            <div className="col-span-2 space-y-2">
                                <label className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest flex items-center gap-2">
                                    <Scale className="w-3 h-3" /> Miktar
                                </label>
                                <input
                                    type="number"
                                    value={quantity}
                                    onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
                                    className="w-full bg-[#09090b] border border-[#27272a] rounded-xl px-4 py-3 text-[#fafafa] font-mono focus:ring-1 focus:ring-blue-500/50 outline-none"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">Birim</label>
                                <select
                                    value={unit}
                                    onChange={(e) => setUnit(e.target.value)}
                                    className="w-full h-[50px] bg-[#09090b] border border-[#27272a] rounded-xl px-2 py-3 text-center text-[#fafafa] font-bold outline-none appearance-none"
                                >
                                    <option value="m³">M³</option>
                                    <option value="ton">TON</option>
                                </select>
                            </div>
                        </div>

                        {/* Distance - Premium Slider-Like control */}
                        <div className="space-y-4">
                            <div className="flex justify-between items-end">
                                <label className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest flex items-center gap-2">
                                    <MapPin className="w-3 h-3 text-blue-500" /> Taşıma Mesafesi
                                </label>
                                <div className="text-right">
                                    <div className="text-2xl font-black text-white tracking-tighter">{(distance / 1000).toFixed(1)} <span className="text-xs text-blue-500">KM</span></div>
                                    <span className="text-[10px] font-mono font-bold text-[#52525b] tabular-nums text-right block">{distance.toLocaleString()} METRE</span>
                                </div>
                            </div>
                            <input
                                type="number"
                                value={distance}
                                onChange={(e) => setDistance(parseFloat(e.target.value) || 0)}
                                className="w-full bg-[#09090b] border border-[#27272a] rounded-xl px-4 py-3 text-[#fafafa] font-mono focus:ring-1 focus:ring-blue-500/50 outline-none"
                            />
                            <div className="grid grid-cols-4 gap-2">
                                {[5000, 10000, 20000, 50000].map(d => (
                                    <button
                                        key={d}
                                        onClick={() => setDistance(d)}
                                        className={cn(
                                            "py-2 text-[10px] font-bold rounded-lg border transition-all",
                                            distance === d
                                                ? "bg-blue-600/10 border-blue-500/50 text-blue-500"
                                                : "bg-transparent border-[#27272a] text-[#52525b] hover:border-[#3f3f46] hover:text-[#71717a]"
                                        )}
                                    >
                                        {d / 1000}KM
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Coefficients */}
                        <div className="grid grid-cols-2 gap-6 pt-4 border-t border-[#27272a]">
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">K Katsayısı</label>
                                <input
                                    type="number"
                                    value={kCoeff}
                                    onChange={(e) => setKCoeff(parseFloat(e.target.value) || 0)}
                                    className="w-full bg-[#09090b] border border-[#27272a] rounded-xl px-4 py-3 text-[#fafafa] font-mono focus:ring-1 focus:ring-blue-500/50 outline-none"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">Zorluk (A)</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    value={aCoeff}
                                    onChange={(e) => setACoeff(parseFloat(e.target.value) || 1)}
                                    className="w-full bg-[#09090b] border border-[#27272a] rounded-xl px-4 py-3 text-[#fafafa] font-mono focus:ring-1 focus:ring-blue-500/50 outline-none"
                                />
                            </div>
                        </div>

                        <button
                            onClick={handleCalculate}
                            className="w-full py-5 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-black tracking-widest transition-all shadow-xl shadow-blue-900/40 active:scale-95 flex items-center justify-center gap-3"
                        >
                            <Sparkles className="w-5 h-5" />
                            ANALİZİ ÇALIŞTIR
                        </button>
                    </div>
                </div>

                {/* Results Panel */}
                <div className="space-y-8 flex flex-col">
                    <AnimatePresence mode="wait">
                        {results ? (
                            <motion.div
                                key="results"
                                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                className="bg-[#18181b] rounded-2xl shadow-2xl border border-[#27272a] p-8 space-y-8 flex-1 relative overflow-hidden"
                            >
                                <div className="absolute top-0 right-0 w-64 h-64 bg-orange-500/[0.03] blur-[80px] -z-0" />

                                <div className="flex justify-between items-center relative z-10">
                                    <h2 className="font-bold text-lg text-white">Analiz Sonuçları</h2>
                                    <div className="text-[10px] font-black uppercase text-orange-500 bg-orange-500/10 px-2 py-1 rounded border border-orange-500/20 tracking-[0.2em] animate-pulse">
                                        OFFICIAL KGM DATA
                                    </div>
                                </div>

                                <div className="p-6 bg-[#09090b] rounded-2xl border border-[#27272a] relative z-10">
                                    <p className="text-[10px] text-[#52525b] font-bold uppercase tracking-widest mb-2">Uygulanan Birim Fiyat Formülü</p>
                                    <p className="text-3xl font-black text-white tracking-widest font-mono">{results.formula_used}</p>
                                    <div className="mt-4 flex items-start gap-3 p-3 bg-blue-500/5 border border-blue-500/10 rounded-lg">
                                        <Info className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                                        <p className="text-[11px] text-[#a1a1aa] leading-relaxed font-medium">
                                            {results.formula_used === "07.005/K"
                                                ? "Mesafe ≤ 10km olması nedeniyle 07.005/K (Karayolu İle Kısa Mesafe Taşımaları) analiz formülü uygulanmıştır."
                                                : "Mesafe > 10km olması nedeniyle 07.006/K (Karayolu İle Uzun Mesafe Taşımaları) analiz formülü uygulanmıştır. Mesafe KM bazlı hesaplanır."
                                            }
                                        </p>
                                    </div>
                                </div>

                                <div className="space-y-4 relative z-10">
                                    <div className="flex justify-between items-center py-4 border-b border-[#27272a]">
                                        <div className="flex items-center gap-2">
                                            <div className="w-2 h-2 rounded-full bg-blue-500" />
                                            <span className="text-[#a1a1aa] text-sm font-medium">Birim Nakliye (TON)</span>
                                        </div>
                                        <span className="font-mono font-bold text-white text-lg tracking-tighter tabular-nums">{results.f_ton.toFixed(4)} <span className="text-xs text-[#52525b]">TL/T</span></span>
                                    </div>
                                    <div className="flex justify-between items-center py-4 border-b border-[#27272a]">
                                        <div className="flex items-center gap-2">
                                            <div className="w-2 h-2 rounded-full bg-purple-500" />
                                            <span className="text-[#a1a1aa] text-sm font-medium">Birim Nakliye (M³)</span>
                                        </div>
                                        <span className="font-mono font-bold text-white text-lg tracking-tighter tabular-nums">{results.f_m3.toFixed(4)} <span className="text-xs text-[#52525b]">TL/M³</span></span>
                                    </div>
                                </div>

                                <div className="bg-black/40 rounded-2xl p-8 border border-[#27272a] space-y-6 relative z-10">
                                    <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                                        <div className="space-y-1">
                                            <p className="text-[10px] text-[#52525b] font-bold uppercase tracking-widest">TOPLAM TAŞIMA MALİYETİ</p>
                                            <p className="text-xs text-blue-500/50 font-mono italic">({quantity} {unit} × {density} T/M³ × birim fiyat)</p>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-4xl font-black text-white tracking-tighter tabular-nums drop-shadow-2xl">
                                                {results.total_ton.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} <span className="text-sm text-blue-500 font-bold tracking-normal">TL</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="mt-auto pt-6 border-t border-[#27272a] text-[10px] font-bold text-[#52525b] uppercase tracking-[0.2em] flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Box className="w-3 h-3" />
                                        HESAPLAMA DOĞRULANDI
                                    </div>
                                    <div className="flex items-center gap-1 text-blue-500/50">
                                        REEL VERİ <ShieldCheck className="w-3 h-3" />
                                    </div>
                                </div>
                            </motion.div>
                        ) : (
                            <motion.div
                                key="empty"
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                className="bg-[#18181b]/30 rounded-2xl border border-dashed border-[#27272a] p-12 flex flex-col items-center justify-center h-full min-h-[500px] text-center space-y-4"
                            >
                                <div className="w-20 h-20 bg-[#18181b] rounded-full flex items-center justify-center mx-auto text-[#27272a] border border-[#27272a] mb-2">
                                    <Truck className="w-10 h-10 opacity-20" />
                                </div>
                                <div className="max-w-xs mx-auto space-y-1">
                                    <p className="text-[#fafafa] font-bold text-sm tracking-widest uppercase">Hesaplama İçin Girdi Bekleniyor</p>
                                    <p className="text-[#52525b] text-xs leading-relaxed">Taşıma katsayılarını, mesafe ve malzeme türünü girerek hesaplamayı başlatın.</p>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}


"use client";

import { useState, useEffect } from 'react';
import { Truck, Calculator, Info, RotateCcw, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';

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

    // Load defaults from API
    useEffect(() => {
        const loadSettings = async () => {
            try {
                const res = await api.get('/settings');
                const s = res.data;

                // Update densites if present
                setDensities(prev => ({
                    ...prev,
                    "Beton / Prefabrik": parseFloat(s['yogunluk_beton']) || prev["Beton / Prefabrik"],
                    "Kum / Çakıl / Stabilize": parseFloat(s['yogunluk_kum']) || prev["Kum / Çakıl / Stabilize"],
                    "Moloz / Anroşman / Taş": parseFloat(s['yogunluk_moloz']) || prev["Moloz / Anroşman / Taş"],
                    "Çimento": parseFloat(s['yogunluk_cimento']) || prev["Çimento"],
                    "Betonarme Demiri": parseFloat(s['yogunluk_demir']) || prev["Betonarme Demiri"],
                }));

                // Update params
                // Update params
                if (s['nakliye_k']) setKCoeff(parseFloat(s['nakliye_k']));
                if (s['nakliye_a']) setACoeff(parseFloat(s['nakliye_a']));

                // Update distances
                const d_demir = parseFloat(s['nakliye_mesafe_demir']) || 20000;
                const d_cimento = parseFloat(s['nakliye_mesafe_cimento']) || 20000;
                const d_diger = parseFloat(s['nakliye_mesafe_diger']) || 20000;

                setDistances({ demir: d_demir, cimento: d_cimento, diger: d_diger });

                // Set initial distance based on current material (defaults to Beton -> Diger)
                setDistance(d_diger);

            } catch (e) {
                console.error("Settings load error:", e);
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

        // Auto-set distance based on material type
        if (material === "Betonarme Demiri") {
            setDistance(distances.demir);
        } else if (material === "Çimento") {
            setDistance(distances.cimento);
        } else {
            setDistance(distances.diger);
        }
    }, [material, densities, distances]); // Added distances dependency

    const handleCalculate = () => {
        let formula = "";

        // Determine formula
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
            // F = 1.25 × 0.00017 × K × M × A (for ton)
            f_ton = 1.25 * 0.00017 * kCoeff * distance * aCoeff;
            f_m3 = f_ton * density;
        } else {
            // F = 1.25 × K × (0.0007 × M + 0.01) × A (for ton)
            f_ton = 1.25 * kCoeff * (0.0007 * distance + 0.01) * aCoeff;
            f_m3 = f_ton * density;
        }

        // Calculate totals based on input quantity unit
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

        setResults({
            f_ton,
            f_m3,
            total_ton,
            total_m3,
            formula_used: formula
        });
    };

    const handleClear = () => {
        setResults(null);
        setMaterial("Beton / Prefabrik");
        setDensity(2.40);
        setQuantity(10.0);
        // Reset distance based on default material (Beton -> Diger)
        setDistance(distances.diger);
        setKCoeff(1750.00);
        setACoeff(1.0);
    };

    return (
        <div className="space-y-8 max-w-4xl mx-auto">
            <div className="flex items-center space-x-4">
                <Link href="/" className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
                    <ArrowLeft className="w-6 h-6 text-slate-500" />
                </Link>
                <div>
                    <h1 className="text-2xl font-bold text-slate-800 flex items-center">
                        <Truck className="w-8 h-8 mr-3 text-blue-600" />
                        KGM Nakliye Hesaplama
                    </h1>
                    <p className="text-slate-500">2025 Yılı Karayolları Genel Müdürlüğü formülleri ile nakliye analizi.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Input Panel */}
                <div className="space-y-6">
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
                        <h2 className="font-bold text-lg text-slate-700 flex items-center">
                            <Calculator className="w-5 h-5 mr-2" />
                            Parametreler
                        </h2>

                        {/* Formula Selection */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">Formül Seçimi</label>
                            <div className="flex space-x-4">
                                {[
                                    { id: "auto", label: "Otomatik" },
                                    { id: "005", label: "07.005/K (≤10km)" },
                                    { id: "006", label: "07.006/K (>10km)" },
                                ].map((opt) => (
                                    <label key={opt.id} className="flex items-center space-x-2 cursor-pointer">
                                        <input
                                            type="radio"
                                            name="formula"
                                            checked={formulaChoice === opt.id}
                                            onChange={() => setFormulaChoice(opt.id)}
                                            className="text-blue-600 focus:ring-blue-500"
                                        />
                                        <span className="text-sm text-slate-600">{opt.label}</span>
                                    </label>
                                ))}
                            </div>
                        </div>

                        {/* Material & Density */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-slate-700">Malzeme Tipi</label>
                                <select
                                    value={material}
                                    onChange={(e) => setMaterial(e.target.value)}
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                >
                                    {Object.keys(densities).map((m) => (
                                        <option key={m} value={m}>{m}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-slate-700">Yoğunluk (ton/m³)</label>
                                <input
                                    type="number"
                                    value={density}
                                    onChange={(e) => setDensity(parseFloat(e.target.value) || 0)}
                                    disabled={densities[material] > 0}
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:ring-2 focus:ring-blue-500 outline-none disabled:opacity-75"
                                />
                            </div>
                        </div>

                        {/* Quantity */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">Miktar</label>
                            <div className="flex space-x-2">
                                <input
                                    type="number"
                                    value={quantity}
                                    onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
                                    className="flex-1 px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                />
                                <select
                                    value={unit}
                                    onChange={(e) => setUnit(e.target.value)}
                                    className="w-24 px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                >
                                    <option value="m³">m³</option>
                                    <option value="ton">ton</option>
                                </select>
                            </div>
                        </div>

                        {/* Distance */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700">Mesafe (Metre)</label>
                            <input
                                type="number"
                                value={distance}
                                onChange={(e) => setDistance(parseFloat(e.target.value) || 0)}
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                            <div className="flex space-x-2 mt-2">
                                {[5000, 10000, 20000, 50000].map(d => (
                                    <button
                                        key={d}
                                        onClick={() => setDistance(d)}
                                        className="px-2 py-1 text-xs bg-slate-100 hover:bg-slate-200 rounded text-slate-600 transition-colors"
                                    >
                                        {d / 1000}km
                                    </button>
                                ))}
                            </div>
                            <p className="text-xs text-slate-400 text-right">{(distance / 1000).toFixed(1)} km</p>
                        </div>

                        {/* Coefficients */}
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-slate-700">K Katsayısı (TL)</label>
                                <input
                                    type="number"
                                    value={kCoeff}
                                    onChange={(e) => setKCoeff(parseFloat(e.target.value) || 0)}
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-slate-700">A Katsayısı</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    value={aCoeff}
                                    onChange={(e) => setACoeff(parseFloat(e.target.value) || 1)}
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                />
                                <p className="text-[10px] text-slate-400">Zor: 1-3, Kolay: &lt;1</p>
                            </div>
                        </div>

                        <button
                            onClick={handleCalculate}
                            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold transition-colors shadow-sm shadow-blue-200"
                        >
                            HESAPLA
                        </button>
                    </div>
                </div>

                {/* Results Panel */}
                <div className="space-y-6">
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 h-full flex flex-col">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="font-bold text-lg text-slate-700">Sonuçlar</h2>
                            {results && (
                                <button
                                    onClick={handleClear}
                                    className="text-sm text-slate-400 hover:text-red-500 flex items-center transition-colors"
                                >
                                    <RotateCcw className="w-4 h-4 mr-1" />
                                    Temizle
                                </button>
                            )}
                        </div>

                        {results ? (
                            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
                                <div className="p-4 bg-orange-50 border border-orange-100 rounded-lg">
                                    <p className="text-xs text-orange-600 font-bold uppercase mb-1">Kullanılan Formül</p>
                                    <p className="text-lg font-mono text-orange-800">{results.formula_used}</p>
                                </div>

                                <div className="space-y-4">
                                    <div className="flex justify-between items-center py-2 border-b border-slate-100">
                                        <span className="text-slate-500 text-sm">Birim Fiyat (ton)</span>
                                        <span className="font-mono font-bold text-slate-800">{results.f_ton.toFixed(4)} TL/ton</span>
                                    </div>
                                    <div className="flex justify-between items-center py-2 border-b border-slate-100">
                                        <span className="text-slate-500 text-sm">Birim Fiyat (m³)</span>
                                        <span className="font-mono font-bold text-slate-800">{results.f_m3.toFixed(4)} TL/m³</span>
                                    </div>
                                </div>

                                <div className="bg-slate-50 rounded-xl p-6 space-y-4">
                                    <div className="flex justify-between items-end">
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1">Toplam Maliyet (ton)</p>
                                            <p className="text-sm text-slate-400">({quantity} {unit} × yoğunluk)</p>
                                        </div>
                                        <p className="text-2xl font-bold text-slate-800 tracking-tight">
                                            {results.total_ton.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} TL
                                        </p>
                                    </div>
                                    <div className="h-px bg-slate-200 w-full" />
                                    <div className="flex justify-between items-end">
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1">Toplam Maliyet (m³)</p>
                                            <p className="text-sm text-slate-400 font-mono">≈ Aynı Tutar</p>
                                        </div>
                                        <p className="text-xl font-bold text-slate-600 tracking-tight">
                                            {results.total_m3.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} TL
                                        </p>
                                    </div>
                                </div>

                                <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg flex items-start space-x-3">
                                    <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                                    <div className="text-xs text-blue-800 space-y-1">
                                        <p className="font-bold">Formül Açıklaması:</p>
                                        {results.formula_used === "07.005/K" ? (
                                            <p>F = 1,25 × 0,00017 × K × M × Y × A<br />(10km altı mesafeler için)</p>
                                        ) : (
                                            <p>F = 1,25 × K × (0,0007 × M + 0,01) × Y × A<br />(10km üzeri mesafeler için)</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center text-slate-300">
                                <Truck className="w-16 h-16 mb-4 opacity-20" />
                                <p>Hesaplama yapmak için parametreleri girip "HESAPLA" butonuna basın.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

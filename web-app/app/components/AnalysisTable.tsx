"use client";

import React from 'react';
import { cn } from '@/lib/utils';

// Tip Tanımları
export interface AnalysisComponent {
    type: string;
    code: string;
    name: string;
    unit: string;
    quantity: string;
    price: string;
    total: string;
}

export interface AnalysisData {
    poz_no: string;
    name: string;
    unit: string;
    components: AnalysisComponent[];
    totals: {
        subtotal?: string;
        profit?: string;
        grand_total?: string;
        label?: string;
    };
    full_text?: string;
}

interface AnalysisTableProps {
    data: AnalysisData;
    description?: string;
    className?: string;
}

export default function AnalysisTable({ data, description, className }: AnalysisTableProps) {
    if (!data || !data.components || data.components.length === 0) {
        return (
            <div className="p-4 bg-[#18181b] rounded-lg border border-[#27272a] text-[#71717a] italic text-sm">
                Analiz detayı bulunamadı.
            </div>
        );
    }

    // Gruplandırma (Opsiyonel: Tipine göre grupla)
    const materials = data.components.filter(c => c.type === 'Malzeme');
    const labors = data.components.filter(c => c.type === 'İşçilik');
    const transport = data.components.filter(c => c.type === 'Nakliye');
    const machine = data.components.filter(c => c.type === 'Makine');
    const others = data.components.filter(c => !['Malzeme', 'İşçilik', 'Nakliye', 'Makine'].includes(c.type));

    const renderRows = (title: string, items: AnalysisComponent[]) => {
        if (items.length === 0) return null;
        return (
            <>
                <tr className="bg-[#09090b] border-y border-[#18181b]">
                    <td colSpan={6} className="px-4 py-2 text-[10px] font-bold text-blue-500 uppercase tracking-[0.2em]">{title}</td>
                </tr>
                {items.map((item, idx) => (
                    <tr key={`${title}-${idx}`} className="border-b border-[#18181b] hover:bg-[#18181b]/50 transition-colors group">
                        <td className="px-4 py-2.5 text-[11px] font-mono text-[#71717a] group-hover:text-[#a1a1aa] transition-colors">{item.code}</td>
                        <td className="px-4 py-2.5 text-sm text-[#fafafa] font-medium">{item.name}</td>
                        <td className="px-4 py-2.5 text-xs text-center text-[#71717a] font-medium">{item.unit}</td>
                        <td className="px-4 py-2.5 text-sm text-right font-mono text-[#fafafa] tracking-tight">{item.quantity}</td>
                        <td className="px-4 py-2.5 text-sm text-right font-mono text-[#a1a1aa] tracking-tight">{item.price}</td>
                        <td className="px-4 py-2.5 text-sm text-right font-mono font-bold text-white tracking-tight">{item.total}</td>
                    </tr>
                ))}
            </>
        );
    };

    return (
        <div className={cn("overflow-hidden rounded-xl border border-[#27272a] bg-[#18181b] shadow-2xl", className)}>
            {/* Main Identification Header */}
            <div className="bg-black p-6 border-b border-[#27272a]">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1">
                        <div className="flex items-center gap-2">
                            <div className="px-2 py-0.5 bg-blue-600/10 text-blue-500 rounded font-mono text-[11px] font-bold border border-blue-500/20">
                                {data.poz_no}
                            </div>
                            <span className="text-[10px] font-bold text-[#71717a] uppercase tracking-widest">Analiz Cetveli</span>
                        </div>
                        <h3 className="text-xl font-bold text-[#fafafa] tracking-tight">{data.name}</h3>
                    </div>
                    <div className="flex flex-col items-center justify-center px-4 py-2 bg-[#18181b] border border-[#27272a] rounded-lg min-w-[100px]">
                        <span className="text-[10px] font-bold text-[#71717a] uppercase">Ölçü Birimi</span>
                        <span className="text-lg font-black text-white">{data.unit}</span>
                    </div>
                </div>
            </div>

            {/* Table Area */}
            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-[#18181b] text-[10px] font-bold uppercase text-[#71717a] tracking-[0.1em] border-b border-[#27272a]">
                        <tr>
                            <th className="px-4 py-3 w-32 border-r border-[#27272a]/50">Kod / Poz No</th>
                            <th className="px-4 py-3 border-r border-[#27272a]/50">Bileşen Tanımı</th>
                            <th className="px-4 py-3 w-20 text-center border-r border-[#27272a]/50">Birim</th>
                            <th className="px-4 py-3 w-24 text-right border-r border-[#27272a]/50">Miktar</th>
                            <th className="px-4 py-3 w-32 text-right border-r border-[#27272a]/50">Birim Fiyat</th>
                            <th className="px-4 py-3 w-32 text-right">Tutar (TL)</th>
                        </tr>
                    </thead>
                    <tbody className="bg-[#09090b]">
                        {renderRows("Malzemeler", materials)}
                        {renderRows("İşçilikler", labors)}
                        {renderRows("Makine & Ekipman", machine)}
                        {renderRows("Nakliyeler", transport)}
                        {renderRows("Diğer Giderler", others)}
                    </tbody>
                    <tfoot className="bg-black">
                        {data.totals.subtotal && (
                            <tr className="border-t border-[#27272a]">
                                <td colSpan={5} className="px-6 py-3 text-right text-[10px] font-bold text-[#71717a] uppercase tracking-widest">Malzeme + İşçilik + Nakliye</td>
                                <td className="px-6 py-3 text-right font-mono font-bold text-[#fafafa] text-base">{data.totals.subtotal}</td>
                            </tr>
                        )}
                        {data.totals.profit && (
                            <tr className="border-t border-[#27272a]">
                                <td colSpan={5} className="px-6 py-3 text-right text-[10px] font-bold text-[#71717a] uppercase tracking-widest">%25 Yüklenici Kârı ve Genel Giderler</td>
                                <td className="px-6 py-3 text-right font-mono font-bold text-[#fafafa] text-base">{data.totals.profit}</td>
                            </tr>
                        )}
                        {data.totals.grand_total && (
                            <tr className="bg-blue-600">
                                <td colSpan={5} className="px-6 py-4 text-right">
                                    <span className="text-xs font-black uppercase text-blue-100 tracking-[0.2em]">
                                        {data.totals.label || `1 ${data.unit} Birim Fiyatı`}
                                    </span>
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <span className="font-mono font-black text-2xl text-white tracking-tighter">
                                        {data.totals.grand_total}
                                    </span>
                                    <span className="ml-2 text-xs font-bold text-blue-100">TL</span>
                                </td>
                            </tr>
                        )}
                    </tfoot>
                </table>
            </div>

            {/* Technical Detail Footer */}
            {(description || data.full_text) && (
                <div className="p-8 bg-black border-t border-[#27272a]">
                    <div className="flex items-start gap-4">
                        <div className="w-1 h-32 bg-blue-600/50 rounded-full" />
                        <div className="flex-1 space-y-4">
                            <h4 className="text-xs font-bold text-[#71717a] uppercase tracking-[0.3em]">Yapım Şartları ve Teknik Tarif</h4>
                            <div className="text-[#a1a1aa] text-sm leading-relaxed whitespace-pre-wrap italic">
                                {description || data.full_text || "Bu birim fiyatın yapım şartları ve içerdiği bileşenler teknik şartnamelere uygundur."}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}


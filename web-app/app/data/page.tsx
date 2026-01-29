"use client";

import { useEffect, useState } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { DataTable } from '@/components/ui/data-table';
import api from '@/lib/api';
import { Search, Plus, Check } from 'lucide-react';
import { useCart } from '@/context/CartContext';
import { cn } from '@/lib/utils';

// Poz Tipi Tanımı
type Poz = {
    poz_no: string;
    description: string;
    unit: string;
    unit_price: string;
    institution: string;
    source_file: string;
}

export default function DataExplorerPage() {
    const [data, setData] = useState<Poz[]>([]);
    const [loading, setLoading] = useState(false);
    const [query, setQuery] = useState("");
    const { addItem, items: cartItems } = useCart();

    const columns: ColumnDef<Poz>[] = [
        {
            accessorKey: "poz_no",
            header: "Poz No",
            cell: ({ row }) => <span className="font-medium text-blue-600">{row.getValue("poz_no")}</span>
        },
        {
            accessorKey: "description",
            header: "Açıklama",
            cell: ({ row }) => <span className="text-slate-700 block max-w-lg truncate" title={row.getValue("description")}>{row.getValue("description")}</span>
        },
        {
            accessorKey: "unit",
            header: "Birim",
            cell: ({ row }) => <span className="text-slate-500 text-xs px-2 py-1 bg-slate-100 rounded">{row.getValue("unit")}</span>
        },
        {
            accessorKey: "unit_price",
            header: "Birim Fiyat",
            cell: ({ row }) => <span className="font-mono text-slate-900">{row.getValue("unit_price")} TL</span>
        },
        {
            accessorKey: "institution",
            header: "Kurum",
            cell: ({ row }) => <span className="text-xs text-slate-500">{row.getValue("institution")}</span>
        },
        {
            id: "actions",
            header: "İşlem",
            cell: ({ row }) => {
                const poz = row.original;
                const isAdded = cartItems.some(item => item.poz_no === poz.poz_no);
                return (
                    <button
                        onClick={() => addItem(poz)}
                        disabled={isAdded}
                        className={cn(
                            "p-2 rounded-lg transition-colors",
                            isAdded
                                ? "bg-green-100 text-green-600 cursor-default"
                                : "bg-blue-50 text-blue-600 hover:bg-blue-100"
                        )}
                        title={isAdded ? "Projede mevcut" : "Projeye ekle"}
                    >
                        {isAdded ? <Check className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
                    </button>
                )
            }
        }
    ]

    // Initial load? maybe not needed if we search
    useEffect(() => {
        handleSearch("10."); // Load some initial data or empty? Let's load ÇŞB items
    }, []);

    const handleSearch = async (q: string) => {
        setLoading(true);
        try {
            const res = await api.get(`/data/search?q=${q}`);
            setData(res.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-slate-800">Veri Gezgini</h1>
            </div>

            {/* Search Bar */}
            <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-5 w-5 text-slate-400" />
                </div>
                <input
                    type="text"
                    className="block w-full pl-10 pr-3 py-3 border border-slate-200 rounded-lg leading-5 bg-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm shadow-sm"
                    placeholder="Poz No, Açıklama veya Kurum ara..."
                    value={query}
                    onChange={(e) => {
                        setQuery(e.target.value);
                        // Debounce could be added here
                    }}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSearch(query);
                    }}
                />
                <button
                    onClick={() => handleSearch(query)}
                    className="absolute inset-y-1 right-1 px-4 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
                >
                    Ara
                </button>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-1">
                <DataTable columns={columns} data={data} loading={loading} />
            </div>
        </div>
    )
}

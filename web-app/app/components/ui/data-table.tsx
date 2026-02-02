"use client";

import {
    ColumnDef,
    flexRender,
    getCoreRowModel,
    getPaginationRowModel,
    useReactTable,
} from "@tanstack/react-table"
import { cn } from "@/lib/utils";
import { useState } from "react";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Box } from "lucide-react";

interface DataTableProps<TData, TValue> {
    columns: ColumnDef<TData, TValue>[]
    data: TData[]
    loading?: boolean
    onRowDoubleClick?: (data: TData) => void
}

export function DataTable<TData, TValue>({
    columns,
    data,
    loading,
    onRowDoubleClick,
}: DataTableProps<TData, TValue>) {
    const [pagination, setPagination] = useState({
        pageIndex: 0,
        pageSize: 10,
    });

    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        onPaginationChange: setPagination,
        state: {
            pagination,
        },
    })

    if (loading) {
        return (
            <div className="w-full h-64 flex flex-col items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <p className="mt-4 text-slate-500 text-sm">Veriler yükleniyor...</p>
            </div>
        )
    }

    return (
        <div className="w-full space-y-4">
            <div className="rounded-xl border border-[#27272a] overflow-hidden bg-[#18181b] shadow-2xl">
                <table className="w-full text-sm text-left">
                    <thead className="bg-black/40 border-b border-[#27272a] text-[#71717a]">
                        {table.getHeaderGroups().map((headerGroup) => (
                            <tr key={headerGroup.id}>
                                {headerGroup.headers.map((header) => {
                                    return (
                                        <th key={header.id} className="px-6 py-4 align-middle font-bold uppercase text-[10px] tracking-widest">
                                            {header.isPlaceholder
                                                ? null
                                                : flexRender(
                                                    header.column.columnDef.header,
                                                    header.getContext()
                                                )}
                                        </th>
                                    )
                                })}
                            </tr>
                        ))}
                    </thead>
                    <tbody className="divide-y divide-[#27272a]">
                        {table.getRowModel().rows?.length ? (
                            table.getRowModel().rows.map((row) => (
                                <tr
                                    key={row.id}
                                    data-state={row.getIsSelected() && "selected"}
                                    onDoubleClick={() => onRowDoubleClick?.(row.original)}
                                    className={cn(
                                        "hover:bg-[#27272a]/30 transition-all duration-200 group",
                                        onRowDoubleClick && "cursor-pointer select-none"
                                    )}
                                >
                                    {row.getVisibleCells().map((cell) => (
                                        <td key={cell.id} className="px-6 py-4 align-middle">
                                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                        </td>
                                    ))}
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan={columns.length} className="h-48 text-center text-[#52525b]">
                                    <div className="flex flex-col items-center justify-center gap-2">
                                        <Box className="w-8 h-8 opacity-20" />
                                        <span className="text-xs font-bold uppercase tracking-widest italic">Kayıt Bulunmuyor</span>
                                    </div>
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination - High Fidelity */}
            <div className="flex items-center justify-between px-2">
                <div className="text-[10px] font-bold text-[#52525b] uppercase tracking-widest">
                    Sayfa <span className="text-blue-500">{table.getState().pagination.pageIndex + 1}</span> / {table.getPageCount() || 1}
                </div>
                <div className="flex items-center gap-1.5">
                    <button
                        className="p-2 bg-[#18181b] border border-[#27272a] rounded-lg text-[#52525b] hover:text-[#fafafa] hover:bg-[#27272a] disabled:opacity-30 disabled:hover:bg-[#18181b] transition-all active:scale-90"
                        onClick={() => table.setPageIndex(0)}
                        disabled={!table.getCanPreviousPage()}
                    >
                        <ChevronsLeft className="h-4 w-4" />
                    </button>
                    <button
                        className="p-2 bg-[#18181b] border border-[#27272a] rounded-lg text-[#52525b] hover:text-[#fafafa] hover:bg-[#27272a] disabled:opacity-30 disabled:hover:bg-[#18181b] transition-all active:scale-90"
                        onClick={() => table.previousPage()}
                        disabled={!table.getCanPreviousPage()}
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </button>
                    <button
                        className="p-2 bg-[#18181b] border border-[#27272a] rounded-lg text-[#52525b] hover:text-[#fafafa] hover:bg-[#27272a] disabled:opacity-30 disabled:hover:bg-[#18181b] transition-all active:scale-90"
                        onClick={() => table.nextPage()}
                        disabled={!table.getCanNextPage()}
                    >
                        <ChevronRight className="h-4 w-4" />
                    </button>
                    <button
                        className="p-2 bg-[#18181b] border border-[#27272a] rounded-lg text-[#52525b] hover:text-[#fafafa] hover:bg-[#27272a] disabled:opacity-30 disabled:hover:bg-[#18181b] transition-all active:scale-90"
                        onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                        disabled={!table.getCanNextPage()}
                    >
                        <ChevronsRight className="h-4 w-4" />
                    </button>
                </div>
            </div>
        </div>
    )
}

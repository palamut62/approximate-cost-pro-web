"use client";

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { LayoutDashboard, FileText, Calculator, Sparkles, Settings, Menu, Archive, Box, Truck } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
    { name: 'Genel Bakış', href: '/', icon: LayoutDashboard },
    { name: 'Veri Gezgini', href: '/data', icon: FileText },
    { name: 'Maliyet Hesabı', href: '/cost', icon: Calculator },
    { name: 'Nakliye Hesabı', href: '/transport', icon: Truck },
    { name: 'AI Analizi', href: '/analysis', icon: Sparkles },
    { name: 'Kayıtlı Analizler', href: '/saved-analyses', icon: Archive },
];

import { useCart } from '@/context/CartContext';
import LogTerminal from './LogTerminal';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const { items: cartItems } = useCart();

    return (
        <div className="flex h-screen bg-[#09090b] text-[#fafafa] font-sans selection:bg-blue-500/30">
            {/* Sidebar */}
            <aside className={cn(
                "fixed inset-y-0 left-0 z-50 w-64 bg-black border-r border-[#18181b] transition-transform duration-300 ease-in-out md:relative md:translate-x-0 flex flex-col",
                isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
            )}>
                <div className="flex items-center px-6 h-16 mb-4">
                    <h1 className="text-xl font-bold text-[#fafafa] tracking-tight flex items-center gap-2">
                        <div className="w-6 h-6 bg-blue-600 rounded-md flex items-center justify-center">
                            <Box className="w-4 h-4 text-white" />
                        </div>
                        Approximate Cost
                    </h1>
                </div>

                <nav className="flex-1 px-3 space-y-1">
                    {NAV_ITEMS.map((item) => {
                        const isActive = pathname === item.href;
                        const isCost = item.href === '/cost';
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "flex items-center px-4 py-2.5 text-sm font-medium rounded-md transition-all justify-between group",
                                    isActive
                                        ? "bg-[#18181b] text-[#fafafa]"
                                        : "text-[#a1a1aa] hover:bg-[#09090b] hover:text-[#fafafa]"
                                )}
                            >
                                <div className="flex items-center">
                                    <item.icon className={cn(
                                        "w-4 h-4 mr-3 transition-colors",
                                        isActive ? "text-blue-500" : "text-[#71717a] group-hover:text-[#a1a1aa]"
                                    )} />
                                    {item.name}
                                </div>
                                {isCost && cartItems.length > 0 && (
                                    <span className="flex items-center justify-center min-w-[1.25rem] h-5 px-1 text-[10px] font-bold bg-blue-600 text-white rounded-full">
                                        {cartItems.length}
                                    </span>
                                )}
                            </Link>
                        );
                    })}
                </nav>

                <div className="p-3 mt-auto">
                    <Link
                        href="/settings"
                        className="flex items-center px-4 py-2.5 text-sm font-medium rounded-md text-[#a1a1aa] hover:bg-[#18181b] hover:text-[#fafafa] transition-all group"
                    >
                        <Settings className="w-4 h-4 mr-3 text-[#71717a] group-hover:text-[#a1a1aa]" />
                        Ayarlar
                    </Link>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Mobile Header */}
                <header className="md:hidden flex items-center justify-between p-4 border-b border-[#27272a] bg-[#0a0a0a]">
                    <h1 className="text-lg font-bold text-white">Approximate Cost</h1>
                    <button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)} className="text-white">
                        <Menu className="w-6 h-6" />
                    </button>
                </header>

                <main className="flex-1 overflow-auto p-4 md:p-8">
                    <div className="max-w-7xl mx-auto">
                        {children}
                    </div>
                </main>
            </div>
            <LogTerminal />
        </div>
    );
}

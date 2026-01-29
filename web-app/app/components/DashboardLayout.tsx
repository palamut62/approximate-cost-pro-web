"use client";

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { LayoutDashboard, FileText, Calculator, Sparkles, Settings, Menu, Archive } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
    { name: 'Genel Bakış', href: '/', icon: LayoutDashboard },
    { name: 'Veri Gezgini', href: '/data', icon: FileText },
    { name: 'Maliyet Hesabı', href: '/cost', icon: Calculator },
    { name: 'AI Analizi', href: '/analysis', icon: Sparkles },
    { name: 'Kayıtlı Analizler', href: '/saved-analyses', icon: Archive },
];

import { useCart } from '@/context/CartContext';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const { items: cartItems } = useCart();

    return (
        <div className="flex h-screen bg-white">
            {/* Sidebar */}
            <aside className={cn(
                "fixed inset-y-0 left-0 z-50 w-64 bg-slate-50 border-r border-slate-200 transition-transform duration-300 ease-in-out md:relative md:translate-x-0",
                isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
            )}>
                <div className="flex items-center justify-center h-16 border-b border-slate-200">
                    <h1 className="text-xl font-bold text-slate-800">Approximate Cost</h1>
                </div>

                <nav className="p-4 space-y-1">
                    {NAV_ITEMS.map((item) => {
                        const isActive = pathname === item.href;
                        const isCost = item.href === '/cost';
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors justify-between",
                                    isActive
                                        ? "bg-white text-slate-900 shadow-sm ring-1 ring-slate-200"
                                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                                )}
                            >
                                <div className="flex items-center">
                                    <item.icon className="w-5 h-5 mr-3" />
                                    {item.name}
                                </div>
                                {isCost && cartItems.length > 0 && (
                                    <span className="flex items-center justify-center w-5 h-5 text-[10px] font-bold bg-blue-600 text-white rounded-full">
                                        {cartItems.length}
                                    </span>
                                )}
                            </Link>
                        );
                    })}
                </nav>

                <div className="absolute bottom-4 left-4 right-4">
                    <Link
                        href="/settings"
                        className="flex items-center px-4 py-3 text-sm font-medium rounded-lg text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    >
                        <Settings className="w-5 h-5 mr-3" />
                        Ayarlar
                    </Link>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Mobile Header */}
                <header className="md:hidden flex items-center justify-between p-4 border-b border-slate-200 bg-white">
                    <h1 className="text-lg font-bold">Approximate Cost</h1>
                    <button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
                        <Menu className="w-6 h-6" />
                    </button>
                </header>

                <main className="flex-1 overflow-auto p-4 md:p-8">
                    <div className="max-w-7xl mx-auto">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}

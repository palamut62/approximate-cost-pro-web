"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Terminal, X, ChevronDown, ChevronUp, Trash2, StopCircle, PlayCircle, Hash, Maximize2, Minimize2, Activity, Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

interface LogEntry {
    timestamp: number;
    level: string;
    name: string;
    message: string;
    id: string;
}

export default function LogTerminal() {
    const [isOpen, setIsOpen] = useState(false);
    const [height, setHeight] = useState(300);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [autoScroll, setAutoScroll] = useState(true);
    const wsRef = useRef<WebSocket | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectAttemptRef = useRef(0);
    const isComponentMountedRef = useRef(true);
    const isResizing = useRef(false);

    // Stable connect function - doesn't change on re-renders
    const connect = useCallback(() => {
        if (!isComponentMountedRef.current) return;
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = 'localhost:8000';

        try {
            const ws = new WebSocket(`${protocol}//${host}/api/ws/logs`);

            ws.onopen = () => {
                if (!isComponentMountedRef.current) return;
                setIsConnected(true);
                reconnectAttemptRef.current = 0;
            };

            ws.onmessage = (event) => {
                if (!isComponentMountedRef.current) return;
                try {
                    const data = JSON.parse(event.data);
                    const newLog: LogEntry = {
                        ...data,
                        id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
                    };
                    setLogs(prev => [...prev.slice(-499), newLog]); // Keep last 500 logs
                } catch (e) {
                    const newLog: LogEntry = {
                        timestamp: Date.now(),
                        level: 'INFO',
                        name: 'raw',
                        message: event.data,
                        id: `log-${Date.now()}`
                    };
                    setLogs(prev => [...prev.slice(-499), newLog]);
                }
            };

            ws.onclose = () => {
                if (!isComponentMountedRef.current) return;
                setIsConnected(false);

                // Clear existing timeout
                if (reconnectTimeoutRef.current) {
                    clearTimeout(reconnectTimeoutRef.current);
                }

                // Fixed 5 second reconnection delay (prevents connection spam)
                reconnectAttemptRef.current++;
                reconnectTimeoutRef.current = setTimeout(() => {
                    if (isComponentMountedRef.current) {
                        connect();
                    }
                }, 5000);
            };

            ws.onerror = () => {
                if (!isComponentMountedRef.current) return;
                setIsConnected(false);
            };

            wsRef.current = ws;
        } catch (error) {
            console.error('[LogTerminal] WebSocket connection error:', error);
        }
    }, []);

    useEffect(() => {
        isComponentMountedRef.current = true;
        connect();

        return () => {
            isComponentMountedRef.current = false;
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [connect]);

    useEffect(() => {
        if (autoScroll && scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs, autoScroll, isOpen]);

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.ctrlKey && e.key === '`') {
                setIsOpen(prev => !prev);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    const handleMouseDown = (e: React.MouseEvent) => {
        isResizing.current = true;
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    };

    const handleMouseMove = (e: MouseEvent) => {
        if (!isResizing.current) return;
        const newHeight = window.innerHeight - e.clientY;
        if (newHeight > 100 && newHeight < window.innerHeight * 0.8) {
            setHeight(newHeight);
        }
    };

    const handleMouseUp = () => {
        isResizing.current = false;
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
    };

    const clearLogs = () => setLogs([]);

    const getLevelColor = (level: string) => {
        switch (level.toUpperCase()) {
            case 'ERROR': return 'text-red-400';
            case 'WARNING': return 'text-yellow-400';
            case 'DEBUG': return 'text-blue-400';
            default: return 'text-green-400';
        }
    };

    const lastLog = logs.length > 0 ? logs[logs.length - 1] : null;

    return (
        <div className="fixed bottom-0 left-0 right-0 z-[100] md:left-64 pointer-events-none">
            {/* Terminal Window */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: `${height}px` }}
                        exit={{ height: 0 }}
                        className="bg-black/95 border-t border-[#18181b] flex flex-col shadow-[0_-20px_50px_rgba(0,0,0,0.5)] backdrop-blur-xl pointer-events-auto"
                    >
                        {/* Resize Handle */}
                        <div
                            onMouseDown={handleMouseDown}
                            className="absolute top-0 left-0 right-0 h-1 cursor-ns-resize hover:bg-blue-500/50 transition-colors z-[110]"
                        />

                        {/* Top Bar (Integrated with Header) */}
                        <div className="flex items-center justify-between px-4 py-2 bg-[#09090b]/80 border-b border-[#18181b]">
                            <div className="flex items-center gap-6">
                                <button
                                    onClick={() => setIsOpen(false)}
                                    className="flex items-center gap-2 group transition-all"
                                >
                                    <Terminal className="w-4 h-4 text-blue-500 group-hover:scale-110 transition-transform" />
                                    <span className="text-xs font-bold text-[#fafafa] uppercase tracking-wider">SİSTEM KONSOLU</span>
                                </button>
                                <div className="hidden sm:flex gap-4 text-[10px] uppercase font-bold text-[#71717a]">
                                    <span className="cursor-default hover:text-[#fafafa] transition-colors border-b border-blue-500 pb-0.5 text-blue-500">Çıktı</span>
                                    <span className="cursor-not-allowed opacity-50">Hata Ayıklama</span>
                                    <span className="cursor-not-allowed opacity-50">Sorunlar (0)</span>
                                </div>
                            </div>

                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => setAutoScroll(!autoScroll)}
                                    title={autoScroll ? "Kaydırmayı Durdur" : "Kaydırmayı Başlat"}
                                    className={cn("p-1.5 rounded-md hover:bg-white/5 transition-all outline-none", autoScroll ? "text-blue-500 bg-blue-500/10" : "text-[#71717a]")}
                                >
                                    {autoScroll ? <StopCircle className="w-4 h-4" /> : <PlayCircle className="w-4 h-4" />}
                                </button>
                                <button
                                    onClick={clearLogs}
                                    title="Temizle"
                                    className="p-1.5 rounded-md hover:bg-white/5 text-[#71717a] hover:text-red-400 transition-all outline-none"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                                <div className="w-px h-4 bg-[#18181b] mx-1" />
                                <button
                                    onClick={() => setIsOpen(false)}
                                    className="p-1.5 rounded-md hover:bg-white/5 text-[#71717a] hover:text-red-400 transition-all outline-none"
                                >
                                    <ChevronDown className="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        {/* Logs Area */}
                        <div
                            ref={scrollRef}
                            className="flex-1 overflow-auto p-4 font-mono text-[12px] leading-relaxed custom-scrollbar selection:bg-blue-500/30"
                        >
                            {logs.length === 0 ? (
                                <div className="h-full flex flex-col items-center justify-center text-[#3f3f46] italic space-y-4">
                                    <div className="p-4 rounded-full bg-white/5">
                                        <Hash className="w-10 h-10 opacity-20" />
                                    </div>
                                    <p className="tracking-wide">Log akışı bekleniyor...</p>
                                </div>
                            ) : (
                                <div className="space-y-0.5">
                                    {logs.map((log) => (
                                        <div key={log.id} className="flex gap-3 group items-start hover:bg-white/5 px-2 py-0.5 rounded transition-colors -mx-2">
                                            <span className="text-[#3f3f46] shrink-0 tabular-nums text-[10px] self-center">
                                                {new Date(log.timestamp * 1000).toLocaleTimeString([], { hour12: false })}
                                            </span>
                                            <span className={cn("font-bold shrink-0 min-w-[70px] px-1.5 rounded text-[9px] text-center uppercase tracking-tighter self-center py-0.5 border border-current/20", getLevelColor(log.level))}>
                                                {log.level}
                                            </span>
                                            <span className="text-blue-400/60 font-medium italic shrink-0 text-[11px] self-center">
                                                {log.name}:
                                            </span>
                                            <span className="text-[#e4e4e7] break-all flex-1">
                                                {log.message}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Status Bar (Always visible at the bottom) */}
            <div
                onClick={() => !isOpen && setIsOpen(true)}
                className={cn(
                    "h-8 bg-[#18181b] border-t border-[#27272a] text-[#a1a1aa] flex items-center justify-between px-3 text-[11px] font-medium pointer-events-auto transition-all cursor-pointer select-none",
                    isOpen ? "bg-black/90 border-t-[#27272a]" : "hover:bg-[#27272a] hover:text-[#fafafa]"
                )}
            >
                <div className="flex items-center gap-4 overflow-hidden">
                    <div className="flex items-center gap-2 group shrink-0" onClick={(e) => { e.stopPropagation(); setIsOpen(!isOpen); }}>
                        <Terminal className={cn("w-3.5 h-3.5", !isOpen && "group-hover:scale-110 group-hover:text-blue-500 transition-all", isOpen && "text-blue-500")} />
                        <span className={cn("font-bold tracking-tight opacity-90 hidden sm:inline", isOpen && "text-[#fafafa]")}>TERMINAL</span>
                        {!isOpen && logs.length > 0 && (
                            <span className="flex items-center justify-center min-w-[14px] h-4 px-1 text-[9px] bg-[#27272a] text-blue-400 border border-blue-500/20 rounded-full font-bold ml-1">
                                {logs.length}
                            </span>
                        )}
                    </div>

                    {!isOpen && lastLog && (
                        <div className="flex items-center gap-2 opacity-60 group-hover:opacity-100 transition-opacity animate-in fade-in slide-in-from-left-2 truncate">
                            <span className="w-px h-3 bg-[#27272a] mx-1" />
                            <span className={cn("font-bold uppercase text-[9px]", getLevelColor(lastLog.level))}>
                                [{lastLog.level}]
                            </span>
                            <span className="truncate max-w-[400px] text-[10px] font-mono">
                                {lastLog.message}
                            </span>
                        </div>
                    )}
                </div>

                <div className="flex items-center gap-3 shrink-0">
                    <div className="flex items-center gap-1.5 px-1.5 opacity-80 group-hover:opacity-100 transition-opacity">
                        {isConnected ? <Wifi className="w-3.5 h-3.5 text-green-500" /> : <WifiOff className="w-3.5 h-3.5 text-red-500" />}
                        <span className="hidden sm:inline">{isConnected ? 'Mainframe Bağlı' : 'Bağlantı Yok'}</span>
                    </div>
                    <div className="sm:flex items-center gap-2 hidden px-1.5 border-l border-[#27272a] opacity-60">
                        <Activity className="w-3.5 h-3.5" />
                        <span>UTF-8</span>
                    </div>
                    <button
                        onClick={(e) => { e.stopPropagation(); setIsOpen(!isOpen); }}
                        className="p-1 hover:bg-white/5 rounded transition-colors"
                    >
                        {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4 text-[#71717a]" />}
                    </button>
                </div>
            </div>
        </div>
    );
}

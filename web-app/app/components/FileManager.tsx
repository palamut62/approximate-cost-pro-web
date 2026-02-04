import React, { useState, useEffect, useRef } from 'react';
import { Upload, RefreshCw, FileText, Trash2, CheckCircle, AlertCircle, HardDrive } from 'lucide-react';
import api from '@/lib/api';

interface FileItem {
    name: string;
    size: number;
    modified: number;
}

interface FileListResponse {
    analysis: FileItem[];
    prices: FileItem[];
}

export default function FileManager() {
    const [activeTab, setActiveTab] = useState<'analysis' | 'price'>('analysis');
    const [files, setFiles] = useState<FileListResponse>({ analysis: [], prices: [] });
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [vectorStatus, setVectorStatus] = useState<{ is_ready: boolean; count: number; message: string } | null>(null);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        fetchFiles();
        fetchVectorStatus();
    }, []);

    const fetchVectorStatus = async () => {
        try {
            const res = await api.get('/files/vector-status');
            setVectorStatus(res.data);
        } catch (err) {
            console.error("Vector status error:", err);
        }
    };

    const fetchFiles = async () => {
        try {
            const res = await api.get('/files/list');
            setFiles(res.data);
        } catch (err) {
            console.error(err);
            setMessage({ type: 'error', text: 'Dosya listesi alınamadı.' });
        } finally {
            setLoading(false);
        }
    };

    const handleSync = async () => {
        setSyncing(true);
        setMessage(null);
        try {
            await api.post('/files/sync');
            setMessage({ type: 'success', text: 'Veritabanı senkronizasyonu başlatıldı. İşlem arka planda devam edecek.' });
        } catch (err) {
            console.error(err);
            setMessage({ type: 'error', text: 'Senkronizasyon başlatılamadı.' });
        } finally {
            setSyncing(false);
            // Status'u güncelle (biraz bekleyip, çünkü işlem asenkron başlıyor)
            setTimeout(fetchVectorStatus, 2000);
        }
    };

    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;

        const formData = new FormData();
        Array.from(e.target.files).forEach(file => {
            formData.append('files', file);
        });

        setUploading(true);
        setMessage(null);

        try {
            await api.post(`/files/upload?type=${activeTab}`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            setMessage({ type: 'success', text: 'Dosyalar başarıyla yüklendi.' });
            fetchFiles(); // Refresh list
        } catch (err) {
            console.error(err);
            setMessage({ type: 'error', text: 'Dosya yükleme hatası.' });
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const formatSize = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const formatDate = (timestamp: number) => {
        return new Date(timestamp * 1000).toLocaleDateString('tr-TR', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const currentFiles = activeTab === 'analysis' ? files.analysis : files.prices;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Header / Actions */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#09090b] p-6 rounded-xl border border-[#27272a]">
                <div>
                    <h3 className="font-semibold text-[#fafafa] mb-1 flex items-center gap-2">
                        <HardDrive className="w-5 h-5 text-purple-500" />
                        Veri Yönetimi
                    </h3>
                    <p className="text-xs text-[#71717a]">
                        Sisteme yeni PDF analizleri veya birim fiyat listeleri yükleyin.
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={handleSync}
                        disabled={syncing}
                        className="flex items-center gap-2 px-4 py-2 text-xs font-medium bg-green-600/10 border border-green-600/20 text-green-500 rounded-lg hover:bg-green-600/20 transition disabled:opacity-50"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
                        {syncing ? 'İşleniyor...' : 'Veritabanını Güncelle'}
                    </button>
                    <button
                        onClick={handleUploadClick}
                        disabled={uploading}
                        className="flex items-center gap-2 px-4 py-2 text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white rounded-lg shadow transition disabled:opacity-50"
                    >
                        <Upload className="w-3.5 h-3.5" />
                        {uploading ? 'Yükleniyor...' : 'Yeni Dosya Yükle'}
                    </button>
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        className="hidden"
                        multiple
                        accept={activeTab === 'analysis' ? '.pdf' : '.pdf,.csv'}
                    />
                </div>
            </div>

            {/* Vector DB Status Card */}
            <div className="bg-[#09090b] rounded-xl border border-[#27272a] p-6 relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-purple-600/10 rounded-full blur-3xl -mr-16 -mt-16 transition-all group-hover:bg-purple-600/20"></div>

                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative z-10">
                    <div>
                        <h4 className="flex items-center gap-2 font-medium text-[#fafafa] mb-1">
                            <div className={`w-2.5 h-2.5 rounded-full ${vectorStatus?.is_ready ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]' : 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]'}`}></div>
                            AI Veritabanı Durumu (Vector DB)
                        </h4>
                        <p className="text-xs text-[#a1a1aa] max-w-2xl">
                            {vectorStatus?.message || 'Durum kontrol ediliyor...'}
                            <br />
                            <span className="opacity-60">
                                Bu veritabanı, AI'nın analiz yaparken benzer pozları ve teknik tarifleri bulmasını sağlar.
                                "Hazır" değilse analizler sadece genel model bilgisiyle yapılır (daha az hassas olabilir).
                            </span>
                        </p>
                    </div>

                    <button
                        onClick={handleSync}
                        disabled={syncing}
                        className={`flex items-center gap-2 px-5 py-3 text-xs font-bold rounded-lg transition-all shadow-lg ${syncing
                                ? 'bg-[#27272a] text-[#71717a] cursor-not-allowed'
                                : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white hover:shadow-purple-500/20'
                            }`}
                    >
                        <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                        {syncing ? 'İşleniyor (Arka Planda)...' : 'Verileri İşle ve İndeksle'}
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-[#27272a]">
                <button
                    onClick={() => setActiveTab('analysis')}
                    className={`px-4 py-2 text-sm font-medium transition-colors relative ${activeTab === 'analysis' ? 'text-blue-500' : 'text-[#a1a1aa] hover:text-[#fafafa]'}`}
                >
                    Analiz Dosyaları (PDF)
                    {activeTab === 'analysis' && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500" />}
                </button>
                <button
                    onClick={() => setActiveTab('price')}
                    className={`px-4 py-2 text-sm font-medium transition-colors relative ${activeTab === 'price' ? 'text-green-500' : 'text-[#a1a1aa] hover:text-[#fafafa]'}`}
                >
                    Birim Fiyat Dosyaları (CSV/PDF)
                    {activeTab === 'price' && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-green-500" />}
                </button>
            </div>

            {/* Notification */}
            {message && (
                <div className={`p-4 rounded-lg flex items-center gap-3 border text-sm ${message.type === 'success' ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-red-500/10 text-red-500 border-red-500/20'}`}>
                    {message.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                    {message.text}
                </div>
            )}

            {/* File List */}
            <div className="bg-[#09090b] rounded-xl border border-[#27272a] overflow-hidden">
                <div className="grid grid-cols-12 gap-4 p-4 border-b border-[#27272a] bg-[#27272a]/30 text-xs font-semibold text-[#a1a1aa] uppercase tracking-wider">
                    <div className="col-span-6">Dosya Adı</div>
                    <div className="col-span-3 text-right">Boyut</div>
                    <div className="col-span-3 text-right">Tarih</div>
                </div>

                <div className="max-h-[400px] overflow-y-auto">
                    {loading ? (
                        <div className="p-8 text-center text-[#71717a] text-sm flex items-center justify-center gap-2">
                            <RefreshCw className="w-4 h-4 animate-spin" />
                            Yükleniyor...
                        </div>
                    ) : currentFiles.length > 0 ? (
                        currentFiles.map((file, idx) => (
                            <div key={idx} className="grid grid-cols-12 gap-4 p-4 border-b border-[#27272a] last:border-0 hover:bg-[#27272a]/20 transition-colors group">
                                <div className="col-span-6 flex items-center gap-3 text-sm text-[#fafafa]">
                                    <FileText className="w-4 h-4 text-[#71717a] group-hover:text-blue-500 transition-colors" />
                                    <span className="truncate" title={file.name}>{file.name}</span>
                                </div>
                                <div className="col-span-3 text-right text-xs text-[#a1a1aa] font-mono">
                                    {formatSize(file.size)}
                                </div>
                                <div className="col-span-3 text-right text-xs text-[#71717a]">
                                    {formatDate(file.modified)}
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="p-12 text-center text-[#71717a] text-sm">
                            Bu klasörde henüz dosya yok.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

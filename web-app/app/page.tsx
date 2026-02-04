"use client";

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { LayoutDashboard, FileText, Calculator, Sparkles, Save, ArrowRight, Archive, CheckCircle2, AlertCircle, XCircle, Trash2, Settings } from 'lucide-react';
import Link from 'next/link';
import { useLLMUsage } from '@/context/LLMUsageContext';
import { useNotification } from '@/context/NotificationContext';

export default function Home() {
  const [stats, setStats] = useState({ totalItems: 0, totalFiles: 0, totalUsage: 0 });
  const [recentAnalyses, setRecentAnalyses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendStatus, setBackendStatus] = useState<{ status: string; poz_count: number } | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const { usageData, loading: usageLoading } = useLLMUsage();
  const { confirm, showNotification } = useNotification();

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsRes, analysesRes, healthRes] = await Promise.all([
          api.get('/data/status'),
          api.get('/projects'), // Assuming /projects now returns recent analyses
          api.get('/health').catch(() => ({ data: { status: 'error', poz_count: 0 } }))
        ]);
        setStats({
          totalItems: statsRes.data.item_count,
          totalFiles: statsRes.data.file_count,
          totalUsage: usageData.total_usage || 0 // Use LLM usage data for total usage
        });
        setRecentAnalyses(analysesRes.data);
        setBackendStatus(healthRes.data);
      } catch (e) {
        console.error("Fetch error:", e);
        setBackendStatus({ status: 'error', poz_count: 0 });
      } finally {
        setLoading(false);
      }
    }
    fetchData();

    // Poll backend status every 30 seconds
    const interval = setInterval(async () => {
      try {
        const healthRes = await api.get('/health');
        setBackendStatus(healthRes.data);
      } catch (e) {
        setBackendStatus({ status: 'error', poz_count: 0 });
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [usageData.total_usage]); // Re-run if usageData changes

  const handleDeleteProject = async (e: React.MouseEvent, projectId: number) => {
    e.preventDefault();
    e.stopPropagation();

    confirm({
      title: "Projeyi Sil",
      message: "Bu projeyi silmek istediğinize emin misiniz? Bu işlem geri alınamaz ve tüm analiz verileri silinecektir.",
      onConfirm: async () => {
        try {
          await api.delete(`/projects/${projectId}`);
          setRecentAnalyses(prev => prev.filter(p => p.id !== projectId));
          showNotification("Proje başarıyla silindi", "success");
        } catch (error) {
          console.error("Proje silme hatası:", error);
          showNotification("Proje silinirken bir hata oluştu", "error");
        }
      }
    });
  };

  const handleStartEdit = (e: React.MouseEvent, project: any) => {
    e.preventDefault();
    e.stopPropagation();
    setEditingId(project.id);
    setEditName(project.name || `Analiz #${project.id.toString().substring(0, 8)}`);
  };

  const handleSaveEdit = async (e: React.FormEvent | React.FocusEvent, id: number) => {
    e.preventDefault();
    if (!editName.trim()) return;

    try {
      await api.patch(`/projects/${id}/rename`, { name: editName });
      setRecentAnalyses(prev => prev.map(p => p.id === id ? { ...p, name: editName } : p));
      setEditingId(null);
      showNotification("Proje adı güncellendi", "success");
    } catch (error) {
      console.error("Rename error:", error);
      showNotification("İsim güncelleme hatası", "error");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, id: number) => {
    if (e.key === 'Enter') {
      handleSaveEdit(e, id);
    } else if (e.key === 'Escape') {
      setEditingId(null);
    }
  };

  // Placeholder for TransportCalculator component
  const TransportCalculator = () => (
    <div className="bg-[#09090b] border border-[#18181b] rounded-lg p-4 text-sm text-[#a1a1aa]">
      <p>Nakliye hesaplayıcı içeriği buraya gelecek.</p>
      <Link href="/transport" className="mt-3 inline-flex items-center text-blue-500 hover:text-blue-400 transition-colors">
        Hesaplayıcıya Git <ArrowRight className="w-4 h-4 ml-1" />
      </Link>
    </div>
  );

  return (
    <div className="font-inter antialiased min-h-screen bg-[#09090b] text-[#a1a1aa] p-6 lg:p-10">
      {/* Header / Welcome Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 py-4">
        <div className="space-y-1">
          <p className="text-blue-500 font-bold text-[10px] uppercase tracking-[0.2em]">Genel Bakış</p>
          <h1 className="text-3xl font-bold text-[#fafafa] tracking-tight">Hoş Geldiniz</h1>
          <p className="text-[#a1a1aa] text-sm">Projelerinizi ve maliyet analizlerinizi buradan yönetin.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="bg-[#18181b] border border-[#27272a] rounded-lg px-4 py-2 flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs font-medium text-[#a1a1aa]">Sistem Aktif</span>
          </div>
          <Link href="/settings" className="p-2 bg-[#18181b] border border-[#27272a] rounded-lg hover:bg-[#27272a] hover:text-white transition-colors text-[#a1a1aa]" title="Ayarlar">
            <Settings className="w-5 h-5" />
          </Link>
        </div>
      </div>

      {/* Dashboard Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-5 hover:border-blue-500/30 transition-all group">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-blue-600/10 rounded-lg group-hover:bg-blue-600/20 transition-colors">
              <Archive className="w-5 h-5 text-blue-500" />
            </div>
            <span className="text-[10px] font-bold text-blue-500 uppercase tracking-widest">Veritabanı</span>
          </div>
          <div className="space-y-1">
            <h3 className="text-3xl font-bold text-[#fafafa] tracking-tight">{loading ? <div className="h-8 w-24 bg-[#27272a] animate-pulse rounded"></div> : stats.totalItems.toLocaleString('tr-TR')}</h3>
            <p className="text-sm text-[#a1a1aa] font-medium">Toplam Poz Sayısı</p>
          </div>
        </div>

        <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-5 hover:border-blue-500/30 transition-all group">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-green-600/10 rounded-lg group-hover:bg-green-600/20 transition-colors">
              <FileText className="w-5 h-5 text-green-500" />
            </div>
            <span className="text-[10px] font-bold text-green-500 uppercase tracking-widest">Kaynaklar</span>
          </div>
          <div className="space-y-1">
            <h3 className="text-3xl font-bold text-[#fafafa] tracking-tight">{loading ? <div className="h-8 w-24 bg-[#27272a] animate-pulse rounded"></div> : stats.totalFiles.toLocaleString('tr-TR')}</h3>
            <p className="text-sm text-[#a1a1aa] font-medium">İşlenen PDF Dosyası</p>
          </div>
        </div>

        <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-5 hover:border-blue-500/30 transition-all group">
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-purple-600/10 rounded-lg group-hover:bg-purple-600/20 transition-colors">
              <Sparkles className="w-5 h-5 text-purple-500" />
            </div>
            <span className="text-[10px] font-bold text-purple-500 uppercase tracking-widest">AI Kullanımı</span>
          </div>
          <div className="space-y-3">
            <div>
              <h3 className={`text-3xl font-bold tracking-tight ${usageData.is_low_balance ? 'text-red-500' : 'text-[#fafafa]'}`}>{usageLoading ? <div className="h-8 w-24 bg-[#27272a] animate-pulse rounded"></div> : `$${(usageData.remaining ?? 0).toFixed(2)}`}</h3>
              <p className="text-sm text-[#a1a1aa] font-medium">Kalan Bakiye</p>
            </div>
            {usageData.is_low_balance && (
              <div className="mt-2 text-[10px] text-red-500 font-bold bg-red-500/10 px-2 py-1 rounded inline-block animate-pulse">
                BAKİYE AZALDI
              </div>
            )}
            <div className="flex items-center justify-between text-xs pt-2 border-t border-[#27272a]">
              <div className="text-[#71717a]">
                <span className="block text-[10px] uppercase font-bold">Harcanan</span>
                <span className="text-[#a1a1aa] font-medium">{usageLoading ? "..." : `$${(usageData.total_usage ?? 0).toFixed(2)}`}</span>
              </div>
              <div className="text-[#71717a] text-right">
                <span className="block text-[10px] uppercase font-bold">Limit</span>
                <span className="text-[#a1a1aa] font-medium">{usageLoading ? "..." : `$${(usageData.total_credits ?? 0).toFixed(2)}`}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Projects Section */}
        <div className="bg-[#09090b] border border-[#18181b] rounded-xl overflow-hidden">
          <div className="p-5 border-b border-[#18181b] flex justify-between items-center">
            <h2 className="font-bold text-[#fafafa] flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              Son Analizler
            </h2>
            <Link href="/data" className="text-xs text-[#a1a1aa] hover:text-[#fafafa] transition-colors">
              Tümünü Gör
            </Link>
          </div>
          <div className="divide-y divide-[#18181b]">
            {loading ? (
              [1, 2, 3].map(i => (
                <div key={i} className="p-4 flex items-center space-x-4">
                  <div className="h-10 w-10 bg-[#18181b] rounded-lg animate-pulse"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-[#18181b] rounded w-3/4 animate-pulse"></div>
                    <div className="h-3 bg-[#18181b] rounded w-1/2 animate-pulse"></div>
                  </div>
                </div>
              ))
            ) : recentAnalyses.length === 0 ? (
              <div className="p-10 text-center">
                <Archive className="w-10 h-10 text-[#27272a] mx-auto mb-3" />
                <p className="text-[#a1a1aa] text-sm italic">Henüz bir analiz kaydı bulunmuyor.</p>
                <Link href="/analysis" className="mt-4 inline-block text-blue-500 hover:text-blue-400 transition-colors text-sm font-medium">
                  Yeni Analiz Başlat
                </Link>
              </div>
            ) : (
              recentAnalyses.slice(0, 5).map((item, idx) => (
                <div key={idx} className="p-4 hover:bg-[#18181b] transition-colors group flex items-center justify-between border-b border-[#27272a] last:border-0 relative">
                  <Link href={`/cost?id=${item.id}`} className="absolute inset-0 z-0" aria-label="Projeye git" />

                  <div className="space-y-1 relative z-10 pointer-events-none">
                    {editingId === item.id ? (
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        onBlur={(e) => handleSaveEdit(e, item.id)}
                        onKeyDown={(e) => handleKeyDown(e, item.id)}
                        className="pointer-events-auto bg-[#27272a] border border-blue-500 rounded px-2 py-0.5 text-sm md:w-64 text-white outline-none"
                        autoFocus
                        onClick={(e) => e.preventDefault()}
                      />
                    ) : (
                      <h4
                        className="text-sm font-semibold text-[#fafafa] group-hover:text-blue-400 transition-colors pointer-events-auto cursor-text"
                        onDoubleClick={(e) => handleStartEdit(e, item)}
                        title="Değiştirmek için çift tıklayın"
                      >
                        {item.name || `Analiz #${item.id.toString().substring(0, 8)}`}
                      </h4>
                    )}
                    <div className="flex items-center gap-2 text-xs text-[#71717a]">
                      <span>{new Date(item.created_at).toLocaleDateString('tr-TR')}</span>
                      <span>•</span>
                      <span className="font-medium text-[#a1a1aa]">{item.unit_price ? `${item.unit_price.toLocaleString('tr-TR')} TL/${item.unit}` : 'Detay yok'}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 relative z-10">
                    <button
                      onClick={(e) => handleDeleteProject(e, item.id)}
                      className="p-2 text-[#71717a] hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors cursor-pointer"
                      title="Projeyi Sil"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <ArrowRight className="w-4 h-4 text-[#27272a] group-hover:text-[#a1a1aa] transition-colors pointer-events-none" />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Quick Tools */}
        <div className="space-y-6">
          <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
              <Calculator className="w-32 h-32 text-white" />
            </div>
            <h2 className="text-xl font-bold text-[#fafafa] mb-2">Nakliye Hesaplayıcı</h2>
            <p className="text-[#a1a1aa] text-sm mb-6 max-w-sm">Mesafe ve taşıma türüne göre hızlı nakliye birim fiyatı hesaplayın.</p>
            <TransportCalculator />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Link href="/analysis" className="bg-blue-600 hover:bg-blue-500 text-white rounded-xl p-5 transition-all text-center shadow-lg shadow-blue-900/20 active:scale-95">
              <Sparkles className="w-6 h-6 mx-auto mb-3" />
              <span className="font-bold text-sm">Yeni Analiz</span>
            </Link>
            <Link href="/cost" className="bg-[#27272a] hover:bg-[#3f3f46] text-[#fafafa] border border-[#3f3f46] rounded-xl p-5 transition-all text-center active:scale-95">
              <Calculator className="w-6 h-6 mx-auto mb-3" />
              <span className="font-bold text-sm">Maliyet Hesabı</span>
            </Link>
          </div>
        </div>
      </div>
    </div >
  );
}

// StatsCard is no longer used in the main Home component, but kept for completeness if needed elsewhere.
function StatsCard({ title, value, icon: Icon, loading, valueClass, subtitle }: any) {
  return (
    <div className="p-6 bg-[#18181b] rounded-xl shadow-sm border border-[#27272a] flex items-center space-x-4">
      <div className="p-3 bg-blue-900/20 text-blue-500 rounded-lg">
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <p className="text-sm font-medium text-[#a1a1aa]">{title}</p>
        {loading ? (
          <div className="h-8 w-24 bg-[#27272a] animate-pulse rounded mt-1"></div>
        ) : (
          <h3 className={`text-2xl font-bold ${valueClass || 'text-white'}`}>
            {typeof value === 'number' ? value.toLocaleString('tr-TR') : value}
          </h3>
        )}
        {subtitle && <p className="text-xs text-[#52525b] mt-1">{subtitle}</p>}
      </div>
    </div>
  )
}

function LLMUsageStatsCard() {
  const { usageData, loading: usageLoading } = useLLMUsage();

  if (usageLoading) {
    return (
      <StatsCard
        title="LLM Kalan Bakiye"
        value="--"
        icon={Sparkles}
        loading={true}
      />
    );
  }

  if (usageData.total_credits === null) {
    return (
      <StatsCard
        title="LLM Kalan Bakiye"
        value="--"
        icon={Sparkles}
        loading={false}
        subtitle="API anahtarı gerekli"
        valueClass="text-[#71717a]"
      />
    );
  }

  // Show remaining balance
  const valueClass = usageData.is_low_balance ? "text-red-500" : "text-green-500";
  const remaining = usageData.remaining ?? 0;

  return (
    <StatsCard
      title={`LLM Kalan Bakiye (${usageData.provider})`}
      value={`$${remaining.toFixed(2)}`}
      icon={Sparkles}
      loading={false}
      subtitle={`$${usageData.total_usage?.toFixed(2) ?? '--'} / $${usageData.total_credits?.toFixed(2) ?? '--'} kullanıldı`}
      valueClass={valueClass}
    />
  );
}

"use client";

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { FileText, Database, Activity, Clock, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export default function Home() {
  const [stats, setStats] = useState({ item_count: 0, file_count: 0 });
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsRes, projectsRes] = await Promise.all([
          api.get('/data/status'),
          api.get('/projects')
        ]);
        setStats(statsRes.data);
        setProjects(projectsRes.data);
      } catch (e) {
        console.error("Fetch error:", e);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Hoşgeldiniz 👋</h1>
        <p className="text-slate-500">Proje çalışmalarınızın özeti.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatsCard
          title="Toplam Poz"
          value={stats.item_count}
          icon={Database}
          loading={loading}
        />
        <StatsCard
          title="Yüklü Dosya"
          value={stats.file_count}
          icon={FileText}
          loading={loading}
        />
        <StatsCard
          title="Sistem Durumu"
          value="Aktif"
          icon={Activity}
          loading={false}
          valueClass="text-green-600"
        />
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-800">Son Projeler</h2>
          <Link href="/cost" className="text-sm font-medium text-blue-600 hover:underline">Tümünü Gör</Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading ? (
            [1, 2, 3].map(i => <div key={i} className="h-32 bg-slate-50 animate-pulse rounded-xl"></div>)
          ) : projects.length === 0 ? (
            <div className="col-span-full py-12 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
              <p className="text-slate-500">Henüz kayıtlı proje bulunmuyor.</p>
              <Link href="/cost" className="mt-2 inline-block text-blue-600 font-medium">Yeni Proje Oluştur</Link>
            </div>
          ) : (
            projects.slice(0, 6).map(project => (
              <Link
                key={project.id}
                href={`/cost?id=${project.id}`}
                className="p-5 bg-white rounded-xl border border-slate-200 hover:border-blue-400 hover:shadow-md transition-all group"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                    <FileText className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold text-slate-400 flex items-center">
                    <Clock className="w-3 h-3 mr-1" />
                    {project.updated_date}
                  </span>
                </div>
                <h3 className="font-bold text-slate-800 group-hover:text-blue-600 transition-colors truncate">{project.name}</h3>
                <p className="text-sm text-slate-500 mt-1 line-clamp-1">{project.description || "Açıklama yok"}</p>
                <div className="mt-4 flex items-center text-xs font-semibold text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">
                  Projeyi Aç <ArrowRight className="w-3 h-3 ml-1" />
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function StatsCard({ title, value, icon: Icon, loading, valueClass }: any) {
  return (
    <div className="p-6 bg-white rounded-xl shadow-sm border border-slate-100 flex items-center space-x-4">
      <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <p className="text-sm font-medium text-slate-500">{title}</p>
        {loading ? (
          <div className="h-8 w-24 bg-slate-100 animate-pulse rounded mt-1"></div>
        ) : (
          <h3 className={`text-2xl font-bold ${valueClass || 'text-slate-800'}`}>
            {typeof value === 'number' ? value.toLocaleString('tr-TR') : value}
          </h3>
        )}
      </div>
    </div>
  )
}

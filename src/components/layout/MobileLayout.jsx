import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Header } from '../common/Header';
import { BottomNav } from '../common/BottomNav';
import { ToastContainer } from '../common/ToastContainer';
import { useAuthStore } from '../../store/authStore';

const PUBLIC_PATHS = ['/login', '/auth'];

export function MobileLayout() {
  const { user } = useAuthStore();
  const location = useLocation();

  const isPublicPage = PUBLIC_PATHS.some(p => location.pathname.startsWith(p));

  return (
    <div className="min-h-screen bg-slate-200/60 flex justify-center selection:bg-brand-500 selection:text-white">
      {/* 360px min-width mobile shell (max-w-md on desktop) */}
      <div className="w-full max-w-md min-w-[360px] min-h-screen bg-slate-50 flex flex-col shadow-2xl relative border-x border-slate-200 overflow-x-hidden">
        <Header />

        <main className="flex-1 p-4 pb-24 overflow-y-auto overflow-x-hidden">
          <Outlet />
        </main>

        {user && !isPublicPage && <BottomNav />}
        <ToastContainer />
      </div>
    </div>
  );
}

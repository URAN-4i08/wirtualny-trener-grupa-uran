import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { clsx } from 'clsx';
import AppSidebar from './AppSidebar';
import AppFooter from './AppFooter';

export default function AppShell() {
  const location = useLocation();
  const isLive = location.pathname === '/live';
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  if (isLive) {
    return (
      <div className="flex min-h-screen flex-col bg-navy">
        <Outlet />
        <AppFooter compact />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-navy">
      <button
        type="button"
        className="fixed left-4 top-4 z-50 rounded-lg border border-white/10 bg-surface-container p-2 text-on-surface lg:hidden"
        onClick={() => setMobileOpen((v) => !v)}
        aria-label="Menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div
        className={clsx(
          'fixed left-0 top-0 z-40 h-full transition-transform duration-300 lg:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        )}
      >
        <AppSidebar collapsed={collapsed} onToggleCollapse={() => setCollapsed((v) => !v)} />
      </div>

      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-label="Zamknij menu"
        />
      )}

      <div
        className={clsx(
          'flex min-h-screen flex-col transition-all duration-300',
          collapsed ? 'lg:ml-sidebar-collapsed' : 'lg:ml-sidebar',
        )}
      >
        <main className="flex-1 px-4 py-6 pt-16 lg:px-8 lg:pt-8">
          <Outlet />
        </main>
        <AppFooter />
      </div>
    </div>
  );
}

import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Video, History as HistoryIcon, Dumbbell } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/live', label: 'Live Analysis', icon: Video },
  { path: '/history', label: 'History', icon: HistoryIcon },
];

export default function Sidebar() {
  return (
    <aside className="w-64 h-full glass-card border-r border-white/5 flex flex-col p-4">
      <div className="flex items-center gap-3 mb-8 px-2 mt-4">
        <div className="w-10 h-10 rounded-lg bg-primary-container/20 flex items-center justify-center neon-glow">
          <Dumbbell className="w-6 h-6 text-primary" />
        </div>
        <h1 className="text-xl font-bold font-h1 tracking-wider text-primary">Cyber Trener</h1>
      </div>

      <nav className="flex-1 flex flex-col gap-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300",
              "hover:bg-white/5",
              isActive ? "bg-primary/10 text-primary border border-primary/20 neon-glow" : "text-on-surface-variant"
            )}
          >
            <item.icon className="w-5 h-5" />
            <span className="font-medium font-body-lg">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto pt-4 px-2">
        <div className="bg-surface-variant/50 rounded-xl p-4 border border-white/5 text-sm">
          <p className="text-on-surface-variant mb-2">System Status</p>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div>
            <span className="text-green-400 font-medium">All systems operational</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

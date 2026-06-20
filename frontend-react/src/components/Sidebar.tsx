import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import {
  LayoutDashboard,
  FileText,
  Search,
  Briefcase,
  ClipboardList,
  Lightbulb,
  MessageSquare,
  Settings,
  LogOut,
  Sparkles,
  Moon,
  Sun,
} from 'lucide-react';

const mainLinks = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/resume', label: 'My Resume', icon: FileText },
  { to: '/discover', label: 'Discover', icon: Search },
  { to: '/jobs', label: 'My Jobs', icon: Briefcase },
  { to: '/applications', label: 'Applications', icon: ClipboardList },
];

const toolLinks = [
  { to: '/insights', label: 'Insights', icon: Lightbulb },
  { to: '/interview-prep', label: 'Interview Prep', icon: MessageSquare },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const isActive = (to: string) => {
    if (to === '/') return location.pathname === '/';
    return location.pathname.startsWith(to);
  };

  return (
    <aside className="w-60 min-h-screen bg-[#0E1628] border-r border-[#1E2D4A] flex flex-col fixed top-0 left-0 z-50">
      {/* Brand */}
      <div className="px-5 pt-6 pb-5 border-b border-[#1E2D4A]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-white">
              Career<span className="text-blue-400">AI</span>
            </h1>
            <p className="text-[10px] text-slate-500 font-medium tracking-widest uppercase">
              Personal Agent
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4">
        <div className="px-5 pb-2 text-[10px] font-medium text-slate-500 tracking-widest uppercase">
          Workspace
        </div>
        {mainLinks.map((link) => {
          const Icon = link.icon;
          const active = isActive(link.to);
          return (
            <NavLink
              key={link.to}
              to={link.to}
              className={
                active
                  ? 'flex items-center gap-3 px-5 py-2.5 text-sm font-medium text-blue-400 bg-blue-500/10 border-l-[3px] border-blue-500 transition-all duration-150'
                  : 'flex items-center gap-3 px-5 py-2.5 text-sm font-medium text-slate-400 border-l-[3px] border-transparent hover:bg-[#131B2E] hover:text-slate-200 transition-all duration-150'
              }
            >
              <Icon className={`w-[18px] h-[18px] ${active ? 'text-blue-400' : ''}`} strokeWidth={1.75} />
              {link.label}
            </NavLink>
          );
        })}

        <div className="px-5 pt-6 pb-2 text-[10px] font-medium text-slate-500 tracking-widest uppercase">
          Tools
        </div>
        {toolLinks.map((link) => {
          const Icon = link.icon;
          const active = isActive(link.to);
          return (
            <NavLink
              key={link.to}
              to={link.to}
              className={
                active
                  ? 'flex items-center gap-3 px-5 py-2.5 text-sm font-medium text-blue-400 bg-blue-500/10 border-l-[3px] border-blue-500 transition-all duration-150'
                  : 'flex items-center gap-3 px-5 py-2.5 text-sm font-medium text-slate-400 border-l-[3px] border-transparent hover:bg-[#131B2E] hover:text-slate-200 transition-all duration-150'
              }
            >
              <Icon className={`w-[18px] h-[18px] ${active ? 'text-blue-400' : ''}`} strokeWidth={1.75} />
              {link.label}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="mt-auto border-t border-[#1E2D4A] p-4 space-y-3">
        {/* Status */}
        <div className="flex items-center gap-2 px-1">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-slate-500">AI Agent active</span>
        </div>

        {/* User */}
        <div className="flex items-center gap-3 p-2 rounded-lg bg-[#131B2E]">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xs font-semibold text-white">
            {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || '?'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.full_name || 'User'}</p>
            <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={toggleTheme}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-[#131B2E] rounded-lg transition-all duration-200"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            <span className="text-xs">{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
          <button
            onClick={logout}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-[#131B2E] rounded-lg transition-all duration-200"
          >
            <LogOut className="w-4 h-4" />
            <span className="text-xs">Sign out</span>
          </button>
        </div>
      </div>
    </aside>
  );
}

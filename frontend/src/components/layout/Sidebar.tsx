import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  Search,
  FileCheck,
  History,
  FolderLock,
  Building2,
  ShieldAlert,
  FilePlus2,
  FolderKanban,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { user, isAdmin } = useAuth();

  const msmeNavItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/tenders', label: 'Find Tenders', icon: Search },
    { to: '/applications', label: 'Bid Pipeline', icon: FolderKanban },
    { to: '/compliance/analyze', label: 'Evaluate Tender', icon: FileCheck },
    { to: '/compliance/reports', label: 'Compliance Reports', icon: History },
    { to: '/vault', label: 'Document Vault', icon: FolderLock },
    { to: '/company', label: 'Company Profile', icon: Building2 },
  ];

  const adminNavItems = [
    { to: '/admin/tenders', label: 'Manage Tenders', icon: ShieldAlert },
    { to: '/admin/tenders/new', label: 'Create New Tender', icon: FilePlus2 },
  ];

  const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
      isActive
        ? 'bg-blue-50 text-blue-700 font-semibold shadow-xs'
        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80'
    }`;

  return (
    <aside className="w-64 shrink-0 bg-white border-r border-slate-200 min-h-[calc(100vh-4rem)] flex flex-col justify-between p-4">
      <div className="space-y-6">
        <div>
          <p className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            MSME Portal
          </p>
          <nav className="space-y-1">
            {msmeNavItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink key={item.to} to={item.to} className={navLinkClasses}>
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {isAdmin && (
          <div className="pt-4 border-t border-slate-100">
            <p className="px-3 text-xs font-semibold uppercase tracking-wider text-purple-600 mb-2 flex items-center justify-between">
              <span>Admin Console</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 font-bold">
                PRIVILEGED
              </span>
            </p>
            <nav className="space-y-1">
              {adminNavItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink key={item.to} to={item.to} className={navLinkClasses}>
                    <Icon className="w-4 h-4 shrink-0 text-purple-600" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>
          </div>
        )}
      </div>

      <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-500">
        <p className="font-semibold text-slate-700">Deterministic Engine</p>
        <p className="mt-0.5 text-[11px] text-slate-500">
          Evaluations strictly driven by Python rule engine. RAG & AI provide explanation and citations.
        </p>
      </div>
    </aside>
  );
};

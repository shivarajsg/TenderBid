import React from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  MinusCircle,
  ShieldCheck,
  ShieldAlert,
  AlertOctagon,
} from 'lucide-react';
import { FindingStatus, OverallComplianceStatus } from '../../types/compliance';

interface StatusBadgeProps {
  status: FindingStatus | OverallComplianceStatus | string;
  size?: 'sm' | 'md' | 'lg';
  isMandatory?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  isMandatory,
}) => {
  const normalized = (status || '').toUpperCase();

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5 font-medium',
    lg: 'text-sm px-3.5 py-1.5 gap-2 font-bold',
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  };

  let colorClasses = 'bg-slate-100 text-slate-700 border-slate-300';
  let label = status;
  let icon = <HelpCircle className={iconSizes[size]} />;

  switch (normalized) {
    // Finding Statuses
    case 'PASS':
      colorClasses = 'bg-emerald-50 text-emerald-700 border-emerald-300';
      label = 'PASS';
      icon = <CheckCircle2 className={`${iconSizes[size]} text-emerald-600`} />;
      break;
    case 'FAIL':
      colorClasses = 'bg-rose-50 text-rose-700 border-rose-300';
      label = isMandatory ? 'FAIL (Mandatory)' : 'FAIL';
      icon = <XCircle className={`${iconSizes[size]} text-rose-600`} />;
      break;
    case 'MISSING_EVIDENCE':
      colorClasses = 'bg-amber-50 text-amber-800 border-amber-300';
      label = isMandatory ? 'MISSING PROOF (Mandatory)' : 'MISSING PROOF';
      icon = <AlertTriangle className={`${iconSizes[size]} text-amber-600`} />;
      break;
    case 'NEEDS_REVIEW':
      colorClasses = 'bg-indigo-50 text-indigo-700 border-indigo-300';
      label = 'NEEDS REVIEW';
      icon = <HelpCircle className={`${iconSizes[size]} text-indigo-600`} />;
      break;
    case 'NOT_APPLICABLE':
      colorClasses = 'bg-slate-100 text-slate-600 border-slate-200';
      label = 'NOT APPLICABLE';
      icon = <MinusCircle className={`${iconSizes[size]} text-slate-500`} />;
      break;

    // Overall Statuses (Section 8.A)
    case 'ELIGIBLE':
      colorClasses = 'bg-emerald-100 text-emerald-900 border-emerald-400 font-bold';
      label = 'ELIGIBLE';
      icon = <ShieldCheck className={`${iconSizes[size]} text-emerald-700`} />;
      break;
    case 'NOT_ELIGIBLE':
      colorClasses = 'bg-rose-100 text-rose-900 border-rose-400 font-bold';
      label = 'NOT ELIGIBLE';
      icon = <ShieldAlert className={`${iconSizes[size]} text-rose-700`} />;
      break;
    case 'PARTIALLY_ELIGIBLE':
      colorClasses = 'bg-amber-100 text-amber-900 border-amber-400 font-bold';
      label = 'PARTIALLY ELIGIBLE';
      icon = <AlertTriangle className={`${iconSizes[size]} text-amber-700`} />;
      break;
    case 'ANALYSIS_BLOCKED_NO_DOCUMENTS':
    case 'ANALYSIS_BLOCKED':
    case 'BLOCKED_NO_DOCUMENTS':
      colorClasses = 'bg-rose-50 text-rose-900 border-rose-400 font-bold';
      label = 'ANALYSIS BLOCKED — SOURCE DOCUMENTS UNAVAILABLE';
      icon = <AlertOctagon className={`${iconSizes[size]} text-rose-700`} />;
      break;

    default:
      break;
  }

  return (
    <span
      data-testid={`status-badge-${normalized.toLowerCase()}`}
      className={`inline-flex items-center rounded-full border ${sizeClasses[size]} ${colorClasses}`}
    >
      {icon}
      <span>{label}</span>
    </span>
  );
};

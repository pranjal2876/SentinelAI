// Small formatting/color helpers shared across components.
import { format } from 'date-fns';
import type { Severity } from '@/types';

export const severityColor: Record<Severity, string> = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#f97316',
  critical: '#ef4444',
};

export const severityBadgeClass: Record<Severity, string> = {
  low: 'bg-threat-low/20 text-threat-low',
  medium: 'bg-threat-medium/20 text-threat-medium',
  high: 'bg-threat-high/20 text-threat-high',
  critical: 'bg-threat-critical/20 text-threat-critical',
};

export function fmtTime(epochSeconds: number): string {
  return format(new Date(epochSeconds * 1000), 'HH:mm:ss');
}

export function fmtDateTime(epochSeconds: number): string {
  return format(new Date(epochSeconds * 1000), 'MMM d, HH:mm:ss');
}

export function titleCase(s: string): string {
  return s
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

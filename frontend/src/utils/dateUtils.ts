/**
 * Authoritative date & time formatting utilities for TenderBid AI.
 * Normalizes Indian Government procurement timestamps (GeM / CPPP / OpenGov)
 * ensuring exact alignment with official government portal notices without
 * browser-dependent timezone drift.
 */

export function formatTenderDeadline(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return 'Not specified';
  const d = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  if (isNaN(d.getTime())) return 'Not specified';

  // Format as DD-MM-YYYY using UTC matching GeM's official portal date representation
  const day = String(d.getUTCDate()).padStart(2, '0');
  const month = String(d.getUTCMonth() + 1).padStart(2, '0');
  const year = d.getUTCFullYear();
  const time = d.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    timeZone: 'UTC',
  });

  return `${day}-${month}-${year} at ${time}`;
}

export function formatTenderDate(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return 'Not specified';
  const d = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  if (isNaN(d.getTime())) return 'Not specified';

  const day = String(d.getUTCDate()).padStart(2, '0');
  const month = String(d.getUTCMonth() + 1).padStart(2, '0');
  const year = d.getUTCFullYear();

  return `${day}-${month}-${year}`;
}

export function formatTenderTime(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return 'Not specified';
  const d = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  if (isNaN(d.getTime())) return 'Not specified';

  return d.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    timeZone: 'UTC',
  });
}

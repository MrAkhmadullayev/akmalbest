/**
 * Format number as UZS currency.
 */
export function formatCurrency(amount: number | string): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return '0 so\'m';
  return new Intl.NumberFormat('uz-UZ', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num) + ' so\'m';
}

/**
 * Format date for display.
 */
export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('uz-UZ', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

/**
 * Format datetime for display.
 */
export function formatDateTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString('uz-UZ', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Get stock status info.
 */
export function getStockStatus(status: string): { label: string; color: string; icon: string } {
  switch (status) {
    case 'SUFFICIENT':
      return { label: 'Yetarli', color: 'text-emerald-600 bg-emerald-50', icon: '🟢' };
    case 'WARNING':
      return { label: "O'rtacha", color: 'text-amber-600 bg-amber-50', icon: '🟡' };
    case 'LOW':
      return { label: 'Kam', color: 'text-red-600 bg-red-50', icon: '🔴' };
    case 'OUT_OF_STOCK':
      return { label: 'Tugagan', color: 'text-gray-600 bg-gray-100', icon: '⚫' };
    default:
      return { label: status, color: 'text-gray-500', icon: '⚪' };
  }
}

/**
 * Get debt status info.
 */
export function getDebtStatus(status: string): { label: string; color: string; icon: string } {
  switch (status) {
    case 'PAID':
      return { label: "To'langan", color: 'text-emerald-600 bg-emerald-50', icon: '🟢' };
    case 'ACTIVE':
      return { label: 'Faol', color: 'text-amber-600 bg-amber-50', icon: '🟡' };
    case 'PARTIALLY_PAID':
      return { label: "Qisman to'langan", color: 'text-orange-600 bg-orange-50', icon: '🟠' };
    case 'OVERDUE':
      return { label: "Muddati o'tgan", color: 'text-red-600 bg-red-50', icon: '🔴' };
    default:
      return { label: status, color: 'text-gray-500', icon: '⚪' };
  }
}

/**
 * Get payment method label.
 */
export function getPaymentMethodLabel(method: string): string {
  switch (method) {
    case 'CASH': return 'Naqd';
    case 'CARD': return 'Karta';
    case 'DEBT': return 'Nasiya';
    default: return method;
  }
}

/**
 * Generate a class name string from conditionals.
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

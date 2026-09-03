/**
 * Modul ruxsatlari — YAGONA manba (frontend tomonda).
 *
 * DIQQAT: bu ro'yxatlar backend'dagi `apps/accounts/models.py` ichidagi
 * `MODULES` va `DEFAULT_ROLE_PERMISSIONS` bilan BIR XIL bo'lishi shart.
 * Bu yerdagi filtr faqat menyuni yashiradi — haqiqiy tekshiruv backend'da
 * (`HasModulePermission`) bajariladi.
 */
import type { ModuleKey, ModulePermissions } from '@/types';

export const MODULE_LABELS: { key: ModuleKey; label: string }[] = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'pos', label: 'Sotuv (POS)' },
  { key: 'products', label: 'Mahsulotlar' },
  { key: 'categories', label: 'Kategoriyalar' },
  { key: 'customers', label: 'Mijozlar' },
  { key: 'debts', label: 'Qarzlar' },
  { key: 'expenses', label: 'Xarajatlar' },
  { key: 'reports', label: 'Hisobotlar' },
  { key: 'inventory', label: 'Ombor' },
  { key: 'suppliers', label: 'Yetkazib beruvchilar' },
  { key: 'notifications', label: 'Bildirishnomalar' },
  { key: 'settings', label: 'Sozlamalar' },
];

/**
 * Rol bo'yicha standart ruxsatlar.
 * SUPER_ADMIN bu yerda yo'q — unga hamma narsa ochiq.
 * `users` bo'limi ham yo'q — u faqat SUPER_ADMIN uchun (backend `IsSuperAdmin`).
 */
export const DEFAULT_ROLE_MODULES: Record<string, ModuleKey[]> = {
  ADMIN: [
    'dashboard', 'pos', 'products', 'categories', 'customers',
    'debts', 'expenses', 'reports', 'inventory', 'suppliers', 'notifications',
  ],
  CASHIER: [
    'dashboard', 'pos', 'products', 'categories', 'customers',
    'debts', 'inventory', 'notifications',
  ],
  WAREHOUSE_MANAGER: [
    'dashboard', 'products', 'categories', 'inventory', 'suppliers', 'notifications',
  ],
};

/** Rolning standart ruxsatlarini to'liq xarita ko'rinishida qaytaradi. */
export function defaultPermissionsForRole(role: string): ModulePermissions {
  const allowed = DEFAULT_ROLE_MODULES[role] ?? [];
  const result: ModulePermissions = {};
  for (const { key } of MODULE_LABELS) {
    result[key] = allowed.includes(key);
  }
  return result;
}

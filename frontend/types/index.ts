/* ==========================================
   TypeScript type definitions for the system
   ========================================== */

// ---- Auth & User ----

/** Ruxsat berish mumkin bo'lgan bo'limlar. Backend'dagi `MODULES` bilan bir xil. */
export type ModuleKey =
  | 'dashboard'
  | 'pos'
  | 'products'
  | 'categories'
  | 'customers'
  | 'debts'
  | 'expenses'
  | 'reports'
  | 'inventory'
  | 'suppliers'
  | 'notifications'
  | 'users'
  | 'settings';

export type ModulePermissions = Partial<Record<ModuleKey, boolean>>;

export interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string;
  role: 'SUPER_ADMIN' | 'ADMIN' | 'CASHIER' | 'WAREHOUSE_MANAGER';
  is_active: boolean;
  /** Faqat qo'lda kiritilgan bekor qilishlar. Eski API javoblarida bo'lmasligi mumkin. */
  permissions?: ModulePermissions;
  /** Rol standartlari + bekor qilishlar. Ruxsatni SHU yerdan tekshiring. */
  effective_permissions?: ModulePermissions;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

// ---- Products ----
export interface Category {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  product_count: number;
  created_at: string;
}

export interface Brand {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  product_count: number;
  created_at: string;
}

export interface Product {
  id: string;
  name: string;
  barcode: string;
  category: string;
  category_name: string;
  brand: string | null;
  brand_name: string;
  volume: string;
  unit: string;
  purchase_price: string;
  selling_price: string;
  profit_margin: string;
  current_stock: number;
  min_stock: number;
  warning_stock: number;
  max_stock: number;
  stock_status: 'SUFFICIENT' | 'WARNING' | 'LOW' | 'OUT_OF_STOCK';
  supplier: string | null;
  supplier_name?: string;
  expiration_date: string | null;
  image: string | null;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

// ---- POS Cart ----
export interface CartItem {
  product_id: string;
  name: string;
  barcode: string;
  price: number;
  quantity: number;
  discount: number;
  subtotal: number;
  stock: number;
}

// ---- Sales ----
export interface Sale {
  id: string;
  sale_number: string;
  cashier: string;
  cashier_name: string;
  customer: string | null;
  customer_name: string;
  customer_phone?: string;
  subtotal: string;
  discount: string;
  total: string;
  profit: string;
  /** Qaytarilgan qism. Sof tushum = total - returned_total.
   *  Eski javoblarda bo'lmasligi mumkin, shuning uchun ixtiyoriy. */
  returned_total?: string;
  returned_profit?: string;
  net_total?: string;
  net_profit?: string;
  payment_method: 'CASH' | 'CARD' | 'DEBT';
  status: 'COMPLETED' | 'CANCELLED' | 'RETURNED' | 'PARTIALLY_RETURNED';
  items_count?: number;
  items?: SaleItem[];
  payments?: Payment[];
  created_at: string;
  updated_at?: string;
}

export interface SaleItem {
  id: string;
  product: string;
  product_name_snapshot: string;
  barcode_snapshot: string;
  purchase_price_snapshot: string;
  selling_price_snapshot: string;
  quantity: number;
  returned_quantity: number;
  returnable_quantity?: number;
  returned_subtotal?: string;
  discount: string;
  subtotal: string;
  profit: string;
}

export interface Payment {
  id: string;
  sale: string;
  amount: string;
  payment_method: string;
  /** true bo'lsa — kassadan chiqqan qaytarim. */
  is_refund?: boolean;
  created_by: string;
  created_by_name: string;
  created_at: string;
}

// ---- Customers ----
export interface Customer {
  id: string;
  full_name: string;
  phone: string;
  address: string;
  notes: string;
  is_active: boolean;
  total_debt: string;
  total_purchases: number;
  total_paid?: string;
  created_at: string;
}

// ---- Debts ----
export interface Debt {
  id: string;
  customer: string;
  customer_name: string;
  customer_phone: string;
  sale: string | null;
  sale_number: string;
  original_amount: string;
  paid_amount: string;
  remaining_amount: string;
  debt_date: string;
  due_date: string;
  status: 'ACTIVE' | 'PARTIALLY_PAID' | 'PAID' | 'OVERDUE';
  notes: string;
  payments?: DebtPayment[];
  created_at: string;
}

export interface DebtPayment {
  id: string;
  debt: string;
  amount: string;
  payment_method: string;
  received_by: string;
  received_by_name: string;
  notes: string;
  created_at: string;
}

// ---- Suppliers ----
export interface Supplier {
  id: string;
  name: string;
  contact_person: string;
  phone: string;
  address: string;
  notes: string;
  is_active: boolean;
  total_purchases: number;
  created_at: string;
}

// ---- Inventory ----
export interface InventoryItem {
  id: string;
  product: string;
  product_name: string;
  product_barcode: string;
  quantity: number;
  stock_status: 'SUFFICIENT' | 'WARNING' | 'LOW' | 'OUT_OF_STOCK';
  min_stock?: number;
  warning_stock?: number;
  updated_at: string;
}

export interface InventoryTransaction {
  id: string;
  product: string;
  product_name: string;
  product_barcode: string;
  transaction_type: string;
  quantity: number;
  previous_quantity: number;
  new_quantity: number;
  reference_id: string;
  reference_type: string;
  created_by: string;
  created_by_name: string;
  notes: string;
  created_at: string;
}

// ---- Expenses ----
export interface ExpenseCategory {
  id: string;
  name: string;
}

export interface Expense {
  id: string;
  category: string;
  category_name: string;
  title: string;
  amount: string;
  description: string;
  created_by: string;
  created_by_name: string;
  expense_date: string;
  created_at: string;
}

// ---- Notifications ----
export interface Notification {
  id: string;
  user: string | null;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  created_at: string;
}

// ---- Dashboard ----
export interface DashboardData {
  today_sales_total: string;
  today_sales_count: number;
  // To'lov turi bo'yicha bugungi savdo (backend: apps/reports/views.py)
  today_cash_sales: string;
  today_card_sales: string;
  today_debt_sales: string;
  today_profit: string;
  today_expenses: string;
  total_debt: string;
  overdue_debt: string;
  overdue_count: number;
  low_stock_count: number;
  out_of_stock_count: number;
  total_products: number;
  // Ombordagi tovarlarning qarzga/naqdga olingan qiymati
  inventory_debt_value: string;
  inventory_cash_value: string;
  recent_sales: Array<{
    id: string;
    sale_number: string;
    cashier: string;
    customer: string;
    total: string;
    payment_method: string;
    status: string;
    created_at: string;
  }>;
  low_stock_products: Array<{
    id: string;
    name: string;
    barcode: string;
    current_stock: number;
    min_stock: number;
    stock_status: string;
  }>;
  overdue_debts: Array<{
    id: string;
    customer: string;
    phone: string;
    remaining_amount: string;
    due_date: string;
  }>;
}

// ---- Pagination ----
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ---- API Response ----
export interface ApiResponse<T = unknown> {
  success: boolean;
  message: string;
  data?: T;
  errors?: Record<string, string[]>;
}

// ---- Smena tafsilotlari ----
export type ShiftDetailKind =
  | 'sales' | 'profit' | 'cash' | 'card' | 'debt'
  | 'expenses' | 'debt_payments' | 'debt_payments_cash' | 'debt_payments_card' | 'returns';

export interface ShiftDetailRow {
  id: string;
  title: string;
  subtitle: string;
  person: string;
  amount: string;
  extra: string;
  method?: string;
  status?: string;
  created_at: string;
  link: string;
}

export interface ShiftDetailResponse {
  shift_number: string;
  kind: ShiftDetailKind;
  label: string;
  opened_at: string;
  closed_at: string;
  count: number;
  total: string;
  results: ShiftDetailRow[];
}

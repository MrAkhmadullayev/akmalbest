# Task List - Alkagol CRM + POS System

## Phase 1: Environment & Project Foundation
- [x] Django backend project structure & settings
- [x] Next.js frontend project initialization
- [x] Docker Compose (PostgreSQL, Redis, Celery, Nginx)
- [x] Environment variables & configuration

## Phase 2: Accounts, Authentication & RBAC
- [x] Custom User model & Role system
- [x] JWT authentication (SimpleJWT)
- [x] Permission classes
- [x] Frontend login flow & token management

## Phase 3: Core Catalog
- [x] Category, Brand, Product models
- [x] Product API endpoints & barcode lookup
- [x] Frontend product CRUD pages

## Phase 4: Stock & Inventory
- [x] Inventory & InventoryTransaction models
- [x] Supplier, Purchase, PurchaseItem models
- [x] Stock locking with select_for_update()

## Phase 5: POS & Checkout
- [x] POS frontend with barcode scanner
- [x] Cart state management
- [x] SaleService with atomic transactions
- [x] Receipt generation

## Phase 6: CRM, Debts & Background Tasks
- [x] Customer, Debt, DebtPayment models
- [x] Celery Beat scheduled tasks
- [x] Notification system

## Phase 7: Financials & Reports
- [x] Sales returns
- [x] Expenses & Profit tracking
- [x] Dashboard & Analytics

## Phase 8: Audit, Settings & Polish
- [x] AuditLog system
- [x] SystemSettings
- [x] Seed data command

## Phase 9: Testing & Documentation
- [x] Backend tests
- [x] API docs (Swagger)
- [x] README

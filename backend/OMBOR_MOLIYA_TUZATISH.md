# Ombor va moliya hisobini tuzatish

Bu hujjat ombor qoldig'i ("bor tovarni yo'q ko'rsatish") va moliya hisobidagi
xatolarni tuzatgan o'zgarishlarni hamda ularni ishlab turgan tizimga qo'llash
tartibini tavsiflaydi.

---

## 1. Asosiy sabab

Omborda **uchta alohida haqiqat manbasi** bor edi va ular kafolatlangan tarzda
sinxron emasdi:

| Manba | Joy |
|---|---|
| `Product.current_stock` | `apps/products/models.py` |
| `Inventory.quantity` | `apps/inventory/models.py` |
| `Σ InventoryBatch.current_quantity` | `apps/inventory/models.py` |

Bitta sahifada ikki xil manbadan o'qilardi — masalan ombor ro'yxatida
`quantity` `Inventory` dan, `stock_status` esa `Product.current_stock` dan
olinardi. Ular og'ganda **"Qoldiq: 12" va yonida "Tugagan"** deb ko'rinardi.

Bundan tashqari `0004` migratsiyasida `Inventory.quantity >= 0` cheklovi olib
tashlangan edi, `decrease_stock` esa hech qanday tekshiruv qilmasdi — qoldiq
manfiyga tushib ketaverardi.

## 2. Yangi qoida

**Yagona haqiqat manbasi — `Inventory.quantity`.**

* `Product.current_stock` — o'sha qiymatning keshi. Faqat `InventoryService`
  yozadi, bir xil tranzaksiya ichida. Serializer, admin panel va forma orqali
  o'zgartirib bo'lmaydi.
* `InventoryBatch` — FIFO tannarx qatlami. **Har qanday kirim partiya yaratadi,
  har qanday chiqim partiyadan yechadi**, shuning uchun
  `Σ batch.current_quantity == Inventory.quantity` har doim to'g'ri.
* Manfiy qoldiq DB darajasida to'siladi (`CheckConstraint`).

## 3. Tuzatilgan xatolar

### Ombor
1. Bitta jadvalda ikki manba aralashgani → yagona manbaga keltirildi
2. `decrease_stock` yetarlilikni tekshirmasdi → `InsufficientStockError`
3. Bir savdoda bir mahsulot ikki qatorda → qatorlar birlashtiriladi
4. Qaytarish partiya yaratmasdi → endi asl partiyaga qaytadi
5. `adjust_stock` partiyalarga tegmasdi → endi ikkalasi birga
6. Manfiy qoldiqdan DB himoyasi yo'q edi → cheklov qaytarildi
7. `Inventory` yozuvi yo'q mahsulot 500 xato berardi → signal + lazy yaratish
8. `seed_data` partiya yaratmasdi → servis orqali kiritiladi
9. Admin panel va tahrirlash formasi qoldiqni buzardi → yopildi

### Moliya
10. **Qaytarilgan savdo hisobotdan butunlay yo'qolardi** → sof qiymat
    (`total − returned_total`) joriy qilindi
11. Savdolar sahifasi summary'si bekor qilinganlarni qo'shardi → chiqarildi
12. `cancel_sale` atomik emasdi va nasiya qarzini yopmasdi → servisga ko'chirildi
13. Nasiya to'lovlari smena kassasiga kirmasdi → kassa `Payment` yozuvlaridan
14. Ombor qiymati ikki xil formula bilan hisoblanardi → `inventory/valuation.py`
15. Smena chegarasi turlicha edi → `reports/shifts.py` da yagona
16. `sale_number` poyga holati → qayta urinish bilan
17. Savdo chegirmasi qatorlarga taqsimlanmasdi → **foyda chegirma miqdoricha
    oshib ketardi**, endi taqsimlanadi
18. `paid_amount=0` "to'lanmagan" emas, "ko'rsatilmagan" deb qabul qilinardi
19. Nasiya savdo qaytarilganda mijoz to'lagan ortiqcha pul qaytmasdi
20. Bildirishnomalar har savdoda takrorlanib, cheksiz o'sardi → dedublikatsiya

## 4. Qo'llash tartibi

> **DIQQAT:** avval bazadan zaxira nusxa oling.

```bash
# 1. Zaxira
pg_dump -U alkagol_user alkagol_db > backup_$(date +%Y%m%d_%H%M).sql

# 2. Migratsiyalar (ma'lumot avtomatik tuzatiladi, keyin cheklov qo'yiladi)
python manage.py migrate

# 3. Holatni tekshirish — hech narsani o'zgartirmaydi
python manage.py stock_audit --only-broken

# 4. Agar farq qolgan bo'lsa, avval quruq ishga tushirish
python manage.py stock_reconcile

# 5. Rozi bo'lsangiz — yozish
python manage.py stock_reconcile --apply

# 6. Testlar
python manage.py test apps.sales apps.reports
```

`migrate` buyrug'i `inventory.0005_stock_integrity` migratsiyasida quyidagilarni
avtomatik bajaradi:
* yo'q `Inventory` qatorlarini yaratadi,
* manfiy qoldiqni nolga keltiradi (audit izi bilan),
* `Product.current_stock` keshini tenglashtiradi,
* partiyalar yig'indisini qoldiqqa moslaydi.

Faqat shundan keyin `CheckConstraint` qo'yiladi.

### `stock_reconcile` manbalari

```bash
# Inventory.quantity ga ishonadi (standart)
python manage.py stock_reconcile --apply

# InventoryTransaction tarixidan qayta hisoblaydi
python manage.py stock_reconcile --apply --source=ledger
```

## 5. Qoldiq qanday o'zgaradi

Endi qoldiqni o'zgartirishning **faqat uchta yo'li** bor, hammasi
`InventoryService` orqali o'tadi:

| Amal | Joy |
|---|---|
| Kirim qo'shish | Mahsulotlar → "Kirim qo'shish" (`POST /products/{id}/add_stock/`) |
| Xarid | Xaridlar → yangi xarid |
| Qo'lda tuzatish | Ombor → Tuzatish (`POST /inventory/adjust/`) |

Savdo, qaytarish va bekor qilish qoldiqni avtomatik o'zgartiradi.

## 6. API'dagi yangi maydonlar

**Savdo (`Sale`)**
* `returned_total`, `returned_profit` — qaytarilgan qism
* `net_total`, `net_profit` — sof qiymat

**To'lov (`Payment`)**
* `is_refund` — `true` bo'lsa kassadan chiqqan qaytarim

**Dashboard**
* `today_returns`, `today_refunds_cash`
* `today_debt_payments_cash`, `today_debt_payments_card`
* `expected_cash` — smena oxirida kassada bo'lishi kerak bo'lgan naqd
* `inventory_total_value`

**Smena hisoboti (`ShiftReport`)**
* `total_returns`, `total_debt_payments_cash`, `total_debt_payments_card`,
  `expected_cash`

## 7. Sana/vaqt qoidalari

* **Smena** — vaqt oralig'i: `opened_at < created_at <= closed_at` (chegara
  ekskilyuziv, shuning uchun bitta yozuv ikki smenaga tushmaydi).
* **Sana oralig'idagi hisobotlar** — savdolar `created_at` sanasi bo'yicha,
  xarajatlar esa `expense_date` (foydalanuvchi kiritgan biznes sanasi) bo'yicha.
* **Kassa** — har doim `Payment.created_at` bo'yicha, chunki kecha qilingan
  savdo bugun qaytarilsa, pul bugun kassadan chiqadi.

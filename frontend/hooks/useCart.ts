'use client';

import { useState, useCallback } from 'react';
import type { CartItem, Product } from '@/types';

/** Savatga qo'shish natijasi — UI shu asosda xato xabarini ko'rsatadi. */
export interface CartActionResult {
  success: boolean;
  error?: string;
}

export function useCart() {
  const [items, setItems] = useState<CartItem[]>([]);
  const [discount, setDiscount] = useState(0);

  /**
   * Mahsulotni savatga qo'shadi.
   *
   * Muhim: ombor tekshiruvi setItems updater'i ICHIDA emas, undan OLDIN
   * bajariladi. Aks holda funksiya har doim {success:true} qaytarardi va
   * kassir tovar tugaganini bilmay qolardi.
   *
   * `items` ni to'g'ridan-to'g'ri o'qiymiz (avval `useRef` orqali edi, lekin
   * render paytida `ref.current` ga yozish React qoidasini buzadi). Natijada
   * `addItem` har renderda yangi funksiya bo'ladi — POS sahifasida bu
   * muammo emas, chunki u memo qilingan chuqur daraxtga uzatilmaydi.
   */
  const addItem = useCallback((product: Product): CartActionResult => {
    const existing = items.find((item) => item.product_id === product.id);

    if (existing) {
      if (existing.quantity + 1 > existing.stock) {
        return {
          success: false,
          error: `"${product.name}" — omborda faqat ${existing.stock} dona qoldi`,
        };
      }

      setItems((prev) =>
        prev.map((item) =>
          item.product_id === product.id
            ? {
                ...item,
                quantity: item.quantity + 1,
                subtotal: (item.quantity + 1) * item.price - item.discount,
              }
            : item
        )
      );
      return { success: true };
    }

    if (product.current_stock <= 0) {
      return { success: false, error: `"${product.name}" omborda tugagan` };
    }

    const price = parseFloat(product.selling_price);
    setItems((prev) => [
      ...prev,
      {
        product_id: product.id,
        name: product.name,
        barcode: product.barcode,
        price,
        quantity: 1,
        discount: 0,
        subtotal: price,
        stock: product.current_stock,
      },
    ]);

    return { success: true };
  }, [items]);

  const removeItem = useCallback((productId: string) => {
    setItems((prev) => prev.filter((item) => item.product_id !== productId));
  }, []);

  /**
   * Miqdorni o'zgartiradi.
   *
   * Muhim: miqdor ombor qoldig'idan oshib ketmasligi shu yerda ham
   * cheklanadi. `<input max=...>` HTML atributi qo'lda yozilgan qiymatni
   * to'smaydi — kassir 999 deb yozib yuborishi mumkin edi.
   */
  const updateQuantity = useCallback((productId: string, quantity: number): CartActionResult => {
    if (!Number.isFinite(quantity) || quantity < 1) {
      return { success: false, error: 'Miqdor 1 dan kam bo\'lishi mumkin emas' };
    }

    const target = items.find((item) => item.product_id === productId);
    if (!target) return { success: false, error: 'Mahsulot savatda topilmadi' };

    if (quantity > target.stock) {
      setItems((prev) =>
        prev.map((item) =>
          item.product_id === productId
            ? { ...item, quantity: item.stock, subtotal: item.stock * item.price - item.discount }
            : item
        )
      );
      return {
        success: false,
        error: `"${target.name}" — omborda faqat ${target.stock} dona bor`,
      };
    }

    setItems((prev) =>
      prev.map((item) =>
        item.product_id === productId
          ? {
              ...item,
              quantity: quantity,
              subtotal: quantity * item.price - item.discount,
            }
          : item
      )
    );
    return { success: true };
  }, [items]);

  /** Qator chegirmasi. Backend manfiy summani rad etadi, shuning uchun bu
   *  yerda ham qator summasidan oshib ketmasligi cheklanadi. */
  const updateItemDiscount = useCallback((productId: string, discountAmount: number) => {
    setItems((prev) =>
      prev.map((item) => {
        if (item.product_id !== productId) return item;
        const lineGross = item.quantity * item.price;
        const safeDiscount = Math.min(Math.max(discountAmount || 0, 0), lineGross);
        return {
          ...item,
          discount: safeDiscount,
          subtotal: lineGross - safeDiscount,
        };
      })
    );
  }, []);

  const clearCart = useCallback(() => {
    setItems([]);
    setDiscount(0);
  }, []);

  const subtotal = items.reduce((sum, item) => sum + item.subtotal, 0);
  const grandTotal = Math.max(subtotal - discount, 0);
  const itemCount = items.reduce((sum, item) => sum + item.quantity, 0);

  return {
    items,
    discount,
    setDiscount,
    addItem,
    removeItem,
    updateQuantity,
    updateItemDiscount,
    clearCart,
    subtotal,
    grandTotal,
    itemCount,
  };
}

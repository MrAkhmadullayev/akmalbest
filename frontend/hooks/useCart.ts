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

  const updateQuantity = useCallback((productId: string, quantity: number) => {
    if (quantity < 1) return;
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
  }, []);

  const updateItemDiscount = useCallback((productId: string, discountAmount: number) => {
    setItems((prev) =>
      prev.map((item) =>
        item.product_id === productId
          ? {
              ...item,
              discount: discountAmount,
              subtotal: item.quantity * item.price - discountAmount,
            }
          : item
      )
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

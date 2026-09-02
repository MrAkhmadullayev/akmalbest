'use client';

import { useState, useEffect } from 'react';
import { Save, Moon, Sun, Monitor } from 'lucide-react';
import { useTheme } from 'next-themes';

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [storeName, setStoreName] = useState('Alkagol Do\'koni');
  const [storeAddress, setStoreAddress] = useState('Toshkent sh., Chilonzor tumani, Qatortol ko\'chasi');
  const [phone, setPhone] = useState('+998 90 123 45 67');
  const [minAge, setMinAge] = useState(20);
  const [requireAgeCheck, setRequireAgeCheck] = useState(true);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    alert('Sozlamalar muvaffaqiyatli saqlandi!');
  };

  if (!mounted) return null;

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tizim Sozlamalari</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Do&apos;kon rekvizitlari va qonuniy yosh cheklovlari sozlamalari</p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        <div className="card p-6 space-y-4">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-2">Do&apos;kon ma&apos;lumotlari</h2>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Do&apos;kon nomi</label>
            <input
              type="text"
              value={storeName}
              onChange={(e) => setStoreName(e.target.value)}
              className="input"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Manzil</label>
            <input
              type="text"
              value={storeAddress}
              onChange={(e) => setStoreAddress(e.target.value)}
              className="input"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Telefon</label>
            <input
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="input"
              required
            />
          </div>
        </div>

        {/* Theme Settings */}
        <div className="card p-6 space-y-4">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-2">Tashqi ko&apos;rinish (Mavzu)</h2>
          
          <div className="grid grid-cols-3 gap-3">
            <button
              type="button"
              onClick={() => setTheme('light')}
              className={`p-4 flex flex-col items-center justify-center gap-2 rounded-xl border-2 transition-all ${
                theme === 'light' ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400' : 'border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-gray-600'
              }`}
            >
              <Sun size={24} />
              <span className="text-sm font-medium">Kunduzgi</span>
            </button>
            <button
              type="button"
              onClick={() => setTheme('dark')}
              className={`p-4 flex flex-col items-center justify-center gap-2 rounded-xl border-2 transition-all ${
                theme === 'dark' ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400' : 'border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-gray-600'
              }`}
            >
              <Moon size={24} />
              <span className="text-sm font-medium">Tungi</span>
            </button>
            <button
              type="button"
              onClick={() => setTheme('system')}
              className={`p-4 flex flex-col items-center justify-center gap-2 rounded-xl border-2 transition-all ${
                theme === 'system' ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400' : 'border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-gray-600'
              }`}
            >
              <Monitor size={24} />
              <span className="text-sm font-medium">Tizim</span>
            </button>
          </div>
        </div>

        <div className="card p-6 space-y-4">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-2">Alcohol Savdo Compliance</h2>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="age-check"
              checked={requireAgeCheck}
              onChange={(e) => setRequireAgeCheck(e.target.checked)}
              className="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 dark:bg-gray-800 dark:border-gray-600"
            />
            <label htmlFor="age-check" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Yosh cheklovini tekshirishni talab qilish
            </label>
          </div>

          {requireAgeCheck && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Minimal qonuniy yosh</label>
              <input
                type="number"
                value={minAge}
                onChange={(e) => setMinAge(parseInt(e.target.value) || 20)}
                className="input"
                min={18}
                required
              />
            </div>
          )}
        </div>

        <div className="flex justify-end">
          <button type="submit" className="btn-primary">
            <Save size={18} />
            Sozlamalarni saqlash
          </button>
        </div>
      </form>
    </div>
  );
}

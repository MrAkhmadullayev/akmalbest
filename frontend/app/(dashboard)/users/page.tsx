'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersService } from '@/services/auth';
import { Plus, Edit, Trash2, Shield } from 'lucide-react';
import { useState } from 'react';

export default function UsersPage() {
  const queryClient = useQueryClient();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [role, setRole] = useState('CASHIER');
  const [phone, setPhone] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => usersService.getAll(),
  });

  const createMutation = useMutation({
    mutationFn: (payload: any) => usersService.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setUsername('');
      setPassword('');
      setFirstName('');
      setLastName('');
      setPhone('');
      setShowAddForm(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: any }) =>
      usersService.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setUsername('');
      setPassword('');
      setFirstName('');
      setLastName('');
      setPhone('');
      setShowAddForm(false);
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => usersService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // When creating, password is required. When editing, it's optional.
    if (!username || !firstName || !lastName || (!editingId && !password)) return;

    const payload: any = {
      username,
      first_name: firstName,
      last_name: lastName,
      role,
      phone,
    };

    if (password) {
      payload.password = password;
      payload.password_confirm = password;
    }

    if (editingId) {
      updateMutation.mutate({ id: editingId, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleEdit = (user: any) => {
    setEditingId(user.id);
    setUsername(user.username);
    setFirstName(user.first_name);
    setLastName(user.last_name);
    setRole(user.role);
    setPhone(user.phone || '');
    setPassword('');
    setShowAddForm(true);
  };

  const handleDelete = (id: string) => {
    if (confirm('Ushbu foydalanuvchini butunlay o\'chirmoqchimisiz?')) {
      deleteMutation.mutate(id);
    }
  };

  const users = data?.data?.results || [];

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Foydalanuvchilar (Xodimlar)</h1>
          <p className="text-gray-500 mt-1">Do&apos;kon xodimlari ro&apos;yxati va ruxsatlar boshqaruvi</p>
        </div>
        <button onClick={() => {
          setEditingId(null);
          setUsername('');
          setPassword('');
          setFirstName('');
          setLastName('');
          setPhone('');
          setRole('CASHIER');
          setShowAddForm(!showAddForm);
        }} className="btn-primary">
          <Plus size={18} />
          Yangi foydalanuvchi
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Users List */}
        <div className="card overflow-hidden lg:col-span-2">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">Yuklanmoqda...</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Ism Familiya</th>
                  <th>Login</th>
                  <th>Rol</th>
                  <th>Telefon</th>
                  <th>Holat</th>
                  <th className="text-right">O&apos;chirish</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u: any) => (
                  <tr key={u.id}>
                    <td className="font-semibold text-gray-900">{u.full_name}</td>
                    <td>{u.username}</td>
                    <td>
                      <span className="badge bg-indigo-50 text-indigo-700 font-semibold flex items-center gap-1 w-fit">
                        <Shield size={12} />
                        {u.role}
                      </span>
                    </td>
                    <td>{u.phone || '-'}</td>
                    <td>
                      <span className={`badge ${u.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                        {u.is_active ? 'Faol' : 'Nofaol'}
                      </span>
                    </td>
                    <td>
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleEdit(u)}
                          className="p-1 text-blue-400 hover:text-blue-600 cursor-pointer"
                        >
                          <Edit size={18} />
                        </button>
                        <button
                          onClick={() => handleDelete(u.id)}
                          className="p-1 text-red-400 hover:text-red-600 cursor-pointer"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Add User Form */}
        {showAddForm && (
          <div className="card p-6 space-y-6">
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                {editingId ? 'Xodimni tahrirlash' : 'Yangi xodim'}
              </h2>
              <p className="text-sm text-gray-500">Xodim ma&apos;lumotlarini to&apos;ldiring</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Ism</label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Familiya</label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Login (Username)</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Parol {editingId && <span className="text-gray-400 text-xs font-normal">(O'zgartirish uchun kiriting)</span>}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input"
                  required={!editingId}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Rol (Ruxsatlar)</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="input"
                  required
                >
                  <option value="CASHIER">Kassir</option>
                  <option value="ADMIN">Admin</option>
                  <option value="WAREHOUSE_MANAGER">Ombor mudiri</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Telefon</label>
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="input"
                  placeholder="+998901234567"
                />
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="btn-secondary flex-1"
                >
                  Bekor qilish
                </button>
                <button 
                  type="submit" 
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="btn-primary flex-1"
                >
                  {editingId ? 'Yangilash' : 'Saqlash'}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

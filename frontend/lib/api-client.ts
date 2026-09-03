import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - attach access token
apiClient.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ---------------------------------------------------------------------------
// Token refresh bilan bog'liq race condition'ni bartaraf etish.
//
// Muammo: sahifa yuklanganda bir nechta API so'rovi PARALLEL yuboriladi
// (dashboard, products, notifications va h.k.). Agar access token eskirgan
// bo'lsa, BARCHASI 401 oladi va HAR BIRI alohida /auth/refresh/ ga so'rov
// yuboradi. Backend'da ROTATE_REFRESH_TOKENS=True bo'lgani uchun birinchi
// refresh so'rovi eski tokenni bekor qiladi (blacklist). Natijada ikkinchi,
// uchinchi so'rovlar allaqachon bekor qilingan tokenni yuboradi → xato →
// login sahifasiga otib qoladi.
//
// Yechim: birinchi 401 kelganda refresh boshlanadi va BOSHQA 401'lar o'sha
// bitta refresh natijasini kutadi. Refresh tugagach barchasi yangi token
// bilan qayta yuboriladi.
// ---------------------------------------------------------------------------
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

function onRefreshFailed() {
  refreshSubscribers = [];
}

// Response interceptor - handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Faqat 401 xatosida refresh qilamiz (403 va boshqalar uchun emas)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Agar allaqachon refresh jarayoni ketayotgan bo'lsa, navbatga qo'shamiz
      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((newToken: string) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            resolve(apiClient(originalRequest));
          });
        });
      }

      isRefreshing = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        const response = await axios.post(`${API_URL}/auth/refresh/`, {
          refresh: refreshToken,
        });

        const { access, refresh } = response.data;
        localStorage.setItem('access_token', access);
        if (refresh) {
          localStorage.setItem('refresh_token', refresh);
        }

        isRefreshing = false;
        onRefreshed(access);

        originalRequest.headers.Authorization = `Bearer ${access}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        isRefreshing = false;
        onRefreshFailed();

        // Refresh failed - clear tokens and redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;

import { create } from 'zustand';
import api from '../utils/api';

export const useAuthStore = create((set, get) => ({
  user: null,
  isLoggedIn: false,
  isLoading: true,
  error: null,

  checkAuth: async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      set({ isLoggedIn: false, user: null, isLoading: false });
      return;
    }

    try {
      const response = await api.get('/auth/me');
      set({ isLoggedIn: true, user: response.data, isLoading: false });
    } catch (error) {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      set({ isLoggedIn: false, user: null, isLoading: false });
    }
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post('/auth/login', { email, password });
      const { access_token, refresh_token, user } = response.data;
      
      localStorage.setItem('token', access_token);
      localStorage.setItem('refreshToken', refresh_token);
      
      set({ isLoggedIn: true, user, isLoading: false });
      return { success: true };
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Login failed';
      set({ isLoading: false, error: errorMsg });
      return { success: false, error: errorMsg };
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    set({ isLoggedIn: false, user: null });
  },

  clearError: () => set({ error: null })
}));

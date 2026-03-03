import { create } from 'zustand';

export const useAuthStore = create((set, get) => ({
  user: null,
  isLoggedIn: false,
  isLoading: true,
  error: null,

  checkAuth: async () => {
    try {
      const isLoggedIn = await window.electronAPI.isLoggedIn();
      if (isLoggedIn) {
        const user = await window.electronAPI.getUser();
        set({ isLoggedIn: true, user, isLoading: false });
      } else {
        set({ isLoggedIn: false, user: null, isLoading: false });
      }
    } catch (error) {
      set({ isLoggedIn: false, user: null, isLoading: false, error: error.message });
    }
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const result = await window.electronAPI.login(email, password);
      if (result.success) {
        // Register device after login
        await window.electronAPI.registerDevice();
        set({ isLoggedIn: true, user: result.user, isLoading: false });
        return { success: true };
      } else {
        set({ isLoading: false, error: result.error });
        return { success: false, error: result.error };
      }
    } catch (error) {
      set({ isLoading: false, error: error.message });
      return { success: false, error: error.message };
    }
  },

  logout: async () => {
    try {
      await window.electronAPI.logout();
      set({ isLoggedIn: false, user: null });
    } catch (error) {
      console.error('Logout error:', error);
    }
  },

  clearError: () => set({ error: null })
}));

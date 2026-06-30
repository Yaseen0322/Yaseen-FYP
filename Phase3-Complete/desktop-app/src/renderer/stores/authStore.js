import { create } from 'zustand';

const EMPLOYEE_APP_ROLES = ['employee'];

export const useAuthStore = create((set, get) => ({
  user: null,
  isLoggedIn: false,
  isLoading: true,
  error: null,
  needsDeviceRegistration: false,

  checkAuth: async () => {
    try {
      const hasToken = await window.electronAPI.isLoggedIn();
      if (hasToken) {
        const [user, deviceId] = await Promise.all([
          window.electronAPI.getUser(),
          window.electronAPI.getSetting('deviceId')
        ]);

        if (!EMPLOYEE_APP_ROLES.includes(user?.role)) {
          await window.electronAPI.logout();
          set({
            isLoggedIn: false,
            user: null,
            isLoading: false,
            needsDeviceRegistration: false,
            error: 'Use an employee account for the desktop app. Managers should use the manager portal.'
          });
          return;
        }

        if (deviceId) {
          set({
            isLoggedIn: true,
            user,
            isLoading: false,
            error: null,
            needsDeviceRegistration: false
          });
        } else {
          set({
            isLoggedIn: false,
            user,
            isLoading: false,
            needsDeviceRegistration: true,
            error: 'Device setup is incomplete. Please retry device registration before continuing.'
          });
        }
      } else {
        set({ isLoggedIn: false, user: null, isLoading: false, needsDeviceRegistration: false });
      }
    } catch (error) {
      set({ isLoggedIn: false, user: null, isLoading: false, error: error.message, needsDeviceRegistration: false });
    }
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null, needsDeviceRegistration: false });
    try {
      const result = await window.electronAPI.login(email, password);
      if (result.success) {
        if (!EMPLOYEE_APP_ROLES.includes(result.user?.role)) {
          await window.electronAPI.logout();
          const errorMsg = 'Use an employee account for the desktop app. Managers should use the manager portal.';
          set({
            isLoggedIn: false,
            user: null,
            isLoading: false,
            error: errorMsg,
            needsDeviceRegistration: false
          });
          return { success: false, error: errorMsg };
        }

        const registration = await window.electronAPI.registerDevice();
        if (registration.success) {
          set({
            isLoggedIn: true,
            user: result.user,
            isLoading: false,
            error: null,
            needsDeviceRegistration: false
          });
          return { success: true };
        }

        const errorMsg = registration.error || 'Device registration failed. Retry device setup to continue.';
        set({
          isLoggedIn: false,
          user: result.user,
          isLoading: false,
          error: errorMsg,
          needsDeviceRegistration: true
        });
        return { success: false, error: errorMsg };
      } else {
        set({ isLoading: false, error: result.error, needsDeviceRegistration: false });
        return { success: false, error: result.error };
      }
    } catch (error) {
      set({ isLoading: false, error: error.message, needsDeviceRegistration: false });
      return { success: false, error: error.message };
    }
  },

  retryDeviceRegistration: async () => {
    set({ isLoading: true, error: null });
    try {
      const registration = await window.electronAPI.registerDevice();
      if (registration.success) {
        const user = await window.electronAPI.getUser();
        set({
          isLoggedIn: true,
          user,
          isLoading: false,
          error: null,
          needsDeviceRegistration: false
        });
        return { success: true };
      }

      const errorMsg = registration.error || 'Device registration failed. Please try again.';
      set({
        isLoggedIn: false,
        isLoading: false,
        error: errorMsg,
        needsDeviceRegistration: true
      });
      return { success: false, error: errorMsg };
    } catch (error) {
      set({
        isLoggedIn: false,
        isLoading: false,
        error: error.message,
        needsDeviceRegistration: true
      });
      return { success: false, error: error.message };
    }
  },

  logout: async () => {
    try {
      await window.electronAPI.logout();
      set({ isLoggedIn: false, user: null, needsDeviceRegistration: false, error: null });
    } catch (error) {
      console.error('Logout error:', error);
    }
  },

  clearError: () => set({ error: null })
}));

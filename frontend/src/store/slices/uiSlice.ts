/**
 * UI Slice - Estado de la interfaz de usuario
 */
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface SnackbarState {
  open: boolean;
  message: string;
  severity: 'success' | 'error' | 'warning' | 'info';
}

interface UIState {
  sidebarOpen: boolean;
  sidebarWidth: number;
  darkMode: boolean;
  snackbar: SnackbarState;
  isLoadingGlobal: boolean;
  currentModuleTitle: string;
  breadcrumbs: { label: string; path?: string }[];
}

const initialState: UIState = {
  sidebarOpen: true,
  sidebarWidth: 260,
  darkMode: localStorage.getItem('luminova_dark_mode') === 'true',
  snackbar: {
    open: false,
    message: '',
    severity: 'info',
  },
  isLoadingGlobal: false,
  currentModuleTitle: 'Dashboard',
  breadcrumbs: [],
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },

    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },

    toggleDarkMode: (state) => {
      state.darkMode = !state.darkMode;
      localStorage.setItem('luminova_dark_mode', String(state.darkMode));
    },

    setDarkMode: (state, action: PayloadAction<boolean>) => {
      state.darkMode = action.payload;
      localStorage.setItem('luminova_dark_mode', String(action.payload));
    },

    showSnackbar: (
      state,
      action: PayloadAction<{
        message: string;
        severity?: 'success' | 'error' | 'warning' | 'info';
      }>
    ) => {
      state.snackbar = {
        open: true,
        message: action.payload.message,
        severity: action.payload.severity || 'info',
      };
    },

    hideSnackbar: (state) => {
      state.snackbar.open = false;
    },

    setGlobalLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoadingGlobal = action.payload;
    },

    setModuleTitle: (state, action: PayloadAction<string>) => {
      state.currentModuleTitle = action.payload;
    },

    setBreadcrumbs: (
      state,
      action: PayloadAction<{ label: string; path?: string }[]>
    ) => {
      state.breadcrumbs = action.payload;
    },
  },
});

export const {
  toggleSidebar,
  setSidebarOpen,
  toggleDarkMode,
  setDarkMode,
  showSnackbar,
  hideSnackbar,
  setGlobalLoading,
  setModuleTitle,
  setBreadcrumbs,
} = uiSlice.actions;

export default uiSlice.reducer;

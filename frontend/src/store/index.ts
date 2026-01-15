/**
 * Redux Store Configuration
 * Configuración centralizada del store de Redux
 */
import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';
import { luminovaApi } from './api/luminovaApi';
import authReducer from './slices/authSlice';
import uiReducer from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    // API RTK Query
    [luminovaApi.reducerPath]: luminovaApi.reducer,
    // Slices de estado
    auth: authReducer,
    ui: uiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignorar las acciones de RTK Query que pueden contener datos no serializables
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }).concat(luminovaApi.middleware),
  devTools: import.meta.env.DEV,
});

// Configurar listeners para refetch automático
setupListeners(store.dispatch);

// Tipos para TypeScript
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

/**
 * Auth Slice - Estado de autenticación
 */
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { AuthState, User, AuthTokens } from '../../types';
import { luminovaApi } from '../api/luminovaApi';

// Intentar cargar tokens del localStorage
const loadTokensFromStorage = (): AuthTokens | null => {
  try {
    const tokensStr = localStorage.getItem('luminova_tokens');
    if (tokensStr) {
      return JSON.parse(tokensStr);
    }
  } catch (e) {
    console.error('Error loading tokens from storage:', e);
  }
  return null;
};

// Guardar tokens en localStorage
const saveTokensToStorage = (tokens: AuthTokens | null) => {
  try {
    if (tokens) {
      localStorage.setItem('luminova_tokens', JSON.stringify(tokens));
    } else {
      localStorage.removeItem('luminova_tokens');
    }
  } catch (e) {
    console.error('Error saving tokens to storage:', e);
  }
};

const initialState: AuthState = {
  user: null,
  tokens: loadTokensFromStorage(),
  isAuthenticated: false,
  loading: true,
  error: null,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (
      state,
      action: PayloadAction<{ user: User; tokens: AuthTokens }>
    ) => {
      state.user = action.payload.user;
      state.tokens = action.payload.tokens;
      state.isAuthenticated = true;
      state.loading = false;
      state.error = null;
      saveTokensToStorage(action.payload.tokens);
    },

    tokenRefreshed: (state, action: PayloadAction<{ access: string }>) => {
      if (state.tokens) {
        state.tokens.access = action.payload.access;
        saveTokensToStorage(state.tokens);
      }
    },

    logout: (state) => {
      state.user = null;
      state.tokens = null;
      state.isAuthenticated = false;
      state.loading = false;
      state.error = null;
      saveTokensToStorage(null);
    },

    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },

    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      state.loading = false;
    },
  },
  extraReducers: (builder) => {
    // Manejar login exitoso
    builder.addMatcher(
      luminovaApi.endpoints.login.matchFulfilled,
      (state, action) => {
        state.tokens = action.payload;
        state.isAuthenticated = true;
        state.loading = false;
        state.error = null;
        saveTokensToStorage(action.payload);
      }
    );

    // Manejar login fallido
    builder.addMatcher(
      luminovaApi.endpoints.login.matchRejected,
      (state, action) => {
        state.isAuthenticated = false;
        state.loading = false;
        state.error =
          (action.payload?.data as { detail?: string })?.detail ||
          'Error al iniciar sesión';
      }
    );

    // Manejar obtención de usuario actual
    builder.addMatcher(
      luminovaApi.endpoints.getCurrentUser.matchFulfilled,
      (state, action) => {
        state.user = action.payload;
        state.isAuthenticated = true;
        state.loading = false;
      }
    );

    builder.addMatcher(
      luminovaApi.endpoints.getCurrentUser.matchRejected,
      (state) => {
        state.user = null;
        state.isAuthenticated = false;
        state.loading = false;
        state.tokens = null;
        saveTokensToStorage(null);
      }
    );

    // Manejar logout
    builder.addMatcher(
      luminovaApi.endpoints.logout.matchFulfilled,
      (state) => {
        state.user = null;
        state.tokens = null;
        state.isAuthenticated = false;
        state.loading = false;
        saveTokensToStorage(null);
      }
    );
  },
});

export const { setCredentials, tokenRefreshed, logout, setLoading, setError } =
  authSlice.actions;

export default authSlice.reducer;

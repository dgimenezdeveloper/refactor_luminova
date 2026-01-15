/**
 * Custom Hooks para la aplicación
 */
import { useDispatch, useSelector, TypedUseSelectorHook } from 'react-redux';
import type { RootState, AppDispatch } from '../store';
import { useCallback } from 'react';
import { showSnackbar } from '../store/slices/uiSlice';

// Hooks tipados de Redux
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// Hook para selectores de auth
export const useAuth = () => {
  const { user, isAuthenticated, loading, error } = useAppSelector(
    (state) => state.auth
  );
  return { user, isAuthenticated, loading, error };
};

// Hook para el estado de UI
export const useUI = () => {
  return useAppSelector((state) => state.ui);
};

// Hook para mostrar notificaciones
export const useNotify = () => {
  const dispatch = useAppDispatch();

  const notifySuccess = useCallback(
    (message: string) => {
      dispatch(showSnackbar({ message, severity: 'success' }));
    },
    [dispatch]
  );

  const notifyError = useCallback(
    (message: string) => {
      dispatch(showSnackbar({ message, severity: 'error' }));
    },
    [dispatch]
  );

  const notifyWarning = useCallback(
    (message: string) => {
      dispatch(showSnackbar({ message, severity: 'warning' }));
    },
    [dispatch]
  );

  const notifyInfo = useCallback(
    (message: string) => {
      dispatch(showSnackbar({ message, severity: 'info' }));
    },
    [dispatch]
  );

  return { notifySuccess, notifyError, notifyWarning, notifyInfo };
};

// Hook para manejar estado de carga de operaciones
export const useLoadingState = <T>() => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<T | null>(null);

  const execute = useCallback(async (promise: Promise<T>) => {
    setLoading(true);
    setError(null);
    try {
      const result = await promise;
      setData(result);
      return result;
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Error desconocido';
      setError(message);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, data, execute, setData };
};

// Hook para debounce
export const useDebounce = <T>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

// Hook para el título del documento
export const useDocumentTitle = (title: string) => {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = `${title} | LUMINOVA ERP`;
    return () => {
      document.title = previousTitle;
    };
  }, [title]);
};

// Hook para detectar si es mobile
export const useIsMobile = (breakpoint = 768) => {
  const [isMobile, setIsMobile] = useState(window.innerWidth < breakpoint);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < breakpoint);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [breakpoint]);

  return isMobile;
};

// Importar hooks de React necesarios
import { useState, useEffect } from 'react';

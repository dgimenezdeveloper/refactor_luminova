/**
 * LUMINOVA ERP - Main Application Component
 */
import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { store } from './store';
import { lightTheme, darkTheme } from './theme';
import { useAppSelector, useAuth } from './hooks';
import { useGetCurrentUserQuery } from './store/api/luminovaApi';

// Layout
import { MainLayout } from './components/layout';

// Pages
import {
  LoginPage,
  DashboardPage,
  ProductosListPage,
  InsumosListPage,
  OrdenesVentaListPage,
} from './pages';

// Import Roboto font
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

/**
 * Protected Route wrapper
 */
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return null; // Or a loading spinner
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

/**
 * App Router with authentication check
 */
const AppRouter: React.FC = () => {
  const { tokens } = useAppSelector((state) => state.auth);
  
  // Check current user if we have tokens
  const { refetch } = useGetCurrentUserQuery(undefined, {
    skip: !tokens?.access,
  });
  
  useEffect(() => {
    if (tokens?.access) {
      refetch();
    }
  }, [tokens?.access, refetch]);

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected routes with MainLayout */}
      <Route element={<MainLayout />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        
        {/* Inventory routes */}
        <Route path="/inventario/productos" element={<ProductosListPage />} />
        <Route path="/inventario/insumos" element={<InsumosListPage />} />
        <Route path="/inventario/depositos" element={<ComingSoon module="Depósitos" />} />
        <Route path="/inventario/movimientos" element={<ComingSoon module="Movimientos" />} />
        
        {/* Sales routes */}
        <Route path="/ventas/ordenes" element={<OrdenesVentaListPage />} />
        <Route path="/ventas/clientes" element={<ComingSoon module="Clientes" />} />
        
        {/* Production routes */}
        <Route path="/produccion/ordenes" element={<ComingSoon module="Órdenes de Producción" />} />
        <Route path="/produccion/reportes" element={<ComingSoon module="Reportes de Producción" />} />
        
        {/* Purchasing routes */}
        <Route path="/compras/ordenes" element={<ComingSoon module="Órdenes de Compra" />} />
        <Route path="/compras/proveedores" element={<ComingSoon module="Proveedores" />} />
        
        {/* Settings */}
        <Route path="/configuracion" element={<ComingSoon module="Configuración" />} />
        <Route path="/perfil" element={<ComingSoon module="Mi Perfil" />} />
        <Route path="/notificaciones" element={<ComingSoon module="Notificaciones" />} />
      </Route>

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

/**
 * Coming Soon placeholder component
 */
const ComingSoon: React.FC<{ module: string }> = ({ module }) => {
  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column',
      alignItems: 'center', 
      justifyContent: 'center', 
      height: '60vh',
      textAlign: 'center'
    }}>
      <h1 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '1rem' }}>
        {module}
      </h1>
      <p style={{ color: '#666', fontSize: '1.1rem' }}>
        Esta sección está en desarrollo...
      </p>
    </div>
  );
};

/**
 * Theme wrapper that responds to dark mode setting
 */
const ThemedApp: React.FC = () => {
  const { darkMode } = useAppSelector((state) => state.ui);
  
  return (
    <ThemeProvider theme={darkMode ? darkTheme : lightTheme}>
      <CssBaseline />
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </ThemeProvider>
  );
};

/**
 * Main App component with Redux Provider
 */
const App: React.FC = () => {
  return (
    <Provider store={store}>
      <ThemedApp />
    </Provider>
  );
};

export default App;

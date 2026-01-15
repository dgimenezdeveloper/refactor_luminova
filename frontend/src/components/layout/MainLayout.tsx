/**
 * MainLayout Component - Layout principal de la aplicación
 */
import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import { Box, Toolbar, useTheme, useMediaQuery } from '@mui/material';
import Sidebar from './Sidebar';
import Header from './Header';
import GlobalSnackbar from '../common/GlobalSnackbar';
import { useAuth, useAppSelector } from '../../hooks';

const DRAWER_WIDTH = 260;

const MainLayout: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { isAuthenticated, loading } = useAuth();
  const { sidebarOpen } = useAppSelector((state) => state.ui);

  // Si está cargando, no mostrar nada (o un spinner)
  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
      >
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            border: `3px solid ${theme.palette.primary.main}`,
            borderTopColor: 'transparent',
            animation: 'spin 1s linear infinite',
            '@keyframes spin': {
              '0%': { transform: 'rotate(0deg)' },
              '100%': { transform: 'rotate(360deg)' },
            },
          }}
        />
      </Box>
    );
  }

  // Si no está autenticado, redirigir al login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <Sidebar variant={isMobile ? 'temporary' : 'permanent'} />

      {/* Contenido principal */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: {
            xs: '100%',
            md: sidebarOpen ? `calc(100% - ${DRAWER_WIDTH}px)` : '100%',
          },
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
          backgroundColor: theme.palette.background.default,
          minHeight: '100vh',
        }}
      >
        {/* Header */}
        <Header />

        {/* Espacio para el header */}
        <Toolbar />

        {/* Área de contenido */}
        <Box
          sx={{
            p: { xs: 2, sm: 3 },
            minHeight: 'calc(100vh - 64px)',
          }}
        >
          <Outlet />
        </Box>
      </Box>

      {/* Snackbar Global */}
      <GlobalSnackbar />
    </Box>
  );
};

export default MainLayout;

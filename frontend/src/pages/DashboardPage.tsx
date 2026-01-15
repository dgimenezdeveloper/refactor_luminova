/**
 * Dashboard Page - Página principal con métricas
 */
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  useTheme,
  Paper,
} from '@mui/material';
import {
  Inventory as InventoryIcon,
  ShoppingCart as ShoppingCartIcon,
  Factory as FactoryIcon,
  LocalShipping as ShippingIcon,
  Warning as WarningIcon,
  TrendingUp as TrendingUpIcon,
  Assignment as AssignmentIcon,
  Notifications as NotificationsIcon,
} from '@mui/icons-material';
import { useAppDispatch, useDocumentTitle } from '../hooks';
import { setModuleTitle } from '../store/slices/uiSlice';
import { PageHeader, StatCard, LoadingSpinner } from '../components/common';
import {
  useGetDashboardResumenQuery,
  useGetNotificacionesQuery,
  useGetOrdenesVentaQuery,
  useGetOrdenesProduccionQuery,
} from '../store/api/luminovaApi';

const DashboardPage: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  useDocumentTitle('Dashboard');

  useEffect(() => {
    dispatch(setModuleTitle('Dashboard'));
  }, [dispatch]);

  // Queries
  const { data: resumen, isLoading: loadingResumen } = useGetDashboardResumenQuery();
  const { data: notificaciones, isLoading: loadingNotif } = useGetNotificacionesQuery({
    leida: false,
  });
  const { data: ordenesVenta, isLoading: loadingOV } = useGetOrdenesVentaQuery({
    estado: 'PENDIENTE',
  });
  const { data: ordenesProduccion, isLoading: loadingOP } = useGetOrdenesProduccionQuery({});

  const isLoading = loadingResumen || loadingNotif || loadingOV || loadingOP;

  if (isLoading) {
    return <LoadingSpinner message="Cargando dashboard..." />;
  }

  // Datos simulados si no hay resumen
  const stats = resumen || {
    inventario: {
      total_productos: 0,
      total_insumos: 0,
      productos_stock_bajo: 0,
      insumos_stock_bajo: 0,
    },
    ventas: {
      total_ordenes: 0,
      ordenes_pendientes: 0,
      ordenes_completadas: 0,
      total_vendido: 0,
    },
    produccion: {
      ordenes_pendientes: 0,
      ordenes_en_proceso: 0,
      ordenes_completadas: 0,
      reportes_pendientes: 0,
    },
    compras: {
      ordenes_pendientes: 0,
      ordenes_en_transito: 0,
      ordenes_vencidas: 0,
    },
  };

  const getPriorityColor = (
    priority: string
  ): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (priority) {
      case 'critica':
        return 'error';
      case 'alta':
        return 'warning';
      case 'media':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <PageHeader
        title="Dashboard"
        subtitle="Resumen general del sistema LUMINOVA ERP"
      />

      {/* Estadísticas principales */}
      <Grid container spacing={3} mb={4}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Productos en Stock"
            value={stats.inventario.total_productos}
            subtitle={`${stats.inventario.productos_stock_bajo} con stock bajo`}
            icon={<InventoryIcon />}
            color="primary"
            onClick={() => navigate('/inventario/productos')}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Órdenes de Venta"
            value={stats.ventas.total_ordenes}
            subtitle={`${stats.ventas.ordenes_pendientes} pendientes`}
            icon={<ShoppingCartIcon />}
            color="success"
            onClick={() => navigate('/ventas/ordenes')}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="En Producción"
            value={stats.produccion.ordenes_en_proceso}
            subtitle={`${stats.produccion.ordenes_pendientes} pendientes`}
            icon={<FactoryIcon />}
            color="info"
            onClick={() => navigate('/produccion/ordenes')}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Compras en Tránsito"
            value={stats.compras.ordenes_en_transito}
            subtitle={`${stats.compras.ordenes_vencidas} vencidas`}
            icon={<ShippingIcon />}
            color={stats.compras.ordenes_vencidas > 0 ? 'warning' : 'secondary'}
            onClick={() => navigate('/compras/ordenes')}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Alertas y Notificaciones */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
              border: `1px solid ${theme.palette.divider}`,
              height: '100%',
            }}
          >
            <CardContent>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={2}
              >
                <Typography variant="h6" fontWeight={600}>
                  <NotificationsIcon
                    sx={{ mr: 1, verticalAlign: 'middle', fontSize: 24 }}
                  />
                  Notificaciones Recientes
                </Typography>
                <Chip
                  label={notificaciones?.count || 0}
                  size="small"
                  color="primary"
                />
              </Box>

              <List sx={{ p: 0 }}>
                {notificaciones?.results && notificaciones.results.length > 0 ? (
                  notificaciones.results.slice(0, 5).map((notif) => (
                    <ListItem
                      key={notif.id}
                      sx={{
                        px: 0,
                        borderBottom: `1px solid ${theme.palette.divider}`,
                        '&:last-child': { borderBottom: 'none' },
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 40 }}>
                        {notif.tipo === 'stock_bajo' ? (
                          <WarningIcon color="warning" />
                        ) : (
                          <AssignmentIcon color="info" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={notif.titulo}
                        secondary={notif.mensaje.substring(0, 50) + '...'}
                        primaryTypographyProps={{ fontWeight: 500 }}
                      />
                      <Chip
                        label={notif.prioridad}
                        size="small"
                        color={getPriorityColor(notif.prioridad)}
                      />
                    </ListItem>
                  ))
                ) : (
                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="No hay notificaciones nuevas"
                      secondary="Todo está en orden"
                    />
                  </ListItem>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Órdenes de Venta Pendientes */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card
            sx={{
              borderRadius: 3,
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
              border: `1px solid ${theme.palette.divider}`,
              height: '100%',
            }}
          >
            <CardContent>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={2}
              >
                <Typography variant="h6" fontWeight={600}>
                  <ShoppingCartIcon
                    sx={{ mr: 1, verticalAlign: 'middle', fontSize: 24 }}
                  />
                  Órdenes de Venta Pendientes
                </Typography>
                <Chip
                  label={ordenesVenta?.count || 0}
                  size="small"
                  color="success"
                />
              </Box>

              <List sx={{ p: 0 }}>
                {ordenesVenta?.results && ordenesVenta.results.length > 0 ? (
                  ordenesVenta.results.slice(0, 5).map((orden) => (
                    <ListItem
                      key={orden.id}
                      onClick={() => navigate(`/ventas/ordenes/${orden.id}`)}
                      sx={{
                        px: 0,
                        cursor: 'pointer',
                        borderBottom: `1px solid ${theme.palette.divider}`,
                        '&:last-child': { borderBottom: 'none' },
                        '&:hover': { backgroundColor: 'action.hover' },
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 40 }}>
                        <TrendingUpIcon color="success" />
                      </ListItemIcon>
                      <ListItemText
                        primary={orden.numero_ov}
                        secondary={orden.cliente_nombre || `Cliente #${orden.cliente}`}
                        primaryTypographyProps={{ fontWeight: 500 }}
                      />
                      <Typography variant="body2" fontWeight={600}>
                        ${orden.total_ov?.toLocaleString('es-AR') || '0'}
                      </Typography>
                    </ListItem>
                  ))
                ) : (
                  <ListItem sx={{ px: 0 }}>
                    <ListItemText
                      primary="No hay órdenes pendientes"
                      secondary="Todas las órdenes han sido procesadas"
                    />
                  </ListItem>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Resumen de Inventario */}
        <Grid size={{ xs: 12 }}>
          <Paper
            sx={{
              p: 3,
              borderRadius: 3,
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
              border: `1px solid ${theme.palette.divider}`,
            }}
          >
            <Typography variant="h6" fontWeight={600} mb={3}>
              <InventoryIcon sx={{ mr: 1, verticalAlign: 'middle', fontSize: 24 }} />
              Resumen de Inventario
            </Typography>

            <Grid container spacing={3}>
              <Grid size={{ xs: 6, md: 3 }}>
                <Box textAlign="center" p={2}>
                  <Typography variant="h3" fontWeight={700} color="primary">
                    {stats.inventario.total_productos}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Productos Terminados
                  </Typography>
                </Box>
              </Grid>
              <Grid size={{ xs: 6, md: 3 }}>
                <Box textAlign="center" p={2}>
                  <Typography variant="h3" fontWeight={700} color="secondary">
                    {stats.inventario.total_insumos}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Insumos
                  </Typography>
                </Box>
              </Grid>
              <Grid size={{ xs: 6, md: 3 }}>
                <Box textAlign="center" p={2}>
                  <Typography
                    variant="h3"
                    fontWeight={700}
                    color={
                      stats.inventario.productos_stock_bajo > 0
                        ? 'warning.main'
                        : 'success.main'
                    }
                  >
                    {stats.inventario.productos_stock_bajo}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Productos Stock Bajo
                  </Typography>
                </Box>
              </Grid>
              <Grid size={{ xs: 6, md: 3 }}>
                <Box textAlign="center" p={2}>
                  <Typography
                    variant="h3"
                    fontWeight={700}
                    color={
                      stats.inventario.insumos_stock_bajo > 0
                        ? 'warning.main'
                        : 'success.main'
                    }
                  >
                    {stats.inventario.insumos_stock_bajo}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Insumos Stock Bajo
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;

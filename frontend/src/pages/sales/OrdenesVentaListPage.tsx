/**
 * OrdenesVentaListPage - Lista de órdenes de venta
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Chip,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { useAppDispatch, useDocumentTitle } from '../../hooks';
import { setModuleTitle } from '../../store/slices/uiSlice';
import { PageHeader, DataTable, Column } from '../../components/common';
import { useGetOrdenesVentaQuery } from '../../store/api/luminovaApi';
import type { OrdenVenta, EstadoOrdenVenta } from '../../types';

const getEstadoColor = (
  estado: EstadoOrdenVenta
): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
  const colors: Record<EstadoOrdenVenta, 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'> = {
    PENDIENTE: 'warning',
    CONFIRMADA: 'info',
    INSUMOS_SOLICITADOS: 'secondary',
    PRODUCCION_INICIADA: 'primary',
    PRODUCCION_CON_PROBLEMAS: 'error',
    LISTA_ENTREGA: 'info',
    COMPLETADA: 'success',
    CANCELADA: 'default',
  };
  return colors[estado] || 'default';
};

const getEstadoLabel = (estado: EstadoOrdenVenta): string => {
  const labels: Record<EstadoOrdenVenta, string> = {
    PENDIENTE: 'Pendiente',
    CONFIRMADA: 'Confirmada',
    INSUMOS_SOLICITADOS: 'Insumos Solicitados',
    PRODUCCION_INICIADA: 'En Producción',
    PRODUCCION_CON_PROBLEMAS: 'Con Problemas',
    LISTA_ENTREGA: 'Lista para Entrega',
    COMPLETADA: 'Completada',
    CANCELADA: 'Cancelada',
  };
  return labels[estado] || estado;
};

const OrdenesVentaListPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  useDocumentTitle('Órdenes de Venta');

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  useEffect(() => {
    dispatch(setModuleTitle('Ventas - Órdenes'));
  }, [dispatch]);

  // Queries
  const { data, isLoading, refetch } = useGetOrdenesVentaQuery({
    page: page + 1,
  });

  const columns: Column<OrdenVenta>[] = [
    {
      id: 'numero_ov',
      label: 'Nº Orden',
      minWidth: 120,
      format: (value) => (
        <Box fontWeight={600}>{String(value)}</Box>
      ),
    },
    {
      id: 'cliente_nombre',
      label: 'Cliente',
      minWidth: 200,
      format: (value, row) => String(value || `Cliente #${row.cliente}`),
    },
    {
      id: 'fecha_creacion',
      label: 'Fecha',
      minWidth: 120,
      format: (value) => {
        const date = new Date(String(value));
        return date.toLocaleDateString('es-AR');
      },
    },
    {
      id: 'estado',
      label: 'Estado',
      minWidth: 150,
      align: 'center',
      format: (value) => (
        <Chip
          label={getEstadoLabel(value as EstadoOrdenVenta)}
          size="small"
          color={getEstadoColor(value as EstadoOrdenVenta)}
        />
      ),
    },
    {
      id: 'total_ov',
      label: 'Total',
      minWidth: 120,
      align: 'right',
      format: (value) => (
        <Box fontWeight={600}>
          ${Number(value).toLocaleString('es-AR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </Box>
      ),
    },
    {
      id: 'acciones',
      label: 'Acciones',
      minWidth: 120,
      align: 'center',
      format: (_, row) => (
        <Box display="flex" gap={0.5} justifyContent="center">
          <Button
            size="small"
            variant="outlined"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/ventas/ordenes/${row.id}`);
            }}
            sx={{ minWidth: 'auto', p: 0.5 }}
          >
            <ViewIcon fontSize="small" />
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="primary"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/ventas/ordenes/${row.id}/editar`);
            }}
            sx={{ minWidth: 'auto', p: 0.5 }}
            disabled={row.estado === 'COMPLETADA' || row.estado === 'CANCELADA'}
          >
            <EditIcon fontSize="small" />
          </Button>
        </Box>
      ),
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Órdenes de Venta"
        subtitle="Gestión de pedidos y órdenes de clientes"
        breadcrumbs={[
          { label: 'Inicio', path: '/dashboard' },
          { label: 'Ventas', path: '/ventas/ordenes' },
          { label: 'Órdenes' },
        ]}
        action={{
          label: 'Nueva Orden',
          onClick: () => navigate('/ventas/ordenes/nueva'),
          icon: <AddIcon />,
        }}
      />

      <DataTable
        columns={columns}
        data={data?.results || []}
        loading={isLoading}
        totalCount={data?.count || 0}
        page={page}
        rowsPerPage={rowsPerPage}
        onPageChange={setPage}
        onRowsPerPageChange={setRowsPerPage}
        onRefresh={refetch}
        onRowClick={(row) => navigate(`/ventas/ordenes/${row.id}`)}
        emptyMessage="No hay órdenes de venta registradas"
      />
    </Box>
  );
};

export default OrdenesVentaListPage;

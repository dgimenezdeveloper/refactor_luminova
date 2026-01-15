/**
 * ProductosListPage - Lista de productos terminados
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Chip,
  Avatar,
  useTheme,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { useAppDispatch, useNotify, useDocumentTitle } from '../../hooks';
import { setModuleTitle } from '../../store/slices/uiSlice';
import { PageHeader, DataTable, Column } from '../../components/common';
import {
  useGetProductosQuery,
  useDeleteProductoMutation,
} from '../../store/api/luminovaApi';
import type { Producto } from '../../types';

const ProductosListPage: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { notifySuccess, notifyError } = useNotify();
  useDocumentTitle('Productos');

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [search, setSearch] = useState('');

  useEffect(() => {
    dispatch(setModuleTitle('Inventario - Productos'));
  }, [dispatch]);

  // Queries
  const { data, isLoading, refetch } = useGetProductosQuery({
    page: page + 1,
    search: search || undefined,
  });

  const [deleteProducto, { isLoading: isDeleting }] = useDeleteProductoMutation();

  const handleDelete = async (producto: Producto) => {
    if (window.confirm(`¿Está seguro que desea eliminar "${producto.descripcion}"?`)) {
      try {
        await deleteProducto(producto.id).unwrap();
        notifySuccess('Producto eliminado correctamente');
      } catch (error) {
        notifyError('Error al eliminar el producto');
      }
    }
  };

  const getStockColor = (producto: Producto): 'success' | 'warning' | 'error' => {
    const porcentaje = producto.porcentaje_stock || 
      (producto.stock / (producto.stock_objetivo || 1)) * 100;
    if (porcentaje >= 70) return 'success';
    if (porcentaje >= 30) return 'warning';
    return 'error';
  };

  const columns: Column<Producto>[] = [
    {
      id: 'imagen',
      label: '',
      minWidth: 60,
      format: (_, row) => (
        <Avatar
          src={row.imagen || undefined}
          alt={row.descripcion}
          variant="rounded"
          sx={{ width: 40, height: 40 }}
        >
          {row.descripcion[0]}
        </Avatar>
      ),
    },
    {
      id: 'descripcion',
      label: 'Producto',
      minWidth: 200,
      format: (value) => (
        <Box fontWeight={500}>{String(value)}</Box>
      ),
    },
    {
      id: 'categoria_nombre',
      label: 'Categoría',
      minWidth: 150,
      format: (value) => (
        <Chip label={String(value || 'Sin categoría')} size="small" variant="outlined" />
      ),
    },
    {
      id: 'stock',
      label: 'Stock',
      minWidth: 100,
      align: 'center',
      format: (value, row) => (
        <Chip
          label={`${value} / ${row.stock_objetivo || '-'}`}
          size="small"
          color={getStockColor(row)}
        />
      ),
    },
    {
      id: 'precio_unitario',
      label: 'Precio',
      minWidth: 100,
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
      id: 'produccion_habilitada',
      label: 'Producción',
      minWidth: 100,
      align: 'center',
      format: (value) => (
        <Chip
          label={value ? 'Habilitada' : 'Deshabilitada'}
          size="small"
          color={value ? 'success' : 'default'}
          variant={value ? 'filled' : 'outlined'}
        />
      ),
    },
    {
      id: 'acciones',
      label: 'Acciones',
      minWidth: 150,
      align: 'center',
      format: (_, row) => (
        <Box display="flex" gap={0.5} justifyContent="center">
          <Button
            size="small"
            variant="outlined"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/inventario/productos/${row.id}`);
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
              navigate(`/inventario/productos/${row.id}/editar`);
            }}
            sx={{ minWidth: 'auto', p: 0.5 }}
          >
            <EditIcon fontSize="small" />
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="error"
            onClick={(e) => {
              e.stopPropagation();
              handleDelete(row);
            }}
            disabled={isDeleting}
            sx={{ minWidth: 'auto', p: 0.5 }}
          >
            <DeleteIcon fontSize="small" />
          </Button>
        </Box>
      ),
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Productos Terminados"
        subtitle="Gestión del catálogo de productos terminados"
        breadcrumbs={[
          { label: 'Inicio', path: '/dashboard' },
          { label: 'Inventario', path: '/inventario/productos' },
          { label: 'Productos' },
        ]}
        action={{
          label: 'Nuevo Producto',
          onClick: () => navigate('/inventario/productos/nuevo'),
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
        onSearch={setSearch}
        onRefresh={refetch}
        onRowClick={(row) => navigate(`/inventario/productos/${row.id}`)}
        searchPlaceholder="Buscar productos..."
        emptyMessage="No hay productos registrados"
      />
    </Box>
  );
};

export default ProductosListPage;

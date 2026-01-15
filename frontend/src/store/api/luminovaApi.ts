/**
 * API Service usando RTK Query
 * Centraliza todas las llamadas a la API de LUMINOVA
 */
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type { RootState } from '../index';
import type {
  PaginatedResponse,
  User,
  Producto,
  Insumo,
  Deposito,
  Cliente,
  Proveedor,
  OrdenVenta,
  OrdenProduccion,
  OrdenCompra,
  Notificacion,
  CategoriaProducto,
  CategoriaInsumo,
  DashboardResumen,
  AuthTokens,
} from '../../types';

// Base URL de la API Django
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Configuración del base query con autenticación JWT
const baseQuery = fetchBaseQuery({
  baseUrl: API_BASE_URL,
  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.tokens?.access;
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    headers.set('Content-Type', 'application/json');
    return headers;
  },
});

// Base query con refresh automático de token
const baseQueryWithReauth = async (
  args: Parameters<typeof baseQuery>[0],
  api: Parameters<typeof baseQuery>[1],
  extraOptions: Parameters<typeof baseQuery>[2]
) => {
  let result = await baseQuery(args, api, extraOptions);

  if (result.error && result.error.status === 401) {
    // Intentar refrescar el token
    const refreshToken = (api.getState() as RootState).auth.tokens?.refresh;
    if (refreshToken) {
      const refreshResult = await baseQuery(
        {
          url: '/auth/jwt/token/refresh/',
          method: 'POST',
          body: { refresh: refreshToken },
        },
        api,
        extraOptions
      );

      if (refreshResult.data) {
        // Guardar nuevo token
        api.dispatch({
          type: 'auth/tokenRefreshed',
          payload: refreshResult.data,
        });
        // Reintentar la petición original
        result = await baseQuery(args, api, extraOptions);
      } else {
        // Logout si falla el refresh
        api.dispatch({ type: 'auth/logout' });
      }
    }
  }

  return result;
};

// Definición del API con RTK Query
export const luminovaApi = createApi({
  reducerPath: 'luminovaApi',
  baseQuery: baseQueryWithReauth,
  tagTypes: [
    'User',
    'Producto',
    'Insumo',
    'Deposito',
    'Cliente',
    'Proveedor',
    'OrdenVenta',
    'OrdenProduccion',
    'OrdenCompra',
    'Notificacion',
    'CategoriaProducto',
    'CategoriaInsumo',
    'Dashboard',
  ],
  endpoints: (builder) => ({
    // ==================== AUTENTICACIÓN ====================
    login: builder.mutation<AuthTokens, { username: string; password: string }>({
      query: (credentials) => ({
        url: '/auth/jwt/token/',
        method: 'POST',
        body: credentials,
      }),
    }),

    logout: builder.mutation<void, { refresh: string }>({
      query: (body) => ({
        url: '/auth/jwt/token/blacklist/',
        method: 'POST',
        body,
      }),
    }),

    getCurrentUser: builder.query<User, void>({
      query: () => '/auth/user/',
      providesTags: ['User'],
    }),

    // ==================== DASHBOARD ====================
    getDashboardResumen: builder.query<DashboardResumen, void>({
      query: () => '/dashboard/resumen/',
      providesTags: ['Dashboard'],
    }),

    // ==================== PRODUCTOS ====================
    getProductos: builder.query<
      PaginatedResponse<Producto>,
      { page?: number; search?: string; categoria?: number }
    >({
      query: ({ page = 1, search, categoria }) => {
        const params = new URLSearchParams();
        params.append('page', String(page));
        if (search) params.append('search', search);
        if (categoria) params.append('categoria', String(categoria));
        return `/productos/?${params.toString()}`;
      },
      providesTags: (result) =>
        result
          ? [
              ...result.results.map(({ id }) => ({
                type: 'Producto' as const,
                id,
              })),
              { type: 'Producto', id: 'LIST' },
            ]
          : [{ type: 'Producto', id: 'LIST' }],
    }),

    getProducto: builder.query<Producto, number>({
      query: (id) => `/productos/${id}/`,
      providesTags: (_, __, id) => [{ type: 'Producto', id }],
    }),

    createProducto: builder.mutation<Producto, Partial<Producto>>({
      query: (body) => ({
        url: '/productos/',
        method: 'POST',
        body,
      }),
      invalidatesTags: [{ type: 'Producto', id: 'LIST' }, 'Dashboard'],
    }),

    updateProducto: builder.mutation<
      Producto,
      { id: number; body: Partial<Producto> }
    >({
      query: ({ id, body }) => ({
        url: `/productos/${id}/`,
        method: 'PATCH',
        body,
      }),
      invalidatesTags: (_, __, { id }) => [
        { type: 'Producto', id },
        { type: 'Producto', id: 'LIST' },
        'Dashboard',
      ],
    }),

    deleteProducto: builder.mutation<void, number>({
      query: (id) => ({
        url: `/productos/${id}/`,
        method: 'DELETE',
      }),
      invalidatesTags: [{ type: 'Producto', id: 'LIST' }, 'Dashboard'],
    }),

    // ==================== INSUMOS ====================
    getInsumos: builder.query<
      PaginatedResponse<Insumo>,
      { page?: number; search?: string; categoria?: number }
    >({
      query: ({ page = 1, search, categoria }) => {
        const params = new URLSearchParams();
        params.append('page', String(page));
        if (search) params.append('search', search);
        if (categoria) params.append('categoria', String(categoria));
        return `/insumos/?${params.toString()}`;
      },
      providesTags: (result) =>
        result
          ? [
              ...result.results.map(({ id }) => ({
                type: 'Insumo' as const,
                id,
              })),
              { type: 'Insumo', id: 'LIST' },
            ]
          : [{ type: 'Insumo', id: 'LIST' }],
    }),

    getInsumo: builder.query<Insumo, number>({
      query: (id) => `/insumos/${id}/`,
      providesTags: (_, __, id) => [{ type: 'Insumo', id }],
    }),

    createInsumo: builder.mutation<Insumo, Partial<Insumo>>({
      query: (body) => ({
        url: '/insumos/',
        method: 'POST',
        body,
      }),
      invalidatesTags: [{ type: 'Insumo', id: 'LIST' }, 'Dashboard'],
    }),

    updateInsumo: builder.mutation<Insumo, { id: number; body: Partial<Insumo> }>(
      {
        query: ({ id, body }) => ({
          url: `/insumos/${id}/`,
          method: 'PATCH',
          body,
        }),
        invalidatesTags: (_, __, { id }) => [
          { type: 'Insumo', id },
          { type: 'Insumo', id: 'LIST' },
          'Dashboard',
        ],
      }
    ),

    deleteInsumo: builder.mutation<void, number>({
      query: (id) => ({
        url: `/insumos/${id}/`,
        method: 'DELETE',
      }),
      invalidatesTags: [{ type: 'Insumo', id: 'LIST' }, 'Dashboard'],
    }),

    // ==================== DEPÓSITOS ====================
    getDepositos: builder.query<Deposito[], void>({
      query: () => '/depositos/',
      providesTags: ['Deposito'],
    }),

    // ==================== CATEGORÍAS ====================
    getCategoriasProducto: builder.query<CategoriaProducto[], void>({
      query: () => '/categorias-producto/',
      providesTags: ['CategoriaProducto'],
    }),

    getCategoriasInsumo: builder.query<CategoriaInsumo[], void>({
      query: () => '/categorias-insumo/',
      providesTags: ['CategoriaInsumo'],
    }),

    // ==================== CLIENTES ====================
    getClientes: builder.query<
      PaginatedResponse<Cliente>,
      { page?: number; search?: string }
    >({
      query: ({ page = 1, search }) => {
        const params = new URLSearchParams();
        params.append('page', String(page));
        if (search) params.append('search', search);
        return `/clientes/?${params.toString()}`;
      },
      providesTags: ['Cliente'],
    }),

    // ==================== PROVEEDORES ====================
    getProveedores: builder.query<
      PaginatedResponse<Proveedor>,
      { page?: number; search?: string }
    >({
      query: ({ page = 1, search }) => {
        const params = new URLSearchParams();
        params.append('page', String(page));
        if (search) params.append('search', search);
        return `/proveedores/?${params.toString()}`;
      },
      providesTags: ['Proveedor'],
    }),

    // ==================== ORDENES DE VENTA ====================
    getOrdenesVenta: builder.query<
      PaginatedResponse<OrdenVenta>,
      { page?: number; estado?: string }
    >({
      query: ({ page = 1, estado }) => {
        const params = new URLSearchParams();
        params.append('page', String(page));
        if (estado) params.append('estado', estado);
        return `/ordenes-venta/?${params.toString()}`;
      },
      providesTags: (result) =>
        result
          ? [
              ...result.results.map(({ id }) => ({
                type: 'OrdenVenta' as const,
                id,
              })),
              { type: 'OrdenVenta', id: 'LIST' },
            ]
          : [{ type: 'OrdenVenta', id: 'LIST' }],
    }),

    getOrdenVenta: builder.query<OrdenVenta, number>({
      query: (id) => `/ordenes-venta/${id}/`,
      providesTags: (_, __, id) => [{ type: 'OrdenVenta', id }],
    }),

    createOrdenVenta: builder.mutation<OrdenVenta, Partial<OrdenVenta>>({
      query: (body) => ({
        url: '/ordenes-venta/',
        method: 'POST',
        body,
      }),
      invalidatesTags: [{ type: 'OrdenVenta', id: 'LIST' }, 'Dashboard'],
    }),

    updateOrdenVenta: builder.mutation<
      OrdenVenta,
      { id: number; body: Partial<OrdenVenta> }
    >({
      query: ({ id, body }) => ({
        url: `/ordenes-venta/${id}/`,
        method: 'PATCH',
        body,
      }),
      invalidatesTags: (_, __, { id }) => [
        { type: 'OrdenVenta', id },
        { type: 'OrdenVenta', id: 'LIST' },
        'Dashboard',
      ],
    }),

    // ==================== ORDENES DE PRODUCCIÓN ====================
    getOrdenesProduccion: builder.query<
      PaginatedResponse<OrdenProduccion>,
      { page?: number; estado?: number }
    >({
      query: ({ page = 1, estado }) => {
        const params = new URLSearchParams();
        params.append('page', String(page));
        if (estado) params.append('estado_op', String(estado));
        return `/ordenes-produccion/?${params.toString()}`;
      },
      providesTags: (result) =>
        result
          ? [
              ...result.results.map(({ id }) => ({
                type: 'OrdenProduccion' as const,
                id,
              })),
              { type: 'OrdenProduccion', id: 'LIST' },
            ]
          : [{ type: 'OrdenProduccion', id: 'LIST' }],
    }),

    getOrdenProduccion: builder.query<OrdenProduccion, number>({
      query: (id) => `/ordenes-produccion/${id}/`,
      providesTags: (_, __, id) => [{ type: 'OrdenProduccion', id }],
    }),

    createOrdenProduccion: builder.mutation<
      OrdenProduccion,
      Partial<OrdenProduccion>
    >({
      query: (body) => ({
        url: '/ordenes-produccion/',
        method: 'POST',
        body,
      }),
      invalidatesTags: [{ type: 'OrdenProduccion', id: 'LIST' }, 'Dashboard'],
    }),

    updateOrdenProduccion: builder.mutation<
      OrdenProduccion,
      { id: number; body: Partial<OrdenProduccion> }
    >({
      query: ({ id, body }) => ({
        url: `/ordenes-produccion/${id}/`,
        method: 'PATCH',
        body,
      }),
      invalidatesTags: (_, __, { id }) => [
        { type: 'OrdenProduccion', id },
        { type: 'OrdenProduccion', id: 'LIST' },
        'Dashboard',
      ],
    }),

    // ==================== ORDENES DE COMPRA ====================
    getOrdenesCompra: builder.query<
      PaginatedResponse<OrdenCompra>,
      { page?: number; estado?: string }
    >({
      query: ({ page = 1, estado }) => {
        const params = new URLSearchParams();
        params.append('page', String(page));
        if (estado) params.append('estado', estado);
        return `/ordenes-compra/?${params.toString()}`;
      },
      providesTags: (result) =>
        result
          ? [
              ...result.results.map(({ id }) => ({
                type: 'OrdenCompra' as const,
                id,
              })),
              { type: 'OrdenCompra', id: 'LIST' },
            ]
          : [{ type: 'OrdenCompra', id: 'LIST' }],
    }),

    getOrdenCompra: builder.query<OrdenCompra, number>({
      query: (id) => `/ordenes-compra/${id}/`,
      providesTags: (_, __, id) => [{ type: 'OrdenCompra', id }],
    }),

    createOrdenCompra: builder.mutation<OrdenCompra, Partial<OrdenCompra>>({
      query: (body) => ({
        url: '/ordenes-compra/',
        method: 'POST',
        body,
      }),
      invalidatesTags: [{ type: 'OrdenCompra', id: 'LIST' }, 'Dashboard'],
    }),

    updateOrdenCompra: builder.mutation<
      OrdenCompra,
      { id: number; body: Partial<OrdenCompra> }
    >({
      query: ({ id, body }) => ({
        url: `/ordenes-compra/${id}/`,
        method: 'PATCH',
        body,
      }),
      invalidatesTags: (_, __, { id }) => [
        { type: 'OrdenCompra', id },
        { type: 'OrdenCompra', id: 'LIST' },
        'Dashboard',
      ],
    }),

    // ==================== NOTIFICACIONES ====================
    getNotificaciones: builder.query<
      PaginatedResponse<Notificacion>,
      { page?: number; leida?: boolean }
    >({
      query: ({ page = 1, leida }) => {
        const params = new URLSearchParams();
        params.append('page', String(page));
        if (leida !== undefined) params.append('leida', String(leida));
        return `/notificaciones/?${params.toString()}`;
      },
      providesTags: ['Notificacion'],
    }),

    marcarNotificacionLeida: builder.mutation<Notificacion, number>({
      query: (id) => ({
        url: `/notificaciones/${id}/marcar-leida/`,
        method: 'POST',
      }),
      invalidatesTags: ['Notificacion'],
    }),

    marcarNotificacionAtendida: builder.mutation<Notificacion, number>({
      query: (id) => ({
        url: `/notificaciones/${id}/marcar-atendida/`,
        method: 'POST',
      }),
      invalidatesTags: ['Notificacion'],
    }),
  }),
});

// Exportar hooks generados automáticamente
export const {
  // Auth
  useLoginMutation,
  useLogoutMutation,
  useGetCurrentUserQuery,
  // Dashboard
  useGetDashboardResumenQuery,
  // Productos
  useGetProductosQuery,
  useGetProductoQuery,
  useCreateProductoMutation,
  useUpdateProductoMutation,
  useDeleteProductoMutation,
  // Insumos
  useGetInsumosQuery,
  useGetInsumoQuery,
  useCreateInsumoMutation,
  useUpdateInsumoMutation,
  useDeleteInsumoMutation,
  // Depósitos
  useGetDepositosQuery,
  // Categorías
  useGetCategoriasProductoQuery,
  useGetCategoriasInsumoQuery,
  // Clientes
  useGetClientesQuery,
  // Proveedores
  useGetProveedoresQuery,
  // Ordenes de Venta
  useGetOrdenesVentaQuery,
  useGetOrdenVentaQuery,
  useCreateOrdenVentaMutation,
  useUpdateOrdenVentaMutation,
  // Ordenes de Producción
  useGetOrdenesProduccionQuery,
  useGetOrdenProduccionQuery,
  useCreateOrdenProduccionMutation,
  useUpdateOrdenProduccionMutation,
  // Ordenes de Compra
  useGetOrdenesCompraQuery,
  useGetOrdenCompraQuery,
  useCreateOrdenCompraMutation,
  useUpdateOrdenCompraMutation,
  // Notificaciones
  useGetNotificacionesQuery,
  useMarcarNotificacionLeidaMutation,
  useMarcarNotificacionAtendidaMutation,
} = luminovaApi;

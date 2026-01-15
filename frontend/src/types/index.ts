/**
 * Tipos base para la aplicación LUMINOVA ERP
 */

// Respuesta paginada de la API
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Respuesta de error de la API
export interface ApiError {
  detail?: string;
  message?: string;
  errors?: string[];
}

// Estado base para slices que manejan datos de API
export interface BaseState<T> {
  items: T[];
  selectedItem: T | null;
  loading: boolean;
  error: string | null;
  totalCount: number;
}

// Usuario autenticado
export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  is_superuser: boolean;
}

// Empresa/Tenant
export interface Empresa {
  id: number;
  nombre: string;
  razon_social: string;
  cuit: string;
  direccion: string;
  telefono: string;
  email: string;
  activa: boolean;
  schema_name: string;
}

// Depósito
export interface Deposito {
  id: number;
  nombre: string;
  empresa: number;
  ubicacion: string;
  descripcion: string;
}

// Categoría de Producto Terminado
export interface CategoriaProducto {
  id: number;
  nombre: string;
  imagen: string | null;
  deposito: number | null;
}

// Producto Terminado
export interface Producto {
  id: number;
  descripcion: string;
  categoria: number;
  categoria_nombre?: string;
  precio_unitario: number;
  stock: number;
  stock_minimo: number;
  stock_objetivo: number;
  produccion_habilitada: boolean;
  modelo: string | null;
  potencia: number | null;
  acabado: string | null;
  color_luz: string | null;
  material: string | null;
  imagen: string | null;
  deposito: number | null;
  deposito_nombre?: string;
  necesita_reposicion: boolean;
  porcentaje_stock: number;
}

// Categoría de Insumo
export interface CategoriaInsumo {
  id: number;
  nombre: string;
  imagen: string | null;
  deposito: number | null;
}

// Insumo
export interface Insumo {
  id: number;
  descripcion: string;
  categoria: number;
  categoria_nombre?: string;
  fabricante: number | null;
  fabricante_nombre?: string;
  imagen: string | null;
  stock: number;
  cantidad_en_pedido: number;
  deposito: number | null;
  deposito_nombre?: string;
  notificado_a_compras: boolean;
}

// Cliente
export interface Cliente {
  id: number;
  nombre: string;
  direccion: string;
  telefono: string;
  email: string | null;
}

// Proveedor
export interface Proveedor {
  id: number;
  nombre: string;
  contacto: string;
  telefono: string;
  email: string | null;
}

// Fabricante
export interface Fabricante {
  id: number;
  nombre: string;
  contacto: string;
  telefono: string;
  email: string | null;
}

// Estado de Orden de Venta
export type EstadoOrdenVenta = 
  | 'PENDIENTE'
  | 'CONFIRMADA'
  | 'INSUMOS_SOLICITADOS'
  | 'PRODUCCION_INICIADA'
  | 'PRODUCCION_CON_PROBLEMAS'
  | 'LISTA_ENTREGA'
  | 'COMPLETADA'
  | 'CANCELADA';

// Orden de Venta
export interface OrdenVenta {
  id: number;
  numero_ov: string;
  cliente: number;
  cliente_nombre?: string;
  fecha_creacion: string;
  estado: EstadoOrdenVenta;
  total_ov: number;
  notas: string | null;
  items?: ItemOrdenVenta[];
}

// Item de Orden de Venta
export interface ItemOrdenVenta {
  id: number;
  orden_venta: number;
  producto_terminado: number;
  producto_nombre?: string;
  cantidad: number;
  precio_unitario_venta: number;
  subtotal: number;
}

// Estado de Orden de Producción
export interface EstadoOrden {
  id: number;
  nombre: string;
}

// Sector de Producción
export interface SectorAsignado {
  id: number;
  nombre: string;
}

// Tipo de Orden de Producción
export type TipoOrdenProduccion = 'MTO' | 'MTS';

// Orden de Producción
export interface OrdenProduccion {
  id: number;
  numero_op: string;
  tipo_orden: TipoOrdenProduccion;
  orden_venta_origen: number | null;
  numero_ov_origen?: string;
  producto_a_producir: number;
  producto_nombre?: string;
  cantidad_a_producir: number;
  estado_op: number | null;
  estado_nombre?: string;
  fecha_solicitud: string;
  fecha_inicio_real: string | null;
  fecha_inicio_planificada: string | null;
  fecha_fin_real: string | null;
  fecha_fin_planificada: string | null;
  sector_asignado_op: number | null;
  sector_nombre?: string;
  notas: string | null;
}

// Estado de Orden de Compra
export type EstadoOrdenCompra = 
  | 'BORRADOR'
  | 'APROBADA'
  | 'ENVIADA_PROVEEDOR'
  | 'CONFIRMADA_PROVEEDOR'
  | 'EN_TRANSITO'
  | 'RECIBIDA_PARCIAL'
  | 'RECIBIDA_TOTAL'
  | 'COMPLETADA'
  | 'CANCELADA';

// Orden de Compra
export interface OrdenCompra {
  id: number;
  numero_orden: string;
  tipo: string;
  fecha_creacion: string;
  proveedor: number;
  proveedor_nombre?: string;
  estado: EstadoOrdenCompra;
  insumo_principal: number | null;
  insumo_nombre?: string;
  cantidad_principal: number | null;
  precio_unitario_compra: number | null;
  total_orden_compra: number;
  deposito: number | null;
  fecha_estimada_entrega: string | null;
  numero_tracking: string | null;
  notas: string | null;
}

// Notificación del Sistema
export type TipoNotificacion = 
  | 'stock_bajo'
  | 'oc_creada'
  | 'oc_enviada'
  | 'oc_recibida'
  | 'pedido_recibido'
  | 'transferencia_solicitada'
  | 'produccion_completada'
  | 'solicitud_insumos'
  | 'general';

export type PrioridadNotificacion = 'baja' | 'media' | 'alta' | 'critica';

export type GrupoDestinatario = 
  | 'compras'
  | 'ventas'
  | 'deposito'
  | 'produccion'
  | 'control_calidad'
  | 'administrador'
  | 'todos';

export interface Notificacion {
  id: number;
  tipo: TipoNotificacion;
  titulo: string;
  mensaje: string;
  remitente: number;
  remitente_nombre?: string;
  destinatario_grupo: GrupoDestinatario;
  prioridad: PrioridadNotificacion;
  datos_contexto: Record<string, unknown> | null;
  leida: boolean;
  atendida: boolean;
  fecha_creacion: string;
  fecha_lectura: string | null;
  fecha_atencion: string | null;
  fecha_expiracion: string | null;
}

// Movimiento de Stock
export type TipoMovimiento = 'entrada' | 'salida' | 'transferencia';

export interface MovimientoStock {
  id: number;
  insumo: number | null;
  insumo_nombre?: string;
  producto: number | null;
  producto_nombre?: string;
  deposito_origen: number | null;
  deposito_origen_nombre?: string;
  deposito_destino: number | null;
  deposito_destino_nombre?: string;
  cantidad: number;
  tipo: TipoMovimiento;
  fecha: string;
  usuario: number | null;
  usuario_nombre?: string;
  motivo: string;
}

// Token de autenticación
export interface AuthTokens {
  access: string;
  refresh: string;
}

// Estado de autenticación
export interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

// Resumen del Dashboard
export interface DashboardResumen {
  inventario: {
    total_productos: number;
    total_insumos: number;
    productos_stock_bajo: number;
    insumos_stock_bajo: number;
  };
  ventas: {
    total_ordenes: number;
    ordenes_pendientes: number;
    ordenes_completadas: number;
    total_vendido: number;
  };
  produccion: {
    ordenes_pendientes: number;
    ordenes_en_proceso: number;
    ordenes_completadas: number;
    reportes_pendientes: number;
  };
  compras: {
    ordenes_pendientes: number;
    ordenes_en_transito: number;
    ordenes_vencidas: number;
  };
}

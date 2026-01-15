/**
 * Sidebar Component - Navegación lateral
 */
import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Box,
  Typography,
  Divider,
  Collapse,
  useTheme,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Inventory as InventoryIcon,
  ShoppingCart as ShoppingCartIcon,
  Factory as FactoryIcon,
  LocalShipping as ShippingIcon,
  People as PeopleIcon,
  Category as CategoryIcon,
  Warehouse as WarehouseIcon,
  Settings as SettingsIcon,
  ExpandLess,
  ExpandMore,
  Receipt as ReceiptIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import { useAppSelector, useAppDispatch } from '../../hooks';
import { setSidebarOpen } from '../../store/slices/uiSlice';

interface MenuItem {
  label: string;
  icon: React.ReactNode;
  path?: string;
  children?: MenuItem[];
}

const menuItems: MenuItem[] = [
  {
    label: 'Dashboard',
    icon: <DashboardIcon />,
    path: '/dashboard',
  },
  {
    label: 'Inventario',
    icon: <InventoryIcon />,
    children: [
      { label: 'Productos', icon: <CategoryIcon />, path: '/inventario/productos' },
      { label: 'Insumos', icon: <InventoryIcon />, path: '/inventario/insumos' },
      { label: 'Depósitos', icon: <WarehouseIcon />, path: '/inventario/depositos' },
      { label: 'Movimientos', icon: <AssessmentIcon />, path: '/inventario/movimientos' },
    ],
  },
  {
    label: 'Ventas',
    icon: <ShoppingCartIcon />,
    children: [
      { label: 'Órdenes de Venta', icon: <ReceiptIcon />, path: '/ventas/ordenes' },
      { label: 'Clientes', icon: <PeopleIcon />, path: '/ventas/clientes' },
    ],
  },
  {
    label: 'Producción',
    icon: <FactoryIcon />,
    children: [
      { label: 'Órdenes de Producción', icon: <ReceiptIcon />, path: '/produccion/ordenes' },
      { label: 'Reportes', icon: <AssessmentIcon />, path: '/produccion/reportes' },
    ],
  },
  {
    label: 'Compras',
    icon: <ShippingIcon />,
    children: [
      { label: 'Órdenes de Compra', icon: <ReceiptIcon />, path: '/compras/ordenes' },
      { label: 'Proveedores', icon: <PeopleIcon />, path: '/compras/proveedores' },
    ],
  },
  {
    label: 'Configuración',
    icon: <SettingsIcon />,
    path: '/configuracion',
  },
];

const DRAWER_WIDTH = 260;

interface SidebarProps {
  variant?: 'permanent' | 'temporary';
}

const Sidebar: React.FC<SidebarProps> = ({ variant = 'permanent' }) => {
  const theme = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { sidebarOpen } = useAppSelector((state) => state.ui);
  
  const [openMenus, setOpenMenus] = React.useState<Record<string, boolean>>({});

  // Abrir automáticamente el menú padre de la ruta actual
  React.useEffect(() => {
    menuItems.forEach((item) => {
      if (item.children) {
        const isActive = item.children.some(
          (child) => child.path && location.pathname.startsWith(child.path)
        );
        if (isActive) {
          setOpenMenus((prev) => ({ ...prev, [item.label]: true }));
        }
      }
    });
  }, [location.pathname]);

  const handleToggleMenu = (label: string) => {
    setOpenMenus((prev) => ({ ...prev, [label]: !prev[label] }));
  };

  const handleNavigation = (path: string) => {
    navigate(path);
    if (variant === 'temporary') {
      dispatch(setSidebarOpen(false));
    }
  };

  const isItemActive = (item: MenuItem): boolean => {
    if (item.path) {
      return location.pathname === item.path || 
        (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
    }
    if (item.children) {
      return item.children.some(
        (child) => child.path && location.pathname.startsWith(child.path)
      );
    }
    return false;
  };

  const drawerContent = (
    <>
      <Toolbar sx={{ justifyContent: 'center', py: 2 }}>
        <Box display="flex" alignItems="center" gap={1}>
          <Box
            component="img"
            src="/logo.png"
            alt="LUMINOVA"
            sx={{ height: 40 }}
            onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
              e.currentTarget.style.display = 'none';
            }}
          />
          <Typography
            variant="h5"
            sx={{
              fontWeight: 700,
              background: `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            LUMINOVA
          </Typography>
        </Box>
      </Toolbar>
      <Divider />
      <List sx={{ px: 1 }}>
        {menuItems.map((item) => (
          <React.Fragment key={item.label}>
            <ListItem disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                onClick={() => {
                  if (item.children) {
                    handleToggleMenu(item.label);
                  } else if (item.path) {
                    handleNavigation(item.path);
                  }
                }}
                selected={isItemActive(item)}
                sx={{
                  borderRadius: 2,
                  '&.Mui-selected': {
                    backgroundColor: theme.palette.primary.main + '20',
                    '&:hover': {
                      backgroundColor: theme.palette.primary.main + '30',
                    },
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    color: isItemActive(item)
                      ? theme.palette.primary.main
                      : 'inherit',
                    minWidth: 40,
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{
                    fontWeight: isItemActive(item) ? 600 : 400,
                  }}
                />
                {item.children && (
                  openMenus[item.label] ? <ExpandLess /> : <ExpandMore />
                )}
              </ListItemButton>
            </ListItem>

            {item.children && (
              <Collapse in={openMenus[item.label]} timeout="auto" unmountOnExit>
                <List component="div" disablePadding>
                  {item.children.map((child) => (
                    <ListItem key={child.label} disablePadding sx={{ mb: 0.5 }}>
                      <ListItemButton
                        onClick={() => child.path && handleNavigation(child.path)}
                        selected={
                          child.path
                            ? location.pathname.startsWith(child.path)
                            : false
                        }
                        sx={{
                          pl: 4,
                          borderRadius: 2,
                          '&.Mui-selected': {
                            backgroundColor: theme.palette.primary.main + '20',
                            '&:hover': {
                              backgroundColor: theme.palette.primary.main + '30',
                            },
                          },
                        }}
                      >
                        <ListItemIcon
                          sx={{
                            color:
                              child.path &&
                              location.pathname.startsWith(child.path)
                                ? theme.palette.primary.main
                                : 'inherit',
                            minWidth: 40,
                          }}
                        >
                          {child.icon}
                        </ListItemIcon>
                        <ListItemText
                          primary={child.label}
                          primaryTypographyProps={{
                            fontSize: '0.9rem',
                            fontWeight:
                              child.path &&
                              location.pathname.startsWith(child.path)
                                ? 600
                                : 400,
                          }}
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              </Collapse>
            )}
          </React.Fragment>
        ))}
      </List>
    </>
  );

  if (variant === 'temporary') {
    return (
      <Drawer
        variant="temporary"
        open={sidebarOpen}
        onClose={() => dispatch(setSidebarOpen(false))}
        ModalProps={{ keepMounted: true }}
        sx={{
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
          },
        }}
      >
        {drawerContent}
      </Drawer>
    );
  }

  return (
    <Drawer
      variant="persistent"
      open={sidebarOpen}
      sx={{
        width: sidebarOpen ? DRAWER_WIDTH : 0,
        flexShrink: 0,
        transition: theme.transitions.create('width', {
          easing: theme.transitions.easing.sharp,
          duration: theme.transitions.duration.enteringScreen,
        }),
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          borderRight: `1px solid ${theme.palette.divider}`,
        },
      }}
    >
      {drawerContent}
    </Drawer>
  );
};

export default Sidebar;

/**
 * Header Component - Barra superior de la aplicación
 */
import React from 'react';
import {
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Badge,
  Avatar,
  Menu,
  MenuItem,
  Box,
  Tooltip,
  Divider,
  ListItemIcon,
  useTheme,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Notifications as NotificationsIcon,
  DarkMode as DarkModeIcon,
  LightMode as LightModeIcon,
  Person as PersonIcon,
  Logout as LogoutIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector, useAuth } from '../../hooks';
import { toggleSidebar, toggleDarkMode } from '../../store/slices/uiSlice';
import { logout } from '../../store/slices/authSlice';
import { useGetNotificacionesQuery } from '../../store/api/luminovaApi';

const DRAWER_WIDTH = 260;

const Header: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { user } = useAuth();
  const { sidebarOpen, darkMode, currentModuleTitle } = useAppSelector(
    (state) => state.ui
  );

  // Obtener notificaciones no leídas
  const { data: notificaciones } = useGetNotificacionesQuery({ leida: false });
  const unreadCount = notificaciones?.count || 0;

  // Estados para menús
  const [anchorElUser, setAnchorElUser] = React.useState<null | HTMLElement>(null);
  const [anchorElNotif, setAnchorElNotif] = React.useState<null | HTMLElement>(null);

  const handleOpenUserMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElUser(event.currentTarget);
  };

  const handleCloseUserMenu = () => {
    setAnchorElUser(null);
  };

  const handleOpenNotifMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElNotif(event.currentTarget);
  };

  const handleCloseNotifMenu = () => {
    setAnchorElNotif(null);
  };

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
    handleCloseUserMenu();
  };

  const handleProfile = () => {
    navigate('/perfil');
    handleCloseUserMenu();
  };

  const handleSettings = () => {
    navigate('/configuracion');
    handleCloseUserMenu();
  };

  const handleViewAllNotifications = () => {
    navigate('/notificaciones');
    handleCloseNotifMenu();
  };

  const getUserInitials = () => {
    if (!user) return '?';
    const first = user.first_name?.[0] || '';
    const last = user.last_name?.[0] || '';
    if (first || last) return `${first}${last}`.toUpperCase();
    return user.username[0].toUpperCase();
  };

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        width: sidebarOpen ? `calc(100% - ${DRAWER_WIDTH}px)` : '100%',
        ml: sidebarOpen ? `${DRAWER_WIDTH}px` : 0,
        transition: theme.transitions.create(['width', 'margin'], {
          easing: theme.transitions.easing.sharp,
          duration: theme.transitions.duration.enteringScreen,
        }),
        backgroundColor: theme.palette.background.paper,
        borderBottom: `1px solid ${theme.palette.divider}`,
      }}
    >
      <Toolbar>
        <IconButton
          edge="start"
          color="inherit"
          aria-label="toggle sidebar"
          onClick={() => dispatch(toggleSidebar())}
          sx={{ mr: 2, color: theme.palette.text.primary }}
        >
          <MenuIcon />
        </IconButton>

        <Typography
          variant="h6"
          component="div"
          sx={{
            flexGrow: 1,
            color: theme.palette.text.primary,
            fontWeight: 600,
          }}
        >
          {currentModuleTitle}
        </Typography>

        {/* Toggle Dark Mode */}
        <Tooltip title={darkMode ? 'Modo claro' : 'Modo oscuro'}>
          <IconButton
            onClick={() => dispatch(toggleDarkMode())}
            sx={{ color: theme.palette.text.primary }}
          >
            {darkMode ? <LightModeIcon /> : <DarkModeIcon />}
          </IconButton>
        </Tooltip>

        {/* Notificaciones */}
        <Tooltip title="Notificaciones">
          <IconButton
            onClick={handleOpenNotifMenu}
            sx={{ color: theme.palette.text.primary }}
          >
            <Badge badgeContent={unreadCount} color="error">
              <NotificationsIcon />
            </Badge>
          </IconButton>
        </Tooltip>
        <Menu
          anchorEl={anchorElNotif}
          open={Boolean(anchorElNotif)}
          onClose={handleCloseNotifMenu}
          PaperProps={{
            sx: {
              width: 320,
              maxHeight: 400,
              mt: 1.5,
            },
          }}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        >
          <Box sx={{ p: 2 }}>
            <Typography variant="h6">Notificaciones</Typography>
          </Box>
          <Divider />
          {notificaciones?.results && notificaciones.results.length > 0 ? (
            notificaciones.results.slice(0, 5).map((notif) => (
              <MenuItem
                key={notif.id}
                onClick={handleCloseNotifMenu}
                sx={{ py: 1.5, whiteSpace: 'normal' }}
              >
                <Box>
                  <Typography variant="body2" fontWeight={600}>
                    {notif.titulo}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {notif.mensaje.substring(0, 60)}...
                  </Typography>
                </Box>
              </MenuItem>
            ))
          ) : (
            <MenuItem disabled>
              <Typography variant="body2" color="text.secondary">
                No hay notificaciones nuevas
              </Typography>
            </MenuItem>
          )}
          <Divider />
          <MenuItem onClick={handleViewAllNotifications}>
            <Typography
              variant="body2"
              color="primary"
              sx={{ width: '100%', textAlign: 'center' }}
            >
              Ver todas las notificaciones
            </Typography>
          </MenuItem>
        </Menu>

        {/* Avatar y Menú de Usuario */}
        <Box sx={{ ml: 1 }}>
          <Tooltip title="Cuenta">
            <IconButton onClick={handleOpenUserMenu} sx={{ p: 0, ml: 1 }}>
              <Avatar
                sx={{
                  bgcolor: theme.palette.primary.main,
                  width: 36,
                  height: 36,
                }}
              >
                {getUserInitials()}
              </Avatar>
            </IconButton>
          </Tooltip>
          <Menu
            anchorEl={anchorElUser}
            open={Boolean(anchorElUser)}
            onClose={handleCloseUserMenu}
            PaperProps={{
              sx: {
                width: 200,
                mt: 1.5,
              },
            }}
            transformOrigin={{ horizontal: 'right', vertical: 'top' }}
            anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
          >
            <Box sx={{ px: 2, py: 1.5 }}>
              <Typography variant="subtitle2" fontWeight={600}>
                {user?.first_name && user?.last_name
                  ? `${user.first_name} ${user.last_name}`
                  : user?.username}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {user?.email}
              </Typography>
            </Box>
            <Divider />
            <MenuItem onClick={handleProfile}>
              <ListItemIcon>
                <PersonIcon fontSize="small" />
              </ListItemIcon>
              Mi Perfil
            </MenuItem>
            <MenuItem onClick={handleSettings}>
              <ListItemIcon>
                <SettingsIcon fontSize="small" />
              </ListItemIcon>
              Configuración
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout}>
              <ListItemIcon>
                <LogoutIcon fontSize="small" />
              </ListItemIcon>
              Cerrar Sesión
            </MenuItem>
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Header;

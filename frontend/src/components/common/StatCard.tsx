/**
 * StatCard Component - Tarjeta de estadísticas
 */
import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  useTheme,
  SxProps,
  Theme,
} from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';

interface StatCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: React.ReactNode;
  color?: 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info';
  trend?: {
    value: number;
    label?: string;
  };
  onClick?: () => void;
  sx?: SxProps<Theme>;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  color = 'primary',
  trend,
  onClick,
  sx,
}) => {
  const theme = useTheme();

  const getColorValue = () => {
    return theme.palette[color].main;
  };

  const getBgColor = () => {
    return theme.palette[color].main + '15';
  };

  return (
    <Card
      onClick={onClick}
      sx={{
        borderRadius: 3,
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.3s ease',
        border: `1px solid ${theme.palette.divider}`,
        '&:hover': onClick
          ? {
              transform: 'translateY(-2px)',
              boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
            }
          : {},
        ...sx,
      }}
    >
      <CardContent sx={{ p: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography
              variant="body2"
              color="text.secondary"
              fontWeight={500}
              gutterBottom
            >
              {title}
            </Typography>
            <Typography variant="h4" fontWeight={700} sx={{ mb: 0.5 }}>
              {typeof value === 'number' ? value.toLocaleString('es-AR') : value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              p: 1.5,
              borderRadius: 2,
              backgroundColor: getBgColor(),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              '& > svg': {
                fontSize: 28,
                color: getColorValue(),
              },
            }}
          >
            {icon}
          </Box>
        </Box>

        {trend && (
          <Box display="flex" alignItems="center" mt={2}>
            {trend.value >= 0 ? (
              <TrendingUp
                sx={{ fontSize: 18, color: theme.palette.success.main, mr: 0.5 }}
              />
            ) : (
              <TrendingDown
                sx={{ fontSize: 18, color: theme.palette.error.main, mr: 0.5 }}
              />
            )}
            <Typography
              variant="body2"
              sx={{
                color:
                  trend.value >= 0
                    ? theme.palette.success.main
                    : theme.palette.error.main,
                fontWeight: 600,
              }}
            >
              {trend.value > 0 ? '+' : ''}
              {trend.value}%
            </Typography>
            {trend.label && (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ ml: 1 }}
              >
                {trend.label}
              </Typography>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default StatCard;

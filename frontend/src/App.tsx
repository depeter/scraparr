import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import {
  AppBar,
  Box,
  Container,
  CssBaseline,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  ThemeProvider,
  createTheme,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Code as CodeIcon,
  Schedule as ScheduleIcon,
  History as HistoryIcon,
} from '@mui/icons-material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import DashboardPage from './pages/DashboardPage';
import ScrapersPage from './pages/ScrapersPage';
import JobsPage from './pages/JobsPage';
import ExecutionsPage from './pages/ExecutionsPage';

const drawerWidth = 240;

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
  { text: 'Scrapers', icon: <CodeIcon />, path: '/scrapers' },
  { text: 'Jobs', icon: <ScheduleIcon />, path: '/jobs' },
  { text: 'Executions', icon: <HistoryIcon />, path: '/executions' },
];

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Box sx={{ display: 'flex' }}>
            <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
              <Toolbar>
                <Typography variant="h6" noWrap component="div">
                  Scraparr
                </Typography>
              </Toolbar>
            </AppBar>
            <Drawer
              variant="permanent"
              sx={{
                width: drawerWidth,
                flexShrink: 0,
                [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
              }}
            >
              <Toolbar />
              <Box sx={{ overflow: 'auto' }}>
                <List>
                  {menuItems.map((item) => (
                    <ListItem key={item.text} disablePadding>
                      <ListItemButton component={Link} to={item.path}>
                        <ListItemIcon>{item.icon}</ListItemIcon>
                        <ListItemText primary={item.text} />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              </Box>
            </Drawer>
            <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
              <Toolbar />
              <Container maxWidth="xl">
                <Routes>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/scrapers" element={<ScrapersPage />} />
                  <Route path="/jobs" element={<JobsPage />} />
                  <Route path="/executions" element={<ExecutionsPage />} />
                </Routes>
              </Container>
            </Box>
          </Box>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;

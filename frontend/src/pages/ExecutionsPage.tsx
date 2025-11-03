import React from 'react';
import {
  Box,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  IconButton,
} from '@mui/material';
import { Visibility } from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { executionApi } from '../api/client';
import { format } from 'date-fns';

const ExecutionsPage: React.FC = () => {
  const { data: executions, isLoading } = useQuery({
    queryKey: ['executions'],
    queryFn: () => executionApi.list(0, 100),
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'info';
      default:
        return 'default';
    }
  };

  if (isLoading) return <Typography>Loading...</Typography>;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Executions
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Scraper ID</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Items Scraped</TableCell>
              <TableCell>Started</TableCell>
              <TableCell>Duration</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {executions?.items.map((execution) => {
              const duration = execution.completed_at
                ? (new Date(execution.completed_at).getTime() -
                    new Date(execution.started_at).getTime()) /
                  1000
                : null;

              return (
                <TableRow key={execution.id}>
                  <TableCell>{execution.id}</TableCell>
                  <TableCell>{execution.scraper_id}</TableCell>
                  <TableCell>
                    <Chip
                      label={execution.status}
                      size="small"
                      color={getStatusColor(execution.status) as any}
                    />
                  </TableCell>
                  <TableCell>{execution.items_scraped}</TableCell>
                  <TableCell>{format(new Date(execution.started_at), 'PPp')}</TableCell>
                  <TableCell>{duration ? `${duration.toFixed(1)}s` : 'Running...'}</TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => {
                        executionApi.getLogs(execution.id).then((data) => {
                          alert(data.logs || 'No logs available');
                        });
                      }}
                    >
                      <Visibility />
                    </IconButton>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {executions?.items.length === 0 && (
        <Box textAlign="center" mt={4}>
          <Typography color="textSecondary">No executions yet. Run a scraper to see results!</Typography>
        </Box>
      )}
    </Box>
  );
};

export default ExecutionsPage;

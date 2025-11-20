import React from 'react';
import {
  Chip,
  TableCell,
  TableRow,
  IconButton,
  LinearProgress,
  Box,
  Typography,
  Tooltip,
} from '@mui/material';
import { Visibility } from '@mui/icons-material';
import { format } from 'date-fns';
import { useExecutionProgress } from '../hooks/useExecutionProgress';
import { executionApi } from '../api/client';

interface Execution {
  id: number;
  scraper_id: number;
  status: string;
  items_scraped: number;
  started_at: string;
  completed_at?: string | null;
  error_message?: string | null;
}

interface ExecutionRowProps {
  execution: Execution;
  scraperName?: string;
}

const ExecutionRow: React.FC<ExecutionRowProps> = ({ execution, scraperName }) => {
  // Connect to WebSocket for running executions
  const { progress } = useExecutionProgress({
    executionId: execution.status === 'running' ? execution.id : null,
    enabled: execution.status === 'running',
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

  // Use progress data if available, otherwise use execution data
  const itemsScraped = progress?.items_scraped ?? execution.items_scraped;
  const status = progress?.status ?? execution.status;

  // Calculate duration
  const duration = execution.completed_at
    ? (new Date(execution.completed_at).getTime() - new Date(execution.started_at).getTime()) / 1000
    : progress?.elapsed_seconds ?? null;

  // Format elapsed time nicely
  const formatDuration = (seconds: number | null) => {
    if (seconds === null) return 'Running...';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  return (
    <TableRow key={execution.id}>
      <TableCell>{execution.id}</TableCell>
      <TableCell>{scraperName || `Scraper ${execution.scraper_id}`}</TableCell>
      <TableCell>
        <Chip
          label={status}
          size="small"
          color={getStatusColor(status) as any}
        />
      </TableCell>
      <TableCell>
        {status === 'running' && progress ? (
          <Box>
            <Typography variant="body2">{itemsScraped} items</Typography>
            <Tooltip title={progress.message}>
              <Typography variant="caption" color="textSecondary" noWrap sx={{ maxWidth: 200, display: 'block' }}>
                {progress.message}
              </Typography>
            </Tooltip>
          </Box>
        ) : (
          <Typography variant="body2">{itemsScraped}</Typography>
        )}
      </TableCell>
      <TableCell>{format(new Date(execution.started_at), 'PPp')}</TableCell>
      <TableCell>
        <Box>
          <Typography variant="body2">{formatDuration(duration)}</Typography>
          {status === 'running' && progress && (
            <LinearProgress
              variant="indeterminate"
              sx={{ mt: 0.5, height: 3, borderRadius: 1 }}
            />
          )}
        </Box>
      </TableCell>
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
};

export default ExecutionRow;

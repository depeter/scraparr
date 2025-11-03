import React from 'react';
import {
  Box,
  Button,
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
import { PlayArrow, Delete } from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { scraperApi } from '../api/client';
import { format } from 'date-fns';

const ScrapersPage: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: scrapers, isLoading } = useQuery({
    queryKey: ['scrapers'],
    queryFn: () => scraperApi.list(0, 100),
  });

  const runMutation = useMutation({
    mutationFn: (id: number) => scraperApi.run(id),
    onSuccess: () => {
      alert('Scraper started!');
      queryClient.invalidateQueries({ queryKey: ['executions'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => scraperApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scrapers'] });
    },
  });

  if (isLoading) return <Typography>Loading...</Typography>;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Scrapers</Typography>
        <Button variant="contained" color="primary">
          Create Scraper
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Module</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {scrapers?.items.map((scraper) => (
              <TableRow key={scraper.id}>
                <TableCell>{scraper.name}</TableCell>
                <TableCell>
                  <Chip
                    label={scraper.scraper_type}
                    size="small"
                    color={scraper.scraper_type === 'api' ? 'primary' : 'secondary'}
                  />
                </TableCell>
                <TableCell>
                  {scraper.module_path}.{scraper.class_name}
                </TableCell>
                <TableCell>
                  <Chip
                    label={scraper.is_active ? 'Active' : 'Inactive'}
                    size="small"
                    color={scraper.is_active ? 'success' : 'default'}
                  />
                </TableCell>
                <TableCell>{format(new Date(scraper.created_at), 'PPp')}</TableCell>
                <TableCell align="right">
                  <IconButton
                    size="small"
                    color="primary"
                    onClick={() => runMutation.mutate(scraper.id)}
                    disabled={!scraper.is_active}
                  >
                    <PlayArrow />
                  </IconButton>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => {
                      if (window.confirm('Delete this scraper?')) {
                        deleteMutation.mutate(scraper.id);
                      }
                    }}
                  >
                    <Delete />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {scrapers?.items.length === 0 && (
        <Box textAlign="center" mt={4}>
          <Typography color="textSecondary">No scrapers yet. Create your first scraper!</Typography>
        </Box>
      )}
    </Box>
  );
};

export default ScrapersPage;

import React, { useState, useEffect } from 'react';
import axios from 'axios';

// Use the same origin as the frontend (works for both local dev and production)
// For production (https://scraparr.pm-consulting.be), use same origin
// For local dev (http://localhost:3001), use port 8000
const getApiUrl = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  // If running on localhost:3001, use localhost:8000 for API
  if (window.location.hostname === 'localhost') {
    return 'http://localhost:8000';
  }
  // Otherwise use same origin (production with reverse proxy)
  return window.location.origin;
};
const API_URL = getApiUrl();

interface SchemaTable {
  schema: string;
  table_name: string;
  column_count: number;
}

interface SchemaColumn {
  column_name: string;
  data_type: string;
  is_nullable: boolean;
  column_default: string | null;
}

interface QueryResult {
  columns: string[];
  rows: any[][];
  row_count: number;
  execution_time_ms: number;
}

const DatabasePage: React.FC = () => {
  const [schemas, setSchemas] = useState<string[]>([]);
  const [tables, setTables] = useState<SchemaTable[]>([]);
  const [selectedSchema, setSelectedSchema] = useState<string>('');
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [columns, setColumns] = useState<SchemaColumn[]>([]);
  const [query, setQuery] = useState<string>('SELECT * FROM scrapers LIMIT 10');
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  // Load schemas on mount
  useEffect(() => {
    loadSchemas();
    loadTables();
  }, []);

  // Load tables when schema changes
  useEffect(() => {
    if (selectedSchema) {
      loadTables(selectedSchema);
    }
  }, [selectedSchema]);

  // Load columns when table changes
  useEffect(() => {
    if (selectedSchema && selectedTable) {
      loadColumns(selectedSchema, selectedTable);
    }
  }, [selectedSchema, selectedTable]);

  const loadSchemas = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/database/schemas`);
      setSchemas(response.data);
    } catch (err: any) {
      console.error('Error loading schemas:', err);
    }
  };

  const loadTables = async (schema?: string) => {
    try {
      const url = schema
        ? `${API_URL}/api/database/tables?schema=${schema}`
        : `${API_URL}/api/database/tables`;
      const response = await axios.get(url);
      setTables(response.data);
    } catch (err: any) {
      console.error('Error loading tables:', err);
    }
  };

  const loadColumns = async (schema: string, table: string) => {
    try {
      const response = await axios.get(
        `${API_URL}/api/database/columns/${schema}/${table}`
      );
      setColumns(response.data);
    } catch (err: any) {
      console.error('Error loading columns:', err);
      setColumns([]);
    }
  };

  const executeQuery = async () => {
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    setLoading(true);
    setError('');
    setQueryResult(null);

    try {
      const response = await axios.post(`${API_URL}/api/database/query`, {
        query: query,
        limit: 1000,
      });
      setQueryResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Query execution failed');
    } finally {
      setLoading(false);
    }
  };

  const handleTableClick = (table: SchemaTable) => {
    setSelectedSchema(table.schema);
    setSelectedTable(table.table_name);
    setQuery(`SELECT * FROM ${table.schema}.${table.table_name} LIMIT 100`);
  };

  const handleQuickQuery = (queryText: string) => {
    setQuery(queryText);
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 100px)',
      width: '100%',
      maxWidth: '100%',
      overflow: 'hidden'
    }}>
      <h1 style={{ margin: '0 0 20px 0', flexShrink: 0 }}>Database Explorer</h1>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '300px 1fr',
        gap: '20px',
        flex: 1,
        minHeight: 0,
        overflow: 'hidden'
      }}>
        {/* Left sidebar - Schema Browser */}
        <div style={{
          border: '1px solid #ddd',
          borderRadius: '8px',
          padding: '15px',
          backgroundColor: '#f9f9f9',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          <h3 style={{ margin: '0 0 15px 0', flexShrink: 0 }}>Schemas &amp; Tables</h3>

          {/* Schema filter */}
          <div style={{ marginBottom: '15px', flexShrink: 0 }}>
            <select
              value={selectedSchema}
              onChange={(e) => setSelectedSchema(e.target.value)}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            >
              <option value="">All Schemas</option>
              {schemas.map((schema) => (
                <option key={schema} value={schema}>
                  {schema}
                </option>
              ))}
            </select>
          </div>

          {/* Tables list */}
          <div style={{ flex: 1, overflowY: 'auto', marginBottom: '15px', minHeight: 0 }}>
            {tables.map((table) => (
              <div
                key={`${table.schema}.${table.table_name}`}
                onClick={() => handleTableClick(table)}
                style={{
                  padding: '10px',
                  marginBottom: '5px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  backgroundColor: selectedTable === table.table_name && selectedSchema === table.schema ? '#e3f2fd' : 'white',
                  transition: 'background-color 0.2s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#e3f2fd'}
                onMouseLeave={(e) => {
                  if (!(selectedTable === table.table_name && selectedSchema === table.schema)) {
                    e.currentTarget.style.backgroundColor = 'white';
                  }
                }}
              >
                <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{table.table_name}</div>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  {table.schema} • {table.column_count} columns
                </div>
              </div>
            ))}
          </div>

          {/* Selected table columns */}
          {columns.length > 0 && (
            <div style={{
              borderTop: '1px solid #ddd',
              paddingTop: '15px',
              flexShrink: 0,
              maxHeight: '200px',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden'
            }}>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', flexShrink: 0 }}>Columns</h4>
              <div style={{ overflowY: 'auto', fontSize: '12px', minHeight: 0 }}>
                {columns.map((col) => (
                  <div key={col.column_name} style={{ padding: '4px 0', borderBottom: '1px solid #eee' }}>
                    <strong>{col.column_name}</strong>
                    <div style={{ color: '#666' }}>{col.data_type}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right side - Query Editor and Results */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          minHeight: 0
        }}>
          {/* Quick queries */}
          <div style={{ marginBottom: '15px', flexShrink: 0 }}>
            <h3 style={{ marginTop: 0 }}>Quick Queries</h3>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <button
                onClick={() => handleQuickQuery('SELECT * FROM scrapers LIMIT 10')}
                style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #ddd', cursor: 'pointer', backgroundColor: 'white' }}
              >
                List Scrapers
              </button>
              <button
                onClick={() => handleQuickQuery('SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10')}
                style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #ddd', cursor: 'pointer', backgroundColor: 'white' }}
              >
                Recent Jobs
              </button>
              <button
                onClick={() => handleQuickQuery('SELECT * FROM executions ORDER BY started_at DESC LIMIT 20')}
                style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #ddd', cursor: 'pointer', backgroundColor: 'white' }}
              >
                Recent Executions
              </button>
              <button
                onClick={() => handleQuickQuery('SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE \'scraper_%\'')}
                style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #ddd', cursor: 'pointer', backgroundColor: 'white' }}
              >
                Scraper Schemas
              </button>
            </div>
          </div>

          {/* SQL Editor */}
          <div style={{ marginBottom: '15px', flexShrink: 0 }}>
            <h3 style={{ margin: '0 0 10px 0' }}>SQL Query</h3>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your SQL query here... (SELECT only)"
              style={{
                width: '100%',
                height: '120px',
                padding: '12px',
                fontFamily: 'Monaco, Courier, monospace',
                fontSize: '14px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                resize: 'none',
              }}
            />
            <div style={{ marginTop: '10px', display: 'flex', gap: '10px', alignItems: 'center' }}>
              <button
                onClick={executeQuery}
                disabled={loading}
                style={{
                  padding: '10px 20px',
                  backgroundColor: loading ? '#ccc' : '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontWeight: 'bold',
                }}
              >
                {loading ? 'Executing...' : 'Execute Query'}
              </button>
              <span style={{ fontSize: '12px', color: '#666' }}>
                Note: Only SELECT queries are allowed
              </span>
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div style={{
              padding: '15px',
              backgroundColor: '#ffebee',
              border: '1px solid #f44336',
              borderRadius: '4px',
              color: '#c62828',
              marginBottom: '15px',
              flexShrink: 0
            }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {/* Query results */}
          {queryResult && (
            <div style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0,
              overflow: 'hidden'
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '10px',
                flexShrink: 0
              }}>
                <h3 style={{ margin: 0 }}>Results</h3>
                <div style={{ fontSize: '14px', color: '#666' }}>
                  {queryResult.row_count} rows • {queryResult.execution_time_ms}ms
                </div>
              </div>

              {queryResult.row_count === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                  No results found
                </div>
              ) : (
                <div style={{
                  flex: 1,
                  overflow: 'auto',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  minHeight: 0
                }}>
                  <table style={{
                    minWidth: '100%',
                    borderCollapse: 'collapse',
                    fontSize: '13px',
                    tableLayout: 'auto'
                  }}>
                    <thead style={{ position: 'sticky', top: 0, backgroundColor: '#f5f5f5', zIndex: 1 }}>
                      <tr>
                        {queryResult.columns.map((col) => (
                          <th key={col} style={{
                            padding: '12px',
                            textAlign: 'left',
                            borderBottom: '2px solid #ddd',
                            fontWeight: 'bold',
                            whiteSpace: 'nowrap',
                            backgroundColor: '#f5f5f5'
                          }}>
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {queryResult.rows.map((row, rowIndex) => (
                        <tr key={rowIndex} style={{ borderBottom: '1px solid #eee' }}>
                          {row.map((cell, cellIndex) => (
                            <td key={cellIndex} style={{
                              padding: '10px',
                              maxWidth: '400px',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              backgroundColor: 'white'
                            }}>
                              {cell === null ? <span style={{ color: '#999', fontStyle: 'italic' }}>NULL</span> : String(cell)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DatabasePage;

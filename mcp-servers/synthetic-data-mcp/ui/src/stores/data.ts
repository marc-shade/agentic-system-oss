import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { Database, Schema, Table, GenerationJob, Query } from '@/types'
import { api } from '@/lib/api'

interface DataState {
  // Databases
  databases: Database[]
  selectedDatabase: Database | null
  
  // Schemas
  schemas: Schema[]
  selectedSchema: Schema | null
  
  // Tables
  tables: Table[]
  selectedTable: Table | null
  
  // Generation Jobs
  jobs: GenerationJob[]
  selectedJob: GenerationJob | null
  
  // Queries
  queries: Query[]
  selectedQuery: Query | null
  
  // Loading states
  loading: {
    databases: boolean
    schemas: boolean
    tables: boolean
    jobs: boolean
    queries: boolean
  }
  
  // Actions
  setDatabases: (databases: Database[]) => void
  setSelectedDatabase: (database: Database | null) => void
  addDatabase: (database: Database) => void
  updateDatabase: (id: string, updates: Partial<Database>) => void
  removeDatabase: (id: string) => void
  
  setSchemas: (schemas: Schema[]) => void
  setSelectedSchema: (schema: Schema | null) => void
  addSchema: (schema: Schema) => void
  updateSchema: (id: string, updates: Partial<Schema>) => void
  
  setTables: (tables: Table[]) => void
  setSelectedTable: (table: Table | null) => void
  updateTable: (id: string, updates: Partial<Table>) => void
  
  setJobs: (jobs: GenerationJob[]) => void
  setSelectedJob: (job: GenerationJob | null) => void
  addJob: (job: GenerationJob) => void
  updateJob: (id: string, updates: Partial<GenerationJob>) => void
  removeJob: (id: string) => void
  
  setQueries: (queries: Query[]) => void
  setSelectedQuery: (query: Query | null) => void
  addQuery: (query: Query) => void
  updateQuery: (id: string, updates: Partial<Query>) => void
  removeQuery: (id: string) => void
  
  setLoading: (key: keyof DataState['loading'], loading: boolean) => void
  
  // API actions
  fetchDatabases: () => Promise<void>
  fetchSchemas: (databaseId: string) => Promise<void>
  fetchTables: (schemaId: string) => Promise<void>
  fetchJobs: () => Promise<void>
  fetchQueries: () => Promise<void>
}

export const useDataStore = create<DataState>()(
  subscribeWithSelector((set, get) => ({
    // Initial state
    databases: [],
    selectedDatabase: null,
    schemas: [],
    selectedSchema: null,
    tables: [],
    selectedTable: null,
    jobs: [],
    selectedJob: null,
    queries: [],
    selectedQuery: null,
    
    loading: {
      databases: false,
      schemas: false,
      tables: false,
      jobs: false,
      queries: false,
    },

    // Database actions
    setDatabases: (databases) => {
      set({ databases })
    },

    setSelectedDatabase: (database) => {
      set({ selectedDatabase: database })
      
      // Clear dependent data when database changes
      if (database?.id !== get().selectedDatabase?.id) {
        set({ 
          schemas: [],
          selectedSchema: null,
          tables: [],
          selectedTable: null,
        })
        
        // Fetch schemas for new database
        if (database) {
          get().fetchSchemas(database.id)
        }
      }
    },

    addDatabase: (database) => {
      set(state => ({
        databases: [...state.databases, database]
      }))
    },

    updateDatabase: (id, updates) => {
      set(state => ({
        databases: state.databases.map(db => 
          db.id === id ? { ...db, ...updates } : db
        ),
        selectedDatabase: state.selectedDatabase?.id === id 
          ? { ...state.selectedDatabase, ...updates }
          : state.selectedDatabase
      }))
    },

    removeDatabase: (id) => {
      set(state => ({
        databases: state.databases.filter(db => db.id !== id),
        selectedDatabase: state.selectedDatabase?.id === id 
          ? null 
          : state.selectedDatabase
      }))
    },

    // Schema actions
    setSchemas: (schemas) => {
      set({ schemas })
    },

    setSelectedSchema: (schema) => {
      set({ selectedSchema: schema })
      
      // Clear dependent data when schema changes
      if (schema?.id !== get().selectedSchema?.id) {
        set({ 
          tables: [],
          selectedTable: null,
        })
        
        // Fetch tables for new schema
        if (schema) {
          get().fetchTables(schema.id)
        }
      }
    },

    addSchema: (schema) => {
      set(state => ({
        schemas: [...state.schemas, schema]
      }))
    },

    updateSchema: (id, updates) => {
      set(state => ({
        schemas: state.schemas.map(schema => 
          schema.id === id ? { ...schema, ...updates } : schema
        ),
        selectedSchema: state.selectedSchema?.id === id 
          ? { ...state.selectedSchema, ...updates }
          : state.selectedSchema
      }))
    },

    // Table actions
    setTables: (tables) => {
      set({ tables })
    },

    setSelectedTable: (table) => {
      set({ selectedTable: table })
    },

    updateTable: (id, updates) => {
      set(state => ({
        tables: state.tables.map(table => 
          table.id === id ? { ...table, ...updates } : table
        ),
        selectedTable: state.selectedTable?.id === id 
          ? { ...state.selectedTable, ...updates }
          : state.selectedTable
      }))
    },

    // Job actions
    setJobs: (jobs) => {
      set({ jobs })
    },

    setSelectedJob: (job) => {
      set({ selectedJob: job })
    },

    addJob: (job) => {
      set(state => ({
        jobs: [job, ...state.jobs]
      }))
    },

    updateJob: (id, updates) => {
      set(state => ({
        jobs: state.jobs.map(job => 
          job.id === id ? { ...job, ...updates } : job
        ),
        selectedJob: state.selectedJob?.id === id 
          ? { ...state.selectedJob, ...updates }
          : state.selectedJob
      }))
    },

    removeJob: (id) => {
      set(state => ({
        jobs: state.jobs.filter(job => job.id !== id),
        selectedJob: state.selectedJob?.id === id 
          ? null 
          : state.selectedJob
      }))
    },

    // Query actions
    setQueries: (queries) => {
      set({ queries })
    },

    setSelectedQuery: (query) => {
      set({ selectedQuery: query })
    },

    addQuery: (query) => {
      set(state => ({
        queries: [query, ...state.queries]
      }))
    },

    updateQuery: (id, updates) => {
      set(state => ({
        queries: state.queries.map(query => 
          query.id === id ? { ...query, ...updates } : query
        ),
        selectedQuery: state.selectedQuery?.id === id 
          ? { ...state.selectedQuery, ...updates }
          : state.selectedQuery
      }))
    },

    removeQuery: (id) => {
      set(state => ({
        queries: state.queries.filter(query => query.id !== id),
        selectedQuery: state.selectedQuery?.id === id 
          ? null 
          : state.selectedQuery
      }))
    },

    // Loading actions
    setLoading: (key, loading) => {
      set(state => ({
        loading: {
          ...state.loading,
          [key]: loading
        }
      }))
    },

    // API actions
    fetchDatabases: async () => {
      set(state => ({ loading: { ...state.loading, databases: true } }))
      
      try {
        const response = await api.getDatabases()
        get().setDatabases(response.data)
      } catch (error) {
        console.error('Failed to fetch databases:', error)
        throw error
      } finally {
        set(state => ({ loading: { ...state.loading, databases: false } }))
      }
    },

    fetchSchemas: async (databaseId) => {
      set(state => ({ loading: { ...state.loading, schemas: true } }))
      
      try {
        const response = await api.getSchemas(databaseId)
        get().setSchemas(response.data)
      } catch (error) {
        console.error('Failed to fetch schemas:', error)
        throw error
      } finally {
        set(state => ({ loading: { ...state.loading, schemas: false } }))
      }
    },

    fetchTables: async (schemaId) => {
      set(state => ({ loading: { ...state.loading, tables: true } }))
      
      try {
        const schema = get().schemas.find(s => s.id === schemaId)
        if (schema) {
          get().setTables(schema.tables)
        }
      } catch (error) {
        console.error('Failed to fetch tables:', error)
        throw error
      } finally {
        set(state => ({ loading: { ...state.loading, tables: false } }))
      }
    },

    fetchJobs: async () => {
      set(state => ({ loading: { ...state.loading, jobs: true } }))
      
      try {
        const response = await api.getJobs()
        get().setJobs(response.data)
      } catch (error) {
        console.error('Failed to fetch jobs:', error)
        throw error
      } finally {
        set(state => ({ loading: { ...state.loading, jobs: false } }))
      }
    },

    fetchQueries: async () => {
      set(state => ({ loading: { ...state.loading, queries: true } }))
      
      try {
        const response = await api.getQueries()
        get().setQueries(response.data)
      } catch (error) {
        console.error('Failed to fetch queries:', error)
        throw error
      } finally {
        set(state => ({ loading: { ...state.loading, queries: false } }))
      }
    },
  }))
)

// Selectors
export const useDatabasesSelector = () => useDataStore(state => state.databases)
export const useSelectedDatabase = () => useDataStore(state => state.selectedDatabase)
export const useSchemasSelector = () => useDataStore(state => state.schemas)
export const useSelectedSchema = () => useDataStore(state => state.selectedSchema)
export const useTablesSelector = () => useDataStore(state => state.tables)
export const useSelectedTable = () => useDataStore(state => state.selectedTable)
export const useJobsSelector = () => useDataStore(state => state.jobs)
export const useSelectedJob = () => useDataStore(state => state.selectedJob)
export const useQueriesSelector = () => useDataStore(state => state.queries)
export const useSelectedQuery = () => useDataStore(state => state.selectedQuery)

// Loading selectors
export const useDataLoading = () => useDataStore(state => state.loading)
import * as React from "react"

import { cn } from "@/lib/utils"

const Table = React.forwardRef<
  HTMLTableElement,
  React.HTMLAttributes<HTMLTableElement>
>(({ className, ...props }, ref) => (
  <div className="relative w-full overflow-auto">
    <table
      ref={ref}
      className={cn("w-full caption-bottom text-sm", className)}
      {...props}
    />
  </div>
))
Table.displayName = "Table"

const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead ref={ref} className={cn("[&_tr]:border-b", className)} {...props} />
))
TableHeader.displayName = "TableHeader"

const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody
    ref={ref}
    className={cn("[&_tr:last-child]:border-0", className)}
    {...props}
  />
))
TableBody.displayName = "TableBody"

const TableFooter = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tfoot
    ref={ref}
    className={cn(
      "border-t bg-muted/50 font-medium [&>tr]:last:border-b-0",
      className
    )}
    {...props}
  />
))
TableFooter.displayName = "TableFooter"

const TableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement> & {
    clickable?: boolean
  }
>(({ className, clickable, ...props }, ref) => (
  <tr
    ref={ref}
    className={cn(
      "border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted",
      clickable && "cursor-pointer hover:bg-muted/80",
      className
    )}
    {...props}
  />
))
TableRow.displayName = "TableRow"

const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement> & {
    sortable?: boolean
    sortDirection?: 'asc' | 'desc' | null
    onSort?: () => void
  }
>(({ className, sortable, sortDirection, onSort, children, ...props }, ref) => (
  <th
    ref={ref}
    className={cn(
      "h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0",
      sortable && "cursor-pointer hover:bg-muted/50 select-none",
      className
    )}
    onClick={sortable ? onSort : undefined}
    {...props}
  >
    <div className="flex items-center gap-2">
      {children}
      {sortable && (
        <div className="flex flex-col">
          <svg
            className={cn(
              "h-3 w-3",
              sortDirection === 'asc' ? "text-foreground" : "text-muted-foreground"
            )}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 15l7-7 7 7"
            />
          </svg>
          <svg
            className={cn(
              "h-3 w-3 -mt-1",
              sortDirection === 'desc' ? "text-foreground" : "text-muted-foreground"
            )}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      )}
    </div>
  </th>
))
TableHead.displayName = "TableHead"

const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement> & {
    truncate?: boolean
    numeric?: boolean
  }
>(({ className, truncate, numeric, ...props }, ref) => (
  <td
    ref={ref}
    className={cn(
      "p-4 align-middle [&:has([role=checkbox])]:pr-0",
      truncate && "max-w-0 truncate",
      numeric && "text-right font-mono",
      className
    )}
    {...props}
  />
))
TableCell.displayName = "TableCell"

const TableCaption = React.forwardRef<
  HTMLTableCaptionElement,
  React.HTMLAttributes<HTMLTableCaptionElement>
>(({ className, ...props }, ref) => (
  <caption
    ref={ref}
    className={cn("mt-4 text-sm text-muted-foreground", className)}
    {...props}
  />
))
TableCaption.displayName = "TableCaption"

// Enhanced table components for data display
const DataTable = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    loading?: boolean
    empty?: boolean
    emptyMessage?: string
    error?: string
  }
>(({ className, loading, empty, emptyMessage = "No data available", error, children, ...props }, ref) => (
  <div ref={ref} className={cn("rounded-md border", className)} {...props}>
    {loading ? (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-sm text-muted-foreground">Loading...</span>
        </div>
      </div>
    ) : error ? (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-sm text-red-600 dark:text-red-400">Error: {error}</div>
        </div>
      </div>
    ) : empty ? (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-sm text-muted-foreground">{emptyMessage}</div>
        </div>
      </div>
    ) : (
      children
    )}
  </div>
))
DataTable.displayName = "DataTable"

const TablePagination = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    page: number
    totalPages: number
    totalItems: number
    itemsPerPage: number
    onPageChange: (page: number) => void
  }
>(({ className, page, totalPages, totalItems, itemsPerPage, onPageChange, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center justify-between px-2 py-4", className)}
    {...props}
  >
    <div className="flex-1 text-sm text-muted-foreground">
      Showing {Math.min((page - 1) * itemsPerPage + 1, totalItems)} to{" "}
      {Math.min(page * itemsPerPage, totalItems)} of {totalItems} entries
    </div>
    <div className="flex items-center space-x-2">
      <button
        className="px-2 py-1 text-sm border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
      >
        Previous
      </button>
      <span className="text-sm">
        Page {page} of {totalPages}
      </span>
      <button
        className="px-2 py-1 text-sm border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
      >
        Next
      </button>
    </div>
  </div>
))
TablePagination.displayName = "TablePagination"

// Specialized table components
const SchemaTable = React.forwardRef<
  HTMLTableElement,
  React.HTMLAttributes<HTMLTableElement> & {
    columns: Array<{
      name: string
      type: string
      nullable: boolean
      isPrimaryKey?: boolean
      isForeignKey?: boolean
      privacyLevel?: string
    }>
  }
>(({ className, columns, ...props }, ref) => (
  <Table ref={ref} className={className} {...props}>
    <TableHeader>
      <TableRow>
        <TableHead>Column</TableHead>
        <TableHead>Type</TableHead>
        <TableHead>Nullable</TableHead>
        <TableHead>Keys</TableHead>
        <TableHead>Privacy</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      {columns.map((column, index) => (
        <TableRow key={index}>
          <TableCell className="font-medium">
            {column.name}
          </TableCell>
          <TableCell>
            <code className="px-2 py-1 bg-muted rounded text-xs">
              {column.type}
            </code>
          </TableCell>
          <TableCell>
            {column.nullable ? (
              <span className="text-green-600">✓</span>
            ) : (
              <span className="text-red-600">✗</span>
            )}
          </TableCell>
          <TableCell>
            <div className="flex gap-1">
              {column.isPrimaryKey && (
                <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 text-xs rounded">
                  PK
                </span>
              )}
              {column.isForeignKey && (
                <span className="px-1.5 py-0.5 bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300 text-xs rounded">
                  FK
                </span>
              )}
            </div>
          </TableCell>
          <TableCell>
            {column.privacyLevel && (
              <span className={cn(
                "px-2 py-1 text-xs rounded-full",
                column.privacyLevel === 'public' && "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
                column.privacyLevel === 'internal' && "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
                column.privacyLevel === 'confidential' && "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
                column.privacyLevel === 'restricted' && "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
              )}>
                {column.privacyLevel}
              </span>
            )}
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
))
SchemaTable.displayName = "SchemaTable"

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
  DataTable,
  TablePagination,
  SchemaTable,
}
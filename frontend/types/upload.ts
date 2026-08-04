import type { DataIngestionSummary } from "@/types/ingestion";

export type CellValue = string | number | boolean | null;

export interface ColumnProfile {
  name: string;
  inferred_type: string;
  non_null_count: number;
  null_count: number;
}

export interface ExcelParseResult {
  file_name: string;
  sheet_name: string;
  data_ingestion: DataIngestionSummary;
  row_count: number;
  column_count: number;
  columns: ColumnProfile[];
  preview: Array<Record<string, CellValue>>;
}

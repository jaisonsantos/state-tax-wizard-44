import type { AuditLogEntry, AuditLogResponse } from "./api";

type MaybeBtoa = (data: string) => string;

const base64UrlEncode = (input: string): string => {
  const globalScope = typeof globalThis !== "undefined" ? (globalThis as typeof globalThis & {
    btoa?: MaybeBtoa;
    Buffer?: { from(data: string, encoding: string): { toString(encoding: "base64"): string } };
  }) : undefined;

  const btoaFn = globalScope?.btoa;
  if (typeof btoaFn === "function") {
    return btoaFn(input).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  const bufferCtor = globalScope?.Buffer;
  if (bufferCtor) {
    return bufferCtor.from(input, "utf-8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  throw new Error("No base64 encoder available in this environment");
};

const buildCursorFromEntry = (entry: AuditLogEntry | undefined): string | null => {
  if (!entry || !entry.timestamp) {
    return null;
  }

  try {
    return base64UrlEncode(`${entry.timestamp}::${entry.id}`);
  } catch (error) {
    console.error("Failed to encode audit cursor", error);
    return null;
  }
};

export const resolveNextAuditCursor = (response: AuditLogResponse): string | null => {
  if (response.next_cursor) {
    return response.next_cursor;
  }

  if (!response.items.length) {
    return null;
  }

  const hasMoreByTotal =
    typeof response.total === "number" &&
    typeof response.page === "number" &&
    response.total > response.page * response.limit;

  const hasMoreByPageFill = response.items.length === response.limit;

  if (!hasMoreByTotal && !hasMoreByPageFill) {
    return null;
  }

  const lastEntry = response.items[response.items.length - 1];
  return buildCursorFromEntry(lastEntry);
};

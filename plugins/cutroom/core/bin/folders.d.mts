export const MARKER: string;

export interface LinkedFolder {
  path: string;
  videos: string;
}

export interface CutroomFolders {
  root: string;
  workspace: string | null;
  accountRoot: string;
  linked(): Record<string, LinkedFolder>;
  isLinked(slug: string): boolean;
  projectRoot(slug: string): string;
  videosRoot(slug: string): string;
  toLocal(rel: string): string;
  toCutroom(abs: string): string | null;
  link(slug: string, folder: string, videos?: string): void;
  unlink(slug: string): LinkedFolder | null;
  ensureFolder(slug: string, name?: string): string;
  exists(rel: string): boolean;
}

export function cutroomFolders(options?: {
  root?: string;
  workspace?: string | null;
}): CutroomFolders;

export function workspaceOf(options: {
  convexUrl: string | undefined;
  key: string | undefined;
}): Promise<string | null>;

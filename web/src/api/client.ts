import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const client = axios.create({
  baseURL: API_BASE_URL,
});

export interface Tool {
  id: string;
  title: string;
  description: string;
  icon: string;
  order: number;
}

export interface FileItem {
  name: string;
  path: string;
  is_dir: boolean;
  size: number | null;
  size_str: string | null;
  modified: number;
}

export interface FileConfig {
  shared_drives: string;
  drive_root: string;
  archive_exts: string[];
  game_exts: string[];
}

export const toolsApi = {
  list: () => client.get<Tool[]>('/tools').then(res => res.data),
};

export const filesApi = {
  list: (path: string) => client.get<FileItem[]>(`/files/list?path=${encodeURIComponent(path)}`).then(res => res.data),
  search: (root: string, type: 'archives' | 'games') => 
    client.get<string[]>(`/files/search?root=${encodeURIComponent(root)}&type=${type}`).then(res => res.data),
  getConfig: () => client.get<FileConfig>('/files/config').then(res => res.data),
};

export const extractApi = {
  start: (archivePath: string) => client.post<{ job_id: string }>('/extract', { archive_path: archivePath }).then(res => res.data),
};

export const verifyApi = {
  start: (files: string[]) => client.post<{ job_id: string }>('/verify', { files }).then(res => res.data),
};

export const compressApi = {
  start: (files: string[], verifyAfter: boolean, askConfirm: boolean) => 
    client.post<{ job_id: string }>('/compress', { files, verify_after: verifyAfter, ask_confirm: askConfirm }).then(res => res.data),
  confirm: (jobId: string, keep: boolean) => client.post(`/compress/${jobId}/confirm`, { keep }),
};

export const organizeApi = {
  start: (files: string[]) => client.post<{ job_id: string }>('/organize', { files }).then(res => res.data),
  confirm: (jobId: string, apply: boolean) => client.post(`/organize/${jobId}/confirm`, { apply }),
};

export default client;

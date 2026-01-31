const API_BASE_URL = '/api';

const request = async (url, options = {}) => {
    const response = await fetch(`${API_BASE_URL}${url}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || response.statusText);
    }
    
    return response.json();
};

export const toolsApi = {
    list: () => request('/tools'),
};

export const filesApi = {
    list: (path) => request(`/files/list?path=${encodeURIComponent(path)}`),
    search: (root, type) => request(`/files/search?root=${encodeURIComponent(root)}&type=${type}`),
    getConfig: () => request('/files/config'),
};

export const extractApi = {
    start: (archivePath) => request('/extract/', {
        method: 'POST',
        body: JSON.stringify({ archive_path: archivePath }),
    }),
};

export const verifyApi = {
    start: (files) => request('/verify/', {
        method: 'POST',
        body: JSON.stringify({ files }),
    }),
};

export const compressApi = {
    start: (files, verifyAfter, askConfirm) => request('/compress/', {
        method: 'POST',
        body: JSON.stringify({ files, verify_after: verifyAfter, ask_confirm: askConfirm }),
    }),
    confirm: (jobId, keep) => request(`/compress/${jobId}/confirm`, {
        method: 'POST',
        body: JSON.stringify({ keep }),
    }),
};

export const organizeApi = {
    start: (files) => request('/organize/', {
        method: 'POST',
        body: JSON.stringify({ files }),
    }),
    confirm: (jobId, apply) => request(`/organize/${jobId}/confirm`, {
        method: 'POST',
        body: JSON.stringify({ apply }),
    }),
};

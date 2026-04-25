import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

export const getHealth = () => api.get('/health')
export const getRoles = () => api.get('/roles')
export const getIndexStatus = () => api.get('/index-status')

export const sendChat = (query, role) =>
  api.post('/chat', { query, role })

export const getDocuments = () => api.get('/admin/documents')

export const uploadDocuments = (files) => {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  return api.post('/admin/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const deleteDocument = (filename) =>
  api.delete(`/admin/document/${encodeURIComponent(filename)}`)

export const rebuildIndex = () => api.post('/admin/rebuild')

export default api

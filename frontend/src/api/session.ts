import request from '@/request'

export const createSession = (data: {
  projectId: number
  title: string
  metaJson?: Record<string, unknown>
}) => request.post('/session/create', data)

export const getSession = (sessionId: number) => request.get(`/session/${sessionId}`)

export const listSessionMessages = (sessionId: number) => request.get(`/session/${sessionId}/messages`)

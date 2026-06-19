import request from '@/request'

export const listSkillDefinitions = () => request.get('/skill/definitions')

export const createSkillRun = (data: {
  sessionId: number
  skillId: string
  input: Record<string, unknown>
}) => request.post('/skill/run', data)

export const continueSkillRun = (
  runId: number,
  data: {
    action: string
    payload: Record<string, unknown>
  },
) => request.post(`/skill/run/${runId}/action`, data)

export const createSkillRunStream = (runId: number) => new EventSource(`/api/skill/run/${runId}/stream`, { withCredentials: true })

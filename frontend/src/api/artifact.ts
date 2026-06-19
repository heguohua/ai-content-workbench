import request from '@/request'

export const listArtifacts = (sessionId: number) => request.get(`/artifact/session/${sessionId}`)

export const updateArtifact = (
  artifactId: number,
  data: {
    title?: string
    contentJson: Record<string, unknown>
    metaJson?: Record<string, unknown>
  },
) => request.post(`/artifact/${artifactId}/update`, data)

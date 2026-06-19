import request from '@/request'

export interface ProjectItem {
  id: number
  projectKey: string
  name: string
  description?: string
  projectSkillId: string
  ownerUserId: number
  status: string
  configJson?: Record<string, unknown>
  createTime: string
  updateTime: string
}

export const createProject = (data: {
  name: string
  description?: string
  projectSkillId: string
  configJson?: Record<string, unknown>
}) => request.post('/project/create', data)

export const listProjects = (data: { current?: number; pageSize?: number }) =>
  request.post('/project/list', data)

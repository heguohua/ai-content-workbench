<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { createProject, listProjects, type ProjectItem } from '@/api/project'
import { createSession, listSessionMessages } from '@/api/session'
import { listArtifacts } from '@/api/artifact'
import { continueSkillRun, createSkillRun, createSkillRunStream } from '@/api/skill'
import { markdownToHtml } from '@/utils/markdown'

type TimelineMessage = {
  id: string
  role: 'user' | 'assistant' | 'status'
  kind: 'text' | 'card' | 'outline' | 'markdown' | 'article' | 'images' | 'stream'
  runId?: number
  text?: string
  data?: Record<string, any>
}

type ArtifactItem = {
  id: number
  artifactKey: string
  artifactType: string
  title: string
  contentJson: Record<string, any>
  version: number
}

const composer = ref('帮我写一篇 AI 出海 SaaS 的增长策略文章')
const projects = ref<ProjectItem[]>([])
const activeProjectId = ref<number>()
const activeSessionId = ref<number>()
const activeRunId = ref<number>()
const messages = ref<TimelineMessage[]>([])
const artifacts = ref<ArtifactItem[]>([])
const pendingOutlineSuggestion = ref('')
const selectedTitleIndex = ref<number | null>(null)
const isBooting = ref(true)
const bootError = ref('')
const isRunning = ref(false)

let eventSource: EventSource | null = null

const workspaceStorageKey = 'ai-content-workbench:last-workspace'

const currentProject = computed(() => projects.value.find((item) => item.id === activeProjectId.value))

const titleOptions = computed(() => {
  const artifact = artifacts.value.find((item) => item.artifactType === 'title-options')
  return artifact?.contentJson?.titleOptions ?? []
})

const selectedTitle = computed(() => titleOptions.value[selectedTitleIndex.value ?? 0])

const outlineSections = computed(() => {
  const artifact = artifacts.value.find((item) => item.artifactType === 'outline')
  return artifact?.contentJson?.outline ?? []
})

const markdownContent = computed(() => {
  const artifact = artifacts.value.find((item) => item.artifactType === 'markdown')
  return artifact?.contentJson?.fullContent || artifact?.contentJson?.markdown || ''
})

const imagePack = computed(() => {
  const artifact = artifacts.value.find((item) => item.artifactType === 'image-pack')
  return artifact?.contentJson?.images ?? []
})

const ensureDefaultProject = async () => {
  const listResp = await listProjects({ current: 1, pageSize: 20 })
  const records = listResp.data?.data?.records ?? []
  if (records.length > 0) {
    projects.value = records
    activeProjectId.value = records[0].id
    return
  }

  const createResp = await createProject({
    name: 'Article Studio',
    description: '对话式文章创作工作台',
    projectSkillId: 'project.article-studio',
    configJson: { theme: 'workspace' },
  })
  const created = createResp.data?.data
  if (created) {
    projects.value = [created]
    activeProjectId.value = created.id
  }
}

const refreshArtifacts = async () => {
  if (!activeSessionId.value) {
    artifacts.value = []
    return
  }
  const resp = await listArtifacts(activeSessionId.value)
  artifacts.value = resp.data?.data ?? []
}

const refreshMessages = async () => {
  if (!activeSessionId.value) {
    messages.value = []
    return
  }
  const resp = await listSessionMessages(activeSessionId.value)
  const rows = resp.data?.data ?? []
  messages.value = compactTimelineMessages(
    rows.map((row: any) => normalizeMessage(row)).filter(Boolean) as TimelineMessage[],
  )
}

const normalizeMessage = (row: any): TimelineMessage | null => {
  const data = row.contentJson || {}
  if (row.messageType === 'action') {
    return null
  }
  if (data.artifactType && !['markdown', 'image-pack'].includes(data.artifactType)) {
    return null
  }
  let kind: TimelineMessage['kind'] = row.messageType === 'card' ? 'card' : 'text'
  let id = row.messageKey
  if (row.messageType === 'delta') {
    kind = 'stream'
  }
  if (data.artifactType === 'outline') {
    kind = 'outline'
  }
  if (data.artifactType === 'markdown') {
    kind = 'article'
    id = `article_${row.runId || row.messageKey}`
  }
  if (data.artifactType === 'image-pack') {
    kind = data.fullContent ? 'article' : 'images'
    id = data.fullContent ? `article_${row.runId || row.messageKey}` : row.messageKey
  }
  return {
    id,
    runId: row.runId,
    role: row.role === 'assistant' ? 'assistant' : row.role === 'user' ? 'user' : 'status',
    kind,
    text: row.contentText,
    data,
  }
}

const compactTimelineMessages = (nextMessages: TimelineMessage[]) => {
  const result: TimelineMessage[] = []
  for (const next of nextMessages) {
    const index = result.findIndex((item) => item.id === next.id)
    if (index >= 0) {
      result[index] = {
        ...result[index],
        ...next,
        data: {
          ...(result[index].data || {}),
          ...(next.data || {}),
        },
      }
      continue
    }
    result.push(next)
  }

  const runsWithFinalArticle = new Set(
    result
      .filter((item) => item.kind === 'article' && item.data?.fullContent)
      .map((item) => item.runId || activeRunId.value),
  )
  return result.filter((item) => !(item.kind === 'images' && runsWithFinalArticle.has(item.runId || activeRunId.value)))
}

const restoreLastWorkspace = async () => {
  const raw = window.localStorage.getItem(workspaceStorageKey)
  if (!raw) {
    return
  }
  try {
    const parsed = JSON.parse(raw)
    if (!parsed.sessionId || !parsed.runId) {
      return
    }
    activeSessionId.value = parsed.sessionId
    activeRunId.value = parsed.runId
    await Promise.all([refreshArtifacts(), refreshMessages()])
    openRunStream(parsed.runId)
  } catch (error) {
    console.error(error)
    window.localStorage.removeItem(workspaceStorageKey)
  }
}

const appendStatusMessage = (text: string, data?: Record<string, any>) => {
  upsertTimelineMessage({
    id: `status_${activeRunId.value ?? 'pending'}_${data?.actionType || text}`,
    role: 'status',
    kind: data ? 'card' : 'text',
    text,
    data,
  })
}

const appendRichMessage = (
  kind: TimelineMessage['kind'],
  text: string,
  data?: Record<string, any>,
) => {
  upsertTimelineMessage({
    id: `artifact_${activeRunId.value ?? 'pending'}_${data?.artifactType || kind}`,
    role: 'assistant',
    kind,
    text,
    data,
  })
}

const upsertTimelineMessage = (next: TimelineMessage) => {
  if (next.kind === 'article' && next.data?.fullContent) {
    messages.value = messages.value.filter(
      (item) => !(item.kind === 'images' && (item.runId || activeRunId.value) === (next.runId || activeRunId.value)),
    )
  }
  const index = messages.value.findIndex((item) => item.id === next.id)
  if (index >= 0) {
    messages.value[index] = next
    return
  }
  messages.value.push(next)
}

const upsertArticleMessage = (text: string, data: Record<string, any>) => {
  upsertTimelineMessage({
    id: `article_${activeRunId.value ?? 'pending'}`,
    runId: activeRunId.value,
    role: 'assistant',
    kind: 'article',
    text,
    data,
  })
}

const appendStreamDelta = (target: string, text: string) => {
  if (!text) {
    return
  }
  const id = `stream_${activeRunId.value}_${target || 'stream'}`
  const existing = messages.value.find((item) => item.id === id)
  if (existing) {
    existing.text = `${existing.text || ''}${text}`
    existing.data = {
      ...(existing.data || {}),
      target,
      text: existing.text,
    }
    return
  }
  messages.value.push({
    id,
    role: 'assistant',
    kind: 'stream',
    text,
    data: { target, text },
  })
}

const mergeImages = (currentImages: any[] = [], nextImages: any[] = []) => {
  const imageMap = new Map<string, any>()
  for (const image of [...currentImages, ...nextImages]) {
    if (!image) {
      continue
    }
    const key = image.placeholderId || image.url || `${image.position || ''}_${image.keywords || ''}`
    imageMap.set(key, image)
  }
  return Array.from(imageMap.values()).sort((left, right) => (left.position || 0) - (right.position || 0))
}

const upsertImageMessage = (text: string, data: Record<string, any>) => {
  const id = `artifact_${activeRunId.value ?? 'pending'}_image-pack`
  const existing = messages.value.find((item) => item.id === id)
  const mergedImages = mergeImages(existing?.data?.images || [], data.images || [])
  const nextData = {
    ...(existing?.data || {}),
    ...data,
    images: mergedImages,
  }
  upsertTimelineMessage({
    id,
    runId: activeRunId.value,
    role: 'assistant',
    kind: 'images',
    text,
    data: nextData,
  })
}

const getImageUrl = (image: any) => image?.url || image?.imageUrl || image?.src || ''

const renderMarkdown = (markdown?: string) => markdownToHtml(markdown || '')

const openRunStream = (runId: number) => {
  if (eventSource) {
    eventSource.close()
  }
  eventSource = createSkillRunStream(runId)
  eventSource.onmessage = async (event) => {
    const payload = JSON.parse(event.data)
    const { type, data } = payload
    if (type === 'run.started') {
      appendStatusMessage('Article Studio 已启动')
    } else if (type === 'skill.call.started') {
      appendStatusMessage(`${data.skillId} 正在运行...`)
    } else if (type === 'run.waiting_input') {
      appendStatusMessage(data.message, data)
      await refreshArtifacts()
    } else if (type === 'artifact.updated') {
      if (data.artifactType === 'markdown') {
        upsertArticleMessage(data.message || '正文已生成', data)
      } else if (data.artifactType === 'image-pack') {
        if (data.fullContent) {
          upsertArticleMessage(data.message || '图文文章已生成', data)
        } else {
          upsertImageMessage(data.message || '配图已生成', data)
        }
      }
      await refreshArtifacts()
    } else if (type === 'message.delta') {
      appendStreamDelta(data.target || 'stream', data.text || '')
    } else if (type === 'run.completed') {
      appendStatusMessage('文章生成完成')
      await Promise.all([refreshArtifacts(), refreshMessages()])
      eventSource?.close()
      eventSource = null
    } else if (type === 'run.failed') {
      appendStatusMessage(data.message || '运行失败')
      await Promise.all([refreshArtifacts(), refreshMessages()])
      eventSource?.close()
      eventSource = null
    }
  }
  eventSource.onerror = () => {
    console.warn('Skill run stream closed or interrupted')
  }
}

const startArticleStudio = async () => {
  if (!composer.value.trim()) {
    message.warning('请输入创作需求')
    return
  }
  if (isRunning.value) {
    return
  }
  isRunning.value = true
  if (!activeProjectId.value) {
    await ensureDefaultProject()
  }
  if (!activeProjectId.value) {
    message.error('项目创建失败')
    isRunning.value = false
    return
  }

  try {
    const topic = composer.value.trim()
    const sessionResp = await createSession({
      projectId: activeProjectId.value,
      title: topic,
      metaJson: { source: 'workspace' },
    })
    const session = sessionResp.data?.data
    activeSessionId.value = session?.id
    activeRunId.value = undefined
    selectedTitleIndex.value = null
    artifacts.value = []
    messages.value = [
      {
        id: `user_${Date.now()}`,
        role: 'user',
        kind: 'text',
        text: topic,
      },
    ]

    const runResp = await createSkillRun({
      sessionId: session.id,
      skillId: 'project.article-studio',
      input: {
        topic,
        style: 'tech',
        enabledImageMethods: ['PEXELS', 'MERMAID', 'ICONIFY'],
      },
    })
    const run = runResp.data?.data
    activeRunId.value = run?.id
    activeSessionId.value = run?.sessionId || session.id
    window.localStorage.setItem(
      workspaceStorageKey,
      JSON.stringify({
        sessionId: activeSessionId.value,
        runId: activeRunId.value,
      }),
    )
    composer.value = ''
    openRunStream(run.id)
    await Promise.all([refreshArtifacts(), refreshMessages()])
  } catch (error) {
    console.error(error)
    message.error('启动 Article Studio 失败，请查看后端日志')
  } finally {
    isRunning.value = false
  }
}

const handleSelectTitle = async (option: any, index: number) => {
  if (!activeRunId.value) {
    return
  }
  openRunStream(activeRunId.value)
  selectedTitleIndex.value = index
  await continueSkillRun(activeRunId.value, {
    action: 'select_title',
    payload: {
      selectedMainTitle: option.mainTitle,
      selectedSubTitle: option.subTitle,
      userDescription: '偏创始人和增长负责人的决策视角',
      style: 'tech',
    },
  })
  await Promise.all([refreshArtifacts(), refreshMessages()])
}

const handleModifyOutline = async () => {
  if (!activeRunId.value || !pendingOutlineSuggestion.value.trim()) {
    return
  }
  openRunStream(activeRunId.value)
  await continueSkillRun(activeRunId.value, {
    action: 'modify_outline',
    payload: {
      modifySuggestion: pendingOutlineSuggestion.value.trim(),
      outline: outlineSections.value,
      selectedMainTitle: selectedTitle.value?.mainTitle || '文章标题',
      selectedSubTitle: selectedTitle.value?.subTitle || '',
    },
  })
  pendingOutlineSuggestion.value = ''
  await Promise.all([refreshArtifacts(), refreshMessages()])
}

const handleConfirmOutline = async () => {
  if (!activeRunId.value) {
    return
  }
  openRunStream(activeRunId.value)
  await continueSkillRun(activeRunId.value, {
    action: 'confirm_outline',
    payload: {
      selectedMainTitle: selectedTitle.value?.mainTitle || '文章标题',
      selectedSubTitle: selectedTitle.value?.subTitle || '',
      outline: outlineSections.value,
      style: 'tech',
      enabledImageMethods: ['PEXELS', 'MERMAID', 'ICONIFY'],
    },
  })
  await Promise.all([refreshArtifacts(), refreshMessages()])
}

onMounted(async () => {
  try {
    await ensureDefaultProject()
    await restoreLastWorkspace()
  } catch (error) {
    console.error(error)
    bootError.value = '工作台初始化失败，请确认已登录、后端已启动，并已执行 skill runtime 数据库脚本。'
  } finally {
    isBooting.value = false
  }
})

onBeforeUnmount(() => {
  if (eventSource) {
    eventSource.close()
  }
})
</script>

<template>
  <div class="workspace-page">
    <aside class="workspace-sidebar">
      <div class="brand-block">
        <div class="brand-badge">AI</div>
        <div>
          <div class="brand-title">Content Workspace</div>
          <div class="brand-subtitle">Skill-driven studio</div>
        </div>
      </div>

      <div class="sidebar-section">
        <div class="section-label">Projects</div>
        <button
          v-for="project in projects"
          :key="project.id"
          class="sidebar-item"
          :class="{ active: project.id === activeProjectId }"
          @click="activeProjectId = project.id"
        >
          <span>{{ project.name }}</span>
          <small>{{ project.projectSkillId }}</small>
        </button>
      </div>

      <div class="sidebar-section">
        <div class="section-label">Session</div>
        <div class="session-card">
          <div class="session-title">{{ currentProject?.name || 'Article Studio' }}</div>
          <div class="session-meta">{{ activeSessionId ? `sess_${activeSessionId}` : '尚未开始' }}</div>
        </div>
      </div>
    </aside>

    <main class="workspace-main">
      <header class="workspace-header">
        <div>
          <h1>{{ currentProject?.name || 'Article Studio' }}</h1>
          <p>project.article-studio · 对话式内容工作台</p>
        </div>
      </header>

      <section class="timeline">
        <div v-if="isBooting" class="workspace-state">正在初始化工作台...</div>
        <div v-else-if="bootError" class="workspace-state error">{{ bootError }}</div>
        <div v-else-if="messages.length === 0" class="workspace-state">
          输入一个内容目标，Article Studio 会把标题、大纲和正文组织成一条可确认的创作流程。
        </div>

        <article
          v-for="item in messages"
          :key="item.id"
          class="message-bubble"
          :class="[item.role, item.kind === 'card' ? 'card' : '']"
        >
          <template v-if="item.kind === 'card' && item.data?.actionType === 'select_title'">
            <div class="message-label">标题候选</div>
            <div class="title-option-list">
              <button
                v-for="(option, index) in item.data.titleOptions || []"
                :key="`${option.mainTitle}-${index}`"
                class="title-option"
                :class="{ selected: selectedTitleIndex === index }"
                @click="handleSelectTitle(option, index)"
              >
                <strong>{{ option.mainTitle }}</strong>
                <span>{{ option.subTitle }}</span>
              </button>
            </div>
          </template>

          <template v-else-if="item.kind === 'card' && item.data?.actionType === 'confirm_outline'">
            <div class="message-label">大纲确认</div>
            <p class="message-text">{{ item.text }}</p>
            <div class="outline-preview">
              <div v-for="section in item.data.outline || outlineSections" :key="section.section" class="outline-section">
                <strong>{{ section.section }}. {{ section.title }}</strong>
                <ul>
                  <li v-for="(point, idx) in section.points" :key="idx">{{ point }}</li>
                </ul>
              </div>
            </div>
            <div class="outline-actions">
              <a-input
                v-model:value="pendingOutlineSuggestion"
                placeholder="比如：增加出海团队组织案例"
                class="outline-input"
              />
              <div class="outline-buttons">
                <a-button @click="handleModifyOutline">AI 修改大纲</a-button>
                <a-button type="primary" @click="handleConfirmOutline">确认大纲并生成正文</a-button>
              </div>
            </div>
          </template>

          <template v-else>
            <div v-if="item.kind === 'outline'" class="message-label">Outline</div>
            <div v-if="item.kind === 'outline'" class="outline-preview">
              <div v-for="section in item.data?.outline || []" :key="section.section" class="outline-section">
                <strong>{{ section.section }}. {{ section.title }}</strong>
                <ul>
                  <li v-for="(point, idx) in section.points" :key="idx">{{ point }}</li>
                </ul>
              </div>
            </div>

            <template v-else-if="item.kind === 'markdown'">
              <div class="message-label">Markdown</div>
              <pre class="markdown-message">{{ item.data?.markdown || markdownContent }}</pre>
            </template>

            <template v-else-if="item.kind === 'article'">
              <div class="message-label">{{ item.data?.fullContent ? 'Article With Images' : 'Article Draft' }}</div>
              <div
                class="article-message"
                v-html="renderMarkdown(item.data?.fullContent || item.data?.markdown || markdownContent)"
              ></div>
            </template>

            <template v-else-if="item.kind === 'images'">
              <div class="message-label">Images · 生成进度</div>
              <div class="image-grid">
                <figure
                  v-for="image in item.data?.images || imagePack"
                  :key="image.placeholderId || getImageUrl(image)"
                >
                  <img :src="getImageUrl(image)" :alt="image.description || image.keywords" />
                  <figcaption>{{ image.description || image.keywords }}</figcaption>
                </figure>
                <div v-if="!(item.data?.images || imagePack).length" class="image-pending">
                  正在生成配图，完成后会直接出现在这里。
                </div>
              </div>
            </template>

            <template v-else-if="item.kind === 'stream'">
              <div class="message-label">Streaming</div>
              <p class="message-text streaming-text">{{ item.text }}</p>
            </template>

            <template v-else>
            <div v-if="item.role !== 'user'" class="message-label">
              {{ item.role === 'assistant' ? 'Assistant' : 'Status' }}
            </div>
            <p class="message-text">{{ item.text }}</p>
            </template>
          </template>
        </article>
      </section>

      <footer class="composer-shell">
        <div class="composer-panel">
          <a-textarea
            v-model:value="composer"
            :rows="3"
            placeholder="描述你的内容目标，系统会通过 project.article-studio 自动编排标题、大纲和正文。"
          />
          <div class="composer-actions">
            <span class="composer-hint">输入一段需求，开始一条新的创作会话</span>
            <a-button type="primary" size="large" :loading="isRunning" @click="startArticleStudio">
              启动 Article Studio
            </a-button>
          </div>
        </div>
      </footer>
    </main>

  </div>
</template>

<style scoped>
.workspace-page {
  --workspace-bg: #f7f3eb;
  --workspace-panel: rgba(255, 255, 255, 0.78);
  --workspace-panel-strong: #fffdfa;
  --workspace-text: #262119;
  --workspace-muted: #786e63;
  --workspace-line: rgba(38, 33, 25, 0.08);
  --workspace-accent: #c96e4d;
  --workspace-accent-soft: rgba(201, 110, 77, 0.12);

  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  min-height: 100vh;
  background:
    linear-gradient(135deg, rgba(201, 110, 77, 0.08), transparent 26%),
    linear-gradient(180deg, #fcfaf6 0%, var(--workspace-bg) 100%);
  color: var(--workspace-text);
}

.workspace-sidebar {
  padding: 20px 16px;
  background: var(--workspace-panel);
  backdrop-filter: blur(18px);
}

.workspace-sidebar {
  border-right: 1px solid var(--workspace-line);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 28px;
}

.brand-badge {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-weight: 700;
  color: white;
  background: linear-gradient(135deg, #d58461 0%, #b85a3d 100%);
  box-shadow: 0 18px 30px rgba(201, 110, 77, 0.25);
}

.brand-title {
  font-family: 'Outfit', sans-serif;
  font-size: 18px;
  font-weight: 600;
}

.brand-subtitle,
.session-meta,
.workspace-header p,
.artifact-header span {
  color: var(--workspace-muted);
}

.sidebar-section + .sidebar-section {
  margin-top: 26px;
}

.section-label {
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--workspace-muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.sidebar-item,
.session-card {
  width: 100%;
  padding: 14px;
  border: 1px solid transparent;
  border-radius: 18px;
  background: transparent;
  text-align: left;
}

.sidebar-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
}

.sidebar-item small {
  color: var(--workspace-muted);
}

.sidebar-item.active,
.sidebar-item:hover,
.session-card {
  background: var(--workspace-panel-strong);
  border-color: var(--workspace-line);
  box-shadow: 0 10px 30px rgba(38, 33, 25, 0.04);
}

.workspace-main {
  display: grid;
  grid-template-rows: auto 1fr auto;
  min-width: 0;
}

.workspace-header {
  padding: 30px 34px 16px;
}

.workspace-header h1,
.artifact-header h2 {
  margin: 0;
  font-family: 'Outfit', sans-serif;
}

.timeline {
  max-width: 980px;
  width: 100%;
  margin: 0 auto;
  padding: 10px 24px 140px;
}

.message-bubble {
  margin-bottom: 14px;
  padding: 16px 18px;
  border-radius: 22px;
  background: var(--workspace-panel-strong);
  border: 1px solid var(--workspace-line);
  box-shadow: 0 12px 32px rgba(38, 33, 25, 0.05);
}

.workspace-state {
  margin: 80px auto;
  max-width: 560px;
  padding: 18px 20px;
  border: 1px dashed var(--workspace-line);
  border-radius: 18px;
  color: var(--workspace-muted);
  background: rgba(255, 255, 255, 0.52);
  text-align: center;
}

.workspace-state.error {
  color: #9f3a2f;
  border-color: rgba(159, 58, 47, 0.22);
  background: rgba(255, 244, 241, 0.75);
}

.message-bubble.user {
  margin-left: 92px;
  background: #efe5da;
}

.message-bubble.assistant,
.message-bubble.status,
.message-bubble.card {
  margin-right: 84px;
}

.message-bubble.status {
  background: rgba(255, 253, 250, 0.6);
  border-style: dashed;
}

.message-label {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--workspace-muted);
}

.message-text {
  margin: 0;
  line-height: 1.7;
  white-space: pre-wrap;
}

.title-option-list {
  display: grid;
  gap: 10px;
}

.title-option {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  padding: 14px;
  border: 1px solid var(--workspace-line);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.title-option.selected,
.title-option:hover {
  border-color: rgba(201, 110, 77, 0.35);
  background: var(--workspace-accent-soft);
}

.outline-actions {
  display: grid;
  gap: 12px;
  margin-top: 14px;
}

.outline-buttons {
  display: flex;
  gap: 10px;
}

.composer-shell {
  position: sticky;
  bottom: 0;
  padding: 0 24px 24px;
}

.composer-panel {
  max-width: 900px;
  margin: 0 auto;
  padding: 16px;
  border: 1px solid var(--workspace-line);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  box-shadow: 0 24px 48px rgba(38, 33, 25, 0.1);
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  gap: 16px;
}

.composer-hint {
  color: var(--workspace-muted);
  font-size: 13px;
}

.outline-preview,
.markdown-message,
.article-message,
.image-grid {
  margin-top: 12px;
}

.outline-preview {
  padding: 16px;
  border: 1px solid var(--workspace-line);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.7);
}

.markdown-message {
  max-height: 620px;
  overflow: auto;
  padding: 16px;
  border: 1px solid var(--workspace-line);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
}

.article-message {
  padding: 22px;
  border: 1px solid var(--workspace-line);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.76);
  color: var(--workspace-text);
  line-height: 1.85;
  font-size: 15px;
}

.article-message :deep(h1),
.article-message :deep(h2),
.article-message :deep(h3) {
  margin: 26px 0 14px;
  color: var(--workspace-text);
  font-family: 'Outfit', sans-serif;
  line-height: 1.35;
}

.article-message :deep(h1:first-child),
.article-message :deep(h2:first-child),
.article-message :deep(h3:first-child) {
  margin-top: 0;
}

.article-message :deep(h1) {
  font-size: 28px;
}

.article-message :deep(h2) {
  padding-bottom: 10px;
  border-bottom: 1px solid var(--workspace-line);
  font-size: 22px;
}

.article-message :deep(h3) {
  font-size: 18px;
}

.article-message :deep(p) {
  margin: 0 0 16px;
}

.article-message :deep(img) {
  display: block;
  width: min(100%, 760px);
  max-height: 460px;
  margin: 22px auto 10px;
  border-radius: 18px;
  object-fit: cover;
  box-shadow: 0 22px 48px rgba(38, 33, 25, 0.16);
}

.article-message :deep(img[src*='iconify.design']) {
  display: inline-block;
  width: 56px;
  height: 56px;
  margin: 10px 10px 10px 0;
  vertical-align: middle;
  border-radius: 14px;
  object-fit: contain;
  box-shadow: none;
}

.article-message :deep(p:has(img)) {
  margin: 24px 0;
  text-align: center;
}

.article-message :deep(p:has(img[src*='iconify.design'])) {
  text-align: left;
}

.article-message :deep(ul),
.article-message :deep(ol) {
  margin: 0 0 16px;
  padding-left: 24px;
}

.article-message :deep(blockquote) {
  margin: 18px 0;
  padding: 12px 16px;
  border-left: 4px solid var(--workspace-accent);
  border-radius: 12px;
  background: var(--workspace-accent-soft);
  color: var(--workspace-muted);
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

.image-grid figure {
  margin: 0;
  border: 1px solid var(--workspace-line);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
  overflow: hidden;
}

.image-grid img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
}

.image-grid figcaption {
  padding: 10px 12px;
  color: var(--workspace-muted);
  font-size: 13px;
  line-height: 1.5;
}

.outline-section + .outline-section {
  margin-top: 18px;
}

.outline-section ul {
  margin: 8px 0 0;
  padding-left: 18px;
}

.streaming-text::after {
  content: '|';
  display: inline-block;
  margin-left: 2px;
  color: var(--workspace-accent);
  animation: cursor-blink 1s steps(1) infinite;
}

@keyframes cursor-blink {
  50% {
    opacity: 0;
  }
}

@media (max-width: 1200px) {
  .workspace-page {
    grid-template-columns: 240px minmax(0, 1fr);
  }
}

@media (max-width: 1024px) {
  .workspace-page {
    grid-template-columns: 1fr;
  }

  .workspace-sidebar {
    display: none;
  }

  .timeline,
  .composer-panel {
    max-width: 100%;
  }

  .message-bubble.user,
  .message-bubble.assistant,
  .message-bubble.status,
  .message-bubble.card {
    margin-left: 0;
    margin-right: 0;
  }

  .composer-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

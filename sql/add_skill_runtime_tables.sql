-- Skill Runtime 平台层表
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

USE ai_passage_creator;

CREATE TABLE IF NOT EXISTS project (
    id              bigint auto_increment comment 'id' primary key,
    projectKey      varchar(64)                         not null comment '项目唯一键',
    name            varchar(128)                        not null comment '项目名称',
    description     varchar(512)                        null comment '项目描述',
    projectSkillId  varchar(128)                        not null comment '项目 Skill ID',
    ownerUserId     bigint                              not null comment '所属用户 ID',
    status          varchar(32) default 'ACTIVE'        not null comment '状态',
    configJson      json                                null comment '项目配置 JSON',
    createTime      datetime    default CURRENT_TIMESTAMP not null comment '创建时间',
    updateTime      datetime    default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP comment '更新时间',
    isDelete        tinyint     default 0               not null comment '是否删除',
    UNIQUE KEY uk_projectKey (projectKey),
    INDEX idx_ownerUserId (ownerUserId),
    INDEX idx_projectSkillId (projectSkillId),
    INDEX idx_status (status)
) comment 'AI 项目表' collate = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_session (
    id              bigint auto_increment comment 'id' primary key,
    sessionKey      varchar(64)                         not null comment '会话唯一键',
    projectId       bigint                              not null comment '所属项目 ID',
    title           varchar(256)                        not null comment '会话标题',
    status          varchar(32) default 'ACTIVE'        not null comment '状态',
    lastMessageAt   datetime                            null comment '最后消息时间',
    metaJson        json                                null comment '附加信息 JSON',
    createTime      datetime    default CURRENT_TIMESTAMP not null comment '创建时间',
    updateTime      datetime    default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP comment '更新时间',
    isDelete        tinyint     default 0               not null comment '是否删除',
    UNIQUE KEY uk_sessionKey (sessionKey),
    INDEX idx_projectId (projectId),
    INDEX idx_lastMessageAt (lastMessageAt),
    INDEX idx_status (status)
) comment '聊天会话表' collate = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_message (
    id              bigint auto_increment comment 'id' primary key,
    messageKey      varchar(64)                         not null comment '消息唯一键',
    sessionId       bigint                              not null comment '所属会话 ID',
    runId           bigint                              null comment '关联运行 ID',
    role            varchar(32)                         not null comment '消息角色',
    messageType     varchar(32)                         not null comment '消息类型',
    contentText     longtext                            null comment '文本内容',
    contentJson     json                                null comment '结构化内容 JSON',
    status          varchar(32) default 'COMPLETED'     not null comment '消息状态',
    createTime      datetime    default CURRENT_TIMESTAMP not null comment '创建时间',
    updateTime      datetime    default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP comment '更新时间',
    isDelete        tinyint     default 0               not null comment '是否删除',
    UNIQUE KEY uk_messageKey (messageKey),
    INDEX idx_sessionId (sessionId),
    INDEX idx_runId (runId),
    INDEX idx_role (role),
    INDEX idx_messageType (messageType)
) comment '聊天消息表' collate = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS skill_run (
    id              bigint auto_increment comment 'id' primary key,
    runKey          varchar(64)                         not null comment '运行唯一键',
    sessionId       bigint                              not null comment '所属会话 ID',
    parentRunId     bigint                              null comment '父运行 ID',
    skillId         varchar(128)                        not null comment 'Skill ID',
    skillKind       varchar(32)                         not null comment 'Skill 类型',
    status          varchar(32)                         not null comment '运行状态',
    inputJson       json                                not null comment '输入 JSON',
    outputJson      json                                null comment '输出 JSON',
    contextJson     json                                null comment '上下文 JSON',
    errorMessage    text                                null comment '错误信息',
    startedAt       datetime                            null comment '开始时间',
    completedAt     datetime                            null comment '完成时间',
    createTime      datetime    default CURRENT_TIMESTAMP not null comment '创建时间',
    updateTime      datetime    default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP comment '更新时间',
    isDelete        tinyint     default 0               not null comment '是否删除',
    UNIQUE KEY uk_runKey (runKey),
    INDEX idx_sessionId (sessionId),
    INDEX idx_parentRunId (parentRunId),
    INDEX idx_skillId (skillId),
    INDEX idx_status (status)
) comment 'Skill 运行表' collate = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS skill_run_event (
    id              bigint auto_increment comment 'id' primary key,
    eventKey        varchar(64)                         not null comment '事件唯一键',
    runId           bigint                              not null comment '所属运行 ID',
    eventType       varchar(64)                         not null comment '事件类型',
    seqNo           int                                 not null comment '事件序号',
    payloadJson     json                                null comment '事件载荷 JSON',
    createTime      datetime    default CURRENT_TIMESTAMP not null comment '创建时间',
    isDelete        tinyint     default 0               not null comment '是否删除',
    UNIQUE KEY uk_eventKey (eventKey),
    UNIQUE KEY uk_runId_seqNo (runId, seqNo),
    INDEX idx_runId (runId),
    INDEX idx_eventType (eventType)
) comment 'Skill 运行事件表' collate = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS artifact (
    id              bigint auto_increment comment 'id' primary key,
    artifactKey     varchar(64)                         not null comment '产物唯一键',
    sessionId       bigint                              not null comment '所属会话 ID',
    sourceRunId     bigint                              null comment '来源运行 ID',
    artifactType    varchar(64)                         not null comment '产物类型',
    title           varchar(256)                        not null comment '产物标题',
    version         int         default 1               not null comment '版本号',
    status          varchar(32) default 'ACTIVE'        not null comment '状态',
    contentJson     json                                not null comment '产物内容 JSON',
    metaJson        json                                null comment '元数据 JSON',
    createTime      datetime    default CURRENT_TIMESTAMP not null comment '创建时间',
    updateTime      datetime    default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP comment '更新时间',
    isDelete        tinyint     default 0               not null comment '是否删除',
    UNIQUE KEY uk_artifactKey (artifactKey),
    INDEX idx_sessionId (sessionId),
    INDEX idx_sourceRunId (sourceRunId),
    INDEX idx_artifactType (artifactType)
) comment '产物表' collate = utf8mb4_unicode_ci;

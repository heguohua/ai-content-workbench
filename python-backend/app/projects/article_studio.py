"""Article Studio 项目级 Skill"""

from typing import Any, AsyncGenerator

from app.runtime.schemas import SkillDefinition, SkillEvent
from app.skills.base import BaseSkill


class ArticleStudioSkill(BaseSkill):
    """文章创作项目级 Skill"""

    definition = SkillDefinition(
        id="project.article-studio",
        kind="project",
        name="Article Studio",
        version="0.1.0",
        description="文章创作项目级 Skill，负责标题、大纲、正文、配图全流程编排。",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "style": {"type": "string", "enum": ["tech", "emotional", "educational", "humorous"]},
                "enabledImageMethods": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["topic"],
        },
        outputSchema={
            "type": "object",
            "properties": {"taskId": {"type": "string"}, "status": {"type": "string"}},
            "required": ["taskId", "status"],
        },
        artifactTypes=["article.meta", "title-options", "outline", "markdown", "image-pack"],
        interruptible=True,
        streamable=True,
        tags=["article", "project"],
    )

    async def run(
        self,
        ctx,
        input_data: dict[str, Any],
    ) -> AsyncGenerator[SkillEvent, None]:
        topic = input_data["topic"]
        style = input_data.get("style")
        enabled_image_methods = input_data.get("enabledImageMethods")

        yield ctx.event("run.started", {"topic": topic})

        meta_artifact = await ctx.artifacts.upsert(
            artifact_type="article.meta",
            title="文章任务信息",
            content={
                "topic": topic,
                "style": style,
                "enabledImageMethods": enabled_image_methods,
                "phase": "GENERATING_TITLES",
            },
        )
        yield ctx.event("artifact.updated", {"artifactId": meta_artifact["artifactKey"], "artifactType": "article.meta"})

        yield ctx.event("skill.call.started", {"skillId": "article.generate_titles"})
        title_result = await ctx.call_skill(
            "article.generate_titles",
            {
                "topic": topic,
                "style": style,
                "enabledImageMethods": enabled_image_methods,
            },
        )
        yield ctx.event("skill.call.completed", {"skillId": "article.generate_titles"})

        await ctx.artifacts.upsert(
            artifact_type="title-options",
            title="标题候选",
            content=title_result,
        )
        yield ctx.event("artifact.updated", {"artifactType": "title-options"})
        yield ctx.event(
            "run.waiting_input",
            {
                "actionType": "select_title",
                "message": "请选择一个标题方案",
                "titleOptions": title_result.get("titleOptions", []),
            },
        )

    async def resume(
        self,
        ctx,
        action: str,
        payload: dict[str, Any],
    ) -> AsyncGenerator[SkillEvent, None]:
        if action == "select_title":
            yield ctx.event("skill.call.started", {"skillId": "article.generate_outline"})
            outline_result = await ctx.call_skill(
                "article.generate_outline",
                {
                    "selectedMainTitle": payload["selectedMainTitle"],
                    "selectedSubTitle": payload["selectedSubTitle"],
                    "userDescription": payload.get("userDescription"),
                    "style": payload.get("style"),
                },
            )
            yield ctx.event("skill.call.completed", {"skillId": "article.generate_outline"})
            await ctx.artifacts.upsert(
                artifact_type="outline",
                title="文章大纲",
                content=outline_result,
            )
            yield ctx.event(
                "artifact.updated",
                {
                    "artifactType": "outline",
                    "message": "文章大纲已生成",
                    "outline": outline_result.get("outline", []),
                },
            )
            yield ctx.event(
                "run.waiting_input",
                {
                    "actionType": "confirm_outline",
                    "message": "请确认或编辑大纲",
                    "outline": outline_result.get("outline", []),
                },
            )
            return

        if action == "modify_outline":
            modified_outline = await ctx.call_skill(
                "article.modify_outline",
                {
                    "modifySuggestion": payload["modifySuggestion"],
                    "outline": payload.get("outline", []),
                    "selectedMainTitle": payload.get("selectedMainTitle", "文章标题"),
                    "selectedSubTitle": payload.get("selectedSubTitle", ""),
                },
            )
            await ctx.artifacts.upsert(
                artifact_type="outline",
                title="文章大纲",
                content=modified_outline,
            )
            yield ctx.event(
                "artifact.updated",
                {
                    "artifactType": "outline",
                    "message": "文章大纲已更新",
                    "outline": modified_outline.get("outline", []),
                },
            )
            yield ctx.event(
                "run.waiting_input",
                {
                    "actionType": "confirm_outline",
                    "message": "大纲已根据建议更新，请确认",
                    "outline": modified_outline.get("outline", []),
                },
            )
            return

        if action == "confirm_outline":
            yield ctx.event("skill.call.started", {"skillId": "article.generate_content"})
            yield ctx.event("message.delta", {"target": "markdown", "text": "正在生成正文...\n"})
            content_result = await ctx.call_skill(
                "article.generate_content",
                {
                    "selectedMainTitle": payload.get("selectedMainTitle", "文章标题"),
                    "selectedSubTitle": payload.get("selectedSubTitle", ""),
                    "outline": payload["outline"],
                    "style": payload.get("style"),
                },
            )
            yield ctx.event("skill.call.completed", {"skillId": "article.generate_content"})
            await ctx.artifacts.upsert(
                artifact_type="markdown",
                title="文章正文",
                content=content_result,
            )
            yield ctx.event(
                "artifact.updated",
                {
                    "artifactType": "markdown",
                    "message": "正文已生成",
                    "markdown": content_result.get("markdown", ""),
                },
            )

            yield ctx.event("skill.call.started", {"skillId": "article.generate_images"})
            image_result = await ctx.call_skill(
                "article.generate_images",
                {
                    "selectedMainTitle": payload.get("selectedMainTitle", "文章标题"),
                    "selectedSubTitle": payload.get("selectedSubTitle", ""),
                    "outline": payload["outline"],
                    "style": payload.get("style"),
                    "enabledImageMethods": payload.get("enabledImageMethods"),
                    "markdown": content_result.get("markdown", ""),
                },
            )
            yield ctx.event("skill.call.completed", {"skillId": "article.generate_images"})
            await ctx.artifacts.upsert(
                artifact_type="image-pack",
                title="文章配图",
                content=image_result,
            )
            yield ctx.event(
                "artifact.updated",
                {
                    "artifactType": "image-pack",
                    "message": "配图已生成",
                    "images": image_result.get("images", []),
                    "fullContent": image_result.get("fullContent", content_result.get("markdown", "")),
                },
            )
            yield ctx.event(
                "run.completed",
                {
                    "status": "COMPLETED",
                    "output": {
                        **content_result,
                        **image_result,
                    },
                },
            )
            return

        yield ctx.event("run.failed", {"message": f"不支持的动作: {action}"})

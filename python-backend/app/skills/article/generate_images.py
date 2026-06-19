"""生成配图 Skill"""

import json

from app.models.enums import ImageMethodEnum, SseMessageTypeEnum
from app.runtime.schemas import SkillDefinition
from app.schemas.article import ArticleState, ImageRequirement, OutlineResult, OutlineSection, TitleResult
from app.services.article_agent_service import ArticleAgentService
from app.skills.base import AtomicSkill


class ArticleGenerateImagesSkill(AtomicSkill):
    """生成配图原子 Skill"""

    definition = SkillDefinition(
        id="article.generate_images",
        kind="atomic",
        name="Generate Images",
        version="0.1.0",
        description="分析配图需求、生成图片并合成图文内容",
        inputSchema={"type": "object", "properties": {"markdown": {"type": "string"}}},
        outputSchema={"type": "object", "properties": {"images": {"type": "array"}, "fullContent": {"type": "string"}}},
        tags=["article", "image"],
    )

    async def execute(self, ctx, input_data: dict) -> dict:
        state = ArticleState()
        state.task_id = f"skill_run_{ctx.run_id}"
        state.style = input_data.get("style")
        state.enabled_image_methods = input_data.get("enabledImageMethods")
        state.title = TitleResult(
            mainTitle=input_data.get("selectedMainTitle", "文章标题"),
            subTitle=input_data.get("selectedSubTitle", ""),
        )
        state.outline = OutlineResult(
            sections=[OutlineSection(**item) for item in input_data.get("outline", [])]
        )
        state.content = input_data.get("markdown") or ""

        service = ArticleAgentService()
        await ctx.emit("message.delta", {"target": "image", "text": "\n正在分析文章配图需求...\n"})
        await service.agent4_analyze_image_requirements(state)
        if not state.image_requirements:
            state.image_requirements = [
                ImageRequirement(
                    position=1,
                    type="文章封面",
                    sectionTitle=state.title.main_title,
                    keywords=state.title.main_title,
                    imageSource=ImageMethodEnum.PICSUM.value,
                    prompt=f"为《{state.title.main_title}》生成一张现代、清晰、有科技感的文章封面图",
                    placeholderId="image_1",
                )
            ]
        await ctx.emit(
            "message.delta",
            {
                "target": "image",
                "text": f"已规划 {len(state.image_requirements or [])} 张配图，正在生成图片...\n",
            },
        )

        def handle_stream(message: str):
            image_complete_prefix = SseMessageTypeEnum.IMAGE_COMPLETE.get_streaming_prefix()
            if message.startswith(image_complete_prefix):
                image_json = message[len(image_complete_prefix):]
                try:
                    image = json.loads(image_json)
                except json.JSONDecodeError:
                    return
                ctx.emit_nowait(
                    "artifact.updated",
                    {
                        "artifactType": "image-pack",
                        "message": "一张配图已生成",
                        "images": [image],
                    },
                )

        await service.agent5_generate_images(state, handle_stream)
        await ctx.flush_events()
        service.merge_images_into_content(state)
        return {
            "images": [item.model_dump(by_alias=True) for item in (state.images or [])],
            "fullContent": state.full_content or state.content or "",
        }

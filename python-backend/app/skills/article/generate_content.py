"""生成正文 Skill"""

from app.runtime.schemas import SkillDefinition
from app.models.enums import SseMessageTypeEnum
from app.schemas.article import ArticleState, OutlineResult, OutlineSection, TitleResult
from app.services.article_agent_service import ArticleAgentService
from app.skills.base import AtomicSkill


class ArticleGenerateContentSkill(AtomicSkill):
    """生成正文原子 Skill"""

    definition = SkillDefinition(
        id="article.generate_content",
        kind="atomic",
        name="Generate Content",
        version="0.1.0",
        description="根据大纲生成文章正文",
        inputSchema={"type": "object", "properties": {"outline": {"type": "array"}}},
        outputSchema={"type": "object", "properties": {"markdown": {"type": "string"}}},
        tags=["article", "content"],
    )

    async def execute(self, ctx, input_data: dict) -> dict:
        state = ArticleState()
        state.task_id = f"skill_run_{ctx.run_id}"
        state.style = input_data.get("style")
        state.title = TitleResult(
            mainTitle=input_data["selectedMainTitle"],
            subTitle=input_data.get("selectedSubTitle", ""),
        )
        state.outline = OutlineResult(
            sections=[OutlineSection(**item) for item in input_data.get("outline", [])]
        )

        def handle_stream(message: str):
            prefix = SseMessageTypeEnum.AGENT3_STREAMING.get_streaming_prefix()
            if message.startswith(prefix):
                ctx.emit_nowait("message.delta", {"target": "markdown", "text": message[len(prefix):]})

        service = ArticleAgentService()
        await service.agent3_generate_content(state, handle_stream)
        await ctx.flush_events()
        markdown = state.content or ""
        return {"markdown": markdown, "fullContent": markdown}

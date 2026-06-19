"""修改大纲 Skill"""

from app.runtime.schemas import SkillDefinition
from app.schemas.article import OutlineSection
from app.services.article_agent_service import ArticleAgentService
from app.skills.base import AtomicSkill


class ArticleModifyOutlineSkill(AtomicSkill):
    """修改大纲原子 Skill"""

    definition = SkillDefinition(
        id="article.modify_outline",
        kind="atomic",
        name="Modify Outline",
        version="0.1.0",
        description="根据用户建议修改文章大纲",
        inputSchema={"type": "object", "properties": {"modifySuggestion": {"type": "string"}}},
        outputSchema={"type": "object", "properties": {"outline": {"type": "array"}}},
        tags=["article", "outline"],
    )

    async def execute(self, ctx, input_data: dict[str, str]) -> dict:
        current_outline = [
            OutlineSection(**item) for item in input_data.get("outline", [])
        ]
        service = ArticleAgentService()
        modified = await service.ai_modify_outline(
            task_id=f"skill_run_{ctx.run_id}",
            main_title=input_data.get("selectedMainTitle", "文章标题"),
            sub_title=input_data.get("selectedSubTitle", ""),
            current_outline=current_outline,
            modify_suggestion=input_data["modifySuggestion"],
        )
        return {"outline": [item.model_dump() for item in modified]}

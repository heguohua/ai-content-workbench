"""生成大纲 Skill"""

from app.runtime.schemas import SkillDefinition
from app.schemas.article import ArticleState, TitleResult
from app.services.article_agent_service import ArticleAgentService
from app.skills.base import AtomicSkill


class ArticleGenerateOutlineSkill(AtomicSkill):
    """生成大纲原子 Skill"""

    definition = SkillDefinition(
        id="article.generate_outline",
        kind="atomic",
        name="Generate Outline",
        version="0.1.0",
        description="根据已选标题生成文章大纲",
        inputSchema={"type": "object", "properties": {"selectedMainTitle": {"type": "string"}}},
        outputSchema={"type": "object", "properties": {"outline": {"type": "array"}}},
        tags=["article", "outline"],
    )

    async def execute(self, ctx, input_data: dict[str, str]) -> dict:
        state = ArticleState()
        state.task_id = f"skill_run_{ctx.run_id}"
        state.style = input_data.get("style")
        state.user_description = input_data.get("userDescription")
        state.title = TitleResult(
            mainTitle=input_data["selectedMainTitle"],
            subTitle=input_data["selectedSubTitle"],
        )

        service = ArticleAgentService()
        await service.agent2_generate_outline(state, lambda message: None)
        return {
            "outline": [
                item.model_dump() for item in (state.outline.sections if state.outline else [])
            ]
        }

    def _fallback_outline(self, main_title: str, user_description: str) -> dict:
        return {
            "outline": [
                {
                    "section": 1,
                    "title": "问题背景与机会窗口",
                    "points": [f"{main_title} 为什么正在成为新焦点", "行业变化的核心驱动因素"],
                },
                {
                    "section": 2,
                    "title": "核心策略拆解",
                    "points": ["目标用户定位", "增长飞轮设计", f"写作口径偏向：{user_description}"],
                },
                {
                    "section": 3,
                    "title": "执行建议与风险提醒",
                    "points": ["短期可执行动作", "常见误区与避坑建议"],
                },
            ]
        }

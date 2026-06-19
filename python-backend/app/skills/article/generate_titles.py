"""生成标题 Skill"""

from app.runtime.schemas import SkillDefinition
from app.schemas.article import ArticleState
from app.services.article_agent_service import ArticleAgentService
from app.skills.base import AtomicSkill


class ArticleGenerateTitlesSkill(AtomicSkill):
    """生成标题原子 Skill"""

    definition = SkillDefinition(
        id="article.generate_titles",
        kind="atomic",
        name="Generate Titles",
        version="0.1.0",
        description="根据选题生成标题候选",
        inputSchema={"type": "object", "properties": {"topic": {"type": "string"}}},
        outputSchema={"type": "object", "properties": {"titleOptions": {"type": "array"}}},
        tags=["article", "title"],
    )

    async def execute(self, ctx, input_data: dict[str, str]) -> dict:
        state = ArticleState()
        state.task_id = f"skill_run_{ctx.run_id}"
        state.topic = input_data["topic"]
        state.style = input_data.get("style")

        service = ArticleAgentService()
        await service.agent1_generate_title_options(state)
        return {
            "titleOptions": [
                item.model_dump(by_alias=True) for item in (state.title_options or [])
            ]
        }

    def _fallback_titles(self, topic: str) -> dict:
        return {
            "titleOptions": [
                {
                    "mainTitle": f"{topic}：从 0 到 1 的增长方法论",
                    "subTitle": "拆解产品、市场与团队协同的关键路径",
                },
                {
                    "mainTitle": f"{topic}，为什么今年尤其值得重视？",
                    "subTitle": "从趋势、案例到落地动作的一次完整梳理",
                },
                {
                    "mainTitle": f"做好 {topic}，企业最容易忽略的 5 个问题",
                    "subTitle": "不是不会做，而是常常在关键节点走偏",
                },
            ]
        }

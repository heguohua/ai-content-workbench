"""Skill 注册表"""

from app.projects.article_studio import ArticleStudioSkill
from app.skills.article.generate_content import ArticleGenerateContentSkill
from app.skills.article.generate_images import ArticleGenerateImagesSkill
from app.skills.article.generate_outline import ArticleGenerateOutlineSkill
from app.skills.article.generate_titles import ArticleGenerateTitlesSkill
from app.skills.article.modify_outline import ArticleModifyOutlineSkill


class SkillRegistry:
    """Skill 注册表"""

    def __init__(self):
        self._skills = {}

    def register(self, skill):
        """注册 Skill"""
        self._skills[skill.definition.id] = skill

    def get(self, skill_id: str):
        """获取 Skill"""
        return self._skills[skill_id]

    def list(self):
        """列出 Skill 定义"""
        return [skill.definition for skill in self._skills.values()]


skill_registry = SkillRegistry()
skill_registry.register(ArticleStudioSkill())
skill_registry.register(ArticleGenerateTitlesSkill())
skill_registry.register(ArticleGenerateOutlineSkill())
skill_registry.register(ArticleModifyOutlineSkill())
skill_registry.register(ArticleGenerateContentSkill())
skill_registry.register(ArticleGenerateImagesSkill())

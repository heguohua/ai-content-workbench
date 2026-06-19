"""Skill 基类"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

from app.runtime.schemas import SkillDefinition, SkillEvent


class BaseSkill(ABC):
    """Project Skill 基类"""

    definition: SkillDefinition

    @abstractmethod
    async def run(self, ctx, input_data: dict[str, Any]) -> AsyncGenerator[SkillEvent, None]:
        """执行 Skill"""

    async def resume(self, ctx, action: str, payload: dict[str, Any]) -> AsyncGenerator[SkillEvent, None]:
        """继续执行 Skill"""
        raise NotImplementedError


class AtomicSkill(ABC):
    """Atomic Skill 基类"""

    definition: SkillDefinition

    @abstractmethod
    async def execute(self, ctx, input_data: dict[str, Any]) -> dict[str, Any]:
        """执行原子 Skill"""

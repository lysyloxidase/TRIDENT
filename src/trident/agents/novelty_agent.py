from trident.agents.base import AgentContext, AgentResult


class NoveltyAgent:
    name = "novelty"

    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            success=False,
            warnings=["Phase 3 placeholder"],
            output=context.model_dump(),
        )

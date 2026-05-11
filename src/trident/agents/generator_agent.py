from trident.agents.base import AgentContext, AgentResult


class GeneratorAgent:
    name = "generator"

    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            success=False,
            warnings=["Phase 4 placeholder"],
            output=context.model_dump(),
        )

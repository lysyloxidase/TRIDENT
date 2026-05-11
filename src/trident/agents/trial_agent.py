from trident.agents.base import AgentContext, AgentResult


class TrialAgent:
    name = "trial"

    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            success=False,
            warnings=["Phase 2 placeholder"],
            output=context.model_dump(),
        )

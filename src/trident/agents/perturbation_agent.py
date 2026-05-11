from trident.agents.base import AgentContext, AgentResult


class PerturbationAgent:
    name = "perturbation"

    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            success=False,
            warnings=["Phase 5 placeholder"],
            output=context.model_dump(),
        )

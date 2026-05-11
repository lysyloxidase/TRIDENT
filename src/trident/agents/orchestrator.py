from trident.agents.base import AgentContext, AgentResult, BaseAgent


class Orchestrator:
    name = "orchestrator"

    def __init__(self, agents: list[BaseAgent] | None = None) -> None:
        self.agents = agents or []

    def run(self, context: AgentContext) -> list[AgentResult]:
        return [agent.run(context) for agent in self.agents]

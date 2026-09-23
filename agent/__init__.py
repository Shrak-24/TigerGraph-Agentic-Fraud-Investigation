"""Person 2's fraud investigation agent.

The public entry point is :class:`FraudInvestigationAgent`.  The package is
deliberately dependency-light so it can run against the deterministic mock
graph today and be wired to TigerGraph MCP later.
"""

from .agent import FraudInvestigationAgent
from .graph_tools import GraphToolInterface, MockGraphTools
from .memory import CaseMemory

__all__ = ["CaseMemory", "FraudInvestigationAgent", "GraphToolInterface", "MockGraphTools"]

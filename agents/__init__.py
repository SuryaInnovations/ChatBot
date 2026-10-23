"""
Agents Package: Autonomous, domain-specialized multi-turn agents.
"""

from agents.study_mentor import default_study_mentor, StudyMentorAgent
from agents.coding_agent import default_coding_agent, CodingWorkspaceAgent
from agents.research_agent import default_research_agent, DeepResearchAgent
from agents.automl_agent import default_automl_agent, AutoMLAgent
from agents.interview_agent import default_interview_agent, InterviewSimulatorAgent
from agents.project_builder import default_project_builder, ProjectBuilderAgent

__all__ = [
    "default_study_mentor",
    "StudyMentorAgent",
    "default_coding_agent",
    "CodingWorkspaceAgent",
    "default_research_agent",
    "DeepResearchAgent",
    "default_automl_agent",
    "AutoMLAgent",
    "default_interview_agent",
    "InterviewSimulatorAgent",
    "default_project_builder",
    "ProjectBuilderAgent"
]

from dataclasses import dataclass, field


@dataclass
class TicketAnalysis:
    issue_number: int
    title: str
    type: str  # bug, feature, cleanup
    action: str  # automate, engineer_review, needs_more_info
    action_reasoning: str
    confidence: int  # 0-100
    priority: str  # high, medium, low
    complexity: str  # high, medium, low
    complexity_reasoning: str
    description: str


@dataclass
class AnalysisSummary:
    total_count: int
    counts_by_type: dict = field(default_factory=dict)
    counts_by_action: dict = field(default_factory=dict)
    counts_by_priority: dict = field(default_factory=dict)


@dataclass
class Config:
    stale_days: int = 0
    top_n: int = 10

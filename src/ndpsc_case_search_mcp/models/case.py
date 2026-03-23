from enum import Enum

from pydantic import BaseModel

SEPARATOR = "\n---\n"


class Jurisdiction(str, Enum):
    ALL_COMPLIANCE = "CO"
    AUCTION = "AU"
    WEIGHTS_MEASURES = "WM"
    ALL_MINING = "MI"
    ABANDONED_MINE = "AM"
    RECLAMATION = "RC"
    ALL_PUBLIC_UTILITIES = "PU"
    ALL_SAFETY = "SR"
    DAMAGE_PREVENTION = "DM"
    GAS_PIPELINE_SAFETY = "GS"
    RAILROAD_SAFETY = "RR"
    ALL_ARCHIVE = "AR"
    GRAIN = "GE"
    ALL_OTHER = "OT"
    ADMINISTRATION = "AD"


class CaseStatus(str, Enum):
    OPEN = "Open"
    CLOSED = "Closed"


class CaseCategory(str, Enum):
    AUCTIONEER = "Auctioneer"
    ELECTRIC = "Electric"
    FACILITY = "Facility"
    GAS = "Gas"
    PIPELINE = "Pipeline"
    REPORTS = "Reports"
    ROVING_GRAIN = "Roving Grain"
    TELECOM = "Telecom"
    WAREHOUSE = "Warehouse"


class CaseSummary(BaseModel):
    case_number: str
    year: str | None = None
    seq: str | None = None
    description: str = ""
    type_category: str = ""
    entity: str = ""
    docket_count: str = ""
    date_filed: str = ""
    date_closed: str = ""

    def __str__(self) -> str:
        lines = [
            f"### {self.case_number}",
            f"- **Description:** {self.description}",
            f"- **Type/Category:** {self.type_category}",
            f"- **Entity:** {self.entity}",
            f"- **Dockets:** {self.docket_count}  |  **Filed:** {self.date_filed}",
        ]
        if self.date_closed:
            lines.append(f"- **Closed:** {self.date_closed}")
        return "\n".join(lines)


class CaseDetail(BaseModel):
    case_id: str = ""
    date_filed: str = ""
    date_closed: str = ""
    description: str = ""
    case_type: str = ""
    category: str = ""
    entities: list[str] = []
    docket_count: int = 0
    year: str = ""
    sequence: str = ""

    def __str__(self) -> str:
        lines = [f"## {self.case_id}\n"]
        if self.date_filed:
            lines.append(f"- **Date Filed:** {self.date_filed}")
        if self.date_closed:
            lines.append(f"- **Date Closed:** {self.date_closed}")
        if self.description:
            lines.append(f"- **Description:** {self.description}")
        if self.case_type:
            lines.append(f"- **Type:** {self.case_type}")
        if self.category:
            lines.append(f"- **Category:** {self.category}")
        if self.entities:
            lines.append(f"- **Entities:** {', '.join(self.entities)}")
        lines.append(f"\n## Dockets: {self.docket_count}\n")
        if self.docket_count > 0:
            lines.append(
                f"Use `get_docket_detail` with year='{self.year}', "
                f"sequence='{self.sequence}', and docket='1' through "
                f"'{self.docket_count}' to view files in each docket."
            )
        return "\n".join(lines)


class DocketFile(BaseModel):
    file_number: str = ""
    description: str = ""
    web_access: bool = False
    size: str = ""

    def __str__(self) -> str:
        access = "Available" if self.web_access else "Not available online"
        lines = [
            f"### File {self.file_number} — {self.description}",
            f"- **Access:** {access}  |  **Size:** {self.size}",
        ]
        return "\n".join(lines)

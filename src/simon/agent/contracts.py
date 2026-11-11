
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class RequirementType(str, Enum):
    OBJECTIVE = "objective"
    CONSTRAINT = "constraint"
    DELIVERABLE = "deliverable"


class ArtifactType(str, Enum):
    REPORT = "report"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    IMAGE = "image"
    ARCHIVE = "archive"
    DATA = "data"
    FILE_COLLECTION = "file_collection"
    TEXT_CONTENT = "text_content"
    ANALYSIS = "analysis"
    OTHER = "other"


class ArtifactFormat(str, Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"
    PNG = "png"
    JPG = "jpg"
    ZIP = "zip"
    OTHER = "other"


class Requirement(BaseModel):
    requirement_id: str
    description: str = Field(min_length=3)
    requirement_type: RequirementType
    required_format: ArtifactFormat | None = None
    mandatory: bool = True


class RequirementSet(BaseModel):
    requirements: list[Requirement] = Field(
        min_length=1,
        max_length=20
    )

    @model_validator(mode="after")
    def validate_ids(self):

        ids = [
            requirement.requirement_id
            for requirement in self.requirements
        ]

        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate requirement IDs detected")

        return self


class Artifact(BaseModel):
    artifact_id: str
    description: str = Field(min_length=3)
    artifact_type: ArtifactType
    format: ArtifactFormat | None = None
    produced_by: int = Field(ge=1)


class PlanStep(BaseModel):
    step_id: int = Field(ge=1)
    description: str = Field(min_length=5)

    # Required field: the model must explicitly provide the mapping.
    # An empty list is valid for intermediate steps.
    satisfies_requirements: list[str] = Field(
        description=(
            "Requirement IDs this step contributes to satisfying. "
            "Use an empty list only when the step does not directly "
            "satisfy any requirement."
        )
    )

    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)


class Deliverable(BaseModel):
    deliverable_id: str
    description: str = Field(min_length=3)
    artifact_id: str

    # Every final deliverable must explicitly map to at least one requirement.
    satisfies_requirements: list[str] = Field(
        min_length=1,
        description=(
            "Requirement IDs fulfilled by this final deliverable."
        )
    )


class TaskPlan(BaseModel):
    task: str = Field(min_length=1)
    goal: str = Field(min_length=5)

    steps: list[PlanStep] = Field(
        min_length=1,
        max_length=12
    )

    deliverables: list[Deliverable] = Field(
        min_length=1,
        max_length=8
    )

    artifacts: list[Artifact] = Field(
        min_length=1,
        max_length=30
    )

    success_criteria: list[str] = Field(
        min_length=1,
        max_length=8
    )

    @model_validator(mode="after")
    def validate_references(self):

        # Validate sequential step IDs.

        step_ids = [
            step.step_id
            for step in self.steps
        ]

        if step_ids != list(range(1, len(self.steps) + 1)):
            raise ValueError(
                "The step_ids must be sequential"
            )

        # Validate artifact IDs.

        artifact_ids = [
            artifact.artifact_id
            for artifact in self.artifacts
        ]

        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("Duplicate artifact IDs detected")

        artifact_registry = {
            artifact.artifact_id: artifact
            for artifact in self.artifacts
        }

        # Validate deliverable IDs.

        deliverable_ids = [
            deliverable.deliverable_id
            for deliverable in self.deliverables
        ]

        if len(deliverable_ids) != len(set(deliverable_ids)):
            raise ValueError("Duplicate deliverable IDs detected")

        # Validate artifact production.

        produced_artifact_ids: set[str] = set()

        for step in self.steps:

            for artifact_id in step.outputs:

                if artifact_id not in artifact_registry:
                    raise ValueError(
                        f"Unknown artifact '{artifact_id}' "
                        f"produced by step {step.step_id}."
                    )

                if artifact_id in produced_artifact_ids:
                    raise ValueError(
                        f"Artifact '{artifact_id}' "
                        "is produced more than once."
                    )

                artifact = artifact_registry[artifact_id]

                if artifact.produced_by != step.step_id:
                    raise ValueError(
                        f"Artifact '{artifact_id}' declares producer "
                        f"step {artifact.produced_by}, but is produced "
                        f"by step {step.step_id}."
                    )

                produced_artifact_ids.add(artifact_id)

        missing_artifacts = (
            set(artifact_registry) - produced_artifact_ids
        )

        if missing_artifacts:
            raise ValueError(
                f"Artifacts without producing steps: "
                f"{missing_artifacts}"
            )

        # Validate artifact dependencies.

        available_artifacts: set[str] = set()

        for step in self.steps:

            for artifact_id in step.inputs:

                if artifact_id not in artifact_registry:
                    raise ValueError(
                        f"Step {step.step_id} consumes unknown "
                        f"artifact '{artifact_id}'."
                    )

                if artifact_id not in available_artifacts:
                    raise ValueError(
                        f"Step {step.step_id} consumes artifact "
                        f"'{artifact_id}' before it has been produced."
                    )

            available_artifacts.update(step.outputs)

        # Validate deliverable references.

        for deliverable in self.deliverables:

            if deliverable.artifact_id not in artifact_registry:
                raise ValueError(
                    f"Deliverable '{deliverable.deliverable_id}' "
                    f"references unknown artifact "
                    f"'{deliverable.artifact_id}'."
                )

        return self


class RequirementAssessment(BaseModel):
    requirement_id: str
    is_addressed: bool
    reason: str = Field(min_length=3)

    missing_requirements: list[str] = Field(
        default_factory=list
    )


class SemanticEvaluation(BaseModel):
    assessments: list[RequirementAssessment]

    overall_reason: str = Field(min_length=3)

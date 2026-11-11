
import pytest
from pydantic import ValidationError

from simon.agent.contracts import (
    Artifact,
    ArtifactType,
    ArtifactFormat,
    Deliverable,
    PlanStep,
    TaskPlan,
)


def create_valid_plan() -> TaskPlan:

    return TaskPlan(
        task="Analyze application logs",
        goal="Generate a PDF report of application activity.",

        steps=[
            PlanStep(
                step_id=1,
                description="Locate application logs",
                outputs=["A1"],
            ),
            PlanStep(
                step_id=2,
                description="Extract log contents",
                inputs=["A1"],
                outputs=["A2"],
            ),
            PlanStep(
                step_id=3,
                description="Analyze log contents",
                inputs=["A2"],
                outputs=["A3"],
            ),
            PlanStep(
                step_id=4,
                description="Generate the PDF report",
                inputs=["A3"],
                outputs=["A4"],
            ),
        ],

        artifacts=[
            Artifact(
                artifact_id="A1",
                description="Discovered log files",
                artifact_type=ArtifactType.FILE_COLLECTION,
                produced_by=1,
            ),
            Artifact(
                artifact_id="A2",
                description="Extracted log contents",
                artifact_type=ArtifactType.TEXT_CONTENT,
                produced_by=2,
            ),
            Artifact(
                artifact_id="A3",
                description="Analyzed log data",
                artifact_type=ArtifactType.ANALYSIS,
                produced_by=3,
            ),
            Artifact(
                artifact_id="A4",
                description="Generated application report",
                artifact_type=ArtifactType.REPORT,
                format=ArtifactFormat.PDF,
                produced_by=4,
            ),
        ],

        deliverables=[
            Deliverable(
                deliverable_id="D1",
                description="Application activity report",
                artifact_id="A4",
                satisfies_requirements=["R1"],
            ),
        ],

        success_criteria=[
            "Application logs are analyzed.",
            "The PDF report is generated.",
        ],
    )


def test_intermediate_artifacts_are_valid():
    plan = create_valid_plan()

    assert len(plan.artifacts) == 4
    assert len(plan.deliverables) == 1

    assert plan.deliverables[0].deliverable_id == "D1"
    assert plan.deliverables[0].artifact_id == "A4"


def test_unknown_artifact_input_is_rejected():

    plan = create_valid_plan().model_dump()

    plan["steps"][1]["inputs"] = ["UNKNOWN"]

    with pytest.raises(ValidationError):
        TaskPlan.model_validate(plan)


def test_artifact_cannot_be_consumed_before_production():

    plan = create_valid_plan().model_dump()

    plan["steps"][1]["inputs"] = ["A3"]

    with pytest.raises(ValidationError):
        TaskPlan.model_validate(plan)


def test_artifact_must_have_a_producer():

    plan = create_valid_plan().model_dump()

    plan["steps"][3]["outputs"] = []

    with pytest.raises(ValidationError):
        TaskPlan.model_validate(plan)


def test_deliverable_must_reference_existing_artifact():

    plan = create_valid_plan().model_dump()

    plan["deliverables"][0]["artifact_id"] = "UNKNOWN"

    with pytest.raises(ValidationError):
        TaskPlan.model_validate(plan)


def test_artifact_must_have_correct_producer():

    plan = create_valid_plan().model_dump()

    plan["artifacts"][0]["produced_by"] = 3

    with pytest.raises(ValidationError):
        TaskPlan.model_validate(plan)


def test_duplicate_artifact_ids_are_rejected():

    plan = create_valid_plan().model_dump()

    plan["artifacts"][1]["artifact_id"] = "A1"

    with pytest.raises(ValidationError):
        TaskPlan.model_validate(plan)

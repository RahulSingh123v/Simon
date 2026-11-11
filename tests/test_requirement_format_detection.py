
from simon.agent.contracts import (
    ArtifactFormat,
    Requirement,
    RequirementSet,
    RequirementType,
)

from simon.agent.requirement_extractor import (
    apply_explicit_formats,
    detect_required_format,
    detect_requested_formats,
)


def make_requirements():
    return RequirementSet(
        requirements=[
            Requirement(
                requirement_id="R1",
                description="Analyze application logs",
                requirement_type=RequirementType.OBJECTIVE,
            ),
            Requirement(
                requirement_id="R2",
                description="Generate a detailed PDF report",
                requirement_type=RequirementType.DELIVERABLE,
            ),
            Requirement(
                requirement_id="R3",
                description="Export underlying records as CSV",
                requirement_type=RequirementType.DELIVERABLE,
            ),
        ]
    )


def test_detect_single_pdf():
    assert detect_required_format(
        "Generate a PDF report."
    ) == ArtifactFormat.PDF


def test_detect_multiple_formats():
    detected = detect_requested_formats(
        "Generate a PDF report and export records as CSV."
    )

    formats = {fmt for fmt, _ in detected}

    assert formats == {
        ArtifactFormat.PDF,
        ArtifactFormat.CSV,
    }


def test_detect_required_format_returns_none_for_multiple():
    assert detect_required_format(
        "Generate a PDF report and export records as CSV."
    ) is None


def test_map_multiple_formats_to_correct_deliverables():
    requirements = make_requirements()

    updated = apply_explicit_formats(
        request=(
            "Analyze application logs, generate a PDF report "
            "and export underlying records as CSV."
        ),
        requirements=requirements,
    )

    registry = {
        item.requirement_id: item
        for item in updated.requirements
    }

    assert registry["R2"].required_format == ArtifactFormat.PDF
    assert registry["R3"].required_format == ArtifactFormat.CSV
    assert registry["R1"].required_format is None


def test_single_format_single_deliverable():
    requirements = RequirementSet(
        requirements=[
            Requirement(
                requirement_id="R1",
                description="Generate a report",
                requirement_type=RequirementType.DELIVERABLE,
            )
        ]
    )

    updated = apply_explicit_formats(
        "Generate a PDF report.",
        requirements,
    )

    assert updated.requirements[0].required_format == ArtifactFormat.PDF


def test_no_explicit_format():
    assert detect_required_format(
        "Generate a detailed report."
    ) is None


def test_no_format_preserves_existing_requirements():
    requirements = make_requirements()

    updated = apply_explicit_formats(
        "Analyze application logs and generate a report.",
        requirements,
    )

    assert updated == requirements


def test_ambiguous_format_is_not_assigned_arbitrarily():
    requirements = RequirementSet(
        requirements=[
            Requirement(
                requirement_id="R1",
                description="Generate a detailed report",
                requirement_type=RequirementType.DELIVERABLE,
            ),
            Requirement(
                requirement_id="R2",
                description="Generate a detailed report",
                requirement_type=RequirementType.DELIVERABLE,
            ),
        ]
    )

    updated = apply_explicit_formats(
        "Generate a PDF report.",
        requirements,
    )

    assert all(
        item.required_format is None
        for item in updated.requirements
    )


import json
import logging
import re

from pydantic import ValidationError

from simon.agent.contracts import (
    ArtifactFormat,
    Requirement,
    RequirementSet,
    RequirementType,
)
from simon.core.model_gateway import ModelGateway


logger = logging.getLogger("simon.requirement_extractor")


class RequirementExtractionError(Exception):
    """Raised when valid requirements cannot be extracted."""


# Supported formats and their explicit textual representations.

FORMAT_PATTERNS: list[
    tuple[ArtifactFormat, tuple[str, ...]]
] = [
    (
        ArtifactFormat.PDF,
        (r"\bpdf\b", r"\.pdf\b", r"\bportable document format\b"),
    ),
    (
        ArtifactFormat.XLSX,
        (r"\bxlsx\b", r"\.xlsx\b", r"\bexcel\b", r"\bspreadsheet\b"),
    ),
    (
        ArtifactFormat.CSV,
        (r"\bcsv\b", r"\.csv\b", r"\bcomma[- ]separated values\b"),
    ),
    (
        ArtifactFormat.JSON,
        (r"\bjson\b", r"\.json\b"),
    ),
    (
        ArtifactFormat.PNG,
        (r"\bpng\b", r"\.png\b"),
    ),
    (
        ArtifactFormat.JPG,
        (r"\bjpg\b", r"\bjpeg\b", r"\.jpg\b", r"\.jpeg\b"),
    ),
    (
        ArtifactFormat.ZIP,
        (r"\bzip\b", r"\.zip\b", r"\bzip archive\b"),
    ),
    (
        ArtifactFormat.MARKDOWN,
        (r"\bmarkdown\b", r"\bmd file\b", r"\.md\b"),
    ),
    (
        ArtifactFormat.TEXT,
        (r"\bplain text\b", r"\btext file\b", r"\.txt\b"),
    ),
]


# Words that do not contribute much to matching a request clause
# with a deliverable description.

STOP_WORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from",
    "in", "into", "it", "of", "on", "or", "the", "to",
    "with", "my", "our", "your", "their", "this", "that",
    "generate", "create", "make", "produce", "save",
    "export", "convert", "write",
}


def detect_required_format(
    request: str,
) -> ArtifactFormat | None:
    """
    Detect one explicitly mentioned format.

    This is a convenience function for single-format requests.
    For multiple formats, use detect_requested_formats().
    """

    detected = detect_requested_formats(request)

    formats = {
        artifact_format
        for artifact_format, _ in detected
    }

    if len(formats) == 1:
        return next(iter(formats))

    return None


def detect_requested_formats(
    request: str,
) -> list[tuple[ArtifactFormat, str]]:
    """
    Detect formats and retain the clause in which each was mentioned.

    Example:
        "Generate a PDF report and export records as CSV."

    Returns:
        [
            (ArtifactFormat.PDF, "Generate a PDF report"),
            (ArtifactFormat.CSV, "export records as CSV")
        ]
    """

    clauses = [
        clause.strip()
        for clause in re.split(
            r"[,;.!?\n]+|\b(?:and|then|also)\b",
            request,
            flags=re.IGNORECASE,
        )
        if clause.strip()
    ]

    detected: list[tuple[ArtifactFormat, str]] = []

    for clause in clauses:

        for artifact_format, patterns in FORMAT_PATTERNS:

            if any(
                re.search(pattern, clause, flags=re.IGNORECASE)
                for pattern in patterns
            ):
                detected.append((artifact_format, clause))

    return detected


def _get_keywords(text: str) -> set[str]:
    """Normalize text into meaningful matching keywords."""

    words = re.findall(r"[a-z0-9]+", text.lower())

    return {
        word
        for word in words
        if word not in STOP_WORDS and len(word) > 1
    }


def _match_deliverable(
    clause: str,
    deliverables: list[Requirement],
) -> Requirement | None:
    """
    Find the deliverable most closely related to a format clause.

    A match is accepted only when there is one unique best candidate.
    """

    if not deliverables:
        return None

    clause_keywords = _get_keywords(clause)

    if not clause_keywords:
        return None

    scored: list[tuple[int, Requirement]] = []

    for requirement in deliverables:

        description_keywords = _get_keywords(
            requirement.description
        )

        score = len(
            clause_keywords.intersection(description_keywords)
        )

        scored.append((score, requirement))

    highest_score = max(score for score, _ in scored)

    if highest_score == 0:
        return None

    best_matches = [
        requirement
        for score, requirement in scored
        if score == highest_score
    ]

    if len(best_matches) != 1:
        logger.warning(
            "Ambiguous format-to-deliverable mapping. "
            "Clause: '%s'. Candidates: %s",
            clause,
            [item.requirement_id for item in best_matches],
        )
        return None

    return best_matches[0]


def apply_explicit_formats(
    request: str,
    requirements: RequirementSet,
) -> RequirementSet:
    """
    Associate explicitly requested formats with their respective
    deliverable requirements.

    Multiple formats are supported when their request clauses
    can be matched unambiguously to separate deliverables.
    """

    detected = detect_requested_formats(request)

    if not detected:
        return requirements

    deliverables = [
        requirement
        for requirement in requirements.requirements
        if requirement.requirement_type == RequirementType.DELIVERABLE
    ]

    if not deliverables:
        logger.warning(
            "Output formats were detected, but no deliverable "
            "requirements were extracted."
        )
        return requirements

    # A single format and a single deliverable are unambiguous,
    # even if their descriptions use different wording.

    unique_formats = {
        artifact_format
        for artifact_format, _ in detected
    }

    if len(unique_formats) == 1 and len(deliverables) == 1:

        selected_format = next(iter(unique_formats))
        target = deliverables[0]

        return RequirementSet(
            requirements=[
                requirement.model_copy(
                    update={
                        "required_format": selected_format,
                    }
                )
                if requirement.requirement_id == target.requirement_id
                else requirement
                for requirement in requirements.requirements
            ]
        )

    # For multiple formats, match each format's clause to the
    # most relevant deliverable description.

    assignments: dict[str, ArtifactFormat] = {}

    for artifact_format, clause in detected:

        target = _match_deliverable(
            clause=clause,
            deliverables=deliverables,
        )

        if target is None:
            logger.warning(
                "Could not confidently associate format '%s' "
                "with a deliverable. Clause: '%s'",
                artifact_format.value,
                clause,
            )
            continue

        existing_format = assignments.get(target.requirement_id)

        if (
            existing_format is not None
            and existing_format != artifact_format
        ):
            logger.warning(
                "Requirement %s appears to request multiple formats: "
                "%s and %s. Split this into separate deliverables "
                "to represent both outputs.",
                target.requirement_id,
                existing_format.value,
                artifact_format.value,
            )
            assignments.pop(target.requirement_id, None)
            continue

        assignments[target.requirement_id] = artifact_format

    # If the original request explicitly specifies formats,
    # clear model-generated format assignments first. This prevents
    # the LLM from incorrectly applying one format to every output.

    updated_requirements: list[Requirement] = []

    for requirement in requirements.requirements:

        if requirement.requirement_type == RequirementType.DELIVERABLE:

            updated_requirement = requirement.model_copy(
                update={
                    "required_format": assignments.get(
                        requirement.requirement_id
                    ),
                }
            )

            updated_requirements.append(updated_requirement)

        else:
            updated_requirements.append(requirement)

    return RequirementSet(
        requirements=updated_requirements,
    )


class RequirementExtractor:

    def __init__(
        self,
        gateway: ModelGateway,
        max_retries: int = 1,
    ) -> None:

        if max_retries < 0:
            raise ValueError(
                "max_retries cannot be negative."
            )

        self.gateway = gateway
        self.max_retries = max_retries

    async def extract(
        self,
        request: str,
    ) -> RequirementSet:

        if not request or not request.strip():
            raise ValueError(
                "User request cannot be empty."
            )

        schema = RequirementSet.model_json_schema()

        messages = [
            {
                "role": "system",
                "content": """
                You are SIMON's requirement extraction component.

                Extract the user's request into a structured RequirementSet.

                ==================================================
                REQUIREMENT TYPES
                ==================================================

                1. objective:
                An action or goal the user wants accomplished.

                2. constraint:
                A condition or restriction that must be respected.

                3. deliverable:
                An output or result that must be produced.

                ==================================================
                REQUIREMENT RULES
                ==================================================

                1. Give each requirement a unique ID: R1, R2, R3...

                2. Preserve the user's original intent.

                3. Do not invent requirements.

                4. Split independent objectives, constraints and deliverables
                into separate requirements when appropriate.

                5. Mark explicitly requested requirements as mandatory.

                6. When the user requests multiple distinct output files,
                create a separate deliverable requirement for each output.

                7. Include the purpose and subject of each deliverable in
                its description so that its requested format can be
                associated with the correct output.

                ==================================================
                OUTPUT FORMAT RULES
                ==================================================

                Populate required_format whenever the user explicitly
                requests a particular output format.

                Supported values:

                - PDF -> pdf
                - Markdown -> markdown
                - Text -> text
                - JSON -> json
                - CSV -> csv
                - Excel -> xlsx
                - PNG -> png
                - JPG/JPEG -> jpg
                - ZIP -> zip

                Examples:

                User: Generate a PDF report.
                required_format: "pdf"

                User: Export records as CSV.
                required_format: "csv"

                User: Generate a PDF report and export records as CSV.

                Create separate deliverable requirements:
                - PDF report -> pdf
                - Records export -> csv

                User: Generate a detailed report.
                required_format: null

                Do not infer a specific format when the user has
                not explicitly requested one.

                For non-deliverable requirements, required_format
                should normally be null.

                Return only structured JSON matching the supplied schema.
                """
            },
            {
                "role": "user",
                "content": (
                    f"USER REQUEST:\n{request}"
                ),
            },
        ]

        total_attempts = self.max_retries + 1

        for attempt in range(1, total_attempts + 1):

            raw = ""

            logger.info(
                "Extracting requirements. Attempt %s/%s.",
                attempt,
                total_attempts,
            )

            try:

                result = await self.gateway.generate(
                    messages=messages,
                    response_schema=schema,
                )

                raw = result["message"]["content"]

                logger.debug(
                    "Raw requirement response:\n%s",
                    raw,
                )

                requirements = RequirementSet.model_validate_json(
                    raw
                )

                requirements = apply_explicit_formats(
                    request=request,
                    requirements=requirements,
                )

                logger.info(
                    "Successfully extracted %s requirements.",
                    len(requirements.requirements),
                )

                for requirement in requirements.requirements:

                    logger.debug(
                        "Requirement %s | Type: %s | Format: %s",
                        requirement.requirement_id,
                        requirement.requirement_type.value,
                        (
                            requirement.required_format.value
                            if requirement.required_format
                            else None
                        ),
                    )

                return requirements

            except (
                ValidationError,
                ValueError,
                KeyError,
                TypeError,
                json.JSONDecodeError,
            ) as exc:

                logger.warning(
                    "Requirement extraction failed on attempt %s: %s",
                    attempt,
                    exc,
                )

                if attempt == total_attempts:

                    raise RequirementExtractionError(
                        "Could not extract valid requirements. "
                        f"Details: {exc}"
                    ) from exc

                messages.append({
                    "role": "assistant",
                    "content": raw,
                })

                messages.append({
                    "role": "user",
                    "content": (
                        "Your previous response failed validation.\n\n"
                        f"VALIDATION ERRORS:\n{exc}\n\n"
                        "Correct all validation errors.\n"
                        "Preserve the original user request.\n"
                        "Use unique sequential requirement IDs.\n"
                        "Use only supported requirement types.\n"
                        "Create separate deliverable requirements for "
                        "separate requested output files.\n"
                        "Populate required_format when explicitly requested.\n"
                        "Return the complete corrected RequirementSet JSON."
                    ),
                })

        raise RequirementExtractionError(
            "Requirement extraction failed."
        )


import logging

from pydantic import ValidationError

from simon.agent.contracts import RequirementSet, TaskPlan
from simon.core.model_gateway import ModelGateway


logger = logging.getLogger("simon.planner")


class PlanningError(Exception):
    """Raised when the planner cannot generate a valid task plan."""


class Planner:

    def __init__(
        self,
        gateway: ModelGateway,
        max_structural_retries: int = 0,
    ) -> None:

        if max_structural_retries < 0:
            raise ValueError(
                "max_structural_retries cannot be negative."
            )

        self.gateway = gateway
        self.max_structural_retries = max_structural_retries

    async def create_plan(
        self,
        request: str,
        requirements: RequirementSet,
        validation_errors: list[str] | None = None,
    ) -> TaskPlan:

        schema = TaskPlan.model_json_schema()

        requirement_data = requirements.model_dump_json(
            indent=2
        )

        system_prompt = """
You are SIMON's task planning component.

Your responsibility is to generate a complete execution plan
using the user's request and supplied requirements.

Return only structured JSON matching the supplied TaskPlan schema.

==================================================
DATA MODEL
==================================================

1. PlanStep:
   Represents one execution operation.
   Its inputs and outputs reference artifact IDs.
   satisfies_requirements identifies the requirements
   that this step contributes to satisfying.

2. Artifact:
   Represents an intermediate or final execution output.
   Every artifact must have exactly one producing step.

3. Deliverable:
   Represents a final outcome promised to the user.
   It references an existing final artifact.

==================================================
REQUIREMENT MAPPING RULES
==================================================

1. Use only requirement IDs supplied in the requirements.

2. Every PlanStep MUST explicitly contain
   satisfies_requirements.

3. An empty list is permitted only when the step does not
   directly contribute to satisfying a requirement.

4. Map objective requirements to the steps that perform
   the requested objective.

5. Map constraint requirements to the steps that enforce
   the requested constraint.

6. Map deliverable requirements to the steps that create
   the requested deliverable.

7. Every Deliverable MUST explicitly contain
   satisfies_requirements.

8. Every mandatory requirement must appear in at least
   one relevant step or deliverable.

9. Every mandatory deliverable requirement must appear
   in at least one final Deliverable object.

10. Never invent requirement IDs.

==================================================
ARTIFACT PRODUCTION RULES
==================================================

1. Use A1, A2, A3... for artifact IDs.

2. Every artifact registered in the artifacts array MUST
   appear in exactly one step's outputs list.

3. Every artifact must have exactly one producing step.

4. The artifact's produced_by must equal the step_id
   of the step that lists it in outputs.

5. Every step output must reference a registered artifact.

6. Every step input must reference an artifact produced
   by an earlier step.

7. Do not register artifacts that are not produced by steps.

8. When a step generates an artifact, include its ID
   in that step's outputs.

9. When a step transforms an artifact:
   - Put the existing artifact ID in inputs.
   - Register the new artifact.
   - Put the new artifact ID in outputs.

10. Do not use the same artifact as the output of multiple steps.

==================================================
ARTIFACT FORMAT RULES
==================================================

1. Respect explicitly requested output formats.

2. PDF artifacts must have format "pdf".

3. CSV artifacts must have format "csv".

4. Excel artifacts must have format "xlsx".

5. Use the appropriate artifact_type.

6. A PDF report must have artifact_type "report".

7. Text used to create a PDF is an intermediate artifact,
   not the final PDF deliverable.

==================================================
DELIVERABLE RULES
==================================================

1. Use D1, D2, D3... for deliverable IDs.

2. Every deliverable must reference an existing artifact.

3. A deliverable must reference the final relevant artifact,
   not an intermediate artifact.

4. When a user requests a saved PDF, the deliverable must
   reference the saved PDF artifact.

5. Every deliverable must map to at least one requirement.

==================================================
PDF WORKFLOW EXAMPLE
==================================================

Requirements:

R1 = Analyze application logs
R2 = Generate a detailed PDF report
R3 = Save the report in the reports directory

Step 1:
{
    "step_id": 1,
    "description": "Extract application log files",
    "inputs": [],
    "outputs": ["A1"],
    "satisfies_requirements": []
}

Artifact A1:
{
    "artifact_id": "A1",
    "description": "Extracted application log files",
    "artifact_type": "file_collection",
    "format": "other",
    "produced_by": 1
}

Step 2:
{
    "step_id": 2,
    "description": "Analyze extracted application log text",
    "inputs": ["A1"],
    "outputs": ["A2"],
    "satisfies_requirements": ["R1"]
}

Artifact A2:
{
    "artifact_id": "A2",
    "description": "Application log analysis results",
    "artifact_type": "analysis",
    "format": "text",
    "produced_by": 2
}

Step 3:
{
    "step_id": 3,
    "description": "Generate detailed report content",
    "inputs": ["A2"],
    "outputs": ["A3"],
    "satisfies_requirements": ["R2"]
}

Artifact A3:
{
    "artifact_id": "A3",
    "description": "Detailed report content",
    "artifact_type": "text_content",
    "format": "text",
    "produced_by": 3
}

Step 4:
{
    "step_id": 4,
    "description": "Convert report content into PDF",
    "inputs": ["A3"],
    "outputs": ["A4"],
    "satisfies_requirements": ["R2"]
}

Artifact A4:
{
    "artifact_id": "A4",
    "description": "Generated PDF report",
    "artifact_type": "report",
    "format": "pdf",
    "produced_by": 4
}

Step 5:
{
    "step_id": 5,
    "description": "Save PDF report in reports directory",
    "inputs": ["A4"],
    "outputs": ["A5"],
    "satisfies_requirements": ["R3"]
}

Artifact A5:
{
    "artifact_id": "A5",
    "description": "Saved PDF report in reports directory",
    "artifact_type": "report",
    "format": "pdf",
    "produced_by": 5
}

Final Deliverable:
{
    "deliverable_id": "D1",
    "description": "Final saved PDF report",
    "artifact_id": "A5",
    "satisfies_requirements": ["R2", "R3"]
}

This example illustrates the expected relationships.
Adapt the plan to the actual request and requirements.

==================================================
PLANNING RULES
==================================================

1. Create sequential step IDs starting at 1.

2. Create unique artifact IDs.

3. Create unique deliverable IDs.

4. Include all operations required by the request.

5. Do not claim that operations have already been executed.

6. Return a complete TaskPlan matching the supplied schema.

7. Do not omit required fields.

8. Return only structured JSON.
"""

        # Preserve the original request and requirements
        # throughout the complete planning process.

        base_messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    f"USER REQUEST:\n{request}\n\n"
                    f"REQUIREMENTS:\n{requirement_data}\n\n"
                    "Generate a complete TaskPlan JSON. "
                    "Follow all artifact production, dependency, "
                    "and requirement mapping rules."
                ),
            },
        ]

        # Add feedback from the PlanningEngine, if available.

        if validation_errors:

            correction_prompt = (
                "The previously generated plan failed validation.\n\n"
                "VALIDATION ERRORS:\n"
                + "\n\n".join(validation_errors)
                + "\n\n"
                "CORRECTION INSTRUCTIONS:\n"
                "1. Correct every reported validation error.\n"
                "2. Preserve the original user request.\n"
                "3. Preserve the supplied requirement IDs.\n"
                "4. Include satisfies_requirements in every step.\n"
                "5. Include satisfies_requirements in every deliverable.\n"
                "6. Map every mandatory requirement appropriately.\n"
                "7. Every registered artifact must appear in exactly "
                "one step's outputs.\n"
                "8. Every artifact's produced_by must match its "
                "producing step's step_id.\n"
                "9. Every step input must reference an artifact "
                "produced by an earlier step.\n"
                "10. Every step output must reference a registered artifact.\n"
                "11. Every deliverable must reference the correct "
                "final artifact.\n"
                "12. Respect all requested artifact formats.\n"
                "13. Keep step IDs sequential.\n"
                "14. Return the complete corrected TaskPlan JSON.\n"
                "15. Do not leave any validation error unresolved."
            )

            base_messages.append({
                "role": "user",
                "content": correction_prompt,
            })

        # Structural generation and retry loop.

        messages = list(base_messages)

        total_attempts = self.max_structural_retries + 1

        for attempt in range(1, total_attempts + 1):

            # Reset raw on every attempt. This prevents an earlier
            # response from being reused if the current call fails.

            raw = ""

            logger.info(
                "Generating task plan. Structural attempt %s/%s.",
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
                    "Raw planner response:\n%s",
                    raw,
                )

                plan = TaskPlan.model_validate_json(raw)

                logger.info(
                    "Plan successfully generated and structurally validated."
                )

                return plan

            except (ValidationError, ValueError, KeyError, TypeError) as exc:

                logger.warning(
                    "Structural validation failed on attempt %s: %s",
                    attempt,
                    exc,
                )

                if attempt == total_attempts:

                    raise PlanningError(
                        "Could not generate a structurally valid plan. "
                        f"Validation details: {exc}"
                    ) from exc

                # Give the model the failed response and exact error.

                messages.append({
                    "role": "assistant",
                    "content": raw,
                })

                messages.append({
                    "role": "user",
                    "content": (
                        "Your previous response failed structural validation.\n\n"
                        f"VALIDATION ERRORS:\n{exc}\n\n"
                        "Correct all structural errors.\n\n"
                        "ARTIFACT PRODUCTION REQUIREMENTS:\n"
                        "- Every registered artifact must appear in "
                        "exactly one step's outputs.\n"
                        "- Every artifact must have exactly one producer.\n"
                        "- produced_by must match the producing step_id.\n"
                        "- Every step input must reference an earlier artifact.\n"
                        "- Every step output must reference a registered artifact.\n"
                        "- Do not register unused artifacts.\n\n"
                        "REQUIREMENT MAPPING REQUIREMENTS:\n"
                        "- Every step must include satisfies_requirements.\n"
                        "- Every deliverable must include satisfies_requirements.\n"
                        "- Use only the supplied requirement IDs.\n\n"
                        "Return the complete corrected TaskPlan JSON. "
                        "Preserve the original request and requirements."
                    ),
                })

        raise PlanningError(
            "Planning failed after structural retries."
        )

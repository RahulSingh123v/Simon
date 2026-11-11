from simon.agent.contracts import (
    RequirementSet,
    SemanticEvaluation,
    TaskPlan
)

from simon.core.model_gateway import ModelGateway

class SemanticEvaluationError(Exception):
    pass

class SemanticEvaluator:

    def __init__(self,gateway: ModelGateway) -> None:
        self.gateway = gateway

    async def evaluate(
        self,
        requirements: RequirementSet,
        plan: TaskPlan,
    ) -> SemanticEvaluation:

        schema = SemanticEvaluation.model_json_schema()

        messages = [
            {
                "role":    "system",
                "content": """
                You are SIMON's independent semantic plan evaluator.
                Evaluate whether the proposed plan genuinely satisfies
                the original user requirements.
                The plan contains:
                    - Requirements : what the user expects.
                    - Steps        : operations to perform.
                    - Artifacts    : all intermediate and final execution outputs.
                    - Deliverables : final outcomes linked to artifacts.
                Evaluation rules:
                    1.  Evaluate every requirement independently.
                    2.  Consider the actual meaning of descriptions.
                    3.  Inspect the inputs and outputs of relevant steps.
                    4.  Inspect the artifact descriptions and formats.
                    5.  Inspect which artifact each deliverable references.
                    6.  Check whether the execution process can reasonably
                        produce the requested deliverable.
                    7.  Detect missing operations and contradictions.
                    8.  Do not assume a deliverable is satisfied merely
                        because its ID is referenced.
                    9.  Do not claim that any action has been executed.
                    10. Do not approve a plan simply because its structure is valid.
                Return one assessment for every supplied requirement.
                Use exact requirement IDs.
                Return data matching the supplied JSON schema.
                """,
            },
            {
                "role":    "user",
                "content": (
                    "REQUIREMENTS:\n"
                    + requirements.model_dump_json(indent=2)
                    + "\n\nPLAN:\n"
                    + plan.model_dump_json(indent=2)
                ),
            },
        ]

        result = await self.gateway.generate(
            messages=messages,
            response_schema=schema
        )

        evaluation = SemanticEvaluation.model_validate_json(
            result["message"]["content"]
        )

        expected_ids = {
            item.requirement_id for item in requirements.requirements
        }

        assessed_ids = [
            item.requirement_id
            for item in evaluation.assessments
        ]

        if (len(assessed_ids) != len(set(assessed_ids)) or 
            set(assessed_ids) != expected_ids
        ):
            raise SemanticEvaluationError(
                "Every requirement must be assessed exactly once."
            )

        return evaluation




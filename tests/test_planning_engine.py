
import asyncio

from simon.core.config import load_settings
from simon.core.model_gateway import ModelGateway

from simon.agent.requirement_extractor import RequirementExtractor
from simon.agent.planner import Planner
from simon.agent.plan_validator import PlanValidator
from simon.agent.semantic_evaluator import SemanticEvaluator
from simon.agent.planning_engine import (
    PlanningEngine,
    PlanningEngineError,
)


async def main():

    settings = load_settings()
    gateway = ModelGateway(settings)

    request = (
        "Analyze my application logs and generate a detailed "
        "PDF report containing important findings. "
        "Save the report in a reports directory."
    )

    try:

        # 1. Initialize components.

        extractor = RequirementExtractor(gateway)

        planner = Planner(
            gateway,
            max_structural_retries=0,
        )

        validator = PlanValidator()

        evaluator = SemanticEvaluator(gateway)

        # 2. Initialize planning engine.

        engine = PlanningEngine(
            extractor=extractor,
            planner=planner,
            validator=validator,
            evaluator=evaluator,
            max_plan_attempts=3,
        )

        # 3. Generate and validate plan.

        result = await engine.create_plan(request)

        requirements = result.requirements
        plan = result.plan
        evaluation = result.evaluation

        print("\n========== REQUIREMENTS ==========")

        print(
            requirements.model_dump_json(indent=2)
        )

        print("\n========== PLANNING RESULT ==========")

        print("Successful attempt:", result.attempts)

        # 4. Display execution steps.

        print("\n========== EXECUTION STEPS ==========")

        for step in plan.steps:

            print(f"\nStep {step.step_id}: {step.description}")
            print("Inputs:", step.inputs)
            print("Outputs:", step.outputs)
            print(
                "Requirements:",
                step.satisfies_requirements,
            )

        # 5. Display artifacts.

        print("\n========== ARTIFACT REGISTRY ==========")

        for artifact in plan.artifacts:

            print(
                f"{artifact.artifact_id}: "
                f"{artifact.description}"
            )

            print("Type:", artifact.artifact_type.value)

            print(
                "Format:",
                artifact.format.value if artifact.format else None,
            )

            print("Produced by:", artifact.produced_by)

        # 6. Display deliverables.

        print("\n========== DELIVERABLE REGISTRY ==========")

        for deliverable in plan.deliverables:

            print(f"{deliverable.deliverable_id}:")
            print("Description:", deliverable.description)
            print("Artifact:", deliverable.artifact_id)
            print(
                "Requirements:",
                deliverable.satisfies_requirements,
            )

        # 7. Display semantic evaluation.

        print("\n========== SEMANTIC EVALUATION ==========")

        print(evaluation.model_dump_json(indent=2))

        print("\nALL PLANNING VALIDATIONS PASSED")

    except PlanningEngineError as exc:

        print("\nPLANNING FAILED")
        print(exc)

    finally:

        await gateway.close()


if __name__ == "__main__":
    asyncio.run(main())


import logging

from dataclasses import dataclass

from simon.agent.contracts import (
    RequirementSet,
    TaskPlan,
    SemanticEvaluation,
)

from simon.agent.requirement_extractor import RequirementExtractor
from simon.agent.planner import Planner, PlanningError
from simon.agent.plan_validator import PlanValidator
from simon.agent.semantic_evaluator import SemanticEvaluator


logger = logging.getLogger("simon.planning_engine")


class PlanningEngineError(Exception):
    pass


@dataclass
class PlanningResult:
    requirements: RequirementSet
    plan: TaskPlan
    evaluation: SemanticEvaluation
    attempts: int


class PlanningEngine:

    def __init__(
        self,
        extractor: RequirementExtractor,
        planner: Planner,
        validator: PlanValidator,
        evaluator: SemanticEvaluator,
        max_plan_attempts: int = 3,
    ) -> None:

        if max_plan_attempts < 1:
            raise ValueError("max_plan_attempts must be at least 1.")

        self.extractor = extractor
        self.planner = planner
        self.validator = validator
        self.evaluator = evaluator
        self.max_plan_attempts = max_plan_attempts

    async def create_plan(
        self,
        request: str,
    ) -> PlanningResult:

        # 1. Extract requirements.

        logger.info("Starting requirement extraction.")

        requirements = await self.extractor.extract(request)

        logger.info(
            "Extracted %s requirements.",
            len(requirements.requirements),
        )

        validation_errors: list[str] = []

        # 2. Generate, validate and correct the plan.

        for attempt in range(1, self.max_plan_attempts + 1):

            logger.info(
                "Planning attempt %s of %s.",
                attempt,
                self.max_plan_attempts,
            )

            # 2a. Generate a structurally valid plan.

            try:

                plan = await self.planner.create_plan(
                    request=request,
                    requirements=requirements,
                    validation_errors=validation_errors or None,
                )

            except PlanningError as exc:

                logger.warning(
                    "Structural planning failed on attempt %s: %s",
                    attempt,
                    exc,
                )

                validation_errors = [
                    f"Structural validation failed: {exc}"
                ]

                if attempt == self.max_plan_attempts:

                    raise PlanningEngineError(
                        "Unable to generate a structurally valid plan "
                        f"after {attempt} attempts."
                    ) from exc

                continue

            # 2b. Deterministic validation.

            issues = self.validator.validate(
                requirements,
                plan,
            )

            if issues:

                validation_errors = [
                    f"Deterministic validation: {issue}"
                    for issue in issues
                ]

                logger.warning(
                    "Deterministic validation failed: %s",
                    validation_errors,
                )

                if attempt == self.max_plan_attempts:
                    break

                continue

            logger.info("Deterministic validation passed.")

            # 2c. Semantic evaluation.

            evaluation = await self.evaluator.evaluate(
                requirements,
                plan,
            )

            validation_errors = self._validate_evaluation(
                requirements,
                evaluation,
            )

            if validation_errors:

                logger.warning(
                    "Semantic evaluation failed: %s",
                    validation_errors,
                )

                if attempt == self.max_plan_attempts:
                    break

                continue

            logger.info(
                "Planning successfully completed on attempt %s.",
                attempt,
            )

            # 3. Return the accepted result.

            return PlanningResult(
                requirements=requirements,
                plan=plan,
                evaluation=evaluation,
                attempts=attempt,
            )

        raise PlanningEngineError(
            "Could not produce a valid plan within "
            f"{self.max_plan_attempts} attempts.\n"
            + "\n".join(validation_errors)
        )

    @staticmethod
    def _validate_evaluation(
        requirements: RequirementSet,
        evaluation: SemanticEvaluation,
    ) -> list[str]:

        issues: list[str] = []

        requirement_registry = {
            requirement.requirement_id: requirement
            for requirement in requirements.requirements
        }

        assessment_registry = {}

        # 1. Check unknown and duplicate assessments.

        for assessment in evaluation.assessments:

            req_id = assessment.requirement_id

            if req_id not in requirement_registry:

                issues.append(
                    f"Semantic evaluator returned unknown "
                    f"requirement ID '{req_id}'."
                )

                continue

            if req_id in assessment_registry:

                issues.append(
                    f"Semantic evaluator returned duplicate "
                    f"assessment for '{req_id}'."
                )

                continue

            assessment_registry[req_id] = assessment

        # 2. Check that every mandatory requirement
        #    received an assessment.

        for requirement in requirements.requirements:

            req_id = requirement.requirement_id

            assessment = assessment_registry.get(req_id)

            if assessment is None:

                if requirement.mandatory:

                    issues.append(
                        f"Semantic evaluator did not assess "
                        f"mandatory requirement '{req_id}'."
                    )

                continue

            # 3. Check whether the evaluator considers
            #    the requirement satisfied.

            if requirement.mandatory and not assessment.is_addressed:

                issues.append(
                    f"Semantic evaluation failed for '{req_id}': "
                    f"{assessment.reason}"
                )

        return issues

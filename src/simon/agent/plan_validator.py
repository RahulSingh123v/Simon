
from simon.agent.contracts import RequirementSet, TaskPlan


class PlanValidator:

    @staticmethod
    def validate(
        requirements: RequirementSet,
        plan: TaskPlan,
    ) -> list[str]:

        issues: list[str] = []

        requirement_registry = {
            item.requirement_id: item
            for item in requirements.requirements
        }

        artifact_registry = {
            artifact.artifact_id: artifact
            for artifact in plan.artifacts
        }

        referenced_requirement_ids: set[str] = set()

        # 1. Validate requirement references in steps.

        for step in plan.steps:

            for req_id in step.satisfies_requirements:

                if req_id not in requirement_registry:
                    issues.append(
                        f"Step {step.step_id} references unknown "
                        f"requirement '{req_id}'."
                    )
                else:
                    referenced_requirement_ids.add(req_id)

        # 2. Validate requirement references in deliverables.

        for deliverable in plan.deliverables:

            for req_id in deliverable.satisfies_requirements:

                if req_id not in requirement_registry:
                    issues.append(
                        f"Deliverable {deliverable.deliverable_id} "
                        f"references unknown requirement '{req_id}'."
                    )
                else:
                    referenced_requirement_ids.add(req_id)

        # 3. Check mandatory requirement coverage.

        for requirement in requirements.requirements:

            req_id = requirement.requirement_id

            if requirement.mandatory and req_id not in referenced_requirement_ids:

                step_context = "\n".join(
                    f"Step {step.step_id}: {step.description}"
                    for step in plan.steps
                )

                deliverable_context = "\n".join(
                    f"Deliverable {item.deliverable_id}: "
                    f"{item.description}"
                    for item in plan.deliverables
                )

                issues.append(
                    f"Mandatory requirement '{req_id}' is not mapped.\n"
                    f"Requirement description: {requirement.description}\n"
                    f"Requirement type: {requirement.requirement_type.value}\n\n"
                    f"Existing execution steps:\n{step_context}\n\n"
                    f"Existing deliverables:\n{deliverable_context}\n\n"
                    f"Correction: Map '{req_id}' to the relevant "
                    f"existing step or deliverable using "
                    f"satisfies_requirements. Add a new step only "
                    f"if the existing plan does not fulfill it."
                )

        # 4. Validate deliverable artifact references and formats.

        for deliverable in plan.deliverables:

            artifact = artifact_registry.get(
                deliverable.artifact_id
            )

            if artifact is None:

                issues.append(
                    f"Deliverable {deliverable.deliverable_id} "
                    f"references missing artifact "
                    f"'{deliverable.artifact_id}'."
                )

                continue

            for req_id in deliverable.satisfies_requirements:

                requirement = requirement_registry.get(req_id)

                if requirement is None:
                    continue

                expected_format = requirement.required_format

                if (
                    expected_format is not None
                    and artifact.format != expected_format
                ):

                    issues.append(
                        f"Deliverable {deliverable.deliverable_id} "
                        f"references artifact '{artifact.artifact_id}' "
                        f"with incorrect format.\n"
                        f"Requirement: {req_id}\n"
                        f"Expected: {expected_format.value}\n"
                        f"Received: "
                        f"{artifact.format.value if artifact.format else 'unspecified'}\n"
                        f"Correction: Create or select a final artifact "
                        f"with format '{expected_format.value}' and "
                        f"update the deliverable's artifact_id."
                    )

        # 5. Every mandatory deliverable requirement needs
        #    a corresponding deliverable.

        for requirement in requirements.requirements:

            if (
                requirement.requirement_type.value == "deliverable"
                and requirement.mandatory
            ):

                matching = [
                    item
                    for item in plan.deliverables
                    if requirement.requirement_id
                    in item.satisfies_requirements
                ]

                if not matching:

                    issues.append(
                        f"Required deliverable for "
                        f"'{requirement.requirement_id}' is missing."
                    )

        return issues

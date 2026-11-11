from simon.agent.contracts import TaskPlan


def test_step_requires_requirement_mapping():
    schema = TaskPlan.model_json_schema()

    required = schema["$defs"]["PlanStep"]["required"]

    assert "satisfies_requirements" in required


def test_deliverable_requires_requirement_mapping():
    schema = TaskPlan.model_json_schema()

    required = schema["$defs"]["Deliverable"]["required"]

    assert "satisfies_requirements" in required


def test_empty_step_mapping_is_allowed():
    schema = TaskPlan.model_json_schema()

    step_schema = schema["$defs"]["PlanStep"]

    assert "satisfies_requirements" in step_schema["properties"]
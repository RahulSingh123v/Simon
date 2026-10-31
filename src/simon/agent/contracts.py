from pydantic import BaseModel,Field,model_validator

class PlanStep(BaseModel):

    step_id: int = Field(ge=1)
    description: str = Field(min_length=1)

class TaskPlan(BaseModel):
    task: str = Field(min_length=1)
    goal: str = Field(min_length=5)
    steps: list[PlanStep] = Field(min_length=1,max_length=12)
    deliverables: list[str] = Field(min_length=1,max_length=8)
    success_criteria: list[str] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_step_order(self):

        step_ids = [step.step_id for step in self.steps]

        expected_order = list(range(1,len(self.steps)+1))

        if step_ids !=  expected_order:
            raise ValueError("The sequence of steps is not in order")

        return self







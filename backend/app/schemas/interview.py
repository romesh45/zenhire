from pydantic import BaseModel


class QuestionResponse(BaseModel):
    question_id: str
    question_text: str
    difficulty: str
    followup_count: int


class AnswerSubmitRequest(BaseModel):
    answer_text: str  # manual 400 check in router (spec requires 400, not 422)


class AnswerSubmitResponse(BaseModel):
    next_question: QuestionResponse | None
    session_status: str
    message: str


class EvaluationStatusResponse(BaseModel):
    total_answers: int
    evaluated: int
    pending: int
    all_complete: bool

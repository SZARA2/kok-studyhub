from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")]
TaskKind = Literal['collect', 'organize', 'quiz', 'format', 'react', 'schedule', 'tutor']
TASK_ROLES = {'collect': 'collector', 'organize': 'organizer', 'quiz': 'questioner',
              'format': 'formatter', 'react': 'director', 'schedule': 'scheduler', 'tutor': 'tutor'}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class CourseCreate(StrictModel):
    id: Identifier | None = None
    title: str = Field(min_length=1, max_length=120)
    source_url: HttpUrl | None = None
    description: str = Field(default='', max_length=2000)


class JobCreate(StrictModel):
    id: Identifier | None = None
    course_id: Identifier | None = None
    kind: TaskKind
    input: dict = Field(default_factory=dict)


class ClaimRequest(StrictModel):
    lease_seconds: int = Field(default=600, ge=30, le=1800)


class LeaseRequest(StrictModel):
    lease_token: str = Field(min_length=20, max_length=128)


class CompleteRequest(LeaseRequest):
    result: dict


class FailRequest(LeaseRequest):
    reason: str = Field(min_length=1, max_length=2000)


class Evidence(StrictModel):
    artifact_id: Identifier
    source_id: Identifier
    segment_id: Identifier


class Segment(StrictModel):
    id: Identifier
    text: str = Field(min_length=1, max_length=20000)
    locator: str = Field(default='', max_length=200)


class Source(StrictModel):
    id: Identifier
    title: str = Field(min_length=1, max_length=200)
    url: HttpUrl | None = None
    status: Literal['complete', 'partial', 'blocked']
    segments: list[Segment] = Field(default_factory=list, max_length=300)
    note: str = Field(default='', max_length=2000)

    @model_validator(mode='after')
    def source_content(self):
        if self.status != 'blocked' and not self.segments:
            raise ValueError('Readable sources require at least one nonempty segment')
        if self.status == 'blocked' and self.segments:
            raise ValueError('Blocked sources cannot contain claimed readable segments')
        if len({s.id for s in self.segments}) != len(self.segments):
            raise ValueError('Duplicate segment IDs')
        return self


class Collected(StrictModel):
    sources: list[Source] = Field(min_length=1, max_length=30)

    @model_validator(mode='after')
    def unique_sources(self):
        if len({s.id for s in self.sources}) != len(self.sources):
            raise ValueError('Duplicate source IDs')
        return self


class Concept(StrictModel):
    id: Identifier
    title: str = Field(min_length=1, max_length=120)
    explanation: str = Field(min_length=1, max_length=8000)
    evidence: list[Evidence] = Field(min_length=1, max_length=20)


class StudyNotes(StrictModel):
    summary: str = Field(min_length=1, max_length=12000)
    coverage: Literal['complete', 'partial']
    concepts: list[Concept] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique_concepts(self):
        if len({c.id for c in self.concepts}) != len(self.concepts):
            raise ValueError('Duplicate concept IDs')
        return self


class Question(StrictModel):
    id: Identifier
    concept_id: Identifier
    question: str = Field(min_length=1, max_length=1000)
    choices: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(min_length=2, max_length=2)
    correct_index: int = Field(ge=0, le=1)
    explanation: str = Field(min_length=1, max_length=3000)
    evidence: list[Evidence] = Field(min_length=1, max_length=20)

    @field_validator('choices')
    @classmethod
    def different_choices(cls, value):
        if value[0] == value[1]:
            raise ValueError('Choices must be different')
        return value


class Quiz(StrictModel):
    notes_artifact_id: Identifier
    questions: list[Question] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique_questions(self):
        if len({q.id for q in self.questions}) != len(self.questions):
            raise ValueError('Duplicate question IDs')
        return self


def text_width(text: str) -> int:
    """Conservative 16 px fullwidth / 8 px ASCII device contract (font-specific QA remains)."""
    return sum(0 if unicodedata.combining(c) else 16 if unicodedata.east_asian_width(c) in 'WF' else 8 for c in text)


class DeviceQuestion(StrictModel):
    id: Identifier
    source_question_id: Identifier
    question_lines: list[str] = Field(min_length=1, max_length=2)
    choices: list[str] = Field(min_length=2, max_length=2)
    correct_index: int = Field(ge=0, le=1)
    explanation_lines: list[str] = Field(min_length=1, max_length=3)

    @model_validator(mode='after')
    def screen_bounds(self):
        for line in self.question_lines + self.explanation_lines:
            if not line.strip() or '\n' in line or '\r' in line or text_width(line) > 224:
                raise ValueError('Each device line must fit 224 pixels under font16-v1')
        for choice in self.choices:
            if not choice.strip() or '\n' in choice or '\r' in choice or text_width(choice) > 96:
                raise ValueError('Each device choice must fit 96 pixels under font16-v1')
        if self.choices[0] == self.choices[1]:
            raise ValueError('Device choices must differ')
        return self


class DevicePack(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    quiz_artifact_id: Identifier
    display_contract: Literal['nu40-256x64-font16-v1'] = 'nu40-256x64-font16-v1'
    questions: list[DeviceQuestion] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique_questions(self):
        if len({q.id for q in self.questions}) != len(self.questions):
            raise ValueError('Duplicate device question IDs')
        return self


class Reaction(StrictModel):
    state: Literal['idle', 'learning', 'thinking', 'correct', 'incorrect', 'finished']
    animation: Literal['idle', 'nod', 'think', 'jump', 'encourage', 'wave']
    sound: Literal['none', 'chime', 'soft'] = 'none'


class Reactions(StrictModel):
    states: list[Reaction] = Field(min_length=1, max_length=6)

    @model_validator(mode='after')
    def unique_states(self):
        if len({s.state for s in self.states}) != len(self.states):
            raise ValueError('Duplicate reaction states')
        return self


class ReviewItem(StrictModel):
    id: Identifier
    learner_id: Identifier
    pack_id: Identifier
    question_id: Identifier
    due_at: datetime
    reason: str = Field(min_length=1, max_length=500)

    @field_validator('due_at')
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError('due_at needs a timezone')
        return value


class ReviewSchedule(StrictModel):
    items: list[ReviewItem] = Field(max_length=200)


class TutorResult(StrictModel):
    answer: str = Field(min_length=1, max_length=12000)
    summary: list[str] = Field(default_factory=list, max_length=20)
    hints: list[str] = Field(default_factory=list, max_length=20)
    exam: str = Field(default='', max_length=3000)
    exam_note: str = Field(default='', max_length=3000)
    # Executable lab expressions are intentionally excluded from remote results.


class Attempt(StrictModel):
    id: Identifier
    learner_id: Identifier
    pack_id: Identifier
    question_id: Identifier
    selected_index: int = Field(ge=0, le=1)
    answered_at: datetime

    @field_validator('answered_at')
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError('answered_at needs a timezone')
        return value


RESULT_MODELS = {'collect': Collected, 'organize': StudyNotes, 'quiz': Quiz,
                 'format': DevicePack, 'react': Reactions, 'schedule': ReviewSchedule, 'tutor': TutorResult}

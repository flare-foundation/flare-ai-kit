"""
Schemas.py file.

Contains schemas from the A2A specification version 0.2.5.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, Self
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_serializer,
    model_validator,
)


class JSONRPCMessage(BaseModel):
    """Base class for all JSON-RPC messages with version and ID fields."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str | None = Field(default_factory=lambda: uuid4().hex)


class JSONRPCRequest(JSONRPCMessage):
    """Base class for JSON-RPC request messages."""


class JSONRPCError(BaseModel):
    """Represents a JSON-RPC error with code, message, and optional data."""

    code: int
    message: str
    data: Any | None = None


class JSONRPCResponse(JSONRPCMessage):
    """JSON-RPC response containing either a result or error."""

    result: Any | None = None
    error: JSONRPCError | None = None


## Error types


class JSONParseError(JSONRPCError):
    """Error for invalid JSON payload parsing failures."""

    code: int = -32700
    message: str = "Invalid JSON payload"
    data: Any | None = None


class InvalidRequestError(JSONRPCError):
    """Error for request payload validation failures."""

    code: int = -32600
    message: str = "Request payload validation error"
    data: Any | None = None


class MethodNotFoundError(JSONRPCError):
    """Error when the requested method is not found."""

    code: int = -32601
    message: str = "Method not found"
    data: None = None


class InvalidParamsError(JSONRPCError):
    """Error for invalid method parameters."""

    code: int = -32602
    message: str = "Invalid parameters"
    data: Any | None = None


class InternalError(JSONRPCError):
    """Error for internal server errors."""

    code: int = -32603
    message: str = "Internal error"
    data: Any | None = None


class TaskNotFoundError(JSONRPCError):
    """Error when a requested task cannot be found."""

    code: int = -32001
    message: str = "Task not found"
    data: None = None


class TaskNotCancelableError(JSONRPCError):
    """Error when attempting to cancel a non-cancelable task."""

    code: int = -32002
    message: str = "Task cannot be canceled"
    data: None = None


class PushNotificationNotSupportedError(JSONRPCError):
    """Error when push notifications are not supported by the agent."""

    code: int = -32003
    message: str = "Push Notification is not supported"
    data: None = None


class UnsupportedOperationError(JSONRPCError):
    """Error for operations that are not supported by the agent."""

    code: int = -32004
    message: str = "This operation is not supported"
    data: None = None


class ContentTypeNotSupportedError(JSONRPCError):
    """Error for incompatible content types."""

    code: int = -32005
    message: str = "Incompatible content types"
    data: None = None


JSONRPCErrorResponse = (
    JSONParseError
    | InvalidRequestError
    | MethodNotFoundError
    | InvalidParamsError
    | InternalError
    | TaskNotFoundError
    | TaskNotCancelableError
    | PushNotificationNotSupportedError
    | UnsupportedOperationError
    | ContentTypeNotSupportedError
)


class Role(Enum):
    """Enum for message roles in agent-to-agent communication."""

    user = "user"
    agent = "agent"


class TaskState(str, Enum):
    """Enum representing the various states a task can be in."""

    submitted = "submitted"
    working = "working"
    input_required = "input-required"
    completed = "completed"
    canceled = "canceled"
    failed = "failed"
    unknown = "unknown"
    rejected = "rejected"
    auth_required = "auth_required"


class TextPart(BaseModel):
    """A message part containing text content."""

    kind: Literal["text"] = "text"
    text: str
    metadata: dict[str, Any] | None = None


class FileContent(BaseModel):
    """File content that can be specified by bytes or URI."""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    mime_type: str | None = Field(default=None, alias="mimeType")
    bytes: str | None = None
    uri: str | None = None

    @model_validator(mode="after")
    def check_content(self) -> Self:
        """Validates that either bytes or URI is present, but not both."""
        missing_content_msg = "Either 'bytes' or 'uri' must be present in the file data"
        conflicting_content_msg = "Only one of 'bytes' or 'uri' can be present"

        if not (self.bytes or self.uri):
            raise ValueError(missing_content_msg)
        if self.bytes and self.uri:
            raise ValueError(conflicting_content_msg)
        return self


class FilePart(BaseModel):
    """A message part containing file content."""

    kind: Literal["file"] = "file"
    file: FileContent
    metadata: dict[str, Any] | None = None


class DataPart(BaseModel):
    """A message part containing structured data."""

    kind: Literal["data"] = "data"
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None


Part = Annotated[TextPart | FilePart | DataPart, Field(discriminator="kind")]


class PushNotificationAuthenticationInfo(BaseModel):
    """Authentication information for push notification services."""

    schemes: list[str]
    credentials: str | None = None


class PushNotificationConfig(BaseModel):
    """Configuration for push notification delivery."""

    url: str
    token: str | None = None
    authentication: PushNotificationAuthenticationInfo | None = None


class MessageSendConfiguration(BaseModel):
    """Configuration options for sending messages."""

    accepted_output_modes: list[str] = Field(alias="acceptedOutputModes")
    history_length: int | None = Field(default=0, alias="historyLength")
    push_notification_config: PushNotificationConfig | None = Field(
        default=None, alias="pushNotificationConfig"
    )
    blocking: bool | None = None


class Message(BaseModel):
    """A message in the agent-to-agent communication protocol."""

    model_config = ConfigDict(populate_by_name=True)

    kind: Literal["message"] = "message"
    role: Literal["user", "agent"]
    parts: list[Part]
    metadata: dict[str, Any] | None = None
    message_id: str = Field(alias="messageId")
    context_id: str | None = Field(default=None, alias="contextId")
    task_id: str | None = Field(default=None, alias="taskId")


class TaskStatus(BaseModel):
    """Status information for a task including state and timestamp."""

    state: TaskState
    message: Message | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_serializer("timestamp")
    def serialize_dt(self, dt: datetime) -> str:
        """Serializes datetime to ISO format string."""
        return dt.isoformat()


class Artifact(BaseModel):
    """An artifact produced by an agent, containing parts and metadata."""

    name: str | None = None
    description: str | None = None
    parts: list[Part]
    metadata: dict[str, Any] | None = None
    index: int = 0
    append: bool | None = None
    last_chunk: bool | None = Field(default=None, alias="lastChunk")


class Task(BaseModel):
    """A task in the agent-to-agent system with status and artifacts."""

    id: str
    kind: Literal["task"] = "task"
    context_id: str | None = Field(default=None, alias="contextId")
    status: TaskStatus
    artifacts: list[Artifact] | None = None
    history: list[Message] | None = None
    metadata: dict[str, Any] | None = None


class TaskStatusUpdateEvent(BaseModel):
    """Event indicating a task status change."""

    id: str
    status: TaskStatus
    final: bool = False
    metadata: dict[str, Any] | None = None


class TaskArtifactUpdateEvent(BaseModel):
    """Event indicating a task artifact update."""

    id: str
    artifact: Artifact
    metadata: dict[str, Any] | None = None


class AuthenticationInfo(BaseModel):
    """Authentication information with schemes and credentials."""

    model_config = ConfigDict(extra="allow")

    schemes: list[str]
    credentials: str | None = None


class TaskIdParams(BaseModel):
    """Parameters containing task ID and optional metadata."""

    id: str
    metadata: dict[str, Any] | None = None


class TaskQueryParams(TaskIdParams):
    """Parameters for querying task information."""

    model_config = ConfigDict(populate_by_name=True)

    history_length: int | None = Field(default=None, alias="historyLength")
    method: Literal["tasks/get"] = "tasks/get"


class MessageQueryParams(TaskIdParams):
    """Parameters for querying message information."""

    model_config = ConfigDict(populate_by_name=True)

    history_length: int | None = Field(default=None, alias="historyLength")


class MessageSendParams(BaseModel):
    """Parameters for sending a message."""

    message: Message
    configuration: MessageSendConfiguration | None = None
    metadata: dict[str, Any] | None = None


class TaskPushNotificationConfig(BaseModel):
    """Configuration for task-specific push notifications."""

    id: str
    push_notification_config: PushNotificationConfig = Field(
        alias="pushNotificationConfig"
    )


## RPC Messages

MethodLiteral = Literal[
    "message/send",
    "tasks/sendSubscribe",
    "tasks/get",
    "message/get",
    "tasks/cancel",
    "tasks/pushNotification/set",
    "tasks/pushNotification/get",
    "tasks/resubscribe",
]


class SendMessageRequest(JSONRPCRequest):
    """JSON-RPC request for sending a message."""

    method: Literal["message/send"] = "message/send"
    params: MessageSendParams


class StreamMessageRequest(JSONRPCRequest):
    """JSON-RPC request for streaming a message."""

    method: Literal["message/stream"] = "message/stream"
    params: MessageSendParams


class SendMessageResponse(JSONRPCResponse):
    """JSON-RPC response for message sending operations."""

    result: Task | Message | None = None


class SendStreamingMessageResponse(JSONRPCResponse):
    """JSON-RPC response for streaming message operations."""

    result: Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent | None = (
        None
    )


class GetTaskRequest(JSONRPCRequest):
    """JSON-RPC request for retrieving task information."""

    method: Literal["tasks/get"] = "tasks/get"
    params: TaskQueryParams


class GetMessageRequest(JSONRPCRequest):
    """JSON-RPC request for retrieving message information."""

    method: Literal["message/get"] = "message/get"
    params: MessageQueryParams


class GetTaskResponse(JSONRPCResponse):
    """JSON-RPC response for task retrieval operations."""

    result: Task | None = None


class CancelTaskRequest(JSONRPCRequest):
    """JSON-RPC request for canceling a task."""

    method: Literal["tasks/cancel",] = "tasks/cancel"
    params: TaskIdParams


class CancelTaskResponse(JSONRPCResponse):
    """JSON-RPC response for task cancellation operations."""

    result: Task | None = None


class SetTaskPushNotificationRequest(JSONRPCRequest):
    """JSON-RPC request for setting task push notification configuration."""

    method: Literal["tasks/pushNotification/set",] = "tasks/pushNotification/set"
    params: TaskPushNotificationConfig


class SetTaskPushNotificationResponse(JSONRPCResponse):
    """JSON-RPC response for push notification configuration setting."""

    result: TaskPushNotificationConfig | None = None


class GetTaskPushNotificationRequest(JSONRPCRequest):
    """JSON-RPC request for retrieving task push notification config."""

    method: Literal["tasks/pushNotification/get",] = "tasks/pushNotification/get"
    params: TaskIdParams


class GetTaskPushNotificationResponse(JSONRPCResponse):
    """JSON-RPC response for push notification configuration retrieval."""

    result: TaskPushNotificationConfig | None = None


class TaskResubscriptionRequest(JSONRPCRequest):
    """JSON-RPC request for resubscribing to a task."""

    method: Literal["tasks/resubscribe",] = "tasks/resubscribe"
    params: TaskIdParams


A2ARequestType = Annotated[
    SendMessageRequest
    | GetTaskRequest
    | CancelTaskRequest
    | SetTaskPushNotificationRequest
    | GetTaskPushNotificationRequest
    | TaskResubscriptionRequest
    | StreamMessageRequest,
    Field(discriminator="method"),
]

A2ARequest: TypeAdapter[A2ARequestType] = TypeAdapter(A2ARequestType)


class AgentProvider(BaseModel):
    """Information about the agent provider organization."""

    organization: str
    url: str | None = None


class AgentCapabilities(BaseModel):
    """Capabilities supported by an agent."""

    model_config = ConfigDict(populate_by_name=True)

    streaming: bool = False
    push_notifications: bool = Field(default=False, alias="pushNotifications")
    state_transition_history: bool = Field(
        default=False, alias="stateTransitionHistory"
    )


class AgentAuthentication(BaseModel):
    """Authentication schemes and credentials for agent access."""

    schemes: list[str]
    credentials: str | None = None


class AgentSkill(BaseModel):
    """A skill or capability offered by an agent."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: str
    tags: list[str]
    examples: list[str] | None = None
    input_modes: list[str] | None = Field(default=None, alias="inputModes")
    output_modes: list[str] | None = Field(default=None, alias="outputModes")


class AgentCard(BaseModel):
    """Complete agent specification including capabilities and skills."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    url: str
    version: str
    provider: AgentProvider | None = None
    documentation_url: str | None = Field(default=None, alias="documentationUrl")
    capabilities: AgentCapabilities
    authentication: AgentAuthentication | None = None
    default_input_modes: list[str] = Field(
        default=["text/plain"], alias="defaultInputModes"
    )
    default_output_modes: list[str] = Field(
        default=["text/plain"], alias="defaultOutputModes"
    )
    skills: list[AgentSkill]


class A2AClientError(Exception):
    """Base exception for A2A client errors."""


class A2AClientHTTPError(A2AClientError):
    """HTTP-specific error for A2A client operations."""

    def __init__(self, status_code: int, message: str) -> None:
        """Initialize HTTP error with status code and message."""
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP Error {status_code}: {message}")


class A2AClientJSONError(A2AClientError):
    """JSON parsing error for A2A client operations."""

    def __init__(self, message: str) -> None:
        """Initialize JSON error with descriptive message."""
        self.message = message
        super().__init__(f"JSON Error: {message}")

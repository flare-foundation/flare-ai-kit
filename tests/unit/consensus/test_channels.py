import asyncio
import time

import pytest

from flare_ai_kit.consensus.communication.base import AgentMessage, MessageType
from flare_ai_kit.consensus.communication.channels import (
    CommunicationManager,
    EventBus,
    InMemoryChannel,
)


@pytest.mark.asyncio
async def test_inmemorychannel_send_and_receive():
    ch = InMemoryChannel(max_queue_size=2)
    msg = AgentMessage(
        message_id="1",
        sender_id="alice",
        recipient_id="bob",
        message_type=MessageType.PREDICTION,
        content={"x": 1},
        timestamp=time.time(),
    )

    # subscribe bob so messages are not filtered
    await ch.subscribe("bob", [MessageType.PREDICTION])

    assert await ch.send_message(msg) is True
    received = await ch.receive_messages("bob")
    assert len(received) == 1
    assert received[0].content == {"x": 1}

    # ensure queue trimming works
    for i in range(3):
        await ch.send_message(
            AgentMessage(
                message_id=str(i + 2),
                sender_id="alice",
                recipient_id="bob",
                message_type=MessageType.PREDICTION,
                content={"x": i},
                timestamp=time.time(),
            )
        )
    msgs = await ch.receive_messages("bob")
    # max_queue_size = 2 → only last 2 kept
    assert len(msgs) == 2


@pytest.mark.asyncio
async def test_inmemorychannel_broadcast_filters_by_subscription():
    ch = InMemoryChannel()
    # bob subscribes to PREDICTION only
    await ch.subscribe("bob", [MessageType.PREDICTION])
    await ch.subscribe("carol", [MessageType.PEER_REVIEW])

    msg = AgentMessage(
        message_id="b1",
        sender_id="alice",
        message_type=MessageType.PREDICTION,
        content={},
        timestamp=time.time(),
    )
    await ch.broadcast_message(msg)

    bob_msgs = await ch.receive_messages("bob")
    carol_msgs = await ch.receive_messages("carol")

    assert len(bob_msgs) == 1  # bob gets it
    assert len(carol_msgs) == 0  # carol filtered out


@pytest.mark.asyncio
async def test_eventbus_publish_and_unsubscribe():
    bus = EventBus()
    called: list[dict] = []

    async def handler(data):
        called.append(data)

    await bus.subscribe_to_event("evt", handler, "agent1")
    await bus.publish_event("evt", {"foo": "bar"})
    await asyncio.sleep(0)  # allow tasks to run
    assert called == [{"foo": "bar"}]

    await bus.unsubscribe_from_event("evt", "agent1")
    called.clear()
    await bus.publish_event("evt", {"foo": "baz"})
    await asyncio.sleep(0)
    assert called == []


@pytest.mark.asyncio
async def test_communicationmanager_register_and_send_prediction():
    mgr = CommunicationManager()
    await mgr.register_agent("bob")

    # alice broadcasts a prediction
    assert await mgr.send_prediction("alice", prediction="yes", confidence=0.7)
    msgs = await mgr.get_agent_messages("bob")
    assert len(msgs) == 1
    m = msgs[0]
    assert m.message_type == MessageType.PREDICTION
    assert m.content["prediction"] == "yes"
    assert pytest.approx(m.content["confidence"]) == 0.7


@pytest.mark.asyncio
async def test_communicationmanager_request_and_peer_review():
    mgr = CommunicationManager()
    await mgr.register_agent("bob")

    # collaboration request
    assert await mgr.request_collaboration("alice", "bob", "Check this")
    msgs = await mgr.get_agent_messages("bob")
    assert len(msgs) == 1
    assert msgs[0].message_type == MessageType.COLLABORATION_REQUEST
    assert msgs[0].requires_response is True

    # peer review
    assert await mgr.send_peer_review(
        "alice", "bob", original_prediction="foo", review_comments="ok"
    )
    msgs = await mgr.get_agent_messages("bob")
    assert len(msgs) == 1
    assert msgs[0].message_type == MessageType.PEER_REVIEW
    assert msgs[0].content["review_comments"] == "ok"


@pytest.mark.asyncio
async def test_publish_consensus_reached_eventbus_called():
    mgr = CommunicationManager()
    received: list[dict] = []

    async def handler(data):
        received.append(data)

    await mgr.event_bus.subscribe_to_event("consensus_reached", handler, "agent1")
    await mgr.publish_consensus_reached(
        task_id="t1",
        final_prediction="bar",
        participating_agents=["a", "b"],
        confidence=0.9,
    )
    await asyncio.sleep(0)
    assert received
    evt = received[0]
    assert evt["task_id"] == "t1"
    assert evt["final_prediction"] == "bar"
    assert pytest.approx(evt["confidence"]) == 0.9

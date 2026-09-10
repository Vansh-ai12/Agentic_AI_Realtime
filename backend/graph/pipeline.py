import time
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from agents.planner import plan_query
from agents.retrieval_orchestrator import retrieve_for_all_subquestions
from agents.synthesizer import synthesize_answer
from agents.citation_verifier import verify_all_citations
from agents.critic import critique_answer
from memory.long_term import write_memory, read_relevant_memories
from trackings.trace_logger import log_trace_event
from utils.run_manager import update_run_status

MAX_RETRIES = 3

class PipelineState(TypedDict):
    user_id: str
    original_query: str
    run_id: Optional[str]
    attempt_id: Optional[str]
    sub_questions: Optional[list]
    chunks: Optional[list]
    memories: Optional[list]
    answer: Optional[str]
    cited_chunk_ids: Optional[list]
    citations_verified: Optional[bool]
    verdict: Optional[str]
    critic_reason: Optional[str]
    retry_count: int
    memory_write_result: Optional[dict]


def memory_reader_node(state: PipelineState) -> PipelineState:
    start = time.time()
    memories = read_relevant_memories(user_id=state["user_id"], query=state["original_query"])
    state["memories"] = memories
    print(f"[Memory Reader] Found {len(memories)} relevant memories")

    log_trace_event(
        run_id=state.get("run_id"), attempt_id=state.get("attempt_id"),
        node_name="memory_reader",
        input_data={"query": state["original_query"]},
        output_data={"memories_found": len(memories)},
        latency_ms=int((time.time() - start) * 1000)
    )
    return state


def planner_node(state: PipelineState) -> PipelineState:
    start = time.time()
    result = plan_query(state["original_query"], state.get("run_id"), state.get("attempt_id"))
    state["sub_questions"] = result["sub_questions"]

    log_trace_event(
        run_id=state.get("run_id"), attempt_id=state.get("attempt_id"),
        node_name="planner",
        input_data={"query": state["original_query"]},
        output_data={"sub_questions": result["sub_questions"]},
        tokens_used=result.get("tokens_in", 0) + result.get("tokens_out", 0),
        latency_ms=int((time.time() - start) * 1000)
    )
    return state


def retriever_node(state: PipelineState) -> PipelineState:
    start = time.time()
    chunks = retrieve_for_all_subquestions(state["sub_questions"], user_id=state["user_id"])
    state["chunks"] = chunks

    log_trace_event(
        run_id=state.get("run_id"), attempt_id=state.get("attempt_id"),
        node_name="retriever",
        input_data={"sub_questions": state["sub_questions"]},
        output_data={"chunks_retrieved": len(chunks)},
        latency_ms=int((time.time() - start) * 1000)
    )
    return state


def synthesizer_node(state: PipelineState) -> PipelineState:
    start = time.time()
    critic_feedback = state.get("critic_reason") if state.get("verdict") == "reject" else None
    result = synthesize_answer(
        state["original_query"],
        state["chunks"],
        memories=state.get("memories"),
        run_id=state.get("run_id"),
        attempt_id=state.get("attempt_id"),
        critic_feedback=critic_feedback,
        previous_answer=state.get("answer"),
        previous_cited_ids=state.get("cited_chunk_ids")
    )
    state["answer"] = result["answer"]
    state["cited_chunk_ids"] = result["cited_chunk_ids"]
    state["retry_count"] = state.get("retry_count", 0) + (1 if critic_feedback else 0)

    log_trace_event(
        run_id=state.get("run_id"), attempt_id=state.get("attempt_id"),
        node_name="synthesizer",
        input_data={"is_retry": critic_feedback is not None, "critic_feedback": critic_feedback},
        output_data={"answer": result["answer"], "cited_chunk_ids": result["cited_chunk_ids"]},
        tokens_used=result.get("tokens_in", 0) + result.get("tokens_out", 0),
        latency_ms=int((time.time() - start) * 1000)
    )
    return state


def citation_verifier_node(state: PipelineState) -> PipelineState:
    start = time.time()
    synth_result = {"answer": state["answer"], "cited_chunk_ids": state["cited_chunk_ids"]}
    verification = verify_all_citations(synth_result, state["chunks"], state.get("run_id"), state.get("attempt_id"))
    state["citations_verified"] = verification["all_supported"]

    log_trace_event(
        run_id=state.get("run_id"), attempt_id=state.get("attempt_id"),
        node_name="citation_verifier",
        input_data={"cited_chunk_ids": state["cited_chunk_ids"]},
        output_data={"all_supported": verification["all_supported"]},
        latency_ms=int((time.time() - start) * 1000)
    )
    return state


def critic_node(state: PipelineState) -> PipelineState:
    start = time.time()
    result = critique_answer(
        state["original_query"],
        state["answer"],
        state["citations_verified"],
        run_id=state.get("run_id"),
        attempt_id=state.get("attempt_id")
    )
    state["verdict"] = result["verdict"]
    state["critic_reason"] = result["reason"]

    log_trace_event(
        run_id=state.get("run_id"), attempt_id=state.get("attempt_id"),
        node_name="critic",
        input_data={"answer": state["answer"], "citations_verified": state["citations_verified"]},
        output_data={"verdict": result["verdict"], "reason": result["reason"]},
        tokens_used=result.get("tokens_in", 0) + result.get("tokens_out", 0),
        latency_ms=int((time.time() - start) * 1000)
    )
    return state


def unresolved_node(state: PipelineState) -> PipelineState:
    state["verdict"] = "unresolved"
    state["critic_reason"] = f"Failed to produce an approved answer after {state['retry_count']} attempts. Last reason: {state.get('critic_reason', 'unknown')}"

    update_run_status(
        run_id=state.get("run_id"),
        status="unresolved",
        total_attempts=state.get("retry_count", 0),
        total_tokens=0
    )


    log_trace_event(
        run_id=state.get("run_id"), attempt_id=state.get("attempt_id"),
        node_name="unresolved",
        input_data={"retry_count": state["retry_count"]},
        output_data={"final_reason": state["critic_reason"]}
    )
    return state


def memory_writer_node(state: PipelineState) -> PipelineState:
    start = time.time()
    result = write_memory(
        user_id=state["user_id"],
        user_query=state["original_query"],
        answer=state["answer"],
        source_run_id=state.get("run_id")
    )
    state["memory_write_result"] = result

    update_run_status(
        run_id=state.get("run_id"),
        status="resolved",
        total_attempts=state.get("retry_count", 0) + 1,
        total_tokens=0  # optional — can wire this up properly later if you want a real total
    )

    log_trace_event(
        run_id=state.get("run_id"), attempt_id=state.get("attempt_id"),
        node_name="write_memory",
        input_data={"answer": state["answer"]},
        output_data={"memory_write_result": result},
        latency_ms=int((time.time() - start) * 1000)
    )
    return state


def route_after_critic(state: PipelineState) -> str:
    if state["verdict"] == "approve":
        return "write_memory"
    if state["retry_count"] >= MAX_RETRIES:
        return "unresolved"
    return "retry"


def build_pipeline():
    graph = StateGraph(PipelineState)

    graph.add_node("memory_reader", memory_reader_node)
    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("citation_verifier", citation_verifier_node)
    graph.add_node("critic", critic_node)
    graph.add_node("unresolved", unresolved_node)
    graph.add_node("write_memory", memory_writer_node)

    graph.set_entry_point("memory_reader")
    graph.add_edge("memory_reader", "planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "synthesizer")
    graph.add_edge("synthesizer", "citation_verifier")
    graph.add_edge("citation_verifier", "critic")

    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "write_memory": "write_memory",
            "retry": "synthesizer",
            "unresolved": "unresolved"
        }
    )
    graph.add_edge("write_memory", END)
    graph.add_edge("unresolved", END)

    return graph.compile()
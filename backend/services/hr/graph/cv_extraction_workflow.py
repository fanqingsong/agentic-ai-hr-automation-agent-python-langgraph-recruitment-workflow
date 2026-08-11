# ============================================================================
# Graph1: CV extraction workflow (upload -> extract -> summary -> save to MongoDB)
# ============================================================================

from langgraph.graph import StateGraph, END

from backend.schemas.hr import CVExtractionState
from backend.services.hr.graph.nodes import (
    upload_cv_node,
    extract_cv_data_node,
    generate_summary_node,
    save_candidate_to_mongodb,
    index_candidate_knowledge_node,
)


def create_cv_extraction_workflow():
    """Build and compile the CV extraction graph (no job, no evaluation).

    Graph topology:
      [upload_cv] -> [extract_cv_data_node] -> [generate_summary] -> [save_candidate_to_mongodb]
        -> [index_candidate_knowledge] -> END

    The last node syncs the just-saved candidate into Qdrant (vectors) and
    Neo4j (graph). MongoDB is already the source of truth by this point, so a
    failure there is recorded in state["errors"] but never rolls back or
    blocks the response.
    """
    graph = StateGraph(CVExtractionState)

    graph.add_node("upload_cv", upload_cv_node)
    graph.add_node("extract_cv_data_node", extract_cv_data_node)
    graph.add_node("generate_summary", generate_summary_node)
    graph.add_node("save_candidate_to_mongodb", save_candidate_to_mongodb)
    graph.add_node("index_candidate_knowledge", index_candidate_knowledge_node)

    graph.set_entry_point("upload_cv")
    graph.add_edge("upload_cv", "extract_cv_data_node")
    graph.add_edge("extract_cv_data_node", "generate_summary")
    graph.add_edge("generate_summary", "save_candidate_to_mongodb")
    graph.add_edge("save_candidate_to_mongodb", "index_candidate_knowledge")
    graph.add_edge("index_candidate_knowledge", END)

    return graph.compile()

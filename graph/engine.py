from langgraph.graph import StateGraph, START
from .nodes import spec_synthesizer, planner, scaffolder, builder, fixer, preview_deploy, log_entry
from langsmith import traceable

def make_graph():
    g = StateGraph(dict)

    g.add_node("SpecSynthesizer", spec_synthesizer)
    g.add_node("Planner", planner)
    g.add_node("Scaffolder", scaffolder)
    g.add_node("Builder", builder)
    g.add_node("Fixer", fixer)
    g.add_node("PreviewDeploy", preview_deploy)

    g.add_edge(START, "SpecSynthesizer")
    g.add_edge("SpecSynthesizer", "Planner")
    g.add_edge("Planner", "Scaffolder")
    g.add_edge("Scaffolder", "Builder")
    
    def should_retry(state):
        max_retries = 3
        current_retries = state.get("build_retry_count", 0)
        fixer_made_changes = state.get("fixer_applied_fixes", False)
        build_successful = state.get("run_url") is not None
        
        print(f"should_retry: retries={current_retries}/{max_retries}, fixer_made_changes={fixer_made_changes}, build_successful={build_successful}")
        
        return fixer_made_changes and not build_successful and current_retries < max_retries

    # After Builder: if there's an error OR no run_url (build not successful) -> go to Fixer
    g.add_conditional_edges(
        "Builder",
        lambda state: "Fixer" if state.get("last_error") or not state.get("run_url") else "PreviewDeploy"
    )
    
    # After Fixer: if should_retry conditions are met -> go to Builder, else -> PreviewDeploy
    g.add_conditional_edges(
        "Fixer",
        lambda state: "Builder" if should_retry(state) else "PreviewDeploy"
    )

    return g.compile()

_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = make_graph()
    return _graph

@traceable
def run_graph(initial_state: dict) -> dict:
    g = get_graph()
    try:
        out = g.invoke(initial_state)

        print("FINAL STATE KEYS:", list(out.keys()))
        print("repo_path:", out.get("repo_path"))
        print("slug:", out.get("slug"))
        print("run_url:", out.get("run_url"))
        print("last_error:", out.get("last_error"))
        print("task_log:", [(entry["node"], entry["status"]) for entry in out.get("task_log", [])])

        return out
    except Exception as e:
        print(f"Graph execution failed: {e}")
        initial_state["task_log"] = initial_state.get("task_log", []) + [log_entry("Graph", "err", str(e))]
        initial_state["last_error"] = str(e)
        return initial_state
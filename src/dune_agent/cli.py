import typer
from .logging import configure_logging, logger
from .config import settings
from .workflows.graph import build_graph
from .mcp_server.server import run_mcp_server


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command("run-workflow")
def run_workflow(user_input: str = typer.Argument("hello")):
    configure_logging()
    logger.info("startup", env=settings.env)
    graph = build_graph()
    state = {"tenant_id": settings.tenant_id, "user_input": user_input, "state": "probe"}
    final = graph.invoke(state)
    typer.echo(final.get("agent_output", ""))


@app.command("start-mcp")
def start_mcp():
    configure_logging()
    logger.info("startup_mcp", transport=settings.mcp_server_transport)
    run_mcp_server()


if __name__ == "__main__":
    app()

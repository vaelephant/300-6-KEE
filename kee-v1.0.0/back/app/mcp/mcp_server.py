"""stdio MCP server (`python -m app.mcp`) — tool kee_get_context."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.mcp.mcp_context import mcp_fetch_pack, mcp_pack_text

mcp_server = FastMCP(
    "KEE",
    instructions=(
        "Knowledge Evolution Engine egress plugin. "
        "Call kee_get_context to retrieve a trust-filtered, cited context pack. "
        "Answer only from grounded context; keep [K#] citations."
    ),
)


@mcp_server.tool()
async def kee_get_context(
    question: str,
    top_k: int = 6,
    min_trust: float = 0.45,
    domain: str | None = None,
    include_guarded: bool = True,
) -> str:
    """Retrieve a grounded KEE context pack for agent answering.

    Returns JSON with protocol kee-agent-context/1.0, instructions,
    and context_pack (context text, citations, grounded flag).
    Use only grounded evidence; if grounded is false, say evidence is insufficient.
    """
    pack = await mcp_fetch_pack(
        question=question,
        top_k=top_k,
        min_trust=min_trust,
        domain=domain,
        include_guarded=include_guarded,
    )
    return mcp_pack_text(pack)


def run_mcp() -> None:
    mcp_server.run(transport="stdio")


# Back-compat aliases used by `python -m app.mcp`
mcp = mcp_server
run = run_mcp


if __name__ == "__main__":
    run_mcp()

from __future__ import annotations

from typing import Optional

from google.adk.tools import BaseTool
from langchain_core.tools import tool
from tavily import TavilyClient


def _build_query(
    query: str,
    *,
    entity: Optional[str] = None,
    period: Optional[str] = None,
    metric: Optional[str] = None,
    extra_context: Optional[str] = None,
) -> str:
    """
    Build a normalized search query while keeping the public tools consistent.
    """
    parts = [query.strip()]

    if entity:
        parts.append(f"Entity: {entity}")

    if period:
        parts.append(f"Period: {period}")

    if metric:
        parts.append(f"Metric: {metric}")

    if extra_context:
        parts.append(extra_context)

    return " | ".join(parts)


def _search_tavily(
    query: str,
    *,
    include_domains: Optional[list[str]] = None,
    max_results: int = 5,
):
    """
    Shared TavilyClient implementation.

    The generated `answer` is a discovery aid. Individual result URLs/content
    should be treated as the evidence layer by downstream research agents.
    """
    client = TavilyClient()

    kwargs = {
        "query": query,
        "include_answer": "advanced",
        "topic": "finance",
        "search_depth": "advanced",
        "max_results": max_results,
    }

    if include_domains:
        kwargs["include_domains"] = include_domains

    response = client.search(**kwargs)

    search_results = []
    for i, result in enumerate(response.get("results")):
        search_result = (f"# Result {i+1}\n"
                         f"**Title**: {result.get('title', 'N/A')}\n"
                         f"**Content**: {result.get('content', 'N/A')}\n"
                         f"**Source**: {result.get('url', 'N/A')}\n")
        search_results.append(search_result)

    join_search_results = '\n\n'.join(search_results)

    return f"""
    ### Search Results    
    
    ## Search Query
    {response.get("query")}
    
    ## Ground Truths
    {join_search_results}
    
    ## Synthesized Summary***
    {response.get("answer")}
    """

@tool
def finance_web_search(
    query: str,
    entity: str | None = None,
    period: str | None = None,
    max_results: int = 5,
):
    """
    Search the financial web for broad company, market, industry, and
    financial-research information.

    Best for:
    - financial news and analysis
    - secondary-source evidence
    - industry and market context
    - discovering relevant filings or company disclosures

    Prefer more authoritative source-specific tools when the required evidence
    is expected to exist in regulatory filings, company disclosures, or other
    specialized sources.

    The generated Tavily answer is a discovery aid, not independent evidence.
    """
    search_query = _build_query(
        query,
        entity=entity,
        period=period,
    )
    return _search_tavily(search_query, max_results=max_results)


@tool
def sec_filing_search(
    query: str,
    entity: str | None = None,
    period: str | None = None,
    filing_type: str | None = None,
    max_results: int = 5,
):
    """
    Search SEC and regulatory filing evidence.

    Best for:
    - 10-K annual reports
    - 10-Q quarterly reports
    - 8-K disclosures
    - DEF 14A proxy statements
    - reported financial statements
    - governance disclosures
    - capital allocation and debt disclosures

    Prefer this tool when the desired claim is expected to be disclosed in
    a regulatory filing.
    """
    search_query = _build_query(
        query,
        entity=entity,
        period=period,
        extra_context=(
            f"Filing type: {filing_type}"
            if filing_type
            else None
        ),
    )
    return _search_tavily(
        search_query,
        include_domains=["sec.gov"],
        max_results=max_results,
    )


@tool
def company_ir_search(
    query: str,
    entity: str,
    period: str | None = None,
    company_domains: list[str] | None = None,
    max_results: int = 5,
):
    """
    Search official company investor-relations and corporate disclosures.

    Best for:
    - earnings releases
    - shareholder letters
    - investor presentations
    - capital allocation commentary
    - official company guidance
    - strategic announcements
    - company-reported financial disclosures

    Use this when the company itself is the preferred source.
    """
    search_query = _build_query(
        query,
        entity=entity,
        period=period,
    )
    return _search_tavily(
        search_query,
        include_domains=company_domains,
        max_results=max_results,
    )


@tool
def earnings_transcript_search(
    query: str,
    entity: str,
    period: str | None = None,
    max_results: int = 5,
):
    """
    Search earnings-call transcripts and management commentary.

    Best for:
    - management explanations of capital allocation
    - investment rationale
    - strategic priorities
    - financial-discipline commentary
    - AI and infrastructure investment rationale
    - outlook and guidance

    Treat transcript content as management statements. Corroborate factual
    financial figures with company or regulatory sources where appropriate.
    """
    search_query = _build_query(
        query,
        entity=entity,
        period=period,
        extra_context="earnings call transcript management commentary",
    )
    return _search_tavily(search_query, max_results=max_results)


@tool
def market_data_search(
    query: str,
    entity: str | None = None,
    period: str | None = None,
    metric: str | None = None,
    max_results: int = 5,
):
    """
    Search for market and security-level financial data.

    Best for:
    - stock prices
    - historical returns
    - valuation metrics
    - market capitalization
    - trading volume
    - analyst estimates
    - market-based performance statistics

    Use this for market-observable information rather than company-reported
    accounting or governance disclosures.
    """
    search_query = _build_query(
        query,
        entity=entity,
        period=period,
        metric=metric,
    )
    return _search_tavily(search_query, max_results=max_results)


@tool
def executive_compensation_search(
    query: str,
    entity: str,
    period: str | None = None,
    executive_name: str | None = None,
    max_results: int = 5,
):
    """
    Search regulatory and company disclosures specifically for executive
    compensation and governance evidence.

    Best for:
    - DEF 14A proxy statements
    - executive compensation tables
    - annual incentive metrics
    - performance share units (PSUs)
    - long-term incentive plans
    - performance targets
    - vesting conditions
    - compensation committee disclosures
    - CEO/CFO compensation design
    - shareholder-performance alignment metrics

    Prefer this tool when the research question concerns executive incentives
    or compensation design.
    """
    extra_context = "executive compensation proxy DEF 14A"

    if executive_name:
        extra_context += f" | Executive: {executive_name}"

    search_query = _build_query(
        query,
        entity=entity,
        period=period,
        extra_context=extra_context,
    )
    return _search_tavily(
        search_query,
        include_domains=["sec.gov"],
        max_results=max_results,
    )


@tool
def economic_data_search(
    query: str,
    entity: str | None = None,
    period: str | None = None,
    metric: str | None = None,
    max_results: int = 5,
):
    """
    Search for macroeconomic and economic indicator data.

    Best for:
    - inflation and CPI/PCE
    - GDP and economic growth
    - unemployment and employment
    - interest rates and policy rates
    - Treasury yields
    - money supply
    - credit conditions
    - consumer and business indicators
    - country, regional, or global economic statistics

    Prefer official statistical agencies, central banks, Treasury departments,
    and other primary economic-data sources when available.
    """
    search_query = _build_query(
        query,
        entity=entity,
        period=period,
        metric=metric,
    )
    return _search_tavily(search_query, max_results=max_results)

research_tools: list[BaseTool] = [
    finance_web_search,
    sec_filing_search,
    company_ir_search,
    earnings_transcript_search,
    market_data_search,
    executive_compensation_search,
    economic_data_search,
]
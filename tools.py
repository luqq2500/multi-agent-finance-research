"""
Revised research tools.

Changes from the version this is based on, and why:

1. company_ir_search now REQUIRES company_domains. Previously it was
   Optional[list[str]] = None, and when omitted — which nothing in
   SUBAGENT_RESEARCHER ever instructed an agent to avoid — the tool ran
   `include_domains=None`, i.e. a fully unrestricted web search, despite its
   docstring promising "official company investor-relations." sec_filing_search
   and executive_compensation_search already hardcode `include_domains=["sec.gov"]`
   and are genuinely enforced; company_ir_search was the one tool whose
   restriction was caller-optional. This is very likely a real contributor to
   the aggregator-sourced content (WSJ, Yahoo Finance, moomoo, Seeking Alpha,
   Scribd) that kept showing up under "company IR" style findings across
   several diagnostic runs, despite explicit primary-source-preference
   instructions in SUBAGENT_RESEARCHER — no prompt fix reaches a restriction
   the tool itself doesn't enforce. Making it required forces an explicit,
   visible choice: supply real domains, or don't use this tool. If the caller
   doesn't know a company's official domain, the docstring below points it at
   finance_web_search to discover one first, or executive_compensation_search
   / sec_filing_search for anything that's actually a regulatory disclosure.

2. Result counts now have per-tool guidance and code-level clamping. Every
   tool previously defaulted to 5 with no explanation of when to change it —
   a parameter an agent has no signal to ever adjust just sits at its default.
   sec_filing_search and executive_compensation_search default higher (10):
   both have repeatedly failed to surface deep-table figures (proxy
   compensation tables, Item 6.B-style disclosures) that a narrower result
   set is less likely to contain at all. This raises RECALL — the odds the
   right snippet is even in the candidate set — it does not fix the separate,
   structural fact that snippet search cannot page into a document once
   located; that limitation is unchanged. `_search_tavily` now clamps
   max_results to Tavily's actual 1-20 range regardless of what a caller
   requests, since nothing previously stopped an out-of-range value reaching
   the API.

3. topic was hardcoded to "finance" for every tool, including
   finance_web_search, despite its docstring promising "financial news."
   Tavily's news-topic mode does recency-weighted indexing that finance-topic
   mode does not use. Added a dedicated news_search tool on topic="news" with
   a `days` recency window, and an optional `time_range` parameter on the two
   tools where recency genuinely matters (finance_web_search, market_data_search).
   Left it OFF period-scoped regulatory tools (sec_filing_search,
   company_ir_search, earnings_transcript_search, executive_compensation_search,
   economic_data_search) — a fiscal-year-scoped filing request shouldn't also
   be constrained by "past week," and mixing the two signals is more likely to
   confuse than help.

4. company_ir_search's and news_search's docstrings explicitly flag their
   citations as needing the [secondary-sourced]/[aggregator-sourced] tags
   SUBAGENT_RESEARCHER's Evidence Rules define, right at the point of tool
   selection rather than only in the system prompt read once at the start of
   the conversation — cheap, and consistent with the finding across several
   diagnostic runs that instructions repeated closer to the decision point
   hold up better than ones stated once and far away.
"""

from __future__ import annotations

from typing import Optional

from google.adk.tools import BaseTool
from langchain_core.tools import tool
from tavily import TavilyClient

MIN_RESULTS = 1
MAX_RESULTS = 20  # Tavily's actual ceiling — clamp here, not per-tool.


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
        topic: str = "finance",
        time_range: Optional[str] = None,
        days: Optional[int] = None,
):
    """
    Shared TavilyClient implementation.

    The generated `answer` is a discovery aid. Individual result URLs/content
    should be treated as the evidence layer by downstream research agents.
    """
    client = TavilyClient()

    max_results = max(MIN_RESULTS, min(int(max_results), MAX_RESULTS))

    kwargs = {
        "query": query,
        "include_answer": "advanced",
        "topic": topic,
        "search_depth": "advanced",
        "max_results": max_results,
    }

    if include_domains:
        kwargs["include_domains"] = include_domains

    if time_range:
        kwargs["time_range"] = time_range

    if days is not None and topic == "news":
        kwargs["days"] = days

    response = client.search(**kwargs)

    search_results = []
    for i, result in enumerate(response.get("results")):
        search_result = (f"# Result {i + 1}\n"
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
        max_results: int = 8,
        time_range: str | None = None,
):
    """
    Search the financial web for broad company, market, industry, and
    financial-research information.

    Best for:
    - financial news and analysis
    - secondary-source evidence
    - industry and market context
    - discovering relevant filings or company disclosures (including, when
      you don't yet know it, a company's official investor-relations domain
      to use with company_ir_search)

    Prefer more authoritative source-specific tools when the required evidence
    is expected to exist in regulatory filings, company disclosures, or other
    specialized sources. Results here are NOT restricted to primary sources —
    tag any figure sourced from here as [secondary-sourced] or
    [aggregator-sourced] per your evidence rules, rather than presenting it
    with the same confidence as a filing- or IR-sourced figure.

    max_results: broaden (10-20) for exploratory queries where you don't yet
    know which source will have the answer; narrow (5-8, the default) once
    you've identified a specific topic or source class to focus on.

    time_range: optional recency filter ("day", "week", "month", "year") for
    genuinely current questions. Leave unset for anything period-scoped to a
    specific fiscal year or quarter — recency filtering and an explicit past
    period are conflicting signals.

    The generated Tavily answer is a discovery aid, not independent evidence.
    """
    search_query = _build_query(
        query,
        entity=entity,
        period=period,
    )
    return _search_tavily(search_query, max_results=max_results, time_range=time_range)


@tool
def sec_filing_search(
        query: str,
        entity: str | None = None,
        period: str | None = None,
        filing_type: str | None = None,
        max_results: int = 10,
):
    """
    Search SEC and regulatory filing evidence. Restricted to sec.gov.

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

    max_results defaults higher (10) than other tools because the figures
    this tool is asked for are often buried deep in a filing (a specific
    line item, a numbered subsection, a table) rather than stated near the
    top — a narrow result set is more likely to simply miss the one snippet
    that contains it. Raise further (up to 20) when searching for a
    specific deep-table value you have reason to believe is disclosed but
    haven't yet surfaced; narrow back down once you've found the right
    filing and are confirming a known figure. This does not help if the
    figure is in a part of the document snippets never reach — that's a
    different, structural problem no result count fixes; treat repeated
    misses on a correctly-identified filing as NOT FOUND, not as a signal
    to keep raising max_results indefinitely.
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
        company_domains: list[str],
        period: str | None = None,
        max_results: int = 8,
):
    """
    Search official company investor-relations and corporate disclosures,
    restricted to the domain(s) you supply.

    Best for:
    - earnings releases
    - shareholder letters
    - investor presentations
    - capital allocation commentary
    - official company guidance
    - strategic announcements
    - company-reported financial disclosures

    Use this when the company itself is the preferred source.

    company_domains is REQUIRED — this tool has no default restriction, and
    a call without real domains would silently become an unrestricted web
    search while still looking like an "official source" result to whatever
    reads your report. If you don't already know the company's official
    domain(s) (common patterns: "ir.<company>.com", "investor.<company>.com",
    "<company>.com/investor-relations" — but these vary and guessing wrong
    just returns nothing, which is a visible failure, not a silent one),
    find it first with finance_web_search, or use sec_filing_search /
    executive_compensation_search instead if what you actually need is a
    regulatory disclosure rather than a company communication.

    max_results defaults to 8; raise toward 15-20 if you're confident in the
    domain(s) but not yet finding the specific release or presentation you
    need, narrow toward 5 once you've located the right page or document.
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
        max_results: int = 8,
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

    max_results defaults to 8 — a single call for one quarter's commentary
    doesn't need many results, but broaden toward 15-20 if you need to locate
    which quarter's call actually covers the topic you're after and haven't
    identified it yet.
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
        time_range: str | None = None,
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

    max_results defaults low (5) — market data queries usually have one
    canonical current answer rather than many candidate sources to sift
    through; raise it only if you're pulling a historical series across
    multiple dates rather than a single current figure.

    time_range: optional recency filter ("day", "week", "month", "year"),
    useful for "current" or "as of today" market data. Leave unset when the
    query already specifies a historical date or period.
    """
    search_query = _build_query(
        query,
        entity=entity,
        period=period,
        metric=metric,
    )
    return _search_tavily(search_query, max_results=max_results, time_range=time_range)


@tool
def executive_compensation_search(
        query: str,
        entity: str,
        period: str | None = None,
        executive_name: str | None = None,
        max_results: int = 10,
):
    """
    Search regulatory and company disclosures specifically for executive
    compensation and governance evidence. Restricted to sec.gov.

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

    max_results defaults higher (10) for the same reason as sec_filing_search:
    compensation tables and performance-metric weightings are typically deep
    in a proxy statement's numbered subsections, not near the top, so a
    narrow result set is disproportionately likely to miss them. This raises
    the odds the right snippet is retrieved; it does not mean the figure is
    retrievable if it genuinely sits below what any snippet exposes — several
    prior runs found detailed incentive weightings structurally LOW-YIELD
    through search regardless of result count. If a correctly-identified
    filing keeps returning nothing after raising max_results, that is your
    answer: report NOT FOUND rather than continuing to raise it.
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

    max_results defaults low (5) — a specific economic indicator for a
    specific period usually has one authoritative figure rather than many
    candidate sources; raise it only if you're comparing how a figure is
    reported across multiple statistical agencies or need a longer time
    series.
    """
    search_query = _build_query(
        query,
        entity=entity,
        period=period,
        metric=metric,
    )
    return _search_tavily(search_query, max_results=max_results)


@tool
def news_search(
        query: str,
        entity: str | None = None,
        period: str | None = None,
        max_results: int = 8,
        days: int | None = None,
):
    """
    Search recent financial and business news coverage, using Tavily's
    news-optimized index rather than general web results.

    Best for:
    - recent company announcements, executive changes, or events
    - breaking developments not yet reflected in filings or IR pages
    - press coverage of earnings, guidance changes, or strategic moves
    - time-sensitive "recent" or "latest" questions

    This tool is recency-biased and news-source-biased BY DESIGN — results
    skew toward journalism and press coverage, not primary filings or
    official disclosures. Tag findings from this tool as [secondary-sourced]
    or [aggregator-sourced] per your evidence rules unless independently
    corroborated by a filing- or IR-based tool.

    Do not use this tool for a figure that should come from a regulatory
    filing or official disclosure — use sec_filing_search or
    company_ir_search for that, even if a news article also mentions the
    number; a news restatement of a filed figure is not the same evidence
    tier as the filing itself.

    max_results defaults to 8. days optionally narrows the lookback window
    (e.g. 7, 30, 90) — set it when "recent" needs to mean something specific
    rather than however Tavily's news relevance ranking interprets it.
    """
    search_query = _build_query(
        query,
        entity=entity,
        period=period,
    )
    return _search_tavily(
        search_query,
        max_results=max_results,
        topic="news",
        days=days,
    )


research_tools: list[BaseTool] = [
    finance_web_search,
    sec_filing_search,
    company_ir_search,
    earnings_transcript_search,
    market_data_search,
    executive_compensation_search,
    economic_data_search,
    news_search,
]
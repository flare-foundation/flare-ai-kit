"""Prompt templates for LLM-based pointwise reranking."""
# ruff: noqa: E501
# Long lines are intentional in prompts for readability

POINTWISE_SYSTEM_PROMPT = """You are a customer support answer service. Your task is to evaluate help center passages and score their relevance to a given customer query for a retrieval augmented generation (RAG) system.

Evaluation Process:
1. Analyze the customer's query to identify both explicit needs and implicit context including underlying user goals
2. Assess each passage's ability to directly resolve the query or provide substantive supporting information with actionable guidance
3. Score based on how effectively the passage addresses the query's core intent while considering potential interpretations

Grading Criteria:
<grading_scale>
10: EXCEPTIONAL match - Contains exact step-by-step instructions that perfectly match the query's specific scenario. Must include all required parameters/context and resolve the issue completely without any ambiguity. Reserved for definitive solutions that exactly mirror the user's described situation and require no interpretation.

9: NEAR-PERFECT solution - Contains all critical steps for resolution but may lack one minor non-essential detail. Addresses the precise query parameters with specialized information. Solution must be directly applicable without requiring adaptation or assumptions.

8: STRONG MATCH - Provides complete technical resolution through specific instructions, but may require simple logical inferences for full application. Covers all essential components but might need minor contextualization.

7: GOOD MATCH - Contains substantial relevant details that address core aspects of the query, but lacks one important element for complete resolution. Provides concrete guidance requiring some user interpretation.

6: PARTIAL match - General guidance on the right topic but lacks the specifics for direct application. May only resolve a subset of the request.

5: LIMITED relevance - Related context or approach, but indirect. Requires substantial effort to adapt to the user's exact need.

4: TANGENTIAL - Mentions related concepts/keywords with little practical connection to the request. Minimal actionable value.

3: VAGUE domain info - Talks about the general area but not the query's specifics. No concrete, actionable steps.

2: TOKEN overlap - Shares isolated terms without context or intent aligned to the request. Similarity is coincidental.

1: IRRELEVANT - Uses query terms in a completely unrelated way. No meaningful link to the user's goal.

0: UNRELATED - No thematic or contextual connection to the query at all.
</grading_scale>

Input Format:
<input_format>
<query>
// The customer's question or request
</query>
<passages>
<passage id='id0'>...</passage>
<passage id='id1'>...</passage>
...
</passages>
</input_format>

Output Format:
<output_format>
Return your response in a valid JSON (skip spaces):
{{"id0":score0,"id1":score1,...}}

Strict guidelines:
- Return ONLY a well-formed valid JSON with passage IDs as keys
- Each key must be a passage id in the format "idN"
- Each score must be an integer between 5 to 10. EXCLUDE passages that score below 5 (i.e. 0, 1, 2, 3 or 4)
- Integer values only, no decimals
- Skip spaces in the JSON
- No additional text or formatting
- Maintain original passage ID order
- Note: If NO passages score 5+, return empty JSON object
</output_format>

{few_shot_section}"""

POINTWISE_USER_TEMPLATE = """<query>{query}</query>
<passages>
{passages}
</passages>"""

DEFAULT_FEW_SHOT_EXAMPLES = """<examples>
Example 1:
<query>How do I reset my password?</query>
<passages>
<passage id='id0'>To reset your password, click 'Forgot Password' on the login page, enter your email, and follow the link sent to your inbox.</passage>
<passage id='id1'>Our company was founded in 2010 and has offices worldwide.</passage>
<passage id='id2'>Password requirements include at least 8 characters with one uppercase letter.</passage>
</passages>
Output: {"id0":10,"id2":6}

Example 2:
<query>What are your business hours?</query>
<passages>
<passage id='id0'>Contact our sales team for enterprise pricing options.</passage>
<passage id='id1'>We are open Monday to Friday, 9 AM to 5 PM EST. Weekend support is available via email only.</passage>
</passages>
Output: {"id1":10}
</examples>"""


def format_passages(passages: list[tuple[int, str]]) -> str:
    """
    Format passages for inclusion in the reranker prompt.

    Args:
        passages: List of tuples containing (passage_id, passage_text).

    Returns:
        Formatted string with passages in XML-like tags.

    """
    return "\n".join(
        f"<passage id='id{idx}'>{text}</passage>" for idx, text in passages
    )


def build_system_prompt(few_shot_examples: str | None = None) -> str:
    """
    Build the system prompt with optional custom few-shot examples.

    Args:
        few_shot_examples: Optional custom few-shot examples. If None,
                          uses DEFAULT_FEW_SHOT_EXAMPLES.

    Returns:
        Complete system prompt with few-shot examples.

    """
    examples = few_shot_examples or DEFAULT_FEW_SHOT_EXAMPLES
    few_shot_section = f"\n{examples}" if examples else ""
    return POINTWISE_SYSTEM_PROMPT.format(few_shot_section=few_shot_section)


def build_user_prompt(query: str, passages: list[tuple[int, str]]) -> str:
    """
    Build the user prompt with query and passages.

    Args:
        query: The user query.
        passages: List of tuples containing (passage_id, passage_text).

    Returns:
        Formatted user prompt.

    """
    return POINTWISE_USER_TEMPLATE.format(
        query=query, passages=format_passages(passages)
    )

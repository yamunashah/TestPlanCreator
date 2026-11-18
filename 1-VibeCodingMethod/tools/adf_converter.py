"""
adf_converter.py — Atlassian Document Format (ADF) → Plain Text / Markdown
Layer 3 Tool: Pure function, no Flask dependency, no side effects.
"""


def adf_to_markdown(node, depth=0) -> str:
    """
    Recursively converts an ADF JSON node to Markdown string.
    Handles all common ADF node types used in Jira descriptions/comments.
    """
    if node is None:
        return ""

    # If it's a plain string somehow
    if isinstance(node, str):
        return node

    node_type = node.get("type", "")
    content = node.get("content", [])
    text = node.get("text", "")
    attrs = node.get("attrs", {})
    marks = node.get("marks", [])

    # Apply marks (bold, italic, code, link)
    def apply_marks(t, mark_list):
        for mark in mark_list:
            mt = mark.get("type", "")
            if mt == "strong":
                t = f"**{t}**"
            elif mt == "em":
                t = f"*{t}*"
            elif mt == "code":
                t = f"`{t}`"
            elif mt == "link":
                href = mark.get("attrs", {}).get("href", "")
                t = f"[{t}]({href})"
            elif mt == "strike":
                t = f"~~{t}~~"
            elif mt == "underline":
                t = f"<u>{t}</u>"
        return t

    # --- Inline nodes ---
    if node_type == "text":
        return apply_marks(text, marks)

    if node_type == "hardBreak":
        return "\n"

    if node_type == "mention":
        display = attrs.get("text", attrs.get("id", ""))
        return f"@{display}"

    if node_type == "emoji":
        return attrs.get("text", "")

    if node_type == "inlineCard":
        url = attrs.get("url", "")
        return f"[{url}]({url})"

    # --- Block nodes ---
    if node_type == "doc":
        return "\n".join(adf_to_markdown(c, depth) for c in content).strip()

    if node_type == "paragraph":
        inner = "".join(adf_to_markdown(c, depth) for c in content)
        return inner + "\n"

    if node_type == "heading":
        level = attrs.get("level", 1)
        inner = "".join(adf_to_markdown(c, depth) for c in content)
        return "#" * level + " " + inner + "\n"

    if node_type == "bulletList":
        items = []
        for item in content:
            item_text = "".join(adf_to_markdown(c, depth + 1) for c in item.get("content", []))
            items.append("  " * depth + "- " + item_text.strip())
        return "\n".join(items) + "\n"

    if node_type == "orderedList":
        items = []
        for idx, item in enumerate(content, 1):
            item_text = "".join(adf_to_markdown(c, depth + 1) for c in item.get("content", []))
            items.append("  " * depth + f"{idx}. " + item_text.strip())
        return "\n".join(items) + "\n"

    if node_type == "listItem":
        return "".join(adf_to_markdown(c, depth) for c in content)

    if node_type == "blockquote":
        inner = "".join(adf_to_markdown(c, depth) for c in content)
        lines = inner.strip().split("\n")
        return "\n".join("> " + line for line in lines) + "\n"

    if node_type == "codeBlock":
        lang = attrs.get("language", "")
        inner = "".join(adf_to_markdown(c, depth) for c in content)
        return f"```{lang}\n{inner}\n```\n"

    if node_type == "rule":
        return "---\n"

    if node_type == "table":
        rows = []
        for row_node in content:
            cells = []
            for cell in row_node.get("content", []):
                cell_text = "".join(adf_to_markdown(c, depth) for c in cell.get("content", [])).strip()
                cells.append(cell_text)
            rows.append(cells)
        if not rows:
            return ""
        # Build markdown table
        header = "| " + " | ".join(rows[0]) + " |"
        separator = "| " + " | ".join(["---"] * len(rows[0])) + " |"
        body = "\n".join("| " + " | ".join(row) + " |" for row in rows[1:])
        return "\n".join(filter(None, [header, separator, body])) + "\n"

    if node_type in ("tableRow", "tableHeader", "tableCell"):
        return "".join(adf_to_markdown(c, depth) for c in content)

    if node_type == "media":
        alt = attrs.get("alt", "media")
        url = attrs.get("url", "")
        if url:
            return f"![{alt}]({url})\n"
        return f"[{alt}]\n"

    if node_type == "mediaGroup":
        return "".join(adf_to_markdown(c, depth) for c in content)

    if node_type == "mediaSingle":
        return "".join(adf_to_markdown(c, depth) for c in content)

    # Fallback: recurse into content
    if content:
        return "".join(adf_to_markdown(c, depth) for c in content)

    return text


def safe_convert_description(description_field) -> str:
    """
    Safely converts a Jira description field to markdown.
    Handles: ADF dict, plain string, or None.
    """
    if description_field is None:
        return ""
    if isinstance(description_field, str):
        return description_field
    if isinstance(description_field, dict):
        try:
            return adf_to_markdown(description_field)
        except Exception:
            return "[Could not parse description]"
    return str(description_field)


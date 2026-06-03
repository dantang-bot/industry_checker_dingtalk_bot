"""Format a HubSpot industry summary into a text section for DingTalk."""


def format_section(label: str, summary: dict) -> str:
    """Build one labeled industry breakdown block as plain text."""
    header = f"=== {label} ==="

    if summary["total"] == 0:
        return f"{header}\n(no contacts in this window)"

    lines = [
        header,
        f"Total contacts with industry: {summary['with_industry']}",
        "",
    ]
    if summary["distribution"]:
        pad = max(len(row["name"]) for row in summary["distribution"])
        for row in summary["distribution"]:
            pct = f"{row['percent']:.1f}%"
            lines.append(f"{row['name']:<{pad}}  {row['count']:>3}  {pct:>6}")
    return "\n".join(lines)

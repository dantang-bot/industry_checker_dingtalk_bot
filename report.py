"""Format a HubSpot industry summary into a markdown section for DingTalk."""


def format_section(label: str, summary: dict) -> str:
    """Build one labeled industry breakdown block as DingTalk-flavored markdown."""
    header = f"**{label}**"

    if summary["total"] == 0:
        return f"{header}\n\n_(no contacts in this window)_"

    lines = [
        header,
        "",
        f"Total contacts with industry: **{summary['with_industry']}**",
        "",
    ]
    for row in summary["distribution"]:
        pct = f"{row['percent']:.1f}".rstrip("0").rstrip(".")
        lines.append(f"- {row['name']}: {row['count']} ({pct}%)")
    return "\n".join(lines)

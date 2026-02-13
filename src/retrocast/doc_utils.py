"""Utilities for generating CLI documentation with cogapp."""

import re


def clean_help_output(text: str) -> str:
    """Clean CLI help output for documentation.

    Transforms rich-click output into markdown-compatible format:
    - Strips ANSI escape codes
    - Replaces Unicode box-drawing characters with ASCII equivalents
    - Wraps long lines to 100 characters for readability
    - Replaces host-specific paths with placeholders

    Args:
        text: Raw CLI help output text

    Returns:
        Cleaned and formatted text suitable for markdown documentation
    """
    # Strip ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)

    # Replace Unicode box-drawing characters with ASCII equivalents
    replacements = {
        '╭': '+', '╰': '+', '╮': '+', '╯': '+',
        '─': '-', '│': '|', '├': '+', '┤': '+',
        '┬': '+', '┴': '+', '┼': '+',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Replace host-specific config paths with placeholder
    text = re.sub(
        r'\[default:\s+.+?/config\.yaml\]',
        '[default: {PLATFORM_APP_DIR}/config.yaml]',
        text,
        flags=re.DOTALL
    )

    # Wrap long table lines to 100 characters for documentation readability
    lines = text.split('\n')
    fixed_lines = []
    target_width = 100

    for line in lines:
        if line.startswith('|') and line.endswith('|') and len(line) > target_width:
            content = line[1:-1]
            leading_spaces = len(content) - len(content.lstrip())

            if leading_spaces > 30:
                # Continuation line - just trim to target width
                trimmed = '|' + content[:target_width-2] + '|'
                fixed_lines.append(trimmed)
            else:
                # Check if content fits after removing trailing spaces
                content_stripped = content.rstrip()
                if len(content_stripped) < target_width - 2:
                    # Content fits, just needs padding adjustment
                    line = '|' + content_stripped.ljust(target_width - 2) + '|'
                    fixed_lines.append(line)
                else:
                    # Content is genuinely too long - need to wrap it
                    break_point = target_width - 2
                    spaces_in_content = [
                        i for i, c in enumerate(content[:break_point]) if c == ' '
                    ]
                    if spaces_in_content:
                        split_at = spaces_in_content[-1]
                        first_part = '|' + content[:split_at].rstrip()
                        first_part = (
                            first_part + ' ' * (target_width - 1 - len(first_part)) + '|'
                        )
                        remaining = content[split_at:].strip()
                        if remaining:  # Only create continuation if there's actual content
                            second_part = '|' + ' ' * 37 + remaining
                            second_part = (
                                second_part[:target_width-1].ljust(target_width-1) + '|'
                            )
                            fixed_lines.append(first_part)
                            fixed_lines.append(second_part)
                        else:
                            fixed_lines.append(first_part)
                    else:
                        # No good break point, just trim
                        fixed_lines.append('|' + content[:target_width-2] + '|')
        elif (
            line.startswith('+')
            and line.endswith('+')
            and '-' in line
            and len(line) > target_width
        ):
            # Border line - normalize to target width
            fixed_lines.append('+' + '-' * (target_width - 2) + '+')
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines)

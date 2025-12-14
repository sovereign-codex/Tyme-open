class CMSPreflightError(Exception):
    """Raised when a CMS command violates execution law."""
    pass


def preflight_validate(command: dict):
    """
    Enforces CMS Execution Law (Lesson 8) and
    Autonomous Safety Guarantees (Lesson 9).
    """

    op = command.get("op")

    if not op:
        raise CMSPreflightError("Missing required field: 'op'")

    # --- PATCH RULES ---
    if op == "patch":
        if "content" in command:
            raise CMSPreflightError(
                "Illegal CMS contract: 'patch' cannot include 'content'. "
                "Refused under Lesson 8 (Execution Law)."
            )

        if "mode" in command:
            raise CMSPreflightError(
                "Illegal CMS contract: 'patch' cannot include 'mode'. "
                "Refused under Lesson 9 (Scope Escalation)."
            )

        if "patch" not in command:
            raise CMSPreflightError(
                "Patch operation requires a 'patch' field."
            )

    # --- OVERWRITE RULES ---
    if op == "overwrite":
        if "patch" in command:
            raise CMSPreflightError(
                "Illegal CMS contract: 'overwrite' cannot include 'patch'."
            )

        if "content" not in command:
            raise CMSPreflightError(
                "Overwrite operation requires 'content'."
            )

    # --- CREATE RULES ---
    if op == "create":
        if "content" not in command:
            raise CMSPreflightError(
                "Create operation requires 'content'."
            )

    return True

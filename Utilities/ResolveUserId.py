def resolve_user_id(cursor, clerk_user_id: str) -> int:
    cursor.execute(
        "SELECT user_id FROM users WHERE clerk_user_id = %s",
        (clerk_user_id,)
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"No user found for clerk_user_id '{clerk_user_id}'")
    # Support both dict and tuple cursors
    return row["user_id"] if isinstance(row, dict) else row[0]

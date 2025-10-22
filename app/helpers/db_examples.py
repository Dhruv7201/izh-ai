"""Example usage of database query executor."""
from app.helpers.db_executor import query_executor


async def create_user_example(email: str, name: str):
    """Create a new user."""
    query = """
        INSERT INTO users (email, name)
        VALUES ($1, $2)
        RETURNING id, email, name, created_at
    """
    return await query_executor.fetch_one(query, email, name)


async def get_user_by_id(user_id: int):
    """Get user by ID."""
    query = "SELECT * FROM users WHERE id = $1"
    return await query_executor.fetch_one(query, user_id)


async def get_all_users():
    """Get all users."""
    query = "SELECT * FROM users ORDER BY created_at DESC"
    return await query_executor.fetch_all(query)


async def update_user(user_id: int, name: str):
    """Update user name."""
    query = """
        UPDATE users 
        SET name = $1, updated_at = CURRENT_TIMESTAMP 
        WHERE id = $2
        RETURNING *
    """
    return await query_executor.fetch_one(query, name, user_id)


async def delete_user(user_id: int):
    """Delete user."""
    query = "DELETE FROM users WHERE id = $1"
    return await query_executor.execute(query, user_id)


async def create_conversation_with_message():
    """Example of transaction usage."""
    async with query_executor.transaction() as conn:
        # Create conversation
        conv = await conn.fetchrow(
            "INSERT INTO conversations (user_id, title) VALUES ($1, $2) RETURNING id",
            1, "New Conversation"
        )
        
        # Create first message
        await conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES ($1, $2, $3)",
            conv['id'], "user", "Hello!"
        )
        
        return conv['id']

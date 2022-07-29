from lilybot import db


class ChatbotCustom(db.DatabaseTable):
    """Database table holding all custom options"""
    __tablename__ = "chatbot_custom"
    __uniques__ = "id"

    @classmethod
    async def initial_create(cls):
        """Create the table in the database"""
        async with db.Pool.acquire() as conn:
            await conn.execute(f"""CREATE TABLE IF NOT EXISTS {cls.__tablename__} (
                    guild_id int8 NOT NULL,
                    id serial PRIMARY KEY NOT NULL,
                    user_id int8 NULL,
                    regex varchar NOT NULL
                );
            """)

    def __init__(self, guild_id, user_id, regex, trigger_id=None):
        self.guild_id = guild_id
        self.id = trigger_id
        self.user_id = user_id
        self.regex = regex

    def __str__(self):
        return f"{self.id}, {self.guild_id}, {self.user_id}, {self.regex}"

    @classmethod
    async def get_by(cls, **filters):
        results = await super().get_by(**filters)
        result_list = []
        for result in results:
            obj = ChatbotCustom(guild_id=result.get("guild_id"), trigger_id=result.get("id"),
                                user_id=result.get("user_id"), regex=result.get("regex"))
            result_list.append(obj)
        return result_list

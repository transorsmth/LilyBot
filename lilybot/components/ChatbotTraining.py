from lilybot import db


class ChatbotTraining(db.DatabaseTable):
    """Database table mapping all training from chatbot"""
    __tablename__ = "chatbot_training"

    @classmethod
    async def initial_create(cls):
        """Create the table in the database"""
        async with db.Pool.acquire() as conn:
            await conn.execute(f"""CREATE TABLE IF NOT EXISTS {cls.__tablename__} (
                    user_name varchar NULL,
                    part1 varchar NOT NULL,
                    part2 varchar NOT NULL,
                    user_id int8 NOT NULL,
                    message_id int8 NULL,
                    channel_id int8 NULL,
                    guild_id int8 NULL,
                    is_manual bool NOT NULL DEFAULT true
                );
            """)

    def __init__(self, user_name, part1, part2, user_id, message_id, is_manual, guild_id):
        super().__init__()
        self.user_name = user_name
        self.part1 = part1
        self.part2 = part2
        self.user_id = user_id
        self.message_id = message_id
        self.is_manual = is_manual
        self.guild_id = guild_id

    @classmethod
    async def new_training(cls, user_name, part1, part2, user_id, message_id, is_manual, channel_id, guild_id):
        """Inserts new training into persistant training database"""
        async with db.Pool.acquire() as conn:
            await conn.execute(f"""
                        INSERT INTO {cls.__tablename__}
                        (user_name, part1, part2, user_id, message_id, is_manual, channel_id, guild_id)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
                    """, user_name, part1, part2, user_id, message_id,
                               is_manual, channel_id, guild_id)

    @classmethod
    async def get_by(cls, **kwargs):
        results = await super().get_by(**kwargs)
        result_list = []
        for result in results:
            obj = ChatbotTraining(user_id=result.get("user_id"), part1=result.get("part1"),
                                  part2=result.get("part2"), user_name=result.get("user_name"),
                                  message_id=result.get("message_id"), is_manual=result.get("is_manual"), guild_id=result.get("guild_id"))
            result_list.append(obj)
        return result_list

    async def version_1(self):
        async with db.Pool.acquire() as conn:
            await conn.execute(f"""
                ALTER TABLE {self.__tablename__}
                ADD COLUMN guild_id int8 NULL;
            """)

    __versions__ = [version_1]

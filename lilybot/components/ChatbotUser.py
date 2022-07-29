from lilybot import db


class ChatbotUserCache:
    """ A cached record of a user's XP.
        This has all of the fields of `MemberXP` except the primary key, and an additional `dirty` flag that indicates
        whether the record has been changed since it was loaded from the database or created.
    """

    def __init__(self, banned, messages, user_name, dirty):
        super().__init__()
        # self.user_id = user_id
        self.banned = banned
        self.messages = messages
        self.user_name = user_name
        self.dirty = dirty

    def __repr__(self):
        return f"<ChatbotUserCache user_name={self.user_name!r} messages={self.messages!r} " \
               f"banned={self.banned!r} dirty={self.dirty!r}> "

    @classmethod
    async def from_user_id(cls, user_id):
        """Returns ChatbotUserCache from user_id or empty if not found"""
        record = await ChatbotUser.get_user(user_id=user_id)
        if record is None:
            return cls(False, 0, "", True)
        else:
            return cls(record.banned, record.messages, record.user_name, False)

    @classmethod
    def from_record(cls, record):
        """Create a cache entry from a database record. This copies all shared fields and sets `dirty` to False."""
        return cls(record.banned, record.messages, record.user_name, False)


class ChatbotUser(db.DatabaseTable):
    """Database table mapping a user to their chatbot stuff"""
    __tablename__ = "chatbot_users"
    __uniques__ = "user_id"

    @classmethod
    async def initial_create(cls):
        """Create the table in the database"""
        async with db.Pool.acquire() as conn:
            await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {cls.__tablename__} (
                user_id int8 NOT NULL,
                banned bool NOT NULL DEFAULT false,
                messages int4 NULL DEFAULT 0,
                user_name varchar NULL,
                CONSTRAINT chatbot_users_pk PRIMARY KEY (user_id)
            );
            """)

    def __init__(self, user_id, banned, messages, user_name):
        super().__init__()
        self.user_id = user_id
        self.banned = banned
        self.messages = messages
        self.user_name = user_name

    @classmethod
    async def get_user(cls, **kwargs):
        """Returns single user"""
        results = await ChatbotUser.get_by(**kwargs)

        if results:
            return results[0]
        return None

    @classmethod
    async def get_by(cls, **kwargs):
        """Returns list of users fitting criteria"""
        results = await super().get_by(**kwargs)
        result_list = []
        for result in results:
            obj = ChatbotUser(user_id=result.get("user_id"), banned=result.get("banned"),
                              messages=result.get("messages"), user_name=result.get("user_name"))
            result_list.append(obj)
        return result_list

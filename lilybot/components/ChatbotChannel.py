from lilybot import db


class ChatbotChannelCache:
    """ A cached record of a user's XP.
        This has all of the fields of `MemberXP` except the primary key, and an additional `dirty` flag that indicates
        whether the record has been changed since it was loaded from the database or created.
    """

    def __init__(self, guild_id, messages, respond_in, last_message, train_in, trained_messages, channel_name,
                 dirty=False):
        super().__init__()
        self.guild_id = guild_id
        self.messages = messages
        self.respond_in = respond_in
        self.processing = 0
        self.last_message = last_message
        self.train_in = train_in
        self.trained_messages = trained_messages
        self.channel_name = channel_name
        self.dirty = dirty

    def __repr__(self):
        return f"<ChatbotChannelCache channel_name={self.channel_name!r} messages={self.messages!r} " \
               f"respond_in={self.respond_in!r} dirty={self.dirty!r}> "

    @classmethod
    async def from_channel_id(cls, channel_id, guild_id):
        """Loads from database or creates new channel"""
        record = await ChatbotChannel.get_channel(channel_id=channel_id)
        if record is None:
            return cls(guild_id, 0, False, None, False, 0, "", dirty=True)
        else:
            return cls(record.guild_id, record.messages, record.respond_in, record.last_message, record.train_in,
                       record.trained_messages, record.channel_name)

    @classmethod
    def from_record(cls, record):
        """Create a cache entry from a database record. This copies all shared fields and sets `dirty` to False."""
        return cls(record.guild_id, record.messages, record.respond_in, record.last_message, record.train_in,
                   record.trained_messages,
                   record.channel_name)


class ChatbotChannel(db.DatabaseTable):
    """Database table containing per-channel settings related to chatbot stuff."""
    __tablename__ = "chatbot_channels"
    __uniques__ = "channel_id"

    @classmethod
    async def initial_create(cls):
        """Create the table in the database"""
        async with db.Pool.acquire() as conn:
            await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {cls.__tablename__} (
                channel_id int8 NOT NULL,
                guild_id int8 NOT NULL,
                messages int4 NOT NULL DEFAULT 0,
                respond_in bool NOT NULL,
                processing int4 NOT NULL DEFAULT 0,
                last_message varchar NULL,
                train_in bool NOT NULL DEFAULT true,
                trained_messages int4 NOT NULL DEFAULT 0,
                channel_name varchar NULL,
                CONSTRAINT chatbot_channels_pkey PRIMARY KEY (channel_id)
            );
            CREATE UNIQUE INDEX chatbot_channels_channel_id_idx ON public.chatbot_channels USING btree (channel_id);
            CREATE INDEX chatbot_channels_guild_id_idx ON public.chatbot_channels USING btree (guild_id);
            """)

    def __init__(self, channel_id, guild_id, messages, respond_in, processing, last_message, train_in,
                 trained_messages, channel_name):
        super().__init__()
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.messages = messages
        self.respond_in = respond_in
        self.processing = processing
        self.last_message = last_message
        self.train_in = train_in
        self.trained_messages = trained_messages
        self.channel_name = channel_name

    @classmethod
    async def get_channel(cls, **kwargs):
        """Loads single channel from database"""
        results = await ChatbotChannel.get_by(**kwargs)

        if results:
            return results[0]
        return None

    def __str__(self):
        return f"<#{self.channel_id}>, {self.respond_in}, {self.train_in}"

    @classmethod
    async def get_by(cls, **kwargs):
        """Returns list of channels fitting criteria"""
        results = await super().get_by(**kwargs)
        result_list = []
        for result in results:
            obj = ChatbotChannel(channel_id=result.get("channel_id"), guild_id=result.get("guild_id"),
                                 messages=result.get("messages"),
                                 respond_in=result.get("respond_in"), processing=result.get("processing"),
                                 last_message=result.get("last_message"), train_in=result.get("train_in"),
                                 trained_messages=result.get(
                                     "trained_messages"),
                                 channel_name=result.get("channel_name"))
            result_list.append(obj)
        return result_list

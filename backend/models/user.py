"""user database models with authentication and tracking"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import bcrypt
from backend.config import settings

Base = declarative_base()


class User(Base):
    """user account with authentication and preferences"""
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    preferred_language = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)

    # relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    usage_stats = relationship("UserUsage", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password: str):
        """
        hash and set user password

        args:
            password: plain text password
        """
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """
        verify password against stored hash

        args:
            password: plain text password to verify

        returns:
            true if password matches, false otherwise
        """
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))


class Conversation(Base):
    """conversation session with message history"""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="new conversation")
    language = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    """individual message in conversation"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    tool_calls = Column(Text)  # json string of tool calls
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    conversation = relationship("Conversation", back_populates="messages")


class UserUsage(Base):
    """usage statistics and limits per user"""
    __tablename__ = "user_usage"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    total_messages = Column(Integer, default=0)
    total_conversations = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_tool_calls = Column(Integer, default=0)
    last_activity = Column(DateTime, default=datetime.utcnow)

    # usage breakdown
    resolve_medication_calls = Column(Integer, default=0)
    get_info_calls = Column(Integer, default=0)
    search_ingredient_calls = Column(Integer, default=0)
    check_stock_calls = Column(Integer, default=0)

    # relationships
    user = relationship("User", back_populates="usage_stats")


class UserDatabase:
    """user database manager with authentication and tracking"""

    def __init__(self, db_path: Optional[str] = None):
        """
        initialize user database connection

        args:
            db_path: optional path to sqlite database, uses config default if none
        """
        if db_path is None:
            db_path = settings.user_db_path

        # create engine and session
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        # initialize with demo users if empty
        self._init_demo_users()

    def _init_demo_users(self):
        """create demo users if database is empty"""
        session = self.Session()
        try:
            count = session.query(User).count()

            if count == 0:
                demo_users = [
                    # english users
                    {"id": "USER001", "email": "marilyn_monroe@example.com", "name": "Marilyn Monroe", "password": "demo123", "preferred_language": "en"},
                    {"id": "USER002", "email": "jim_carrey@example.com", "name": "Jim Carrey", "password": "demo123", "preferred_language": "en"},

                    # hebrew users
                    {"id": "USER003", "email": "gal_gadot@example.com", "name": "Gal Gadot", "password": "demo123", "preferred_language": "he"},
                    {"id": "USER004", "email": "lior_raz@example.com", "name": "Lior Raz", "password": "demo123", "preferred_language": "he"},
                    {"id": "USER005", "email": "adi_himelbloy@example.com", "name": "Adi Himelbloy", "password": "demo123", "preferred_language": "he"},

                    # russian users
                    {"id": "USER006", "email": "yulia_snigir@example.com", "name": "Yulia Snigir", "password": "demo123", "preferred_language": "ru"},
                    {"id": "USER007", "email": "alla_pugacheva@example.com", "name": "Alla Pugacheva", "password": "demo123", "preferred_language": "ru"},
                    {"id": "USER008", "email": "sergey_pakhomov@example.com", "name": "Sergey Pakhomov", "password": "demo123", "preferred_language": "ru"},

                    # arabic users
                    {"id": "USER009", "email": "adel_emam@example.com", "name": "Adel Emam", "password": "demo123", "preferred_language": "ar"},
                    {"id": "USER010", "email": "rami_malek@example.com", "name": "Rami Malek", "password": "demo123", "preferred_language": "ar"},
                ]

                for user_data in demo_users:
                    user = User(
                        id=user_data["id"],
                        email=user_data["email"],
                        name=user_data["name"],
                        preferred_language=user_data["preferred_language"]
                    )
                    user.set_password(user_data["password"])

                    # create usage stats
                    usage = UserUsage(user_id=user.id)

                    session.add(user)
                    session.add(usage)

                session.commit()
                print(f"✅ created {len(demo_users)} demo users (password: demo123)")

        finally:
            session.close()

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        authenticate user with email and password

        args:
            email: user email
            password: plain text password

        returns:
            user object if authenticated, none otherwise
        """
        session = self.Session()
        try:
            user = session.query(User).filter(User.email == email, User.is_active == True).first()

            if user and user.check_password(password):
                # update last login
                user.last_login = datetime.utcnow()
                session.commit()
                # refresh to load all attributes before detaching
                session.refresh(user)
                # detach from session
                session.expunge(user)
                return user

            return None
        finally:
            session.close()

    def get_user(self, user_id: str) -> Optional[User]:
        """
        get user by id

        args:
            user_id: user identifier

        returns:
            user object or none
        """
        session = self.Session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                session.refresh(user)
                session.expunge(user)
            return user
        finally:
            session.close()

    def create_conversation(self, user_id: str, language: str = "en") -> str:
        """
        create new conversation for user

        args:
            user_id: user identifier
            language: conversation language

        returns:
            conversation id
        """
        session = self.Session()
        try:
            import uuid
            conversation_id = f"CONV_{uuid.uuid4().hex[:12].upper()}"

            conversation = Conversation(
                id=conversation_id,
                user_id=user_id,
                language=language
            )

            session.add(conversation)

            # update user usage
            usage = session.query(UserUsage).filter(UserUsage.user_id == user_id).first()
            if usage:
                usage.total_conversations += 1
                usage.last_activity = datetime.utcnow()

            session.commit()
            return conversation_id
        finally:
            session.close()

    def add_message(self, conversation_id: str, role: str, content: str, tool_calls: Optional[str] = None, tokens: int = 0):
        """
        add message to conversation

        args:
            conversation_id: conversation identifier
            role: message role (user, assistant, system)
            content: message content
            tool_calls: json string of tool calls (optional)
            tokens: tokens used for this message
        """
        session = self.Session()
        try:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                tool_calls=tool_calls,
                tokens_used=tokens
            )

            session.add(message)

            # update conversation
            conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                conversation.updated_at = datetime.utcnow()

                # update user usage
                usage = session.query(UserUsage).filter(UserUsage.user_id == conversation.user_id).first()
                if usage:
                    usage.total_messages += 1
                    usage.total_tokens += tokens
                    usage.last_activity = datetime.utcnow()

            session.commit()
        finally:
            session.close()

    def track_tool_call(self, user_id: str, tool_name: str):
        """
        track tool usage for user

        args:
            user_id: user identifier
            tool_name: name of tool called
        """
        session = self.Session()
        try:
            usage = session.query(UserUsage).filter(UserUsage.user_id == user_id).first()
            if usage:
                usage.total_tool_calls += 1

                # track specific tool
                if tool_name == "resolve_medication_id":
                    usage.resolve_medication_calls += 1
                elif tool_name == "get_medication_info":
                    usage.get_info_calls += 1
                elif tool_name == "search_by_ingredient":
                    usage.search_ingredient_calls += 1
                elif tool_name == "check_stock":
                    usage.check_stock_calls += 1

                session.commit()
        finally:
            session.close()

    def get_conversation_history(self, conversation_id: str) -> List[dict]:
        """
        get full conversation history

        args:
            conversation_id: conversation identifier

        returns:
            list of message dictionaries
        """
        session = self.Session()
        try:
            messages = session.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at).all()

            history = []
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": msg.tool_calls,
                    "tokens": msg.tokens_used,
                    "timestamp": msg.created_at.isoformat()
                })

            return history
        finally:
            session.close()

    def get_user_usage(self, user_id: str) -> Optional[dict]:
        """
        get user usage statistics

        args:
            user_id: user identifier

        returns:
            usage statistics dictionary
        """
        session = self.Session()
        try:
            usage = session.query(UserUsage).filter(UserUsage.user_id == user_id).first()

            if usage:
                return {
                    "total_messages": usage.total_messages,
                    "total_conversations": usage.total_conversations,
                    "total_tokens": usage.total_tokens,
                    "total_tool_calls": usage.total_tool_calls,
                    "tool_breakdown": {
                        "resolve_medication": usage.resolve_medication_calls,
                        "get_info": usage.get_info_calls,
                        "search_ingredient": usage.search_ingredient_calls,
                        "check_stock": usage.check_stock_calls
                    },
                    "last_activity": usage.last_activity.isoformat() if usage.last_activity else None
                }

            return None
        finally:
            session.close()

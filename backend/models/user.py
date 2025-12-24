"""user database models with authentication and tracking"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import bcrypt
import json
from backend.domain.config import settings
from backend.domain.constants import PRESCRIPTION_ACTIVE_STATUSES
from backend.utils.db_context import get_db_session
from backend.repositories.user_repository import UserRepository

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


class Prescription(Base):
    """prescription record for medication fulfillment"""
    __tablename__ = "prescriptions"

    id = Column(String, primary_key=True)
    patient_id = Column(String, ForeignKey("users.id"), nullable=False)
    med_id = Column(String, nullable=False)
    prescriber_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    pickup_location = Column(String, nullable=False)
    notes = Column(Text)

    # status: pending, ready, expired
    status = Column(String, default="pending")

    # timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ready_at = Column(DateTime)
    picked_up_at = Column(DateTime)

    # relationships
    patient = relationship("User", foreign_keys=[patient_id])


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
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            pool_pre_ping=True,
            pool_recycle=3600
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self._repo = UserRepository(User, Conversation, Message, UserUsage, Prescription)

        # initialize with demo users if empty
        self._init_demo_users()

    def _init_demo_users(self):
        """create demo users if database is empty"""
        self.seed_users(force=False)

    def seed_users(self, force: bool = False) -> int:
        """
        seed demo users from json

        args:
            force: when true, delete existing users before seeding

        returns:
            number of users inserted
        """
        with get_db_session(self.Session, commit=True) as session:
            if force:
                session.query(UserUsage).delete()
                session.query(User).delete()

            count = self._repo.count_users(session)
            if count and not force:
                return 0

            with open(settings.users_json_path, 'r', encoding='utf-8') as f:
                demo_users = json.load(f)

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

                self._repo.add_user(session, user)
                self._repo.add_usage(session, usage)

            print(f"created {len(demo_users)} demo users (password: demo123)")
            return len(demo_users)

    def seed_prescriptions(self, force: bool = False) -> int:
        """
        seed demo prescriptions from json

        args:
            force: when true, delete existing prescriptions before seeding

        returns:
            number of prescriptions inserted
        """
        with get_db_session(self.Session, commit=True) as session:
            if force:
                session.query(Prescription).delete()

            existing = session.query(Prescription).count()
            if existing and not force:
                return 0

            with open(settings.prescriptions_json_path, 'r', encoding='utf-8') as f:
                prescriptions = json.load(f)

            inserted = 0
            for entry in prescriptions:
                prescription = Prescription(
                    id=entry["id"],
                    patient_id=entry["patient_id"],
                    med_id=entry["med_id"],
                    prescriber_name=entry["prescriber_name"],
                    quantity=entry["quantity"],
                    pickup_location=entry["pickup_location"],
                    notes=entry.get("notes"),
                    status=entry.get("status", "pending")
                )
                session.add(prescription)
                inserted += 1

            return inserted

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        authenticate user with email and password

        args:
            email: user email
            password: plain text password

        returns:
            user object if authenticated, none otherwise
        """
        with get_db_session(self.Session, commit=True) as session:
            user = self._repo.get_user_by_email(session, email, active_only=True)

            if user and user.check_password(password):
                # update last login
                user.last_login = datetime.utcnow()
                session.flush()
                # refresh to load all attributes before detaching
                session.refresh(user)
                # detach from session
                session.expunge(user)
                return user

            return None

    def get_user(self, user_id: str) -> Optional[User]:
        """
        get user by id

        args:
            user_id: user identifier

        returns:
            user object or none
        """
        with get_db_session(self.Session) as session:
            user = self._repo.get_user_by_id(session, user_id)
            if user:
                session.refresh(user)
                session.expunge(user)
            return user

    def create_conversation(self, user_id: str, language: str = "en") -> str:
        """
        create new conversation for user

        args:
            user_id: user identifier
            language: conversation language

        returns:
            conversation id
        """
        with get_db_session(self.Session, commit=True) as session:
            import uuid
            conversation_id = f"CONV_{uuid.uuid4().hex[:12].upper()}"

            conversation = Conversation(
                id=conversation_id,
                user_id=user_id,
                language=language
            )

            self._repo.add_conversation(session, conversation)
            self._repo.update_usage(
                session,
                user_id,
                conversations=1,
                last_activity=datetime.utcnow()
            )

            return conversation_id

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
        with get_db_session(self.Session, commit=True) as session:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                tool_calls=tool_calls,
                tokens_used=tokens
            )

            self._repo.add_message(session, message)

            # update conversation
            conversation = self._repo.get_conversation(session, conversation_id)
            if conversation:
                conversation.updated_at = datetime.utcnow()

                # update user usage
                self._repo.update_usage(
                    session,
                    conversation.user_id,
                    messages=1,
                    tokens=tokens,
                    last_activity=datetime.utcnow()
                )

    def track_tool_call(self, user_id: str, tool_name: str):
        """
        track tool usage for user

        args:
            user_id: user identifier
            tool_name: name of tool called
        """
        with get_db_session(self.Session, commit=True) as session:
            increments = {
                "tool_calls": 1,
                "resolve_medication": 1 if tool_name == "resolve_medication_id" else 0,
                "get_info": 1 if tool_name == "get_medication_info" else 0,
                "search_ingredient": 1 if tool_name == "search_by_ingredient" else 0,
                "check_stock": 1 if tool_name == "check_stock" else 0
            }
            self._repo.update_usage(session, user_id, **increments)

    def get_conversation_history(self, conversation_id: str) -> List[dict]:
        """
        get full conversation history

        args:
            conversation_id: conversation identifier

        returns:
            list of message dictionaries
        """
        with get_db_session(self.Session) as session:
            messages = self._repo.list_messages(session, conversation_id)

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

    def get_user_usage(self, user_id: str) -> Optional[dict]:
        """
        get user usage statistics

        args:
            user_id: user identifier

        returns:
            usage statistics dictionary
        """
        with get_db_session(self.Session) as session:
            usage = self._repo.get_usage(session, user_id)

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

    def get_user_prescriptions(self, user_id: str, active_only: bool = True) -> List[dict]:
        """
        get prescriptions for a user

        args:
            user_id: user identifier
            active_only: when true, return pending/ready only

        returns:
            list of prescription dicts
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            with get_db_session(self.Session) as session:
                prescriptions = self._repo.list_prescriptions(
                    session,
                    user_id,
                    active_only,
                    PRESCRIPTION_ACTIVE_STATUSES
                )
                results = []
                for prescription in prescriptions:
                    results.append({
                        "prescription_id": prescription.id,
                        "patient_id": prescription.patient_id,
                        "med_id": prescription.med_id,
                        "prescriber_name": prescription.prescriber_name,
                        "quantity": prescription.quantity,
                        "pickup_location": prescription.pickup_location,
                        "status": prescription.status,
                        "notes": prescription.notes,
                        "created_at": prescription.created_at.isoformat() if prescription.created_at else None,
                        "updated_at": prescription.updated_at.isoformat() if prescription.updated_at else None,
                        "ready_at": prescription.ready_at.isoformat() if prescription.ready_at else None,
                        "picked_up_at": prescription.picked_up_at.isoformat() if prescription.picked_up_at else None
                    })

                return results
        except Exception as e:
            logger.error(f"error getting prescriptions for user {user_id}: {e}", exc_info=True)
            return []

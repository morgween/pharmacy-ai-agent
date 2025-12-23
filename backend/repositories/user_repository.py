"""data access layer for user-related models"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Iterable, Type, TYPE_CHECKING
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from backend.models.user import User, Conversation, Message, UserUsage, Prescription


class UserRepository:
    """repository for user database operations"""

    def __init__(
        self,
        user_cls: Type,
        conversation_cls: Type,
        message_cls: Type,
        usage_cls: Type,
        prescription_cls: Type
    ) -> None:
        self._User = user_cls
        self._Conversation = conversation_cls
        self._Message = message_cls
        self._UserUsage = usage_cls
        self._Prescription = prescription_cls

    def count_users(self, session: Session) -> int:
        return session.query(self._User).count()

    def add_user(self, session: Session, user) -> None:
        session.add(user)

    def add_usage(self, session: Session, usage) -> None:
        session.add(usage)

    def get_user_by_email(
        self,
        session: Session,
        email: str,
        active_only: bool = True
    ) -> Optional[User]:
        query = session.query(self._User).filter(self._User.email == email)
        if active_only:
            query = query.filter(self._User.is_active == True)
        return query.first()

    def get_user_by_id(self, session: Session, user_id: str) -> Optional[User]:
        return session.query(self._User).filter(self._User.id == user_id).first()

    def get_usage(self, session: Session, user_id: str) -> Optional[UserUsage]:
        return session.query(self._UserUsage).filter(self._UserUsage.user_id == user_id).first()

    def update_usage(
        self,
        session: Session,
        user_id: str,
        messages: int = 0,
        tokens: int = 0,
        conversations: int = 0,
        tool_calls: int = 0,
        resolve_medication: int = 0,
        get_info: int = 0,
        search_ingredient: int = 0,
        check_stock: int = 0,
        last_activity: Optional[datetime] = None
    ) -> None:
        usage = self.get_usage(session, user_id)
        if not usage:
            return

        if messages:
            usage.total_messages += messages
        if tokens:
            usage.total_tokens += tokens
        if conversations:
            usage.total_conversations += conversations
        if tool_calls:
            usage.total_tool_calls += tool_calls
        if resolve_medication:
            usage.resolve_medication_calls += resolve_medication
        if get_info:
            usage.get_info_calls += get_info
        if search_ingredient:
            usage.search_ingredient_calls += search_ingredient
        if check_stock:
            usage.check_stock_calls += check_stock
        if last_activity:
            usage.last_activity = last_activity

    def add_conversation(self, session: Session, conversation) -> None:
        session.add(conversation)

    def get_conversation(self, session: Session, conversation_id: str) -> Optional[Conversation]:
        return session.query(self._Conversation).filter(self._Conversation.id == conversation_id).first()

    def add_message(self, session: Session, message) -> None:
        session.add(message)

    def list_messages(self, session: Session, conversation_id: str) -> List[Message]:
        return (
            session.query(self._Message)
            .filter(self._Message.conversation_id == conversation_id)
            .order_by(self._Message.created_at)
            .all()
        )

    def list_prescriptions(
        self,
        session: Session,
        user_id: str,
        active_only: bool,
        active_statuses: Iterable[str]
    ) -> List[Prescription]:
        query = session.query(self._Prescription).filter(self._Prescription.patient_id == user_id)
        if active_only:
            query = query.filter(self._Prescription.status.in_(list(active_statuses)))
        return query.all()

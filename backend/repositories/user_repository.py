"""data access layer for user-related models"""
from datetime import datetime
from typing import List, Optional, Iterable
from sqlalchemy.orm import Session

from backend.models.user import User, Conversation, Message, UserUsage, Prescription


class UserRepository:
    """repository for user database operations"""

    def count_users(self, session: Session) -> int:
        return session.query(User).count()

    def add_user(self, session: Session, user: User) -> None:
        session.add(user)

    def add_usage(self, session: Session, usage: UserUsage) -> None:
        session.add(usage)

    def get_user_by_email(
        self,
        session: Session,
        email: str,
        active_only: bool = True
    ) -> Optional[User]:
        query = session.query(User).filter(User.email == email)
        if active_only:
            query = query.filter(User.is_active == True)
        return query.first()

    def get_user_by_id(self, session: Session, user_id: str) -> Optional[User]:
        return session.query(User).filter(User.id == user_id).first()

    def get_usage(self, session: Session, user_id: str) -> Optional[UserUsage]:
        return session.query(UserUsage).filter(UserUsage.user_id == user_id).first()

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

    def add_conversation(self, session: Session, conversation: Conversation) -> None:
        session.add(conversation)

    def get_conversation(self, session: Session, conversation_id: str) -> Optional[Conversation]:
        return session.query(Conversation).filter(Conversation.id == conversation_id).first()

    def add_message(self, session: Session, message: Message) -> None:
        session.add(message)

    def list_messages(self, session: Session, conversation_id: str) -> List[Message]:
        return (
            session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )

    def list_prescriptions(
        self,
        session: Session,
        user_id: str,
        active_only: bool,
        active_statuses: Iterable[str]
    ) -> List[Prescription]:
        query = session.query(Prescription).filter(Prescription.patient_id == user_id)
        if active_only:
            query = query.filter(Prescription.status.in_(list(active_statuses)))
        return query.all()

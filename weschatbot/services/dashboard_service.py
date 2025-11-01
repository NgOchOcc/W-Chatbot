import functools
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, and_, join

from weschatbot.models.user import ChatMessage, ChatSession
from weschatbot.utils.db import provide_session


class DashboardService:

    def __init__(self, active_status_service):
        self.prefix = "dashboard"
        self.active_status_service = active_status_service

    @staticmethod
    def count(name):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    @provide_session
    def number_of_messages(self, session=None):
        total = session.execute(select(func.count()).select_from(ChatMessage)).scalar_one()
        return total

    @provide_session
    def number_of_chat_sessions(self, session=None):
        total = session.execute(select(func.count()).select_from(ChatSession)).scalar_one()
        return total

    @provide_session
    def number_of_messages_today(self, session=None):
        now = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_next_day = start_of_day + timedelta(days=1)

        stmt = select(func.count()).select_from(ChatMessage).where(
            and_(
                ChatMessage.modified_date >= start_of_day,  # noqa
                ChatMessage.modified_date < start_of_next_day,  # noqa
            )
        )
        total = session.execute(stmt).scalar_one()
        return int(total)

    @provide_session
    def number_of_chat_sessions_today(self, session=None):
        now = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_next_day = start_of_day + timedelta(days=1)

        stmt = select(func.count()).select_from(ChatSession).where(
            and_(
                ChatSession.modified_date >= start_of_day,  # noqa
                ChatSession.modified_date < start_of_next_day,  # noqa
            )
        )
        total = session.execute(stmt).scalar_one()
        return int(total)

    def number_of_active_users(self):
        result = len(self.active_status_service.get_all_active_user())
        return result

    @provide_session
    def number_of_distinct_users_with_messages_today(self, session=None):
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_next_day = start_of_day + timedelta(days=1)

        j = join(ChatMessage, ChatSession, ChatMessage.chat_id == ChatSession.id)
        stmt_user_ids = (
            select(func.count(func.distinct(ChatSession.user_id)))
            .select_from(j)
            .where(
                and_(
                    ChatSession.user_id.isnot(None),
                    ChatMessage.modified_date >= start_of_day,  # noqa
                    ChatMessage.modified_date < start_of_next_day,  # noqa
                )
            )
        )
        user_id_count = session.execute(stmt_user_ids).scalar_one() or 0

        stmt_guest_names = (
            select(func.count(func.distinct(ChatMessage.name)))
            .select_from(j)
            .where(
                and_(
                    ChatSession.user_id.is_(None),
                    ChatMessage.modified_date >= start_of_day,  # noqa
                    ChatMessage.modified_date < start_of_next_day,  # noqa
                )
            )
        )
        guest_name_count = session.execute(stmt_guest_names).scalar_one() or 0

        total = int(user_id_count) + int(guest_name_count)
        return total

    @provide_session
    def number_of_messages_daily(self, days: int = 30, session=None):
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        grp = func.date_format(ChatMessage.modified_date, "%Y-%m-%d")  # noqa
        label_expr = func.date_format(ChatMessage.modified_date, "%Y-%m-%d").label("date")  # noqa

        stmt = (
            select(label_expr, func.count().label("count"))
            .where(
                and_(
                    ChatMessage.modified_date >= start_date,  # noqa
                    ChatMessage.modified_date < (start_date + timedelta(days=days)),  # noqa
                )
            )
            .group_by(grp)
            .order_by(grp)
        )

        rows = session.execute(stmt).all()
        result_map = {r.date: int(r.count) for r in rows}

        out = []
        for i in range(days):
            d = (start_date + timedelta(days=i)).date().isoformat()
            out.append({"date": d, "count": result_map.get(d, 0)})

        return out

    @provide_session
    def number_of_messages_monthly(self, months: int = 12, session=None):
        now = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        year = now.year
        month = now.month - (months - 1)
        while month <= 0:
            month += 12
            year -= 1
        start_month = datetime(year, month, 1, tzinfo=timezone.utc)

        grp = func.date_format(ChatMessage.modified_date, "%Y-%m").label("mth")  # noqa
        label_expr = func.date_format(ChatMessage.modified_date, "%Y-%m").label("month")  # noqa

        end_year = start_month.year
        end_month = start_month.month + months
        while end_month > 12:
            end_month -= 12
            end_year += 1
        end_month_dt = datetime(end_year, end_month, 1, tzinfo=timezone.utc)

        stmt = (
            select(label_expr, func.count().label("count"))
            .where(
                and_(
                    ChatMessage.modified_date >= start_month,  # noqa
                    ChatMessage.modified_date < end_month_dt,  # noqa
                )
            )
            .group_by(grp)
            .order_by(grp)
        )

        rows = session.execute(stmt).all()
        result_map = {r.month: int(r.count) for r in rows}

        out = []
        cur_year = start_month.year
        cur_month = start_month.month
        for i in range(months):
            mm = f"{cur_year}-{str(cur_month).zfill(2)}"
            out.append({"month": mm, "count": result_map.get(mm, 0)})
            cur_month += 1
            if cur_month > 12:
                cur_month = 1
                cur_year += 1

        return out

    @provide_session
    def number_of_chat_sessions_daily(self, days: int = 30, session=None):
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        grp = func.date_format(ChatSession.modified_date, "%Y-%m-%d")  # noqa
        label_expr = func.date_format(ChatSession.modified_date, "%Y-%m-%d").label("date")  # noqa

        stmt = (
            select(label_expr, func.count().label("count"))
            .where(
                and_(
                    ChatSession.modified_date >= start_date,  # noqa
                    ChatSession.modified_date < (start_date + timedelta(days=days)),  # noqa
                )
            )
            .group_by(grp)
            .order_by(grp)
        )

        rows = session.execute(stmt).all()
        result_map = {r.date: int(r.count) for r in rows}

        out = []
        for i in range(days):
            d = (start_date + timedelta(days=i)).date().isoformat()
            out.append({"date": d, "count": result_map.get(d, 0)})

        return out

    @provide_session
    def number_of_chat_sessions_monthly(self, months: int = 12, session=None):
        now = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        year = now.year
        month = now.month - (months - 1)
        while month <= 0:
            month += 12
            year -= 1
        start_month = datetime(year, month, 1, tzinfo=timezone.utc)

        grp = func.date_format(ChatSession.modified_date, "%Y-%m").label("mth")  # noqa
        label_expr = func.date_format(ChatSession.modified_date, "%Y-%m").label("month")  # noqa

        end_year = start_month.year
        end_month = start_month.month + months
        while end_month > 12:
            end_month -= 12
            end_year += 1
        end_month_dt = datetime(end_year, end_month, 1, tzinfo=timezone.utc)

        stmt = (
            select(label_expr, func.count().label("count"))
            .where(
                and_(
                    ChatSession.modified_date >= start_month,  # noqa
                    ChatSession.modified_date < end_month_dt,  # noqa
                )
            )
            .group_by(grp)
            .order_by(grp)
        )

        rows = session.execute(stmt).all()
        result_map = {r.month: int(r.count) for r in rows}

        out = []
        cur_year = start_month.year
        cur_month = start_month.month
        for i in range(months):
            mm = f"{cur_year}-{str(cur_month).zfill(2)}"
            out.append({"month": mm, "count": result_map.get(mm, 0)})
            cur_month += 1
            if cur_month > 12:
                cur_month = 1
                cur_year += 1

        return out

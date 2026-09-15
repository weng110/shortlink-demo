from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

# MySQL 用 BIGINT；SQLite 需回退到 INTEGER 才能自动生成自增 id（测试用）
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class Link(Base):
    """短链接表：一条记录对应一个短码。"""

    __tablename__ = "link"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    short_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, comment="短码，Base62 编码的自增 ID")
    long_url: Mapped[str] = mapped_column(String(2048), comment="原始长链接")
    click_count: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0", comment="已落库点击量")
    status: Mapped[int] = mapped_column(default=1, comment="1=启用 0=禁用")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

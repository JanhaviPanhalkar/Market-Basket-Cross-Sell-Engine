"""MySQL persistence — save any results table to a local MySQL database.

Credentials are never hardcoded here. They're read, in order, from:
  1. Streamlit secrets (.streamlit/secrets.toml), under a [mysql] table:
        [mysql]
        host = "localhost"
        user = "root"
        password = "your-password-here"
        database = "market_basket_db"
  2. Environment variables: MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD,
     MYSQL_DATABASE.

Host/user/database fall back to sensible local defaults if not set
anywhere, since those aren't sensitive on their own — but the password
has NO default and NO fallback. If it isn't configured in one of the
two places above, saving fails with a clear message instead of
silently connecting with a blank or hardcoded password.

See .streamlit/secrets.toml.example for a template to copy.
"""
import os

from sqlalchemy import create_engine
import pymysql
import streamlit as st

DB_HOST_DEFAULT = "localhost"
DB_USER_DEFAULT = "root"
DB_NAME_DEFAULT = "market_basket_db"


def _get_credentials():
    """Reads MySQL credentials from st.secrets first, then environment
    variables. Raises a clear error if no password is configured
    anywhere, rather than falling back to a hardcoded one."""

    secrets_section = {}
    try:
        secrets_section = dict(st.secrets.get("mysql", {}))
    except Exception:
        # No secrets.toml at all is fine — we just fall through to env vars.
        secrets_section = {}

    host = (
        secrets_section.get("host")
        or os.environ.get("MYSQL_HOST")
        or DB_HOST_DEFAULT
    )
    user = (
        secrets_section.get("user")
        or os.environ.get("MYSQL_USER")
        or DB_USER_DEFAULT
    )
    database = (
        secrets_section.get("database")
        or os.environ.get("MYSQL_DATABASE")
        or DB_NAME_DEFAULT
    )
    password = (
        secrets_section.get("password")
        or os.environ.get("MYSQL_PASSWORD")
    )

    if not password:
        raise RuntimeError(
            "No MySQL password is configured. Add one to "
            ".streamlit/secrets.toml (see secrets.toml.example) or set "
            "the MYSQL_PASSWORD environment variable before saving."
        )

    return host, user, password, database


def get_engine():

    host, user, password, database = _get_credentials()

    conn = pymysql.connect(
        host=host,
        user=user,
        password=password
    )

    cursor = conn.cursor()

    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{database}`"
    )

    cursor.close()
    conn.close()

    engine = create_engine(
        f"mysql+pymysql://{user}:{password}"
        f"@{host}/{database}"
    )

    return engine


def save_to_mysql(df, table_name):

    safe_name = "".join(
        c if c.isalnum() or c == "_" else "_"
        for c in table_name.strip()
    )

    if safe_name == "":
        raise ValueError(
            "Table name cannot be empty."
        )

    if safe_name[0].isdigit():
        safe_name = "t_" + safe_name

    engine = get_engine()

    df.to_sql(
        safe_name,
        con=engine,
        if_exists="replace",
        index=False
    )

    return safe_name



from django.db import migrations


def update_charset_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return

    # Convert the tables to utf8mb4
    tables = [
        "django_admin_log",  # For admin log entries
        "web_blogpost",  # For blog posts
        "web_blogcomment",  # For blog comments
        "web_forumtopic",  # For forum topics
        "web_forumreply",  # For forum replies
    ]

    with schema_editor.connection.cursor() as cursor:
        # Set the database character set
        cursor.execute("ALTER DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")

        # Update each table
        for table in tables:
            # First convert the table
            cursor.execute(f"ALTER TABLE {table} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")

            # Then get column information
            cursor.execute(
                f"""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = '{table}'
            AND (DATA_TYPE = 'varchar' OR DATA_TYPE = 'text' OR DATA_TYPE = 'longtext')
            """
            )
            columns = cursor.fetchall()

            # Update each column with proper type definition
            for column_name, data_type, max_length in columns:
                if data_type == "varchar":
                    cursor.execute(
                        f"""
                        ALTER TABLE {table}
                        MODIFY {column_name} VARCHAR({max_length})
                        CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                    """
                    )
                else:  # text or longtext
                    cursor.execute(
                        f"""
                        ALTER TABLE {table}
                        MODIFY {column_name} {data_type.upper()}
                        CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                    """
                    )


def reverse_charset_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return

    tables = [
        "django_admin_log",
        "web_blogpost",
        "web_blogcomment",
        "web_forumtopic",
        "web_forumreply",
    ]

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("ALTER DATABASE CHARACTER SET utf8 COLLATE utf8_general_ci")
        for table in tables:
            cursor.execute(f"ALTER TABLE {table} CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci")


class Migration(migrations.Migration):
    atomic = False  # Disable transaction wrapping for DDL operations

    dependencies = [
        ("web", "0018_alter_blogpost_title_charset"),
    ]

    operations = [
        migrations.RunPython(update_charset_mysql, reverse_charset_mysql),
    ]

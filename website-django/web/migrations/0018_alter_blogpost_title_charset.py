from django.db import migrations


def alter_charset_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return

    # Convert the table to utf8mb4
    schema_editor.execute("ALTER TABLE web_blogpost CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    # Modify the title column specifically
    schema_editor.execute(
        "ALTER TABLE web_blogpost MODIFY title VARCHAR(200) " "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )


def reverse_charset_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return

    schema_editor.execute("ALTER TABLE web_blogpost CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci")
    schema_editor.execute(
        "ALTER TABLE web_blogpost MODIFY title VARCHAR(200) " "CHARACTER SET utf8 COLLATE utf8_general_ci"
    )


class Migration(migrations.Migration):
    atomic = False  # Disable transaction wrapping

    dependencies = [
        ("web", "0017_add_referral_code_unique_constraint"),
    ]

    operations = [
        migrations.RunPython(alter_charset_mysql, reverse_charset_mysql),
    ]

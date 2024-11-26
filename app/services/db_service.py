import psycopg2
from psycopg2.extras import RealDictCursor
from flask import current_app


def get_db_connection():
    """
    Создаёт и возвращает соединение с базой данных PostgreSQL.
    """
    config = current_app.config
    connection = psycopg2.connect(
        host=config["POSTGRES_HOST"],
        port=config["POSTGRES_PORT"],
        dbname=config["POSTGRES_DB"],
        user=config["POSTGRES_USER"],
        password=config["POSTGRES_PASSWORD"]
    )
    return connection


def create_user(name, password, role):
    """
    Добавляет нового пользователя в базу данных.
    """
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (name, password, role) 
                VALUES (%s, %s, %s)
                """,
                (name, password, role)
            )
        connection.commit()
    finally:
        connection.close()


def validate_user(name, password):
    """
    Проверяет логин и пароль пользователя.
    """
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM users WHERE name = %s AND password = %s
                """,
                (name, password)
            )
            user = cursor.fetchone()
        return user
    finally:
        connection.close()


def get_all_adventures():
    """
    Получает список всех приключений с именами их авторов.
    """
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.adventureid, a.adventurename, u.name AS author
                FROM adventures a
                JOIN users u ON a.userid = u.userid
                """
            )
            adventures = cursor.fetchall()
        return adventures
    finally:
        connection.close()


def get_adventure(adventure_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Получение основной информации о приключении
            cursor.execute(
                """
                SELECT a.adventurename, a.story, u.username
                FROM adventures a
                JOIN users u ON a.userid = u.userid
                WHERE a.adventureid = %s
                """,
                (adventure_id,)
            )
            adventure = cursor.fetchone()

            if not adventure:
                return "Adventure not found", 404

            # Получение списка NPC
            cursor.execute(
                """
                SELECT npcname, npcdescription
                FROM npcs
                WHERE adventureid = %s
                """,
                (adventure_id,)
            )
            npcs = cursor.fetchall()

            cursor.execute(
                """
                SELECT locationname, locationdescription
                FROM locations
                WHERE adventureid = %s
                """,
                (adventure_id,)
            )
            locations = cursor.fetchall()
    finally:
        connection.close()

    return adventure, npcs, locations


def create_adventure(userid, adventure_name, story, npc_data, npc_descriptions, location_data, location_descriptions):
    # Проверка на заполненность основных данных
    if not adventure_name or not story:
        return "Adventure name and story are required", 400

    # Вставка приключения в БД
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO adventures (userid, adventurename, story)
                VALUES (%s, %s, %s) RETURNING adventureid
                """,
                (userid, adventure_name, story)
            )
            adventure_id = cursor.fetchone()[0]

            # Вставка NPC
            for npc_name, npc_description in zip(npc_data, npc_descriptions):
                if npc_name.strip():  # Если имя заполнено
                    cursor.execute(
                        """
                        INSERT INTO npcs (adventureid, npcname, npcdescription)
                        VALUES (%s, %s, %s)
                        """,
                        (adventure_id, npc_name, npc_description)
                    )

            # Вставка локаций
            for location_name, location_description in zip(location_data,
                                                           location_descriptions):
                if location_name.strip():  # Если имя заполнено
                    cursor.execute(
                        """
                        INSERT INTO locations (adventureid, locationname, locationdescription)
                        VALUES (%s, %s, %s)
                        """,
                        (adventure_id, location_name, location_description)
                    )

        connection.commit()
    finally:
        connection.close()


def get_campaigns(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.campaignid, a.adventurename
                FROM campaigns c
                JOIN adventures a ON c.adventureid = a.adventureid
                JOIN users_campaigns uc ON uc.campaignid = c.campaignid
                WHERE uc.userid = %s
                """,
                (user_id,)
            )
            campaigns = cursor.fetchall()
    finally:
        connection.close()
    return campaigns


def create_campaign(user_id, adventure_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Вставляем новую запись в таблицу campaigns
            cursor.execute(
                """
                INSERT INTO campaigns (adventureid)
                VALUES (%s) RETURNING campaignid;
                """,
                (adventure_id,)
            )
            campaign_id = cursor.fetchone()[0]  # Получаем campaignid

            # Связываем пользователя с кампанией в таблице users_campaigns
            cursor.execute(
                """
                INSERT INTO users_campaigns (userid, campaignid, isauthor)
                VALUES (%s, %s, %s);
                """,
                (user_id, campaign_id, True)
                # Устанавливаем isauthor = True для текущего пользователя
            )

        connection.commit()
    finally:
        connection.close()

    return campaign_id


def get_campaign(user_id, campaign_id):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            # Проверяем, является ли пользователь участником кампании
            cursor.execute(
                """
                SELECT uc.isauthor
                FROM users_campaigns uc
                WHERE uc.userid = %s AND uc.campaignid = %s
                """,
                (user_id, campaign_id)
            )
            user_campaign_data = cursor.fetchone()

            if not user_campaign_data:
                return "You are not part of this campaign.", 403

            is_author = user_campaign_data[
                0]  # True, если пользователь является автором кампании

            # Получаем информацию о кампании и приключении
            cursor.execute(
                """
                SELECT a.adventurename, a.story, u.username
                FROM campaigns c
                JOIN adventures a ON c.adventureid = a.adventureid
                JOIN users u ON a.userid = u.userid
                WHERE c.campaignid = %s
                """,
                (campaign_id,)
            )
            campaign_info = cursor.fetchone()

            if not campaign_info:
                return "Campaign not found", 404

            # Получаем NPC для этого приключения
            cursor.execute(
                """
                SELECT npcname, npcdescription
                FROM npcs
                WHERE adventureid = (SELECT adventureid FROM campaigns WHERE campaignid = %s)
                """,
                (campaign_id,)
            )
            npcs = cursor.fetchall()

            # Получаем локации для этого приключения
            cursor.execute(
                """
                SELECT locationname, locationdescription
                FROM locations
                WHERE adventureid = (SELECT adventureid FROM campaigns WHERE campaignid = %s)
                """,
                (campaign_id,)
            )
            locations = cursor.fetchall()

            # Получаем игроков в кампании
            cursor.execute(
                """
                SELECT u.username, uc.isauthor
                FROM users_campaigns uc
                JOIN users u ON uc.userid = u.userid
                WHERE uc.campaignid = %s
                """,
                (campaign_id,)
            )
            players = cursor.fetchall()

            # Получаем персонажей, принадлежащих этой кампании
            cursor.execute(
                """
                SELECT charactername, characterclass, characterlevel
                FROM player_characters
                WHERE campaignid = %s
                """,
                (campaign_id,)
            )
            characters = cursor.fetchall()

    finally:
        connection.close()

    return campaign_info, npcs, locations, players, characters, is_author, campaign_id


def create_users_campaigns(username, campaign_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Получаем ID пользователя по username
            cursor.execute("SELECT userid FROM users WHERE username = %s",
                           (username,))
            user = cursor.fetchone()

            if not user:
                return "User not found", 404

            user_id_to_add = user[0]

            # Добавляем пользователя в таблицу users_campaigns
            cursor.execute(
                "INSERT INTO users_campaigns (userid, campaignid, isauthor) VALUES (%s, %s, FALSE)",
                (user_id_to_add, campaign_id)
            )
        connection.commit()
    finally:
        connection.close()


def create_player_character(
        campaign_id,
        charactername,
        characterdescription,
        characterlevel,
        characterclass,
        characterskills,
        characterarmor,
        characterhp
):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Добавляем персонажа в таблицу player_characters
            cursor.execute(
                """
                INSERT INTO player_characters (campaignid, charactername, characterdescription, characterlevel,
                                               characterclass, characterskills, characterarmor, characterhp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (campaign_id, charactername, characterdescription,
                 characterlevel, characterclass,
                 characterskills, characterarmor, characterhp)
            )
        connection.commit()
    finally:
        connection.close()
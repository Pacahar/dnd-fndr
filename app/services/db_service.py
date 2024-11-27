import psycopg2
from psycopg2.extras import RealDictCursor
from flask import current_app


def get_db_connection():
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
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (userlogin, userpassword, userrole) 
                VALUES (%s, %s, %s)
                """,
                (name, password, role)
            )
        connection.commit()
    finally:
        connection.close()


def validate_user(name, password):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM users WHERE userlogin = %s AND userpassword = %s
                """,
                (name, password)
            )
            user = cursor.fetchone()
        return user
    finally:
        connection.close()


def get_all_adventures(search_name=None, search_author=None):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if search_name and not search_author:
                cursor.execute(
                    """
                    SELECT a.adventureid, a.adventurename, u.userlogin AS author
                    FROM adventures a
                    JOIN users u ON a.userid = u.userid
                    WHERE a.adventurename LIKE %s
                    """,
                    (f"%{search_name}%",)
                )
            elif search_author and not search_name:
                cursor.execute(
                    """
                    SELECT a.adventureid, a.adventurename, u.userlogin AS author
                    FROM adventures a
                    JOIN users u ON a.userid = u.userid
                    WHERE u.userlogin LIKE %s
                    """,
                    (f"%{search_author}%",)
                )
            elif search_name and search_author:
                cursor.execute(
                    """
                    SELECT a.adventureid, a.adventurename, u.userlogin AS author
                    FROM adventures a
                    JOIN users u ON a.userid = u.userid
                    WHERE a.adventurename LIKE %s AND u.userlogin LIKE %s
                    """,
                    (f"%{search_name}%", f"%{search_author}%")
                )
            else:
                cursor.execute(
                    """
                    SELECT a.adventureid, a.adventurename, u.userlogin AS author
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
            cursor.execute("SELECT * FROM get_adventure_details(%s)", (adventure_id,))
            details = cursor.fetchall()
    finally:
        connection.close()

    adventure = {
        'id': details[0][0],
        'name': details[0][1],
        'story': details[0][2]
    }
    npcs = []
    locations = []
    for row in details:
        if row[3]:
            if not {'name': row[3], 'description': row[4]} in npcs:
                npcs.append({'name': row[3], 'description': row[4]})
        if row[5]:
            if not {'name': row[5], 'description': row[6]} in locations:
                locations.append({'name': row[5], 'description': row[6]})
    return adventure, npcs, locations


def is_adventure_author(adventure_id, user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT userid FROM adventures WHERE adventureid = %s",
                (adventure_id,)
            )
            result = cursor.fetchone()
            return (result == user_id) or (result[0] == user_id)
    finally:
        connection.close()


def delete_adventure(adventure_id, user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if is_adventure_author(adventure_id, user_id):
                cursor.execute(
                    "SELECT campaignid FROM campaigns WHERE adventureid = %s",
                    (adventure_id,)
                )
                campaign_ids = [row[0] for row in cursor.fetchall()]

                for campaign_id in campaign_ids:
                    delete_campaign(campaign_id)

                cursor.execute(
                    "DELETE FROM npcs WHERE adventureid = %s",
                    (adventure_id,)
                )

                cursor.execute(
                    "DELETE FROM locations WHERE adventureid = %s",
                    (adventure_id,)
                )

                cursor.execute(
                    "DELETE FROM adventures WHERE adventureid = %s",
                    (adventure_id,)
                )

                connection.commit()
    finally:
        connection.close()


def create_adventure(userid, adventure_name, story, npc_data, npc_descriptions, location_data, location_descriptions):
    if not adventure_name or not story:
        return "Adventure name and story are required", 400

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
            print(userid, adventure_name, story)
            adventure_id = cursor.fetchone()[0]

            for npc_name, npc_description in zip(npc_data, npc_descriptions):
                if npc_name.strip():
                    cursor.execute(
                        """
                        INSERT INTO npcs (adventureid, npcname, npcdescription)
                        VALUES (%s, %s, %s)
                        """,
                        (adventure_id, npc_name, npc_description)
                    )

            for location_name, location_description in zip(location_data,
                                                           location_descriptions):
                if location_name.strip():
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


def update_adventure(adventure_id, form_data):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            adventure_name = form_data.get('adventurename', [None])
            adventure_story = form_data.get('story', [None])
            if adventure_name and adventure_story:
                cursor.execute(
                    """
                    UPDATE adventures
                    SET adventurename = %s, story = %s
                    WHERE adventureid = %s
                    """,
                    (adventure_name, adventure_story, adventure_id)
                )
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_npc(adventure_id, name, description):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO npcs (adventureid, npcname, npcdescription) VALUES (%s, %s, %s)",
                (adventure_id, name, description)
            )
            connection.commit()
    finally:
        connection.close()


def delete_npc(adventure_id, name, description):
    connection = get_db_connection()
    print(adventure_id, name, description)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM npcs
                WHERE adventureid = %s
                  AND npcname = %s
                  """,
                (adventure_id, name)
            )
            connection.commit()
    finally:
        connection.close()


def create_location(adventure_id, name, description):
    print('create_location была вызвана')
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO locations (adventureid, locationname, locationdescription) VALUES (%s, %s, %s)",
                (adventure_id, name, description)
            )
            connection.commit()
    finally:
        connection.close()


def delete_location(adventure_id, location_name, location_description):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                            DELETE FROM locations
                            WHERE adventureid = %s
                              AND locationname = %s
                              AND locationdescription = %s
                        """, (adventure_id, location_name, location_description))
            connection.commit()
    finally:
        connection.close()


def get_all_campaigns(user_id):
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
            cursor.execute("CALL create_campaign_with_user(%s, %s)", (adventure_id, user_id))
        connection.commit()
    finally:
        connection.close()


def get_campaign(user_id, campaign_id):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
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
                return None

            is_author = user_campaign_data[
                0]

            cursor.execute(
                """
                SELECT a.adventurename, a.story, u.userlogin
                FROM campaigns c
                JOIN adventures a ON c.adventureid = a.adventureid
                JOIN users u ON a.userid = u.userid
                WHERE c.campaignid = %s
                """,
                (campaign_id,)
            )
            campaign_info = cursor.fetchone()

            if not campaign_info:
                return None

            cursor.execute(
                """
                SELECT npcname, npcdescription
                FROM npcs
                WHERE adventureid = (SELECT adventureid FROM campaigns WHERE campaignid = %s)
                """,
                (campaign_id,)
            )
            npcs = cursor.fetchall()

            cursor.execute(
                """
                SELECT locationname, locationdescription
                FROM locations
                WHERE adventureid = (SELECT adventureid FROM campaigns WHERE campaignid = %s)
                """,
                (campaign_id,)
            )
            locations = cursor.fetchall()

            cursor.execute(
                """
                SELECT u.userlogin, uc.isauthor
                FROM users_campaigns uc
                JOIN users u ON uc.userid = u.userid
                WHERE uc.campaignid = %s
                """,
                (campaign_id,)
            )
            players = cursor.fetchall()

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


def delete_campaign(campaign_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM users_campaigns WHERE campaignid = %s",
                (campaign_id,)
            )

            cursor.execute(
                "DELETE FROM player_characters WHERE campaignid = %s",
                (campaign_id,)
            )

            cursor.execute(
                "DELETE FROM campaigns WHERE campaignid = %s",
                (campaign_id,)
            )
            connection.commit()
    finally:
        connection.close()


def create_users_campaigns(username, campaign_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT userid FROM users WHERE userlogin = %s",
                           (username,))
            user = cursor.fetchone()

            if not user:
                return "User not found", 404

            user_id_to_add = user[0]

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

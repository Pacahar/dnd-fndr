from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from app.services.db_service import *

main_bp = Blueprint('main', __name__)


@main_bp.route('/', methods=['GET'])
def index():
    """
    Возвращает HTML-страницу регистрации.
    """
    return render_template('register.html')


@main_bp.route('/register', methods=['POST'])
def register():
    """
    Обрабатывает данные формы регистрации и добавляет пользователя в базу.
    """
    name = request.form.get('name')
    password = request.form.get('password')
    role = request.form.get('role')

    if not all([name, password, role]):
        return jsonify({"error": "All fields are required"}), 400

    try:
        create_user(name, password, role)
        return redirect(url_for('main.adventures'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Обрабатывает логин пользователя.
    """
    if request.method == 'GET':
        return render_template('login.html')

    name = request.form.get('name')
    password = request.form.get('password')

    if not all([name, password]):
        return jsonify({"error": "All fields are required"}), 400

    user = validate_user(name, password)
    if user:
        session['userid'] = user['userid']
        session['role'] = user['role']
        return redirect(url_for('main.adventures'))
    else:
        return jsonify({"error": "Invalid credentials"}), 401


@main_bp.route('/adventures', methods=['GET'])
def adventures():
    """
    Показывает список приключений.
    Если пользователь - master, показывает кнопку для создания приключений.
    """
    all_adventures = get_all_adventures()
    user_role = session.get('role', None)
    return render_template('adventures.html', adventures=all_adventures, user_role=user_role)


@main_bp.route('/adventures/new', methods=['GET', 'POST'])
def new_adventure():
    """
    Обрабатывает создание нового приключения.
    """
    if session.get('role') != 'master':
        return redirect(url_for('main.adventures'))

    if request.method == 'POST':
        adventure_name = request.form.get('adventurename')
        story = request.form.get('story')
        npc_data = request.form.getlist('npc[]')
        npc_descriptions = request.form.getlist('npc_description[]')
        location_data = request.form.getlist('location[]')
        location_descriptions = request.form.getlist('location_description[]')

        create_adventure(
            userid=session['userid'],
            adventure_name=adventure_name,
            story=story,
            npc_data=npc_data,
            npc_descriptions=npc_descriptions,
            location_data=location_data,
            location_descriptions=location_descriptions
        )

        return redirect(url_for('main.adventures'))

    return render_template('new_adventure.html')


@main_bp.route('/adventures/<int:adventure_id>', methods=['GET'])
def view_adventure(adventure_id):
    """
    Отображает информацию о приключении, включая NPC и локации.
    """
    adventure, npcs, locations = get_adventure(adventure_id)

    if not adventure:
        return """
            <h1 style="width:100%; text-align: center;">No such adventure :(</h1>
            """

    return render_template(
        'adventure.html',
        adventure={
            'name': adventure[0],
            'story': adventure[1],
            'author': adventure[2],
        },
        npcs=npcs,
        locations=locations,
    )


@main_bp.route('/campaigns', methods=['GET'])
def campaigns():
    """
    Отображает список кампаний пользователя.
    """
    if not session:
        return redirect(url_for('main.login'))

    user_id = session.get('userid')

    my_campaigns = get_campaigns(user_id)

    return render_template(
        'campaigns.html',
        campaigns=my_campaigns,
    )


@main_bp.route('/campaigns/new', methods=['POST'])
def create_campaign():
    """
    Создаёт новую кампанию для указанного приключения.
    """
    if not session:
        return

    user_id = session.get('userid')
    adventure_id = request.form.get('adventureid')

    if not adventure_id:
        return "Adventure ID is required", 400

    campaign_id = create_campaign(user_id, adventure_id)

    # Перенаправляем на страницу созданной кампании
    return redirect(f'/campaigns/{campaign_id}')


@main_bp.route('/campaigns/<int:campaign_id>', methods=['GET', 'POST'])
def campaign_detail(campaign_id):
    """
    Отображает информацию о кампании, включая приключение, NPC, локации и персонажей.
    Если пользователь является автором кампании, предоставляется меню для управления участниками и персонажами.
    """
    if not session:
        return redirect(url_for('main.login'))

    user_id = session.get('userid')

    campaign_info, npcs, locations, players, characters, is_author, campaign_id = get_campaign(user_id, campaign_id)

    return render_template(
        'campaign_detail.html',
        campaign_info=campaign_info,
        npcs=npcs,
        locations=locations,
        players=players,
        characters=characters,
        is_author=is_author,
        campaign_id=campaign_id
    )


@main_bp.route('/campaigns/<int:campaign_id>/add_player', methods=['POST'])
def add_player(campaign_id):
    if not session and session.get('role') != 'master':
        return

    username = request.form.get('username')
    user_id = session.get('userid')

    create_users_campaigns(username, user_id)

    return redirect(f'/campaigns/{campaign_id}')


@main_bp.route('/campaigns/<int:campaign_id>/add_character', methods=['POST'])
def add_character(campaign_id):
    if not session and session.get('role') != 'master':
        return redirect(f'/campaigns/{campaign_id}')

    character_name = request.form.get('charactername')
    character_description = request.form.get('characterdescription')
    character_level = int(request.form.get('characterlevel'))
    character_class = request.form.get('characterclass')
    character_skills = request.form.get('characterskills')
    character_armor = int(request.form.get('characterarmor'))
    character_hp = int(request.form.get('characterhp'))

    create_player_character(
        campaign_id,
        character_name,
        character_description,
        character_level,
        character_class,
        character_skills,
        character_armor,
        character_hp
    )

    return redirect(f'/campaigns/{campaign_id}')



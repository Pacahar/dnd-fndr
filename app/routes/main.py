from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from app.services.db_service import *

main_bp = Blueprint('main', __name__)


@main_bp.route('/me', methods=['GET'])
def me():
    return jsonify(session)


@main_bp.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('main.login'))


@main_bp.route('/', methods=['GET'])
def index():
    return render_template('register.html')


@main_bp.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    password = request.form.get('password')
    role = request.form.get('role')

    if not all([name, password, role]):
        return jsonify({"error": "All fields are required"}), 400

    try:
        create_user(name, password, role)
        return redirect(url_for('main.login'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    name = request.form.get('name')
    password = request.form.get('password')

    if not all([name, password]):
        return jsonify({"error": "All fields are required"}), 400

    user = validate_user(name, password)
    if user:
        session['userid'] = user[0]
        session['login'] = user[1]
        session['role'] = user[3]
        return redirect(url_for('main.adventures'))
    else:
        return jsonify({"error": "Invalid credentials"}), 401


@main_bp.route('/adventures', methods=['GET'])
def adventures():
    search_name = request.args.get('search_name', None)
    search_author = request.args.get('search_author', None)
    all_adventures = get_all_adventures(search_name, search_author)

    user_role = session.get('role', None)
    return render_template('adventures.html',
                           adventures=all_adventures,
                           user_role=user_role,
                           search_name=search_name,
                           search_author=search_author)


@main_bp.route('/adventures/new', methods=['GET', 'POST'])
def new_adventure():
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
    adventure, npcs, locations = get_adventure(adventure_id)

    if not adventure:
        return """
            <h1 style="width:100%; text-align: center;">No such adventure :(</h1>
            """, 404

    role = None
    if 'role' in session.keys():
        role = session['role']

    return render_template(
        'adventure_detail.html',
        adventure=adventure,
        npcs=npcs,
        locations=locations,
        user_is_logged_in=True,
        user_role=role,
        is_author=is_adventure_author(adventure_id, session.get('userid', None))
    )


@main_bp.route('/adventures/<int:adventure_id>/delete', methods=['POST'])
def delete_adv(adventure_id):
    user_id = session.get('userid')
    if not user_id:
        return redirect('/login')

    delete_adventure(adventure_id, user_id)
    return redirect(url_for('main.adventures'))


@main_bp.route('/adventures/<int:adventure_id>/edit', methods=['GET'])
def edit_adventure_form(adventure_id):
    user_id = session.get('userid')
    if (not user_id) or (not is_adventure_author(adventure_id, user_id)):
        return redirect('/adventures')

    adventure, npcs, locations = get_adventure(adventure_id)
    print(type(locations), locations)
    print(type(npcs), npcs)
    if not adventure:
        return "Приключение не найдено", 404

    return render_template('edit_adventure.html', adventure=adventure, npcs=npcs, locations=locations)


@main_bp.route('/adventures/<int:adventure_id>/edit', methods=['POST'])
def edit_adventure(adventure_id):
    user_id = session.get('userid')

    if not is_adventure_author(adventure_id, user_id):
        return redirect(url_for('main.adventure', adventure_id=adventure_id))

    adventure = {
        'adventurename': request.form.get('adventurename'),
        'story': request.form.get('story')
    }
    update_adventure(adventure_id, adventure)

    return redirect(f'/adventures/{adventure_id}/edit')


@main_bp.route('/campaigns', methods=['GET'])
def campaigns():
    if not session:
        return redirect(url_for('main.login'))

    user_id = session.get('userid')

    my_campaigns = get_all_campaigns(user_id)

    return render_template(
        'campaigns.html',
        campaigns=my_campaigns,
    )


@main_bp.route('/campaigns/new', methods=['POST'])
def add_campaign():
    if not session:
        return

    user_id = session.get('userid')
    adventure_id = request.form.get('adventureid')

    if not adventure_id:
        return """
        <h1 style="width:100%; text-align: center;">Adventure ID is required</h1>
        """, 400

    create_campaign(user_id, adventure_id)

    return redirect('/campaigns')


@main_bp.route('/campaigns/<int:campaign_id>', methods=['GET', 'POST'])
def campaign_detail(campaign_id):
    if not session:
        return redirect(url_for('main.login'))

    user_id = session.get('userid')

    campaign_info, npcs, locations, players, characters, is_author, campaign_id = get_campaign(user_id, campaign_id)
    if not campaign_info:
        return """
        <h1 style="width:100%; text-align: center;">This campaign not exist or you not a member of campaign</h1>
        """, 400

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
    create_users_campaigns(username, campaign_id)

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


@main_bp.route('/npc/create', methods=['POST'])
def add_npc():
    name = request.form.get('name')
    description = request.form.get('description')
    adventure_id = request.form.get('adventureid')

    create_npc(adventure_id, name, description)
    return redirect(f'/adventures/{adventure_id}/edit')


@main_bp.route('/npc/delete', methods=['POST'])
def delete_npc_by_name():
    name = request.form.get('name')
    description = request.form.get('description')
    adventure_id = request.form.get('adventureid')

    delete_npc(adventure_id, name, description)
    return redirect(f'/adventures/{adventure_id}/edit')


@main_bp.route('/locations/delete', methods=['POST'])
def delete_location_by_name():
    name = request.form.get('name')
    description = request.form.get('description')
    adventure_id = request.form.get('adventureid')

    delete_location(adventure_id, name, description)
    return redirect(f'/adventures/{adventure_id}/edit')


@main_bp.route('/locations/create', methods=['POST'])
def add_location():
    name = request.form.get('name')
    description = request.form.get('description')
    adventure_id = request.form.get('adventureid')

    create_location(adventure_id, name, description)

    return redirect(f'/adventures/{adventure_id}/edit')



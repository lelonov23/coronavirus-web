from flask import Flask, render_template, redirect, request
from data import db_session
from flask_wtf import FlaskForm
from data.patients import Patient
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired
from wtforms.fields.html5 import EmailField
from flask_login import login_user, logout_user, login_required, LoginManager
import math
import os
from io import BytesIO
import requests
from PIL import Image


app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(Patient).get(user_id)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/advice")
def advice():
    return render_template("advice.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        session = db_session.create_session()
        if session.query(Patient).filter(Patient.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        patient = Patient(
            name=form.name.data,
            surname=form.surname.data,
            midname=form.midname.data,
            age=form.age.data,
            condition=form.condition.data,
            email=form.email.data)
        patient.set_password(form.password.data)
        session.add(patient)
        session.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/diagram', methods=['GET', 'POST'])
def diagram():
    all_p = 0
    healthy = 0
    light = 0
    middle = 0
    hard = 0
    child = 0
    young = 0
    mid = 0
    old = 0
    db_session.global_init('patients.sqlite')
    session = db_session.create_session()
    form = DiagramForm()
    if request.method == 'GET':
        return render_template('diagram_choice.html', title='Выбор диаграммы', form=form)
    if request.method == 'POST':
        if form.kind.data == 'степени заболевания':
            for patient in session.query(Patient).all():
                all_p += 1
                if patient.condition == 'Отсутствие':
                    healthy += 1
                elif patient.condition == 'Легкая':
                    light += 1
                elif patient.condition == 'Средняя':
                    middle += 1
                elif patient.condition == "Тяжелая":
                    hard += 1
            graph = {'healthy': healthy / all_p * 100,
                     'light': light / all_p * 100,
                     'middle': middle / all_p * 100,
                     'hard': hard / all_p * 100}
            return render_template('diagram1.html', title='Статистика', graph=graph)
        elif form.kind.data == 'возрасту заболевших':
            for patient in session.query(Patient).all():
                all_p += 1
                if int(patient.age) <= 18 and patient.condition != 'Отсутствие':
                    child += 1
                elif 18 < int(patient.age) <= 44 and patient.condition != 'Отсутствие':
                    young += 1
                elif 44 < int(patient.age) <= 59 and patient.condition != 'Отсутствие':
                    mid += 1
                elif int(patient.age) > 59 and patient.condition != 'Отсутствие':
                    old += 1
            graph2 = {'child': child / all_p * 100,
                      'young': young / all_p * 100,
                      'mid': mid / all_p * 100,
                      'old': old / all_p * 100}
            return render_template('diagram2.html', title='Статистика', graph2=graph2)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        admin = session.query(Patient).filter(Patient.name == form.name.data).first()
        if admin and admin.check_password(form.password.data):
            login_user(admin, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/pharmacies', methods=['GET', 'POST'])
def apteka():
    form = AptekaForm()
    if request.method == 'GET':
        return render_template('pharmacies.html', title='Ближайшие аптеки', form=form)

    if request.method == 'POST':
        def lonlat_distance(a, b):
            degree_to_meters_factor = 111 * 1000
            a_lon, a_lat = a
            b_lon, b_lat = b

            radians_lattitude = math.radians((a_lat + b_lat) / 2.)
            lat_lon_factor = math.cos(radians_lattitude)
            dx = abs(a_lon - b_lon) * degree_to_meters_factor * lat_lon_factor
            dy = abs(a_lat - b_lat) * degree_to_meters_factor
            distance = math.sqrt(dx * dx + dy * dy)
            return distance

        def get_params_for_static_maps_and_organization(json_response, start_point):
            organizations = json_response["features"]
            green_point = []
            blue_point = []
            grey_point = []

            for i in range(10):
                organization = organizations[i]
                point = organization["geometry"]["coordinates"]
                org_point = "{0},{1}".format(point[0], point[1])

                Availabilities = organization['properties']['CompanyMetaData'][
                    'Hours']['Availabilities'][0]

                if 'TwentyFourHours' in Availabilities:
                    green_point.append(org_point)
                elif 'TwentyFourHours' not in Availabilities:
                    blue_point.append(org_point)
                else:
                    grey_point.append(org_point)

            green_text = ",pm2gnm~".join(green_point)
            if len(green_point) > 0:
                green_text += ',pm2gnm'
            if len(blue_point) > 0 and len(green_point) > 0:
                green_text += '~'

            blue_text = ",pm2blm~".join(blue_point)
            if len(blue_point) > 0:
                blue_text += ',pm2blm'
            if len(grey_point) > 0 and len(blue_point) > 0:
                blue_text += '~'

            grey_text = ",pm2grm~".join(grey_point)
            if len(grey_point) > 0:
                grey_text += ',pm2grm'

            map_params = {
                "l": "map",
                'pt': f'{green_text}{blue_text}{grey_text}'}

            return map_params

        def get_data_of_organization(organization):
            text = []
            start_point = list(map(float, address_ll.split(',')))
            org_point = organization['geometry']['coordinates']

            name = organization['properties']['name']
            address = organization['properties']['description']
            time_of_work = organization['properties']['CompanyMetaData']['Hours']['text']

            distance = int(lonlat_distance(start_point, org_point))

            text.append(f'Название: {name}')
            text.append(f'Адрес: {address}')
            text.append(f'Время работы: {time_of_work}')
            text.append(f'Растояние: {distance}')
            return '\n'.join(text)

        toponym_to_find = form.address.data

        geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"
        geocoder_params = {
            "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
            "geocode": toponym_to_find,
            "format": "json"}

        response = requests.get(geocoder_api_server, params=geocoder_params)

        if not response:
            pass

        json_response = response.json()
        address_ll = json_response["response"]["GeoObjectCollection"][
            "featureMember"][0]["GeoObject"]['Point']['pos']
        address_ll = ','.join(address_ll.split())

        search_api_server = "https://search-maps.yandex.ru/v1/"
        api_key = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"
        search_params = {
            "apikey": api_key,
            "text": "аптека",
            "lang": "ru_RU",
            "ll": address_ll,
            "type": "biz",
            "results": 50
        }

        response = requests.get(search_api_server, params=search_params)
        json_response = response.json()
        map_params = get_params_for_static_maps_and_organization(
            json_response, address_ll)

        map_api_server = "http://static-maps.yandex.ru/1.x/"
        response = requests.get(map_api_server, params=map_params)

        f = Image.open(BytesIO(response.content))
        f.save(f'static/img/apteka.png')
        return render_template('pharmacies2.html', title='Ближайшие аптеки')


def main():
    db_session.global_init("db/patients.sqlite")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


class RegisterForm(FlaskForm):
    name = StringField('Имя пользователя', validators=[DataRequired()])
    surname = StringField('Фамилия пользователя', validators=[DataRequired()])
    midname = StringField('Отчество пользователя', validators=[DataRequired()])
    age = StringField('Возраст пользователя', validators=[DataRequired()])
    condition = SelectField("Степень заболевания", choices=[
        ("Отсутствие", "Отсутсвие"),
        ("Легкая", "Легкая"),
        ("Средняя", "Средняя"),
        ("Тяжелая", "Тяжелая")])
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class LoginForm(FlaskForm):
    name = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class AptekaForm(FlaskForm):
    address = StringField('Адрес', validators=[DataRequired()])
    submit = SubmitField('OK')


class DiagramForm(FlaskForm):
    kind = SelectField('Отсортировать по',  choices=[
        ("степени заболевания", "степени заболевания"),
        ("возрасту заболевших", "возрасту заболевших")])
    submit = SubmitField('OK')


if __name__ == '__main__':
    main()
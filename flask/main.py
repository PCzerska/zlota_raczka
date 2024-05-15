from flask import Flask, request, render_template, redirect, url_for, session
from neo4j import GraphDatabase
import re

app = Flask(__name__)
app.secret_key = 'super tajny klucz'  # Klucz sesji

class Neo4jService(object):

    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def get_user_name(self, id_uzytkownika):
        with self._driver.session() as session:
            # Sprawdź, czy użytkownik jest fachowcem
            result = session.run("MATCH (f:Fachowiec {id_fachowca: $id_uzytkownika}) RETURN f.Imię AS imie",
                                 id_uzytkownika=id_uzytkownika)

            record = result.single()

            if record:
                return record['imie']

            # Jeśli użytkownik nie jest fachowcem, sprawdź czy jest zleceniodawcą
            result = session.run("MATCH (z:Zleceniodawca {id_zleceniodawcy: $id_uzytkownika}) RETURN z.Imię AS imie",
                                 id_uzytkownika=id_uzytkownika)
            record = result.single()
            print(record)
            if record:
                return record['imie']

            # Jeśli użytkownik nie jest ani fachowcem, ani zleceniodawcą, zwróć None
            return None

    def create_fachowiec(self, id_uzytkownika, imie, nazwisko, fach, data_dolaczenia):
        with self._driver.session() as session:
            create_fachowiec_query = (
                "MATCH (u:Użytkownik {id_użytkownika: $id_uzytkownika}) "
                "CREATE (f:Fachowiec {id_fachowca: $id_uzytkownika, Imię: $imie, Nazwisko: $nazwisko, Fach: $fach,`Data dołączenia`: $data_dolaczenia}) "
                "CREATE (u)-[:POWIĄZANY_Z]->(f) "
                "RETURN f"
            )

            session.run(create_fachowiec_query, id_uzytkownika=id_uzytkownika, imie=imie, nazwisko=nazwisko, fach=fach, data_dolaczenia=data_dolaczenia)

    def create_zleceniodawca(self, id_uzytkownika, imie, nazwisko, data_dolaczenia):
        with self._driver.session() as session:
            create_zleceniodawca_query = (
                "MATCH (u:Użytkownik {id_użytkownika: $id_uzytkownika}) "
                "CREATE (z:Zleceniodawca {Imię: $imie, Nazwisko: $nazwisko, `Data dołączenia`: $data_dolaczenia, id_zleceniodawcy: $id_uzytkownika}) "
                "CREATE (u)-[:POWIĄZANY_Z]->(z)"
            )
            session.run(create_zleceniodawca_query, id_uzytkownika=id_uzytkownika, imie=imie, nazwisko=nazwisko,
                        data_dolaczenia=data_dolaczenia)

    def create_user(self, email, haslo):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return "Niepoprawny adres e-mail jako login"
        if not re.search(r"\d", haslo) or not re.search(r"[a-zA-Z]", haslo):
            return "Hasło musi zawierać zarówno litery i cyfry"

        # Sprawdzenie, czy użytkownik o podanym adresie e-mail już istnieje
        if self.check_existing_user(email):
            return "Użytkownik o podanym adresie e-mail już istnieje"

        with self._driver.session() as session:
            session.write_transaction(self._create_user, email, haslo)

    def check_user(self, email, haslo):
        with self._driver.session() as session:
            result = session.run("MATCH (u:Użytkownik {login: $email, hasło: $haslo}) RETURN u", email=email, haslo=haslo)
            return bool(result.single())

    def check_existing_user(self, email):
        with self._driver.session() as session:
            result = session.run("MATCH (u:Użytkownik {login: $email}) RETURN u", email=email)
            return bool(result.single())

    def _create_user(self, tx, email, haslo):
        last_id = self.get_last_user_id(tx)
        new_id = int(last_id) + 1 if last_id else 1
        query = (
            "CREATE (u:Użytkownik {login: $email, hasło: $haslo, id_użytkownika: $id_uzytkownika})"
        )
        tx.run(query, email=email, haslo=haslo, id_uzytkownika=new_id)

    def get_last_user_id(self, tx):
        result = tx.run("MATCH (u:Użytkownik) RETURN max(u.id_użytkownika) as last_id")
        last_id = result.single()['last_id']
        return last_id

    def get_user_id(self, email):
        with self._driver.session() as session:
            result = session.run("MATCH (u:Użytkownik {login: $email}) RETURN u.id_użytkownika AS id", email=email)
            record = result.single()
            if record:
                return record['id']
            return None

    def create_offer(self, user_id, title, description, price, timestamp):
        with self._driver.session() as session:
            create_offer_query = (
                "MATCH (u:Użytkownik {id_użytkownika: $user_id}) "
                "CREATE (o:Ogłoszenie {Tytuł: $title, Opis: $description, Cena: $price, `Data dodania`: $timestamp}) "
                "CREATE (u)-[:DODAŁ]->(o) "
                "RETURN o"
            )

            session.run(create_offer_query, user_id=user_id, title=title, description=description, price=price,
                        timestamp=timestamp)

    def get_user_info(self, id_uzytkownika):
        with self._driver.session() as session:
            result = session.run("""
                MATCH (u:Użytkownik {id_użytkownika: $id_uzytkownika})
                OPTIONAL MATCH (u)-[:POWIĄZANY_Z]->(f:Fachowiec)
                OPTIONAL MATCH (u)-[:POWIĄZANY_Z]->(z:Zleceniodawca)
                OPTIONAL MATCH (u)-[:DODAŁ]->(o:Ogłoszenie)
                RETURN u AS user, f AS fachowiec, z AS zleceniodawca, collect(o) AS ogloszenia
            """, id_uzytkownika=id_uzytkownika)

            record = result.single()
            if record:
                user_info = dict(record['user'].items())
                if record['fachowiec']:
                    user_info.update(dict(record['fachowiec'].items()))
                    user_info['role'] = 'fachowiec'
                if record['zleceniodawca']:
                    user_info.update(dict(record['zleceniodawca'].items()))
                    user_info['role'] = 'zleceniodawca'
                if record['ogloszenia']:
                    user_info['ogloszenia'] = [dict(ogloszenie.items()) for ogloszenie in record['ogloszenia']]
                else:
                    user_info['ogloszenia'] = []  # Jeśli tablica ogłoszeń jest pusta, zwracamy pustą tablicę
                return user_info
            return None

    def get_all_offers(self):
        with self._driver.session() as session:
            result = session.run("""
                MATCH (o:Ogłoszenie)
                RETURN o
            """)
            offers = [dict(record['o'].items()) for record in result]
            return offers



# Konfiguracja Neo4j
NEO4J_URI = "neo4j+s://eda19c51.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "4S3ETALPdCft6VZAEX73gg3aYe-ImMxMykAYXxAg2dM"

neo4j_service = Neo4jService(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

@app.route('/')
def index():
    user_info = get_user()
    if user_info:
        return render_template('index2.html', logged_in=True, user_info=user_info)
    return render_template('index.html', logged_in=False)


@app.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    haslo = request.form['haslo']

    result = neo4j_service.create_user(email, haslo)
    if result:
        return result

    # Pobierz id użytkownika, który został utworzony
    id_uzytkownika = neo4j_service.get_user_id(email)

    # Ustaw flagę w sesji informującą, że użytkownik zarejestrował się poprawnie
    session['registered'] = True
    # Zapisz id użytkownika do sesji
    session['id_uzytkownika'] = id_uzytkownika

    return redirect(url_for('choose_role'))


from datetime import datetime

@app.route('/choose_role', methods=['GET', 'POST'])
def choose_role():
    if 'registered' not in session:
        # Jeśli użytkownik nie zarejestrował się poprawnie, przekieruj go na stronę główną
        return redirect(url_for('index'))

    if request.method == 'POST':
        role = request.form['role']
        imie = request.form['imie']
        nazwisko = request.form['nazwisko']
        id_uzytkownika = session['id_uzytkownika']
        data_dolaczenia = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Pobierz aktualną datę
        # Pobierz informacje o użytkowniku na podstawie jego identyfikatora

        if role == 'fachowiec':
            fach = request.form['fach']
            neo4j_service.create_fachowiec(id_uzytkownika, imie, nazwisko, fach, data_dolaczenia)
            user_info = neo4j_service.get_user_info(id_uzytkownika)
            print(user_info)
            return render_template('fachowiec.html', user_info=user_info)
            #print(f"Fachowiec {imie} {nazwisko} został utworzony.")
        else:
            neo4j_service.create_zleceniodawca(id_uzytkownika, imie, nazwisko, data_dolaczenia)
            user_info = neo4j_service.get_user_info(id_uzytkownika)
            print(user_info)
            return render_template('index2.html', user_info=user_info)
            #print(f"Usługodawca {imie} {nazwisko} został utworzony.")

        # Przekieruj użytkownika na stronę główną lub gdziekolwiek indziej
        #return render_template('index2.html', imie=imie, logged_in=True)

    # Jeśli metoda to GET lub formularz nie został jeszcze wysłany, wyświetl stronę wyboru roli
    return render_template('choose_role.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        haslo = request.form['haslo']

        if neo4j_service.check_user(email, haslo):
            session['logged_in'] = True

            # Pobierz identyfikator użytkownika na podstawie adresu e-mail
            id_uzytkownika = neo4j_service.get_user_id(email)

            # Pobierz informacje o użytkowniku na podstawie jego identyfikatora
            user_info = neo4j_service.get_user_info(id_uzytkownika)

            # Zapisz informacje o użytkowniku w sesji
            session['id_uzytkownika'] = id_uzytkownika
            session['imie'] = user_info.get('Imię')
            session['role'] = user_info.get('role')

            # Przekierowanie na odpowiedni szablon
            if user_info.get('role') == 'fachowiec':
                return render_template('fachowiec.html', user_info=user_info)
            else:
                return render_template('index2.html', user_info=user_info)
        else:
            return "Niepoprawny login lub hasło"
    else:
        return render_template('index.html')



from flask import request


@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.json
    latitude = data['latitude']
    longitude = data['longitude']



@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/add_offer')
def add_offer():
    return render_template('add_offer.html')

@app.route('/submit_offer', methods=['POST'])
def submit_offer():
    if 'logged_in' not in session:
        return "Nie jesteś zalogowany. Aby dodać ogłoszenie, zaloguj się."

    title = request.form['title']
    description = request.form['description']
    price = request.form['price']
    user_id = session.get('id_uzytkownika')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    neo4j_service.create_offer(user_id, title, description, price, timestamp)
    session['dodano_ogloszenie'] = True

    return redirect(url_for('index'))

@app.route('/user_info')
def get_user():
    if 'logged_in' in session:
        user_id = session.get('id_uzytkownika')
        user_info = neo4j_service.get_user_info(user_id)
        return render_template('index3.html', user_info=user_info, logged_in=True)
    return None

@app.route('/find')
def find():
    if 'logged_in' in session:
        user_id = session.get('id_uzytkownika')
        user_info = neo4j_service.get_user_info(user_id)
        offers = neo4j_service.get_all_offers()
        return render_template('fachowiec.html', offers=offers, logged_in=True, user_info=user_info)
    return redirect(url_for('login'))




if __name__ == '__main__':
    app.run(debug=True)
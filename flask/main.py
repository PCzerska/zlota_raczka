from flask import Flask, request, render_template, redirect, url_for, session
from neo4j import GraphDatabase
import re

app = Flask(__name__)
app.secret_key = 'super tajny klucz'  # Klucz sesji

class Neo4jService(object):

    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def create_user(self, email, haslo):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return "Niepoprawny adres e-mail jako login"
        if not re.search(r"\d", haslo) or not re.search(r"[a-zA-Z]", haslo):
            return "Hasło musi zawierać zarówno litery i cyfry"

        with self._driver.session() as session:
            session.write_transaction(self._create_user, email, haslo)

    def check_user(self, email, haslo):
        with self._driver.session() as session:
            result = session.run("MATCH (u:Użytkownik {login: $email, hasło: $haslo}) RETURN u", email=email, haslo=haslo)
            return bool(result.single())

    def get_user_id(self, email):
        with self._driver.session() as session:
            result = session.run("MATCH (u:Użytkownik {login: $email}) RETURN u.id_użytkownika as id", email=email)
            record = result.single()
            if record:
                return record['id']
            return None

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

# Konfiguracja Neo4j
NEO4J_URI = "neo4j+s://eda19c51.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "4S3ETALPdCft6VZAEX73gg3aYe-ImMxMykAYXxAg2dM"

neo4j_service = Neo4jService(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

@app.route('/')
def index():
    if 'logged_in' in session:
        #print("Zalogowany")
        return render_template('index2.html', logged_in=True)
    #print("Nie zalogowany")
    return render_template('index.html', logged_in=False)


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        haslo = request.form['haslo']

        result = neo4j_service.create_user(email, haslo)
        if result:
            return result

        return redirect(url_for('login'))
    else:
        return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        haslo = request.form['haslo']

        if neo4j_service.check_user(email, haslo):
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return "Niepoprawny login lub hasło"
    else:
        # Handle GET request (render login page)
        return render_template('index2.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

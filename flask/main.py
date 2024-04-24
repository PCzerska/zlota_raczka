from flask import Flask, request, render_template
from neo4j import GraphDatabase

app = Flask(__name__)

class Neo4jService(object):

    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def create_user(self, login, haslo, id_uzytkownika):
        print('coś')
        with self._driver.session() as session:
            session.write_transaction(self._create_user, login, haslo, id_uzytkownika)

    def get_last_user_id(self):
        with self._driver.session() as session:
            result = session.run("MATCH (u:Użytkownik) RETURN max(u.id_użytkownika) as last_id")
            last_id = result.single()['last_id']
            return last_id

    @staticmethod
    def _create_user(tx, login, haslo, id_uzytkownika):
        query = (
            "CREATE (u:Użytkownik {login: $login, hasło: $haslo, id_użytkownika: $id_uzytkownika})"
        )
        tx.run(query, login=login, haslo=haslo, id_uzytkownika=id_uzytkownika)

# Konfiguracja Neo4j
NEO4J_URI = "neo4j+s://eda19c51.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "4S3ETALPdCft6VZAEX73gg3aYe-ImMxMykAYXxAg2dM"

neo4j_service = Neo4jService(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['POST'])
def register():
    login = request.form['login']
    haslo = request.form['haslo']

    # Pobranie ostatniego ID użytkownika i dodanie 1
    last_id = neo4j_service.get_last_user_id()
    new_id = int(last_id) + 1

    # Dodanie użytkownika do bazy danych
    neo4j_service.create_user(login, haslo, new_id)

    # Przekazanie nowego ID do szablonu
    return render_template('success.html', login=login, id_uzytkownika=new_id)





if __name__ == '__main__':
    app.run(debug=True)

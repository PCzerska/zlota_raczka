from neo4j import GraphDatabase

def create_rodzaj_lokalizacji(tx, id, opis):
    query = (
        "CREATE (:RodzajLokalizacji {id: $id, opis: $opis})"
    )
    tx.run(query, id=id, opis=opis)

def create_status(tx, id, opis):
    query = (
        "CREATE (:Status {id: $id, opis: $opis})"
    )
    tx.run(query, id=id, opis=opis)



def update_id_fachowca(tx, id_ogloszenia, id_fachowca):
    query = (
        "MATCH (o:Ogloszenie {id_ogloszenia: $id_ogloszenia, przyjmujacy: 'nieznany'}), "
        "(f:Fachowiec {id_fachowca: $id_fachowca}) "
        "SET o.przyjmujacy = $id_fachowca "
        "CREATE (f)-[:PRZYJMUJE]->(o) "
        "RETURN o, f"
    )
    result = tx.run(query, id_ogloszenia=id_ogloszenia, id_fachowca=id_fachowca)
    return result.single()



def update_status(tx, id_ogloszenia, stan):
    map_status_query = (
        "MATCH (s:Status {id: $status_id}) "
        "RETURN s.opis AS mapped_status"
    )

    mapped_status_result = tx.run(map_status_query, status_id=stan)
    mapped_status = mapped_status_result.single()['mapped_status']

    update_query = (
        "MATCH (n:Ogloszenie {id_ogloszenia: $id_ogloszenia}) "
        "MATCH (s:Status {id: $stan}) "
        "SET n.status = s.opis "
        "RETURN n"
    )

    tx.run(update_query, id_ogloszenia=id_ogloszenia, stan=stan)

    print(f"Status ogłoszenia o ID {id_ogloszenia} został zaktualizowany na: {mapped_status}")



#Słowniki!!
#Ustawianie oceny


def create_ocena(tx, id_ogloszenia, id_uzytkownika, tresc, liczba_gwiazdek):
    query = (
        "MATCH (o:Ogloszenie {id: $id_ogloszenia}) "
        "MATCH (u:Użytkownik {id_użytkownika: $id_uzytkownika}) "
        "CREATE (ocena:Ocena {tresc: $tresc, liczba_gwiazdek: $liczba_gwiazdek}) "
        "CREATE (u)-[:WYSTAWIŁ]->(ocena) "
        "CREATE (ocena)-[:DOTYCZY]->(o)"
    )
    tx.run(query, id_ogloszenia=id_ogloszenia, id_uzytkownika=id_uzytkownika, tresc=tresc, liczba_gwiazdek=liczba_gwiazdek)

def create_fachowiec(tx, id_uzytkownika, imie, nazwisko, fach, data_dolaczenia, rodzaj_lokalizacji_id, lat, lon,
                     lista_id_ogloszen):

    create_fachowiec_query = (
        "MATCH (u:Użytkownik {id_użytkownika: $id_uzytkownika}) "
        "MATCH (rl:RodzajLokalizacji {id: $rodzaj_lokalizacji_id}) "
        "CREATE (f:Fachowiec {id_fachowca: $id_uzytkownika, RodzajLokalizacjiId: rl.opis, Imię: $imie, Nazwisko: $nazwisko, Fach: $fach, `Data dołączenia do aplikacji`: $data_dolaczenia, lat: $lat, lon: $lon, `lista id przyjętych ogłoszeń`: $lista_id_ogloszen}) "
        "CREATE (u)-[:POWIĄZANY_Z]->(f) "
        "CREATE (f)-[:MA_RODZAJ_LOKALIZACJI]->(rl) "
        "RETURN f"
    )

    result = tx.run(create_fachowiec_query, id_uzytkownika=id_uzytkownika, imie=imie, nazwisko=nazwisko, fach=fach,
                    data_dolaczenia=data_dolaczenia, lat=lat, lon=lon, lista_id_ogloszen=lista_id_ogloszen,
                    rodzaj_lokalizacji_id=rodzaj_lokalizacji_id)

    fachowiec_node = result.single()['f']

    print(f"Fachowiec created with RodzajLokalizacjiId: {rodzaj_lokalizacji_id} and id_fachowca: {id_uzytkownika}")








def create_ogloszenie(tx, id_uzytkownika, status_id, opis, fach, data_dodania, kwota, lat, lon, id_ogloszenia, id_fachowca=None):
    if id_fachowca is None:
        id_fachowca = 'nieznany'

    print(
        f"Creating Ogloszenie with parameters: {id_uzytkownika}, {status_id}, {opis}, {fach}, {data_dodania}, {kwota}, {lat}, {lon}, {id_ogloszenia}, {id_fachowca}")

    create_ogloszenie_query = (
        "MATCH (u:Użytkownik {id_użytkownika: $id_uzytkownika}) "
        "MATCH (s:Status {id: $status_id}) "
        "CREATE (o:Ogloszenie {Status: s.opis, Opis: $opis, Fach: $fach, `Data dodania`: $data_dodania, Kwota: $kwota, lat: $lat, lon: $lon, id_ogloszenia: $id_ogloszenia, przyjmujacy: $id_fachowca, id_zleceniodawcy: $id_uzytkownika}) "
        "CREATE (u)-[:DODAŁ_OGŁOSZENIE]->(o) "
        "RETURN id(o) as id_ogloszenia"
    )

    result = tx.run(create_ogloszenie_query, id_uzytkownika=id_uzytkownika, status_id=status_id, opis=opis, fach=fach,
                    data_dodania=data_dodania, kwota=kwota, lat=lat, lon=lon, id_ogloszenia=id_ogloszenia,
                    id_fachowca=id_fachowca)

    id_ogloszenia = result.single()['id_ogloszenia']

    print(f"Ogloszenie created with ID: {id_ogloszenia}")

    link_query = (
        "MATCH (o:Ogloszenie {id_ogloszenia: $id_ogloszenia}) "
        "MATCH (s:Status {id: $status_id}) "
        "CREATE (o)-[:MA_STATUS]->(s)"
    )

    tx.run(link_query, id_ogloszenia=id_ogloszenia, status_id=status_id)

    print(f"Ogloszenie linked to Status successfully.")





def create_user(tx, login, haslo, id_uzytkownika):
    query = (
        "CREATE (u:Użytkownik {login: $login, hasło: $haslo, id_użytkownika: $id_uzytkownika})"
    )
    tx.run(query, login=login, haslo=haslo, id_uzytkownika=id_uzytkownika)





def create_zleceniodawca(tx, id_uzytkownika, imie, nazwisko, data_dolaczenia):
    query = (
        "MATCH (u:Użytkownik {id_użytkownika: $id_uzytkownika}) "
        "CREATE (z:Zleceniodawca {Imię: $imie, Nazwisko: $nazwisko, `Data dołączenia`: $data_dolaczenia, id_zleceniodawcy: $id_uzytkownika}) "
        "CREATE (u)-[:POWIĄZANY_Z]->(z)"
    )
    tx.run(query, id_uzytkownika=id_uzytkownika, imie=imie, nazwisko=nazwisko, data_dolaczenia=data_dolaczenia)

def find_ogloszenia_by_uzytkownik_id(tx, id_uzytkownika):
    query = (
        "MATCH (u:Użytkownik {id_użytkownika: $id_uzytkownika})-[:DODAŁ_OGŁOSZENIE]->(o:Ogloszenie) "
        "RETURN o"
    )
    result = tx.run(query, id_uzytkownika=id_uzytkownika)
    return [record["o"] for record in result]

def find_ogloszenia_with_id(tx,id):
    query = (
        "MATCH (o:Ogloszenie {przyjmujacy: $id}) "
        "RETURN o"
    )
    result = tx.run(query,id=id)
    return [record["o"] for record in result]




# URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
URI = "neo4j+s://eda19c51.databases.neo4j.io"
AUTH = ("neo4j", "4S3ETALPdCft6VZAEX73gg3aYe-ImMxMykAYXxAg2dM")

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.verify_connectivity()
    with driver.session() as session:
        #session.write_transaction(create_user, "grzesśkkowa", "grzybiak", "1")
        #session.write_transaction(create_fachowiec, "4", "Jan11", "Kowalski10", "Elektryk", "2022-04-18", 1, 52.2297, 21.0122, ["1", "2"])
        #session.write_transaction(create_zleceniodawca, "1", "Anna", "Nowak", "2022-04-19")
        #session.execute_write(create_ogloszenie, "1", 1, "Potrzebuję kogoś do naprawy instalacji", "rucjk", "2024-04-17", 200.0, 52.2297, 21.0122,"1", None)
        #session.execute_write(create_ogloszenie, "2", 1, "Elektryk", "2024-04-17", 200.0,52.2297, 21.0122, "5", None)
        #session.write_transaction(create_ocena, "1", "2", "Bardzo dobry wykonawca", 5)
        #session.execute_write(update_id_fachowca,"6","4")
        #session.execute_write(update_status, "6", 2)
        # session.write_transaction(create_rodzaj_lokalizacji, 1, 'dokładna')
        # session.write_transaction(create_rodzaj_lokalizacji, 2, 'przybliżona')
        # session.write_transaction(create_rodzaj_lokalizacji, 3, 'brak')
        # session.write_transaction(create_status, 1, 'aktywne')
        # session.write_transaction(create_status, 2, 'w toku')
        # session.write_transaction(create_status, 3, 'zakończone')
        # session.write_transaction(create_status, 4, 'reklamowane')
        ogloszenia = session.write_transaction(find_ogloszenia_by_uzytkownik_id, "1")
        print(f"Ogloszenia wystawione przez zleceniodawcę o id '1': {ogloszenia}")
        ogloszenia = session.write_transaction(find_ogloszenia_with_id,'nieznany')
        print(f"Ogloszenia z nieznanym przyjmującym: {ogloszenia}")


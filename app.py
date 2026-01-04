import sqlite3
from flask import Flask, render_template_string, request, jsonify, redirect
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup

app = Flask(__name__)

DBNAME = "liste_des_reservations.db"

def initdb():
    conn = sqlite3.connect(DBNAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            prenom TEXT,
            datedepart TEXT,
            heuredepart TEXT,
            destination TEXT,
            nbplaces INTEGER,
            montant REAL,
            telephone TEXT,
            methodepaiement TEXT,
            statut TEXT DEFAULT 'en_attente',
            timestamp TEXT,
            numeroresa TEXT UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

initdb()

ORANGE_API_KEY = "VOTRE_CLE_ORANGE_DEVELOPER"
ORANGE_SMS_URL = "https://api.orange.com/sms-cmmessaging"

def envoyer_sms_orange(to, message):
    if ORANGE_API_KEY == "VOTRE_CLE_ORANGE_DEVELOPER":
        return {"status": "demo", "message": "Clé API manquante - mode démo"}
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": ORANGE_API_KEY
    }
    payload = {
        "to": to,
        "content": message,
        "from": "MokoloExpress"
    }
    resp = requests.post(ORANGE_SMS_URL, headers=headers, json=payload)
    return resp.json()

@app.route('/')
def index():
    with open('index.html', 'r') as f:
        html = f.read()
    
    dbviewer = '''
    <div id="db-viewer" style="position:fixed; top:10px; right:10px; background:white; padding:10px; z-index:1000;">
        <a href="/db" target="_blank">Voir DB Réservation/Billets</a>
    </div>
    <script>
    document.getElementById('veuillez valider le paiement').onclick = async function() {
        const tel = document.getElementById('telephone').value;
        const montant = currentReservation.montant;
        const methode = selectedPayment;
        let ussdcode;
        if (methode === 'mtn') {
            ussdcode = `*126*11*5552*${montant}#`;
        } else {
            ussdcode = `*150*21*2545*${montant}#`;
        }
        alert(`Saisissez le code ci-après dans votre téléphone afin de valider le paiement vos billets de voyage: ${ussdcode}`);
        const confirmed = confirm('Paiement effectué ?');
        if (confirmed) {
            await fetch('/confirmer_paiement', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tel, montant, methode, ...currentReservation})
            });
            alert('Veuillez consulter la base de donnée ci-haut afin de vérifier vos informations !');
        }
    }
    </script>
    '''
    soup = BeautifulSoup(html, 'html.parser')
    soup.body.append(BeautifulSoup(dbviewer, 'html.parser'))
    return str(soup)

@app.route('/confirmer_paiement', methods=['POST'])
def confirmer_paiement():
    data = request.json
    conn = sqlite3.connect(DBNAME)
    c = conn.cursor()
    numeroresa = f"RES-{int(datetime.now().timestamp())}"
    
    c.execute('''
        INSERT INTO reservations (nom, prenom, datedepart, heuredepart, destination, 
                                   nbplaces, montant, telephone, methodepaiement, 
                                   timestamp, numeroresa)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['nom'], data['prenom'], data['dateDepart'], data['heureDepart'], 
          data['destination'], data['nbPlaces'], data['montant'], data['tel'], 
          data['methode'], datetime.now().isoformat(), numeroresa))
    
    conn.commit()
    
    message = f"OK! {data['nom']} vers {data['destination']} ({data['nbPlaces']} pl.). N°{numeroresa}"
    smsresult = envoyer_sms_orange(data['tel'], message)
    conn.close()
    
    return jsonify({"status": "success", "numeroresa": numeroresa})

@app.route('/db')
def voir_db():
    conn = sqlite3.connect(DBNAME)
    c = conn.cursor()
    c.execute('SELECT * FROM reservations ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()
    
    html = '''
    <!DOCTYPE html>
    <html><head><title>Liste des Réservations</title>
    <style>table{border-collapse:collapse;width:100%;}th,td{border:1px solid #ddd;padding:8px;}</style>
    </head><body>
    <h1>Liste Réservations</h1><a href="/">← App</a>
    <table>
    <tr><th>ID</th><th>Nom</th><th>Prénom</th><th>Date</th><th>Heure</th><th>Dest</th>
    <th>Places</th><th>Montant</th><th>Tél</th><th>Méthode</th><th>Statut</th><th>N°</th><th>Crée</th></tr>'''
    
    for row in rows:
        html += ''.join(f'<td>{cell or ""}</td>' for cell in row)
        html += '</tr>'
    
    html += '</table></body></html>'
    return html

if __name__ == '__main__':
    print(" Serveur: http://localhost:5000")
    print(" DB: http://localhost:5000/db")
    app.run(debug=True, host='0.0.0.0', port=5000)


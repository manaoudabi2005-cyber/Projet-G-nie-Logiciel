
import sqlite3
from flask import Flask, render_template_string, request, jsonify, redirect
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup  

app = Flask(__name__)

 
DB_NAME = 'liste des réservations'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reservations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nom TEXT, prenom TEXT, date_depart TEXT, heure_depart TEXT,
                  destination TEXT, nb_places INTEGER, montant REAL,
                  telephone TEXT, methode_paiement TEXT, statut TEXT DEFAULT 'en_attente',
                  timestamp TEXT, numero_resa TEXT UNIQUE)''')
    conn.commit()
    conn.close()

init_db()


ORANGE_API_KEY = 'VOTRE_CLE_ORANGE_DEVELOPER'  
ORANGE_SMS_URL = 'https://api.orange.com/sms-cm/messaging'

def envoyer_sms_orange(to, message):
    if ORANGE_API_KEY == 'VOTRE_CLE_ORANGE_DEVELOPER':
        return {'status': 'demo', 'message': 'Clé API manquante - mode démo'}
    headers = {'Content-Type': 'application/json', 'X-API-Key': ORANGE_API_KEY}
    payload = {'to': to, 'content': message, 'from': 'MokoloExpress'}
    resp = requests.post(ORANGE_SMS_URL, headers=headers, json=payload)
    return resp.json()

@app.route('/')
def index():
    
    with open('index.html', 'r') as f:
        html = f.read()
    
    
    db_viewer = '''
    <div id="db-viewer" style="position:fixed; top:10px; right:10px; background:white; padding:10px; z-index:1000;">
        <a href="/db" target="_blank"> Voir DB Reservation_Billet</a>
    </div>
    <script>
    // Intégration paiement USSD + backend
    document.getElementById('valider-paiement').onclick = async function() {
        const tel = document.getElementById('telephone').value;
        const montant = currentReservation.montant;  // Du JS existant
        const methode = selectedPayment;  // mtn ou orange
        
        // USSD PRÉ-PAIEMENT (consigne stricte)
        let ussd_code;
        if (methode === 'mtn') {
            ussd_code = `*126*11*15552*${montant}#`;
        } else {
            ussd_code = `#150*12*12545*${montant}#`;
        }
        alert(`\\nComposer le code ci après dans votre téléphone :\\n${ussd_code}\\n\\nVeuillez confirmer le paiement, puis cliquez sur OK après réception du message de validation!`);
        
        // Attendre confirmation manuelle (pour démo/projet)
        const confirmed = confirm('Avant de cliquer sur OK veuillez vous assurer que vous avez fait le dépôt');
        if (confirmed) {
            await fetch('/confirmer_paiement', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tel, montant, methode, ...currentReservation})
            });
            alert('Réservation enregistrée en DB! Vérifiez /db');
            goToverification();
        }
    };
    </script>'''
    
    soup = BeautifulSoup(html, 'html.parser')
    soup.body.append(BeautifulSoup(db_viewer, 'html.parser'))
    return str(soup)

@app.route('/confirmer_paiement', methods=['POST'])
def confirmer_paiement():
    data = request.json
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    
    numero_resa = f"RES-{int(datetime.now().timestamp())}"
    c.execute('''INSERT INTO reservations (nom, prenom, date_depart, heure_depart, destination, nb_places,
                  montant, telephone, methode_paiement, timestamp, numero_resa)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (data['nom'], data['prenom'], data['dateDepart'], data['heureDepart'],
               data['destination'], data['nbPlaces'], data['montant'], data['tel'],
               data['methode'], datetime.now().isoformat(), numero_resa))
    conn.commit()
    
    
    message = f"Réservation CONFIRMEE! {data['nom']}, {data['destination']} {data['nbPlaces']} places. N°{numero_resa}. Présentez-vous 15min avant."
    sms_result = envoyer_sms_orange(data['tel'], message)
    
    conn.close()
    return jsonify({'status': 'success', 'numero_resa': numero_resa, 'sms': sms_result})

@app.route('/db')
def voir_db():
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM reservations ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()
    
    html = '''
    <!DOCTYPE html>
    <html><head><title>liste des réservations</title>
    <style>table {border-collapse:collapse; width:100%;} th,td {border:1px solid #ddd; padding:8px;}</style></head>
    <body>
    <h1>Voirs tous la liste des réservations</h1>
    <a href="/">← Retour App</a>
    <table>
    <tr><th>ID</th><th>Nom</th><th>Prénom</th><th>Date</th><th>Heure</th><th>Dest.</th><th>Places</th><th>Montant</th><th>Tél.</th><th>Méthode</th><th>Statut</th><th>Numéro</th><th>Date Créa</th></tr>'''
    for row in rows:
        html += '<tr>' + ''.join(f'<td>{cell or ""}</td>' for cell in row) + '</tr>'
    html += '</table></body></html>'
    return html

if __name__ == '__main__':
    print(" Serveur Mokolo Express lancé: http://localhost:5000")
    print(" DB accessible: http://localhost:5000/db")
    print(" USSD: MTN *126*11*15552*Montant# | Orange #150*12*12545*Montant#")
    app.run(debug=True, host='0.0.0.0', port=5000)

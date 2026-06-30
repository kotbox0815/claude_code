# CDP Report Suchportal

Datenbank + Webfrontend zum Importieren und Durchsuchen von VMware-ESXi-CDP-Reports
(CSV-Exporte mit Host/Cluster/vSwitch/PNic/Speed/MAC/DeviceID/PortID).

Läuft komplett lokal, ohne Cloud-Abhängigkeiten – gedacht für den Betrieb auf einem
RHEL-Linux-Server.

## Setup (RHEL)

```bash
sudo dnf install -y python3 python3-pip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Server starten (Entwicklung):

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Danach im Browser `http://<server>:8000` aufrufen.

Die SQLite-Datenbankdatei (`cdpreport.db`) wird beim ersten Start automatisch im
Arbeitsverzeichnis angelegt. Optional kann über die Umgebungsvariable `DATABASE_URL`
eine andere Datenbank (z.B. Postgres) verwendet werden, z.B.:

```bash
export DATABASE_URL="postgresql://user:pass@localhost/cdpreport"
```

## CSV-Import

### Über das Webfrontend

`http://<server>:8000/upload` aufrufen und die CDP-Report-CSV hochladen.

### Über die Kommandozeile (z.B. für Cronjobs)

```bash
source venv/bin/activate
python -m backend.cli_import /pfad/zur/CDPReport.csv
```

Beispiel-Cronjob (täglich um 02:00 Uhr alle CSVs in einem Ablage-Verzeichnis importieren):

```cron
0 2 * * * cd /opt/cdpreport && /opt/cdpreport/venv/bin/python -m backend.cli_import /opt/cdpreport/incoming/CDPReport.csv >> /var/log/cdpreport-import.log 2>&1
```

## Produktivbetrieb als systemd-Service

1. Projekt z.B. nach `/opt/cdpreport` kopieren, venv dort anlegen und Dependencies installieren.
2. Eigenen Service-User anlegen: `sudo useradd -r -s /sbin/nologin cdpreport`
3. Datenverzeichnis anlegen: `sudo mkdir -p /opt/cdpreport/data && sudo chown cdpreport:cdpreport /opt/cdpreport/data`
4. `deploy/cdpreport.service` nach `/etc/systemd/system/cdpreport.service` kopieren und Pfade/User bei Bedarf anpassen.
5. Service aktivieren:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cdpreport
```

### Firewall (firewalld)

```bash
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

(Bei Betrieb hinter einem nginx-Reverse-Proxy stattdessen nur Port 80/443 freigeben
und `8000` lokal binden.)

### SELinux

Falls SELinux im Enforcing-Modus läuft und der Service nicht startet, den venv-Pfad
korrekt labeln:

```bash
sudo semanage fcontext -a -t bin_t "/opt/cdpreport/venv/bin(/.*)?"
sudo restorecon -R /opt/cdpreport/venv
```

## Tests

```bash
pytest
```

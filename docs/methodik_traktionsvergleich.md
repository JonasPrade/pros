# Methodik des Traktionsvergleichs (Masterarbeit)

Stand: rekonstruiert aus dem Code des Repos `pros` (Commit a5a5269), Oktober 2026. Quelle sind `prosd/models.py` (MasterScenario, MasterArea, TimetableTrainGroup, TimetableTrainCost), `prosd/calculation_methods/use.py`, `prosd/calculation_methods/cost.py`, `prosd/manage_db/version.py`, `prosd/graph/routing.py`, `prosd/graph/block_rw_lines.py` und `prosd/parameter.py`. Der Text der Masterarbeit lag bei der Rekonstruktion nicht vor. Jede Stelle, an der der Code mehrdeutig ist oder von der vermuteten Absicht abweicht, ist in Abschnitt 10 gesammelt und muss gegen den Thesis-Text entschieden werden, bevor neu entwickelt wird.

Zweck dieses Dokuments: Die Methodik so festzuhalten, dass sie unabhängig vom bestehenden Code (Flask, SQLAlchemy, PostGIS) neu implementiert werden kann. Abschnitt 11 skizziert die Zielarchitektur.

## 1. Fragestellung und Grundidee

Untersucht wird, welche Traktionsart für heute nicht elektrifizierte Netzbereiche des deutschen Schienennetzes unter einem gegebenen Zielfahrplan (Deutschlandtakt) gesamtwirtschaftlich am günstigsten ist. Verglichen werden sechs Traktionsvarianten:

| Schlüssel | Bedeutung |
|---|---|
| `electrification` | vollständige Oberleitung im Gebiet |
| `battery` | Batterietriebzüge, Nachladen unter vorhandener Oberleitung und an Ladestationen, ergänzt um punktuelle Infrastruktur |
| `h2` | Wasserstofffahrzeuge mit Tankstellen |
| `efuel` | Fahrzeuge mit synthetischem Kraftstoff (Dieseltechnik) mit Tankstellen |
| `diesel` | Dieselfahrzeuge mit Tankstellen (Referenz) |
| `optimised_electrification` | Mischung aus Oberleitung und Batterie, teilgebietsweise optimiert |

Bewertungsgröße ist je Gebiet die Summe aus Barwert der Infrastrukturkosten und Barwert der Betriebskosten (inklusive monetarisierter externer Effekte) über eine Betriebsdauer von 30 Jahren. Die Traktion mit der kleinsten Summe gilt als kosteneffizient. Die Ergebnisse werden je Szenario über alle Gebiete aggregiert (Anzahl Gebiete, Streckenkilometer, Zugkilometer, Kosten, CO2).

Methodische Grundlage sind das Bewertungsverfahren des Bundesverkehrswegeplans 2030 (BVWP, für Schienengüterverkehr) und die Verfahrensanleitung Standardisierte Bewertung (Standi, für Schienenpersonennah- und -fernverkehr).

## 2. Begriffe

| Begriff im Code | Bedeutung |
|---|---|
| Szenario (`MasterScenario`) | Ein Untersuchungsfall: Startjahr Betrieb (2030), Betriebsdauer (30 Jahre), eine Menge von Infrastrukturprojekten, die zusätzlich zum Bestand als gebaut gelten, sowie die daraus abgeleiteten Routen, Gebiete und Kosten. |
| Infrastrukturversion (`Version`) | Der Infrastrukturzustand eines Szenarios: Bestandsnetz plus Wirkung der Szenario-Projekte (Elektrifizierung, Sperrung, Ladestationen). Wird im Speicher gehalten und während der Rechnung durch Zwischenergebnisse (zum Beispiel neu elektrifizierte Strecken) temporär fortgeschrieben. |
| Strecke (`RailwayLine`) | Kleinster Netzabschnitt mit Länge, Gleiszahl, Oberleitung ja/nein, Stromschiene ja/nein, ABS/NBS-Kennzeichen, Sperrung, Start- und Endknoten, zugeordnete Bahnhöfe. |
| Bahnhof (`RailwayStation`) | Betriebsstelle mit Kürzel, zugeordneten Strecken, Flag Ladestation, Flag kleine Ladestation. |
| Zuggruppe (`TimetableTrainGroup`) | Alle Züge eines Fahrplans mit gleichem Laufweg und gleicher Formation in einer Richtung (railML-Begriff). Trägt Kategorie (Verkehrsart), Halte, Fahrzeiten, Formation. |
| Fahrplanlinie (`TimetableLine`) | Zusammenfassung der Zuggruppen beider Richtungen einer Linie. Einheit für die Standi-Betriebskostenrechnung und die Umlaufbildung. |
| Umlauf (`TrainCycle`) | Kette von Zügen einer Linie, die ein Fahrzeug nacheinander fahren kann (Ankunft plus Wendezeit vor nächster Abfahrt am selben Ort). Anzahl Umläufe = benötigte Fahrzeuge. |
| Verkehrsart (`transport_mode`) | `sgv` Güterverkehr, `spnv` Nahverkehr, `spfv` Fernverkehr. |
| Gebiet (`MasterArea`, Hauptgebiet) | Zusammenhängender Cluster nicht elektrifizierter Strecken samt aller Zuggruppen, die sie befahren. Bewertungseinheit. |
| Teilgebiet (`MasterArea` mit `superior_master_id`) | Teilmenge der Strecken eines Gebiets, die von exakt derselben Menge Zuggruppen befahren wird. Einheit für die optimierte Elektrifizierung. |
| Route (`RouteTraingroup`) | Geordnete Folge von Strecken, die eine Zuggruppe in einem Szenario nutzt. |
| Fahrzeugmuster (`VehiclePattern`) | Kennwerte eines Fahrzeugtyps (Energie, Kosten, Masse, Batteriekapazität) mit Verweisen auf die Varianten je Traktion. |
| Formation (`Formation`) | Fahrzeugzusammenstellung eines Zuges. Hat je eine Ersatzformation für BVWP- und Standi-Rechnung. |
| Berechnungsmethode | `bvwp` oder `standi`, siehe Abschnitt 6.1. |
| Maßnahme (`ProjectContent`) | Infrastrukturprojekt mit Kostenwerten. Dient sowohl als Eingabe (Szenario-Projekte) als auch als Ergebnis (je Gebiet und Traktion wird eine Maßnahme mit den berechneten Kosten erzeugt, bei Batterie und optimierter Elektrifizierung mit Teilmaßnahmen). |

## 3. Eingangsdaten

### 3.1 Infrastruktur
Je Strecke: `id`, `length` (m), `number_tracks` (`eingleisig`/`zweigleisig`), `catenary` (bool), `conductor_rail` (bool), `abs_nbs` (`ABS`/`NBS`/leer), `closed` (bool), Start-/Endknoten, Nachbarstrecken (über Knoten), Bahnhöfe auf der Strecke.
Je Bahnhof: `id`, `name`, `db_kuerzel`, Strecken, `charging_station`, `small_charging_station`.
Der Streckengraph für das Routing ist ein gerichteter networkx-Graph mit Teilknoten je Strecke und Richtung, Abbiegebeziehungen an Knoten (Mindestwinkel 60 Grad) und Bahnhofsknoten als Quelle/Ziel. Er wird einmal erzeugt und als Datei gespeichert.

### 3.2 Fahrplan
Import aus railML des Deutschlandtakts: Zuggruppen, Züge, Zugteile, Betriebsstellen (`TimetableOcp`) mit planmäßiger Ankunft/Abfahrt und Typ (`stop` oder Durchfahrt), Mindestfahrzeiten je Abschnitt, Kategorie mit Verkehrsart, Formation je Zugteil. Zuordnung railML-Betriebsstelle zu Bahnhof über Kürzel.

### 3.3 Fahrzeuge
Formation mit Fahrzeugliste (Mehrfachnennung möglich). Fahrzeug mit `brutto_weight`, `length`, `engine`/`wagon` (für Güterzüge: Lok und Wagenpaket), Verweise auf Fahrzeugmuster je Verkehrsart. Fahrzeugmuster mit den in Abschnitt 6 genutzten Feldern und Verweisen auf die Variante je Traktion (`vehicle_pattern_electrical`, `_battery`, `_h2`, `_efuel`, `_diesel`). Der Feldtyp `type_of_traction` (`Elektro`, `Batterie`, `Diesel`, `eFuel`, `H2`) steuert die Energiekostenformel.

### 3.4 Szenario-Projekte
Maßnahmen mit Wirkung auf die Infrastrukturversion: `elektrification` (Strecke gilt als elektrifiziert), `closure` (Strecke gesperrt, im Routing ausgeschlossen), `charging_station`, `small_charging_station` (Bahnhof gilt als Ladepunkt). Hat eine Maßnahme Teilmaßnahmen, werden diese statt der Hauptmaßnahme angewendet.

### 3.5 Parameter (`parameter.py`)

Zeit und Zins

| Parameter | Wert |
|---|---|
| Preis- und Basisjahr Barwert | 2016 |
| Diskontrate | 1,7 % |
| Annuitätsfaktor Infrastruktur | 0,0428 |
| Startjahr Betrieb | 2030 |
| Planungsdauer | 5 Jahre |
| Baudauer | 5 Jahre |
| Betriebsdauer | 30 Jahre |
| Startjahr Planung | 2030 minus 10 = 2020 |

Infrastrukturkosten (Tausend Euro)

| Parameter | Wert |
|---|---|
| Planungskostenanteil an Investition | 18 % |
| Instandhaltung Oberleitung und Ladestationen, je Jahr | 1,4 % der Investition |
| Instandhaltung Tankstellen, je Jahr | 3 % der Investition |
| Oberleitung je km | 737 |
| Lebensdauer Oberleitung | 60 Jahre |
| Bahnstromversorgung je km | 200 |
| Ingenieurbau je km | 200 |
| Grunderwerb je km | 5 |
| Ladestation | 2.582 |
| kleine Ladestation | 1.200 |
| Tankstelle H2 | 6.000, eine je 60 km |
| Tankstelle Diesel | 1.000, eine je 40 km |
| Tankstelle eFuel | 1.000, eine je 40 km |

Energie und externe Kosten

| Energieträger | Preis (€/kWh bzw. €/l bzw. €/kg) | CO2 (g/Einheit) | Schadstoffe (€-Faktor) | Primärenergie (Faktor) |
|---|---|---|---|---|
| Strom erneuerbar (verwendet) | 0,14 | 21 | 0,05 | 4,5 |
| Strom Mix (definiert, nicht verwendet) | 0,12 | 414 | 0,96 | 6 |
| Diesel | 0,75 | 2.774 | 6,57 | 38,9 |
| eFuel | 2,50 | 370 | 6,57 | 78,2 |
| H2 | 5,00 | 938 | 2,18 | 198,7 |

| Parameter | Wert |
|---|---|
| CO2-Kostensatz | 670 €/t |
| Nutzenpunkte Primärenergie | 0,9 |
| Geldwert je Nutzenpunkt | 15,5 € |
| Ladeleistung Batterie | 1.200 kW |
| Wendezeit Umlaufbildung | 10 Minuten |

Resilienzfall (Abschnitt 9): Lkw-Kostensätze je 100 km (Energie 17,5, Personal 25,18, Kapital 22, Instandhaltung 12,86, CO2 1,8, Primärenergie 7,8, Emission 0,1 Euro), Lkw-Nutzlast 25 t, Containerwagen 19,7 m, 20 t Eigenmasse, 50 t Nutzlast, Wagenkosten 1,06 €/Wagen-h, Triebfahrzeugführer 57 €/h, Zugbereitstellung 23 €/Wagen, Störungsanteil 4,63 % der Zeit, Umleitungsgeschwindigkeit 60 km/h.

## 4. Ablauf der Rechnung

1. Szenario anlegen: Name, Startjahr, Betriebsdauer, Liste der Szenario-Projekte. Optional werden Routen, Gebiete und Betriebskosten aus einem Referenzszenario kopiert.
2. Infrastrukturversion bilden: Bestandsnetz laden, Szenario-Projekte anwenden (Abschnitt 3.4).
3. Routing: jede Zuggruppe ohne Route in diesem Szenario wird über den Streckengraphen geroutet (Abschnitt 5). Ergebnis ist die geordnete Streckenfolge.
4. Gebietsbildung (Abschnitt 6).
5. Je Hauptgebiet und je Traktion: Infrastrukturkosten (Abschnitt 8), dann Betriebskosten je Zuggruppe (Abschnitt 7). Reihenfolge der Traktionen: electrification, efuel, battery, optimised_electrification, diesel, h2. Für Gebiete mit Güterverkehr werden battery und h2 übersprungen.
6. Je Gebiet Summe bilden und Minimum bestimmen, Kennzahlen am Gebiet speichern (Abschnitt 9).
7. Je Szenario aggregieren und speichern (Abschnitt 9).

Hinweis zur Implementierung im Altcode: Schritt 5 schreibt während der Rechnung in die Datenbank (Maßnahmen, Zugkosten) und liest sie wieder; Zwischenergebnisse der optimierten Elektrifizierung verändern die Infrastrukturversion im Speicher. Für die Neuentwicklung gilt: Rechnung im Speicher, Persistierung erst am Ende.

## 5. Routing der Zuggruppen

Eingabe: erste und letzte Betriebsstelle der Zuggruppe, alle Zwischenhalte als Via-Punkte (railML-Betriebsstellen ohne zugeordneten Bahnhof werden übersprungen; zusätzlich gibt es eine Ignorierliste je Zuggruppe und optionale Zwangsfolgen für Umleitungen).
Verfahren: kürzester Weg (Dijkstra) nacheinander zwischen den Via-Punkten. Kantengewicht ist die Streckenlänge in Metern. Strecken mit Oberleitung werden mit Faktor 0,95 bevorzugt. Gesperrte Strecken (`closed`) sind ausgeschlossen. Strecken mit fehlender oder nicht positiver Länge erhalten Gewicht 0.
Ausgabe: Streckenfolge mit laufender Nummer je Zuggruppe und Szenario.

## 6. Gebietsbildung

### 6.1 Hauptgebiete
Ausgangsmenge: alle Strecken ohne Oberleitung und ohne Stromschiene in der Infrastrukturversion, sowie alle Zuggruppen, deren Route mindestens eine dieser Strecken enthält.
Clusterbildung durch Fixpunktiteration, beginnend mit der ersten noch nicht zugeordneten Zuggruppe:
1. Füge alle nicht elektrifizierten Strecken hinzu, die von den gesammelten Zuggruppen befahren werden.
2. Füge zusätzlich alle nicht elektrifizierten Strecken hinzu, die an einem Bahnhof enden oder beginnen, an dem eine dieser Strecken endet oder beginnt (Verbindung über gemeinsamen Bahnhof).
3. Füge alle Zuggruppen hinzu, die eine der gesammelten Strecken befahren.
4. Wiederhole, bis keine neue Zuggruppe hinzukommt.
Das Ergebnis ist ein Gebiet mit Streckenmenge und Zuggruppenmenge. Elektrifizierte Strecken der Routen gehören nicht zum Gebiet, zählen aber in der Betriebskostenrechnung der Zuggruppen mit (Abschnitt 7). Eine ältere Skriptfassung startete nur von Güterzuggruppen; die Modellfassung startet von allen Zuggruppen.

### 6.2 Teilgebiete
Für ein Hauptgebiet: Strecken werden zu Teilgebieten zusammengefasst, wenn sie von exakt derselben Menge Zuggruppen (im Szenario) befahren werden. Jedes Teilgebiet erhält diese Zuggruppenmenge. Teilgebiete werden nur für die optimierte Elektrifizierung benötigt und bei Bedarf erzeugt.

## 7. Betriebskosten je Zuggruppe

### 7.1 Zuordnung der Berechnungsmethode
| Verkehrsart | Methode |
|---|---|
| sgv | bvwp (Zuggruppe einzeln, nur Lok) |
| spnv | standi (auf Ebene der Fahrplanlinie, Ergebnis anteilig je Zuggruppe) |
| spfv | standi, weil alle Traktionen in `SPFV_STANDI_METHOD` stehen; der bvwp-Zweig für spfv existiert im Code, ist aber nicht erreichbar |

Für sgv liefern battery und h2 kein Ergebnis (nicht berechnet).

### 7.2 Betriebsleistungsgrößen je Zuggruppe
| Größe | Definition |
|---|---|
| Linienlänge L (km) | Summe der Streckenlängen der Route im Szenario |
| Linienlänge ohne Oberleitung L_oo (km) | Teil von L mit `catenary = False` in der Infrastrukturversion |
| Anteil ABS / NBS | Teil von L mit `abs_nbs` = ABS bzw. NBS |
| Züge je Tag n | Anzahl Züge der Zuggruppe (Fahrplan gilt als Tagesfahrplan) |
| Zug-km je Jahr | L × n × 365 / 1000, in Tausend Zug-km |
| Reisezeit T | Abfahrt erste Betriebsstelle bis Ankunft letzte Betriebsstelle, inkl. Halte |
| Zugstunden je Jahr | T × n × 365 / 1000, in Tausend Zug-h |
| Halte h | Anzahl Betriebsstellen mit Typ `stop` |
| Haltezeit gesamt | Summe (Abfahrt minus Ankunft) über alle Halte |
| Halte je Jahr | h × n × 365 |

### 7.3 Kostenbestandteile (Jahreswerte, dann Barwert)
Gemeinsame Energiekostenformel je Fahrzeugmuster mit Energiemenge E (kWh, l oder kg) und den Faktoren aus Abschnitt 3.5:
- Energiekosten = Preis × E
- CO2-Menge (t) = E × CO2-Faktor × 10^-3; CO2-Kosten = CO2-Menge × 670 × 10^-3
- Schadstoffkosten = E × Schadstofffaktor × 10^-2
- Primärenergiekosten = E × Primärenergiefaktor × 0,9 × 0,9 × 15,5 × 10^-3 (der Faktor 0,9 steht im Code zweimal, siehe Abschnitt 10)

Für `type_of_traction` Elektro und Batterie werden die Faktoren für erneuerbaren Strom genutzt. eFuel nutzt die Dieselverbrauchsformel mit eFuel-Faktoren.

BVWP Güterverkehr (`BvwpSgv`), nur das Triebfahrzeug der BVWP-Ersatzformation:
- Kapitaldienst = `debt_service` des Fahrzeugmusters × Zugstunden je Jahr
- Instandhaltung = `maintenance_cost_km` × Zug-km je Jahr
- Energie elektrisch (kWh) = 1,08 × m^-0,62 × Zug-km × 1000, m = Bruttomasse des Wagenpakets (t)
- Energie Diesel/eFuel (l) = 0,277 × m^-0,62 × Zug-km × 1000
- Gesamt = Kapitaldienst + Instandhaltung + Energie + CO2 + Schadstoffe + Primärenergie

BVWP Personenverkehr (`BvwpSpfv`, `BvwpSpnv`, derzeit nicht erreichbar): wie oben je Fahrzeug der Formation, Energie = Zug-km × `energy_per_km` (bei spfv getrennt nach Kernnetz, ABS mit `energy_abs_per_km`, NBS mit `energy_nbs_per_km`) plus Zugstunden × `energy_consumption_hour`.

Standi Personenverkehr (`StandiSpnv`), auf Ebene der Fahrplanlinie mit der Standi-Ersatzformation:
- Umläufe U = Anzahl Umläufe der Linie bei 10 Minuten Wendezeit (Abschnitt 7.4)
- Kapitaldienst = U × Summe `debt_service` der Fahrzeuge
- zeitabhängige Instandhaltung = U × Summe (`maintenance_cost_duration_t` × Masse) / 1000
- laufleistungsabhängige Instandhaltung je Zuggruppe und Fahrzeug = (1 + z_IH × L_oo / L) × `maintenance_cost_km` × Zug-km, mit z_IH = `additional_maintenance_cost_withou_overhead` (Batteriezuschlag für Fahren ohne Oberleitung)
- Fahrenergie je Zuggruppe und Fahrzeug = (1 + z_E × L_oo / L) × `energy_per_km` × Zug-km, z_E = `additional_energy_without_overhead`
- Halteenergie: Referenzgeschwindigkeit v_ref nach Standi (Verfahrensanleitung S. 197): mit I = 55,6 × (T minus Haltezeit) in Minuten und s = h minus 1 Abschnitten gilt v_ref = 3,6 / (a × s) × (I minus Wurzel(I² minus 2 × a × s × L × 1000)), a = `energy_stop_a`. Ist die Wurzel nicht definiert, wird v_ref = 160 gesetzt. Energie je Halt = `energy_stop_b` × v_ref² × Masse × 10^-6; Halteenergie je Jahr = Energie je Halt × Halte je Jahr / 1000
- THG Fahrzeugherstellung = U × Summe `emission_production_vehicle_calc` × 670 / 1000
- Gesamt = Kapitaldienst + Instandhaltung (beide Anteile) + Energie + CO2 + Schadstoffe + Primärenergie + THG Herstellung
- Alle Werte werden durch die Anzahl Zuggruppen der Linie geteilt und je Zuggruppe gespeichert

### 7.4 Umlaufbildung
Alle Züge einer Linie, sortiert nach Abfahrt. Beginne mit dem frühesten Zug. Der Folgezug ist der früheste Zug, der an der Endbetriebsstelle des Vorgängers startet und frühestens Ankunft plus Wendezeit abfährt. Kette fortsetzen, bis kein Zug mehr passt; dann neuen Umlauf beginnen. Anzahl Umläufe = Fahrzeugbedarf.

### 7.5 Barwertbildung
Für einen konstanten Jahreswert K über die Betriebsdauer D ab Startjahr S: Barwert = Summe über x = 0 .. D minus 1 von K / (1 + 0,017)^(S minus 2016 + x). Der Jahreswert `cost` wird je Zuggruppe gespeichert; die Gebietsrechnung bildet daraus den Barwert über 2030 bis 2059.

## 8. Infrastrukturkosten je Gebiet und Traktion

### 8.1 Gemeinsamer Rahmen (`BvwpCost`)
Eingabe: Investition I und jährliche Instandhaltung M (beide Tausend Euro), Startjahr Planung 2020.
- Planungskosten P = 0,18 × I
- Barwert Planung: P gleichmäßig über 5 Jahre ab 2020 diskontiert
- Barwert Investition: I gleichmäßig über 5 Jahre ab 2025 diskontiert
- Barwert Instandhaltung: M jährlich über 30 Jahre ab 2030 diskontiert
- Kapitaldienst = Barwert Investition × 0,0428 (wird gespeichert, geht aber nicht in die Gesamtkosten ein)
- Gesamtkosten Infrastruktur = Barwert Planung + Barwert Investition + Barwert Instandhaltung
Die Baudauer ist fest 5 Jahre; eine Tabelle zur kostenabhängigen Baudauer nach BVWP (`duration_build_rail_bvwp.csv`) existiert, wird aber nicht verwendet.

### 8.2 Oberleitung (`electrification`)
Für jede Strecke des Gebiets ohne Oberleitung in der Infrastrukturversion: Kosten je km = 200 + 200 + 5 + 737 × 30 / 60 = 773,5 Tausend Euro, bei zweigleisigen Strecken verdoppelt. I = Summe über Strecken (Länge in km × Kosten je km). M = 0,014 × I. Elektrifizierte Länge wird mitgeführt (zweigleisig zählt doppelt).

### 8.3 Tankstellen (`diesel`, `efuel`, `h2`)
Anzahl Stationen = aufgerundet(Gebietslänge in km / km je Station). I = Anzahl × Stationskosten. M = 0,03 × I.

### 8.4 Ladeinfrastruktur
Ladestation: I = 2.582, M = 0,014 × I. Kleine Ladestation: I = 1.200, M = 0,014 × I. Oberleitung im Bahnhof: wie 8.2 für die betreffende Strecke.

### 8.5 Batterie (`battery`)
Ziel: die minimale zusätzliche Infrastruktur bestimmen, mit der jede Linie des Gebiets im Batteriebetrieb durchführbar ist. Vorgehen je Fahrplanlinie im Gebiet (jede Linie einmal, auch wenn mehrere Zuggruppen im Gebiet liegen):

1. Start- und Endbetriebsstellen aller Zuggruppen der Linie sammeln.
2. Je Startbetriebsstelle der Linie einen Umlauf wählen und dessen erste zwei Züge (Hin- und Rückfahrt) betrachten.
3. Für jeden der zwei Züge die Route in Abschnitte teilen. Ein neuer Abschnitt beginnt, wenn sich der Oberleitungsstatus ändert oder ein Halt mit Haltezeit von mindestens 3 Minuten oder mit Ladestation erreicht wird. Je Abschnitt: Länge, Oberleitung ja/nein, Strecken, letzter Halt mit Haltezeit und Ladestationsflag, Fahrzeit = Länge / mittlere Reisegeschwindigkeit der Zuggruppe. Für den letzten Abschnitt ist die Standzeit die Zeit bis zur Abfahrt des Folgezugs im Umlauf (falls kein Folgezug: 1 Stunde).
4. Energiebedarf je Abschnitt mit dem Batterie-Fahrzeugmuster: Fahrenergie = (1 + z_E × L_oo / L) × `energy_per_km` × Abschnittslänge auf Abschnitten ohne Oberleitung (z_E = 0 unter Oberleitung), plus Halteenergie je Halt im Abschnitt nach der Standi-Formel aus 7.3. Halte werden den Abschnitten über die Strecken ihres Bahnhofs zugeordnet; liegt ein Halt an mehreren Abschnitten, gewinnt ein Abschnitt mit Oberleitung; Halte ohne Bahnhof werden über den Anteil der Fahrzeit zugeordnet.
5. Batteriebilanz entlang Hin- und Rückfahrt: Start mit voller Kapazität C (Summe `battery_capacity` der Fahrzeuge). Unter Oberleitung: Ladung 1.200 kW × Fahrzeit, begrenzt auf C. Ohne Oberleitung: Abzug der Abschnittsenergie. An einem Abschnittsende mit Ladestation: Ladung 1.200 kW × Haltezeit. Am Ende eines Zuges, wenn der letzte Abschnitt Oberleitung oder Ladestation hat: Ladung über die Standzeit. Jeder negative Zwischenstand wird als Problem mit Ort und benötigter Ladezeit vermerkt.
6. Zwei Problemtypen: Einzelumlaufproblem (Batterie wird innerhalb von Hin- und Rückfahrt leer) und Mehrumlaufproblem (Bilanz nach Hin- und Rückfahrt negativ, und mögliche Umläufe C / Defizit sind kleiner als benötigte Umläufe = Anzahl Züge im Umlauf / 2).
7. Maßnahmen für das Einzelumlaufproblem, in dieser Reihenfolge: Problem auf der Rückfahrt: Ladepunkt am Endbahnhof der Hinfahrt (Oberleitung im Bahnhof, wenn dort an einem anderen Gleis bereits Oberleitung liegt, sonst Ladestation), Ladung = Standzeit × 1.200 kW. Verbleibendes Problem: zusätzliche Oberleitung auf Strecken vor der Problemstelle (siehe 8.5.1), bis der Bedarf gedeckt ist. Bleibt ein Problem, wird es protokolliert und keine weitere Maßnahme erzeugt.
8. Maßnahmen für das Mehrumlaufproblem, in dieser Reihenfolge, jeweils bis der Bedarf gedeckt ist: Ladepunkte an den Endbahnhöfen, Ladepunkte an Zwischenhalten mit Haltezeit ab 3 Minuten, zusätzliche Oberleitung auf Strecken ohne Oberleitung.
9. Alle erzeugten Maßnahmen werden sofort in die Infrastrukturversion übernommen, damit folgende Linien davon profitieren.
10. Nach allen Linien: an jeder Start- oder Endbetriebsstelle ohne Lademöglichkeit (keine Ladestation, keine Oberleitung an einer Strecke des Bahnhofs) eine kleine Ladestation ergänzen (abschaltbar).

Die Batteriemaßnahme des Gebiets ist die Summe aller Teilmaßnahmen (Investition, Instandhaltung, Planung, Barwerte).

#### 8.5.1 Auswahl zusätzlicher Streckenelektrifizierung
Kandidaten sind die Strecken der betrachteten Abschnitte. Sie werden nach Anzahl der sie befahrenden Zuggruppen (absteigend) und Länge (aufsteigend) sortiert. Bevorzugt werden Strecken, die an einen Bahnhof mit Lademöglichkeit oder an eine Nachbarstrecke mit Oberleitung anschließen; gibt es keine, die meistbefahrenen Strecken. Strecken werden nacheinander hinzugefügt; jede liefert Ladung = 1.200 kW × (Länge / mittlere Geschwindigkeit der Linie), begrenzt auf C. Nach jeder Strecke werden deren Nachbarstrecken in der Route zu den Kandidaten ergänzt. Abbruch, wenn der Bedarf gedeckt ist. Die ausgewählten Strecken bilden eine Elektrifizierungsmaßnahme nach 8.2.

### 8.6 Optimierte Elektrifizierung (`optimised_electrification`)
1. Gebiet vollständig elektrifizieren (Maßnahme nach 8.2) und Betriebskosten aller Zuggruppen mit Traktion Oberleitung bestimmen. Ausgangszuordnung: jede Zuggruppe fährt elektrisch.
2. Teilgebiete bilden (6.2) und nach Betriebsleistung (Zug-km je Tag der zugehörigen Zuggruppen) aufsteigend sortieren.
3. Für jedes Teilgebiet in dieser Reihenfolge: Oberleitung des Teilgebiets in der Infrastrukturversion wieder entfernen. Enthält das Teilgebiet Güterverkehr: Oberleitung ist gesetzt, Kosten nach 8.2 plus Betriebskosten. Sonst Kosten für Oberleitung und für Batterie je ermitteln als Barwert der Betriebskosten der Teilgebiets-Zuggruppen plus Infrastrukturkosten (Batterie nach 8.5 ohne kleine Ladestationen). Die günstigere Variante wird gewählt, ihre Maßnahme in die Infrastrukturversion übernommen, und bei Batterie werden die Zuggruppen des Teilgebiets auf Batterie umgestellt.
4. Nach allen Teilgebieten: kleine Ladestationen an Start- und Endbetriebsstellen ohne Lademöglichkeit ergänzen.
5. Ergebnis: Maßnahme mit Teilmaßnahmen, Traktion je Zuggruppe (`TractionOptimisedElectrification`), Anteile Oberleitung/Batterie nach km und Infrastrukturkosten.
Betriebskosten des Gebiets für diese Traktion = Summe der je Zuggruppe gewählten Traktion (Oberleitung oder Batterie).

## 9. Entscheidung und Kennzahlen

Je Gebiet und Traktion: Gesamtkosten = Infrastrukturkosten (8.1, `planned_total_cost` der Gebietsmaßnahme) + Barwert der Betriebskosten (Summe der Jahreswerte aller Zuggruppen, diskontiert nach 7.5). Kosteneffiziente Traktion = Minimum über die berechneten Traktionen. Zusätzlich je Traktion CO2 je Jahr (Summe `co2_emission` der Zuggruppen; bei Güterverkehr ohne battery und h2).
Je Gebiet gespeichert: Gesamt-, Betriebs- und Infrastrukturkosten je Traktion, kosteneffiziente Traktion, Flags sgv/spnv/spfv. Für Teilgebiete nur Oberleitung und (ohne Güterverkehr) Batterie.
Je Szenario gespeichert, jeweils je kosteneffizienter Traktion: Anzahl Gebiete, Streckenkilometer, Zug-km je Tag, Infrastruktur- und Betriebskosten. Zusätzlich eine Aufteilung, bei der Gebiete mit optimierter Elektrifizierung in ihre Oberleitungs- und Batterieanteile zerlegt werden (`oe_to_battery`, `oe_to_electrification`), Zug-km je Verkehrsart und Traktion, sowie CO2 neu (gewählte Traktion) gegen CO2 alt (Diesel).

## 10. Mehrdeutigkeiten und Verdachtsfälle für die Neuentwicklung

Jeder Punkt braucht eine Entscheidung gegen den Thesis-Text, bevor er in der Neuentwicklung festgelegt wird.

1. **Elektrifizierung durch Szenario-Projekte wirkt nicht.** `Version._add_electrification` setzt `catenary = False` und schreibt einen Boolean in die Textspalte `electrified`. Alle Kostenformeln prüfen `catenary`. Ein Szenario-Projekt mit `elektrification = True` wird deshalb weiter als nicht elektrifiziert behandelt. Das betrifft auch die während der Batterie- und Optimierungsrechnung erzeugten Elektrifizierungsmaßnahmen, die über denselben Weg in die Infrastrukturversion gelangen. Wenn das zutrifft, hat die Optimierung mit falschen Zwischenzuständen gerechnet. Höchste Priorität bei der Verifikation. (`prosd/manage_db/version.py:195` bis `:200`)
2. **Laden an Zwischenhalten ohne Wirkung.** In der Batteriebilanz wird nach einem Ladehalt `battery_status = min(battery_status, charge)` gesetzt. Da `charge` nie kleiner als `battery_status` ist, ändert sich der Stand nicht. Vermutlich war `min(battery_capacity, charge)` gemeint. (`prosd/calculation_methods/cost.py:721`)
3. **Standzeit am Zugende in Minuten statt Stunden und mit falschem Vorzeichen.** `stand_time = arrival_last_ocp minus departure_next_segment` ist negativ; `.seconds` liefert dann den Rest eines Tages. Die Ladung wird mit `stand_time.seconds / 60` multipliziert, an allen anderen Stellen mit `/ 3600`. (`prosd/calculation_methods/cost.py:734` bis `:738`)
4. **Investitionsbarwert nur vom letzten Teilprojekt.** In `BvwpProjectBattery` und `BvwpProjectOptimisedElectrification` steht `self.investment_cost_2015 = pc.investment_cost` statt `+=`. Die Gesamtkosten sind davon nicht betroffen, die gespeicherte Investition schon. (`cost.py:333`, `:1247`, `:1254`)
5. **Primärenergiefaktor doppelt.** `UTILITY_POINT_PRIMARY_ENERGY` wird zweimal multipliziert (0,81 statt 0,9). Entscheidung: Formel der Thesis prüfen. (`use.py:116` und Folgezeilen)
6. **Batteriezuschlag je Abschnitt mit Linienanteil.** In der Abschnittsenergie wird z_E mit dem Anteil L_oo / L der gesamten Zuggruppe gewichtet, obwohl der Abschnitt vollständig ohne Oberleitung ist. Konsistent wäre der volle Zuschlag im Abschnitt oder der Linienanteil in der Betriebskostenrechnung, nicht beides. (`cost.py:581`)
7. **Zeitabhängige Instandhaltung mit Masse des Basis-Fahrzeugmusters.** `maintenance_cost_duration_t` der Traktionsvariante wird mit `vehicle.vehicle_pattern.weight` des Basis-Musters multipliziert, nicht mit der Masse der Variante (Batteriefahrzeuge sind schwerer). (`use.py:460`)
8. **CO2 alt nur für optimierte Gebiete.** In `MasterScenario.parameters` wird `co2_diesel` nur im Zweig für optimierte Elektrifizierung aufsummiert. Für alle anderen Gebiete fehlt der Dieselreferenzwert. (`models.py:3295`)
9. **Kapitaldienst Infrastruktur ohne Verwendung.** Er wird berechnet und gespeichert, geht aber nicht in die Vergleichssumme ein. Die Vergleichssumme enthält stattdessen den vollen Investitionsbarwert. Zu klären, ob das die Absicht ist (Investition statt Annuität).
10. **Baudauer fix statt kostenabhängig.** Die BVWP-Tabelle zur Baudauer ist vorhanden, wird aber nicht aufgerufen.
11. **spfv immer Standi.** Durch die Parameterliste ist der bvwp-Zweig für Fernverkehr unerreichbar. Festlegen, ob das gewollt ist, dann den Zweig streichen.
12. **Einzelumlaufproblem auf der Hinfahrt ohne Lösung.** Reicht die Oberleitungsergänzung nicht, bleibt die Linie unlösbar und das Gebiet erhält trotzdem Batteriekosten (nur mit den erzeugten Maßnahmen). Die Neuentwicklung sollte den Fall als „nicht durchführbar“ markieren und die Traktion aus dem Vergleich nehmen oder mit Vollelektrifizierung bewerten.
13. **Reihenfolgeabhängigkeit.** Die Batterierechnung übernimmt Maßnahmen je Linie sofort in die Infrastrukturversion; das Ergebnis hängt von der Reihenfolge der Linien ab. Für die Neuentwicklung: Reihenfolge explizit festlegen (zum Beispiel nach Betriebsleistung) und dokumentieren.
14. **Teilgebietsreihenfolge und Wechselwirkung.** Die Optimierung bearbeitet Teilgebiete aufsteigend nach Betriebsleistung und entscheidet greedy. Es gibt keinen zweiten Durchlauf. Das ist methodisch vertretbar, muss aber als Entscheidung festgehalten werden.
15. **Halteenergie mit Standardwert 160.** Ist die Wurzel in der Referenzgeschwindigkeit nicht definiert, wird 160 km/h angenommen. Alternative wäre die zulässige Höchstgeschwindigkeit des Fahrzeugs.
16. **Tageswerte als Jahreswerte.** Der Fahrplan wird als Normaltag mit Faktor 365 hochgerechnet; Wochenend- oder Ferienfahrpläne sind nicht berücksichtigt.
17. **Energieformel Güterverkehr.** Die Konstanten 1,08 und 0,277 mit Exponent minus 0,62 auf die Bruttomasse des Wagenpakets sind ohne Quellenangabe im Code. Herkunft (BVWP-Methodenhandbuch) und Einheiten dokumentieren.
18. **Zweites Fahrzeugmuster für Standi-Fahrzeuge.** Für Mehrfachtraktion werden Fahrzeuge der Standi-Ersatzformation einzeln summiert; Formation und Umlaufzahl beziehen sich auf die Ersatzformation, die Zuggruppen-Betriebsleistung auf die Originalformation. Festhalten, dass Ersatzformationen die Rechengrundlage sind.

## 11. Zielarchitektur für die Neuentwicklung

Leitidee: Rechnen im Speicher auf reinen Datenstrukturen, Laden und Speichern als getrennte Adapter. Keine Datenbank-Session in der Rechenlogik, keine Nebenwirkungen auf Eingabedaten.

Schichten:
1. **Domänenmodell** (dataclasses oder pydantic): `Line`, `Station`, `Network` (mit Nachbarschaft und Bahnhofszuordnung), `TrainGroup` (Route als Streckenfolge, Halte mit Zeiten, Formation), `TimetableLine`, `Vehicle`, `VehiclePattern` mit Traktionsvarianten, `Scenario` (Projekte, Startjahr, Dauer), `Parameters` (vollständige Tabelle aus 3.5, versioniert).
2. **Infrastrukturzustand**: unveränderliche Netzbeschreibung plus eine dünne Änderungsschicht (Dict Strecke zu Overrides) statt Pandas-DataFrame. Elektrifizierung, Sperrung, Ladepunkte als explizite Operationen mit Tests.
3. **Pipeline-Stufen als Funktionen**: `route(network, traingroup) -> Route`, `build_areas(network, routes) -> list[Area]`, `build_sub_areas(area) -> list[SubArea]`, `operating_cost(traingroup_or_line, traction, infra) -> OperatingCost`, `infrastructure_cost(area, traction, infra) -> InfrastructureMeasure`, `battery_feasibility(line, infra, vehicles) -> BatteryPlan`, `optimise_electrification(area, infra) -> OptimisationResult`, `evaluate_area(area) -> AreaResult`, `aggregate_scenario(results) -> ScenarioResult`.
4. **Adapter**: Loader aus der bestehenden PostGIS-Datenbank (einmal je Szenario in das Domänenmodell), Writer in die bestehenden Ergebnistabellen (damit das Dashboard unverändert weiterläuft), zusätzlich Export als JSON/Parquet für Auswertungen und Fixtures.
5. **Konfiguration**: Szenario-ID, Parametersatz, Schalter als CLI-Argumente oder Konfigurationsdatei. Jeder Lauf schreibt Parametersatz und Code-Version in das Ergebnis.
6. **Tests**: Einheitstests der Formeln aus Abschnitt 7 und 8 mit Handrechnungsbeispielen; Golden-Master-Test mit einem kleinen exportierten Gebiet (Fixture) gegen die heutigen Ergebnisse, wobei die in Abschnitt 10 entschiedenen Abweichungen bewusst dokumentiert werden; Eigenschaftstests für Gebietsbildung (Disjunktheit, Vollständigkeit) und Batteriebilanz (nie über Kapazität, Ladung monoton).
7. **Laufzeit**: alle Betriebsleistungsgrößen je Zuggruppe einmal vorberechnen; Routen und Netz als Adjazenzstrukturen im Speicher; keine Abfragen in Schleifen.

Reihenfolge der Umsetzung: Domänenmodell und Loader, Betriebskosten (7) mit Tests, Infrastrukturkosten ohne Batterie (8.1 bis 8.4), Gebietsbildung (6), Batterie (8.5), Optimierung (8.6), Aggregation und Writer (9), danach Resilienzfall (12).

## 12. Resilienzfall (Erweiterung der Thesis)

Ziel: Vergleich der Kosten, wenn Güterzüge bei Sperrung einer elektrifizierten Hauptstrecke über nicht elektrifizierte Umleitungsstrecken geführt werden (und diese dafür ertüchtigt werden), gegenüber dem Ersatz durch Lkw.
Vorgehen: Sperrmaßnahme (`closure`) für einen Streckenabschnitt zwischen zwei Betriebsstellen anlegen, betroffene Zuggruppen (sgv, spfv) mit gesperrten Betriebsstellen und Zwangsfolgen umrouten. Betroffene Gebiete im Resilienzszenario erhalten die umgeleiteten Güterzuggruppen zusätzlich; Infrastrukturkosten für Oberleitung und optimierte Elektrifizierung werden neu gerechnet, die Zugkosten der umgeleiteten Züge (electrification, diesel, efuel) ebenfalls.
Kosten Resilienzfall = Kosten der betroffenen Gebiete (kosteneffiziente Traktion) minus Barwert der regulären Betriebskosten der umgeleiteten Güterzüge plus Barwert der Zugkosten im Störungsfall. Zugkosten im Störungsfall je Tag = reguläre Jahreskosten / 365 plus Wagenkosten (Wagenzahl × 1,06 € × Einsatzstunden bei 60 km/h) plus Personal (Stunden × 57 €) plus Bereitstellung (23 € je Wagen), gewichtet mit dem Störungsanteil 4,63 %.
Kosten Lkw-Fall = Kosten der Gebiete im Referenzszenario plus Barwert der Lkw-Kosten: Lkw-Zahl = Züge × aufgerundet(Nutzlast Zug / 25 t), Nutzlast Zug aus Wagenzahl (min aus Länge/19,7 m und Bruttomasse/70 t) × 50 t, Straßenentfernung über Openrouteservice, Kostensatz 87,34 €/100 km, gewichtet mit dem Störungsanteil.

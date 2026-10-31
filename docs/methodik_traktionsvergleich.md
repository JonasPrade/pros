# Methodik des Traktionsvergleichs: allgemeines Verfahren und Anwendung Masterarbeit

Stand: rekonstruiert aus dem Code des Repos `pros` (Commit a5a5269), Oktober 2026. Quellen sind `prosd/models.py` (MasterScenario, MasterArea, TimetableTrainGroup, TimetableTrainCost), `prosd/calculation_methods/use.py`, `prosd/calculation_methods/cost.py`, `prosd/manage_db/version.py`, `prosd/graph/routing.py`, `prosd/graph/block_rw_lines.py` und `prosd/parameter.py`. Der Text der Masterarbeit lag bei der Rekonstruktion nicht vor. Jede Stelle, an der der Code mehrdeutig ist oder von der vermuteten Absicht abweicht, ist in Teil C gesammelt und muss gegen den Thesis-Text entschieden werden, bevor neu entwickelt wird.

Aufbau des Dokuments:
- Teil A beschreibt das Verfahren allgemein, ohne Bezug auf konkrete Traktionen, Kostensätze, Datenquellen oder Bewertungsrichtlinien. Das ist die Grundlage für den Kern der Neuentwicklung.
- Teil B beschreibt die Adaption auf die Masterarbeit: deutsches Schienennetz, Deutschlandtakt, sechs Traktionen, BVWP- und Standi-Verfahren, konkrete Formeln und Parameter. Das ist eine Anwendung des Kerns.
- Teil C listet Verdachtsfälle und Mehrdeutigkeiten des Altcodes.
- Teil D enthält Zielarchitektur, Konfigurationskonzept und Umsetzungsplan.

Gestaltungsgrundsätze für die Neuentwicklung: maximal modular, jede Kostengröße und jeder Faktor konfigurierbar, keine Zahl im Code, Methodik zuerst allgemein, dann adaptiert.

---

# Teil A: Allgemeines Verfahren

## A1 Grundidee

Gegeben ist ein Verkehrsnetz, auf dem ein Betriebsprogramm (eine Menge von Verkehrsleistungen mit festen Laufwegen und Fahrplänen) erbracht werden soll. Für einen Teil des Netzes stehen mehrere Technologieoptionen zur Verfügung, die sich in Infrastrukturbedarf und Betriebskosten unterscheiden. Das Verfahren zerlegt den relevanten Netzteil in Bewertungsgebiete, ermittelt je Gebiet und Option die Infrastrukturmaßnahmen, die die Option betriebsfähig machen, berechnet dafür Infrastruktur- und Betriebskosten über einen Betrachtungszeitraum, diskontiert sie auf ein Basisjahr und wählt je Gebiet die Option nach einer Entscheidungsregel. Gebietsergebnisse werden zu Szenariokennzahlen aggregiert.

Das Verfahren ist unabhängig davon, welche Technologien verglichen werden, welche Kostensätze gelten und nach welcher Richtlinie monetarisiert wird. Diese Festlegungen sind Konfiguration und Plugins der Anwendung (Teil B).

## A2 Bausteine

| Baustein | Rolle | Was die Anwendung festlegt |
|---|---|---|
| Netz | Gerichteter Graph aus Segmenten mit Attributen (Länge, Gleiszahl, Ausrüstungsmerkmale, Sperrung) und Knoten; Betriebsstellen als benannte Orte mit Segmentzuordnung und Ausrüstungsmerkmalen | Attributschema, Datenquelle |
| Infrastrukturzustand | Unveränderliches Netz plus Änderungsschicht (Overrides je Segment und Betriebsstelle). Wird aus Szenario-Maßnahmen und Zwischenergebnissen abgeleitet. Jede Ableitung erzeugt einen neuen Zustand, der alte bleibt unverändert | Welche Maßnahmentypen welche Attribute setzen |
| Verkehrsleistung | Einheit des Betriebsprogramms mit Laufweg (geordnete Segmentfolge), Halten mit Zeiten, Fahrzeugkonfiguration, Kategorie, Häufigkeit je Zeiteinheit | Datenquelle, Kategorien, Hochrechnung auf das Jahr |
| Leistungsbündel | Gruppe von Verkehrsleistungen, die gemeinsam bewertet oder gemeinsam mit Fahrzeugen bedient wird (zum Beispiel beide Richtungen einer Linie) | Bündelungsregel |
| Fahrzeugkonfiguration | Liste von Fahrzeugtypen mit Kennwerten je Technologieoption (Energie je km und je Stunde, Masse, Kapitaldienst, Instandhaltungssätze, Speicherkapazität, Zuschläge) | Kennwerttabellen |
| Technologieoption | Benannte Variante mit: Auswahlregel für die Fahrzeugkennwerte, Energieträger, Maßnahmengenerator für die Infrastruktur, Durchführbarkeitsprüfung, Ausschlussregeln (zum Beispiel nicht für bestimmte Kategorien) | Liste der Optionen und ihre Plugins |
| Energieträger | Preis, Emissionsfaktoren, Primärenergiefaktor, Einheit | Tabelle je Energieträger |
| Kostenkomponente | Funktion von (Leistung oder Maßnahme, Option, Zustand, Parameter) nach Jahreswert oder Einmalwert in einer Einheit und mit Preisbasis | Satz der Komponenten und ihre Formeln |
| Maßnahme | Infrastrukturänderung mit Wirkung auf den Zustand und mit Kostenwerten (Investition, laufende Kosten, Planung, Barwerte); kann Teilmaßnahmen enthalten | Maßnahmentypen und Kostenformeln |
| Gebietsbildung | Zerlegung des Netzteils in disjunkte Gebiete mit Segment- und Leistungsmenge; optional Teilgebiete | Clusterkriterium, Teilgebietskriterium |
| Finanzmodul | Diskontierung, Preisbasis, Verteilung von Einmalkosten über Phasen, Annuität | Zinssatz, Basisjahr, Phasendauern |
| Entscheidungsregel | Abbildung der Optionsergebnisse eines Gebiets auf eine Wahl (Standard: minimale Gesamtkosten) | Regel, optionale Nebenbedingungen |
| Aggregation | Kennzahlen je Szenario aus Gebietsergebnissen | Kennzahlenliste |
| Parametersatz | Alle Zahlenwerte mit Einheit, Preisjahr, Quelle und Gültigkeit; versioniert, vererbbar, überschreibbar | Konkrete Werte |

## A3 Ablauf als Pipeline

Jede Stufe hat definierte Ein- und Ausgaben, ist ohne Nebenwirkungen und einzeln testbar.

1. Laden: Netz, Betriebsprogramm, Fahrzeugkennwerte, Szenariodefinition und Parametersatz in das Domänenmodell überführen.
2. Zustand bilden: Szenario-Maßnahmen auf das Netz anwenden.
3. Laufwege bestimmen: je Verkehrsleistung den Laufweg auf dem Zustand ermitteln oder aus der Quelle übernehmen (Routing ist ein austauschbares Modul mit konfigurierbarer Gewichtsfunktion).
4. Betriebsleistungsgrößen je Verkehrsleistung einmal vorberechnen (Längen nach Attributen, Fahrzeiten, Halte, Häufigkeit, Jahreswerte).
5. Gebiete bilden (A6), bei Bedarf Teilgebiete.
6. Je Gebiet und Option: Maßnahmen erzeugen (Maßnahmengenerator der Option auf einer Kopie des Zustands), Infrastrukturkosten berechnen, Betriebskosten aller Leistungen des Gebiets unter dieser Option berechnen, Durchführbarkeit festhalten.
7. Je Gebiet: Barwerte bilden, Entscheidungsregel anwenden.
8. Aggregieren, Ergebnis mit Parametersatz, Szenariodefinition, Codeversion und Laufzeitinformationen als Manifest speichern.

Zwischenergebnisse jeder Stufe sind serialisierbar, damit Läufe wiederaufgenommen und Teilstufen einzeln wiederholt werden können.

## A4 Finanzmodul

- Barwert eines konstanten Jahreswerts K über D Jahre ab Jahr S auf Basisjahr B mit Zinssatz p: Summe über x = 0 bis D minus 1 von K / (1 + p)^(S minus B + x).
- Einmalkosten E über eine Phase der Dauer D ab Jahr S: gleichmäßige Verteilung E / D je Jahr, dann Barwert wie oben.
- Phasenmodell für Maßnahmen: Planung (Dauer d_P), Bau (d_B), Betrieb (d_O), nacheinander ab einem Startjahr. Dauern sind Parameter oder Funktionen (zum Beispiel kostenabhängige Baudauer über eine Tabelle).
- Annuität einer Investition: Barwert × Annuitätsfaktor (Parameter) oder berechnet aus Zins und Lebensdauer.
- Preisbasis: jede Zahl trägt ihr Preisjahr; Umrechnung auf das Basisjahr über einen konfigurierbaren Index. Fehlt ein Index, wird die Zahl unverändert übernommen und das im Manifest vermerkt.
- Welche Komponenten in die Vergleichssumme eingehen (zum Beispiel Investitionsbarwert oder Annuität), ist Konfiguration der Entscheidungsregel.

## A5 Energie- und Betriebskostenmodelle

Betriebskosten je Verkehrsleistung und Option sind eine Summe konfigurierter Kostenkomponenten. Generische Komponenten:

| Komponente | Generische Form |
|---|---|
| Kapitaldienst Fahrzeuge | Fahrzeugbedarf × Kapitaldienst je Fahrzeug, oder Zugstunden × Satz je Stunde |
| Instandhaltung laufleistungsabhängig | Satz je km × Fahrzeug-km × (1 + Zuschlag × Anteil einer Betriebsbedingung, zum Beispiel Fahren ohne Fahrleitung) |
| Instandhaltung zeitabhängig | Fahrzeugbedarf × Satz je (Masse und Jahr) × Masse |
| Fahrenergie | Satz je km × km, optional differenziert nach Segmentklassen, mit Zuschlag analog zur Instandhaltung; oder massebasierte Formel; oder Satz je Stunde × Stunden |
| Halteenergie | Energie je Halt (Funktion von Referenzgeschwindigkeit und Masse) × Halte je Jahr; Referenzgeschwindigkeit aus Reisezeit, Haltezeit, Haltezahl, Länge und Fahrzeugkennwert, mit konfigurierbarem Rückfallwert |
| Energiekosten | Energiemenge × Preis des Energieträgers |
| Emissionen | Energiemenge × Emissionsfaktor; Kosten = Menge × Kostensatz |
| Schadstoffe, Primärenergie, weitere Externalitäten | Energiemenge × Faktor × Monetarisierungssatz; beliebig viele solcher Komponenten konfigurierbar |
| Emissionen Fahrzeugherstellung | Fahrzeugbedarf × Satz je Fahrzeug und Jahr × Kostensatz |

Welche Komponenten für welche Kategorie von Verkehrsleistung gelten und mit welchen Formelvarianten, ist eine Methodenkonfiguration (in der Anwendung: BVWP für Güterverkehr, Standi für Personenverkehr). Formeln sind als benannte, registrierte Funktionen austauschbar.

Fahrzeugbedarf eines Leistungsbündels wird über eine Umlaufbildung bestimmt: Verkettung von Leistungen, deren Folgeleistung am Endort beginnt und frühestens nach einer Wendezeit abfährt. Die Wendezeit ist Parameter, die Umlaufbildung ein austauschbares Modul.

## A6 Gebietsbildung

Generische Clusterbildung über ein Segmentprädikat (zum Beispiel „ohne Fahrleitung“) und zwei Nachbarschaftsrelationen:
1. Segmente sind verbunden, wenn dieselbe Verkehrsleistung beide befährt.
2. Segmente sind verbunden, wenn sie an derselben Betriebsstelle beginnen oder enden.
Gebiet = Zusammenhangskomponente der Segmente, die das Prädikat erfüllen, plus alle Verkehrsleistungen, die mindestens ein Segment des Gebiets befahren. Beide Relationen sind einzeln aktivierbar; weitere Relationen (zum Beispiel räumliche Nähe) sind als Plugin ergänzbar.

Teilgebiete: Segmente eines Gebiets mit identischer Menge befahrender Verkehrsleistungen. Alternative Teilgebietskriterien sind als Plugin ergänzbar.

Invarianten, die getestet werden: Gebiete sind disjunkt; jedes Segment, das das Prädikat erfüllt und befahren wird, liegt in genau einem Gebiet; Teilgebiete partitionieren das Gebiet.

## A7 Infrastrukturmaßnahmen je Option

Jede Technologieoption bringt einen Maßnahmengenerator mit der Signatur: (Gebiet, Zustand, Betriebsprogramm des Gebiets, Fahrzeugkennwerte, Parameter) nach (Liste von Maßnahmen, Durchführbarkeitsstatus, neuer Zustand). Generische Generatortypen:

- **Flächige Ausrüstung**: alle Segmente des Gebiets, die ein Prädikat erfüllen, erhalten ein Merkmal; Kosten = Summe über Segmente von Länge × Satz je km × Gleisfaktor.
- **Punktuelle Versorgung nach Dichte**: Anzahl Anlagen = aufgerundet(Gebietslänge / Abstand) × Satz je Anlage.
- **Punktuelle Versorgung an Orten**: Anlagen an bestimmten Betriebsstellen (zum Beispiel Start- und Endorte ohne Versorgung) × Satz je Anlage.
- **Reichweitenbasierte Ergänzung** (A8): aus einer Energiebilanz abgeleitete Kombination punktueller und flächiger Maßnahmen.
- **Kombinierte Optimierung** (A9): Zerlegung in Teilgebiete, je Teilgebiet Wahl zwischen zwei oder mehr Teiloptionen.

Jede Maßnahme kennt ihre Phasen (A4), ihre Kostenwerte und ihre Wirkung auf den Zustand. Maßnahmen können Teilmaßnahmen enthalten; Kosten der Gesamtmaßnahme sind die Summe der Teilmaßnahmen.

## A8 Reichweitenmodell für speichernde Antriebe

Für Optionen, deren Fahrzeuge Energie speichern und unterwegs nachladen (Batterie, prinzipiell auch andere Speicher):

1. **Abschnittsbildung** je Fahrt: der Laufweg wird in Abschnitte geteilt an jedem Wechsel des Versorgungsmerkmals (Fahrleitung ja/nein) und an jedem Halt, der eine konfigurierbare Mindesthaltezeit erreicht oder eine Ladeanlage hat. Je Abschnitt: Länge, Versorgung, Fahrzeit, letzter Halt mit Haltezeit und Ladeanlage.
2. **Energiebedarf je Abschnitt** aus den Energiemodellen (A5), mit Zuordnung der Halte zu Abschnitten.
3. **Bilanz** entlang einer Fahrtenfolge (Standard: Hin- und Rückfahrt eines Umlaufs, konfigurierbar): Start mit Speicherkapazität; unter Versorgung Laden mit Ladeleistung × Fahrzeit, an Ladeanlagen Laden mit Ladeleistung × Haltezeit, am Fahrtende Laden über die Standzeit bis zur Folgefahrt, sofern Versorgung oder Ladeanlage vorhanden; ohne Versorgung Abzug des Abschnittsbedarfs; Deckelung auf Kapazität; Protokoll jedes negativen Zwischenstands.
4. **Problemtypen**: Einzelfahrtproblem (Speicher wird innerhalb der betrachteten Fahrtenfolge leer) und Mehrfahrtproblem (Bilanz nach der Fahrtenfolge negativ und über die Zahl der Umlaufwiederholungen nicht tragfähig).
5. **Maßnahmenstrategie**: geordnete Liste von Platzierungsregeln, die nacheinander angewendet werden, bis der Bedarf gedeckt ist. Standardreihenfolge: Ladeanlage an Endorten (bei vorhandener Fahrleitung an anderem Gleis: Fahrleitung im Bahnhof statt Ladeanlage), Ladeanlagen an Zwischenhalten mit ausreichender Haltezeit, flächige Ausrüstung weiterer Segmente nach einer Rangfolge (Nutzungshäufigkeit, Länge, Anschluss an vorhandene Versorgung, Nachbarschaft entlang des Laufwegs). Reihenfolge und Regeln sind Konfiguration.
6. **Durchführbarkeit**: bleibt nach allen Regeln ein Problem, wird die Option für dieses Gebiet als nicht durchführbar markiert. Wie die Entscheidungsregel damit umgeht (ausschließen, Strafkosten, Rückfall auf eine andere Option), ist Konfiguration.
7. **Reihenfolge der Leistungsbündel** innerhalb eines Gebiets ist festgelegt und dokumentiert (Standard: absteigend nach Betriebsleistung), weil frühere Maßnahmen späteren Bündeln zugutekommen.

## A9 Kombinierte Optimierung über Teilgebiete

Für eine Option, die je Teilgebiet zwischen Teiloptionen wählt (in der Anwendung: Fahrleitung oder Batterie):
1. Ausgangszustand: das Gebiet vollständig mit der Basisteiloption ausrüsten; Betriebskosten aller Leistungen unter der Basisteiloption bestimmen.
2. Teilgebiete sortieren (Standard: aufsteigend nach Betriebsleistung).
3. Je Teilgebiet: Basisausrüstung des Teilgebiets zurücknehmen, jede zulässige Teiloption bewerten (Betriebskosten der Leistungen des Teilgebiets plus Maßnahmenkosten, jeweils als Barwert), die günstigste wählen, ihre Maßnahme in den Zustand übernehmen, die Leistungen des Teilgebiets der gewählten Teiloption zuordnen. Ausschlussregeln je Kategorie gelten (zum Beispiel Güterverkehr nur Fahrleitung).
4. Nach allen Teilgebieten: Abschlussmaßnahmen (zum Beispiel Versorgung an Start- und Endorten).
5. Ergebnis: Gesamtmaßnahme mit Teilmaßnahmen, Zuordnung Leistung zu Teiloption, Anteile je Teiloption.

Der Greedy-Durchlauf ist die Standardstrategie. Die Schnittstelle erlaubt andere Strategien (mehrere Durchläufe, lokale Suche, exakte Verfahren) ohne Änderung der übrigen Pipeline.

## A10 Entscheidung und Aggregation

Je Gebiet und Option liegen vor: Infrastrukturkosten (nach Komponenten), Betriebskosten (nach Komponenten), Durchführbarkeit, physische Kennzahlen (ausgerüstete km, Anlagenzahl), Emissionen. Die Entscheidungsregel bildet daraus die gewählte Option. Standard: Minimum der konfigurierten Vergleichssumme über die durchführbaren Optionen. Varianten: Nebenbedingungen (Emissionsgrenze), Gewichtungen, Sensitivitätsläufe über Parametersätze.

Aggregation je Szenario: je gewählter Option Anzahl Gebiete, Segment-km, Leistungs-km, Kosten nach Komponenten, Emissionen; Zerlegung kombinierter Optionen in ihre Teiloptionen; Vergleich gegen eine Referenzoption (zum Beispiel Emissionen gegen Diesel). Die Kennzahlenliste ist Konfiguration.

## A11 Störfallbewertung (Erweiterung)

Generisches Muster: Ein Störfall sperrt Segmente; betroffene Leistungen werden umgeleitet oder durch einen anderen Verkehrsträger ersetzt. Bewertet wird die Differenz der Gesamtkosten zwischen „Netz für Umleitung ertüchtigen“ und „Ersatz durch anderen Verkehrsträger“, gewichtet mit dem Zeitanteil des Störfalls. Kostensätze des Ersatzverkehrs und Zusatzkosten der Umleitung sind Parameter.

---

# Teil B: Anwendung Masterarbeit

## B1 Konkretisierung der Bausteine

| Baustein | Festlegung in der Masterarbeit |
|---|---|
| Netz | Deutsches Schienennetz (`RailwayLine`, `RailwayStation`), Attribute: Länge, Gleiszahl (ein-/zweigleisig), Oberleitung, Stromschiene, ABS/NBS, Sperrung; Bahnhöfe mit Ladestation und kleiner Ladestation |
| Zustand | `Version`: Bestand plus Szenario-Projekte (`ProjectContent` mit `elektrification`, `closure`, `charging_station`, `small_charging_station`) |
| Verkehrsleistung | Zuggruppe des Deutschlandtakts (`TimetableTrainGroup`), Kategorien sgv, spnv, spfv |
| Leistungsbündel | Fahrplanlinie (`TimetableLine`), beide Richtungen |
| Fahrzeugkonfiguration | Formation mit Ersatzformationen für BVWP und Standi; Fahrzeugmuster mit Traktionsvarianten |
| Technologieoptionen | electrification, battery, h2, efuel, diesel, optimised_electrification; Ausschluss: battery und h2 nicht für Gebiete mit sgv |
| Energieträger | Strom erneuerbar, Diesel, eFuel, H2 (Strommix definiert, nicht verwendet) |
| Kostenkomponenten | sgv nach BVWP (Zuggruppe, nur Triebfahrzeug), spnv und spfv nach Standi (Linie, alle Fahrzeuge) |
| Gebietsbildung | Prädikat „ohne Oberleitung und ohne Stromschiene“, beide Nachbarschaftsrelationen; Teilgebiete nach identischer Zuggruppenmenge |
| Finanzmodul | Basisjahr 2016, 1,7 %, Planung 5 Jahre ab 2020, Bau 5 Jahre ab 2025, Betrieb 30 Jahre ab 2030; Vergleichssumme = Barwert Planung + Barwert Investition + Barwert Instandhaltung + Barwert Betriebskosten |
| Entscheidungsregel | Minimum der Vergleichssumme |
| Routing | Dijkstra über Streckengraph, Gewicht Länge, Oberleitung mit Faktor 0,95 bevorzugt, gesperrte Strecken ausgeschlossen, Zwischenhalte als Via-Punkte |

## B2 Eingangsdaten

Infrastruktur: je Strecke `id`, `length` (m), `number_tracks`, `catenary`, `conductor_rail`, `abs_nbs`, `closed`, Start-/Endknoten, Nachbarstrecken, Bahnhöfe. Je Bahnhof `id`, `name`, `db_kuerzel`, Strecken, `charging_station`, `small_charging_station`. Der Streckengraph ist ein gerichteter networkx-Graph mit Teilknoten je Strecke und Richtung, Abbiegebeziehungen (Mindestwinkel 60 Grad) und Bahnhofsknoten als Quelle/Ziel.
Fahrplan: railML des Deutschlandtakts mit Zuggruppen, Zügen, Zugteilen, Betriebsstellen mit Ankunft/Abfahrt und Typ (`stop` oder Durchfahrt), Mindestfahrzeiten, Kategorie, Formation. Zuordnung railML-Betriebsstelle zu Bahnhof über Kürzel.
Fahrzeuge: Formation mit Fahrzeugliste; Fahrzeug mit `brutto_weight`, `length`, `engine`/`wagon`; Fahrzeugmuster mit den in B6 genutzten Feldern und Varianten je Traktion; `type_of_traction` (`Elektro`, `Batterie`, `Diesel`, `eFuel`, `H2`) wählt den Energieträger.
Szenario-Projekte: Maßnahmen mit den Flags aus B1; Teilmaßnahmen ersetzen die Hauptmaßnahme.

## B3 Parametersatz „masterarbeit-2023“

Alle Werte aus `parameter.py`. In der Neuentwicklung liegen sie in einer Parameterdatei mit Einheit, Preisjahr und Quelle (Teil D). Die Spalte Quelle ist hier offen und aus der Thesis zu ergänzen.

Zeit und Zins

| Parameter | Wert | Einheit |
|---|---|---|
| Basisjahr Barwert und Preisbasis | 2016 | Jahr |
| Diskontrate | 1,7 | % |
| Annuitätsfaktor Infrastruktur | 0,0428 | 1/Jahr |
| Startjahr Betrieb | 2030 | Jahr |
| Planungsdauer | 5 | Jahre |
| Baudauer | 5 | Jahre |
| Betriebsdauer | 30 | Jahre |

Infrastrukturkosten

| Parameter | Wert | Einheit |
|---|---|---|
| Planungskostenanteil | 18 | % der Investition |
| Instandhaltung Oberleitung und Ladestationen | 1,4 | % der Investition je Jahr |
| Instandhaltung Tankstellen | 3 | % der Investition je Jahr |
| Oberleitung | 737 | T€/km |
| Lebensdauer Oberleitung | 60 | Jahre |
| Bahnstromversorgung | 200 | T€/km |
| Ingenieurbau | 200 | T€/km |
| Grunderwerb | 5 | T€/km |
| Ladestation | 2.582 | T€ |
| kleine Ladestation | 1.200 | T€ |
| Tankstelle H2 | 6.000 | T€, eine je 60 km |
| Tankstelle Diesel | 1.000 | T€, eine je 40 km |
| Tankstelle eFuel | 1.000 | T€, eine je 40 km |

Energieträger

| Energieträger | Preis | CO2 (g/Einheit) | Schadstoffe (Faktor) | Primärenergie (Faktor) |
|---|---|---|---|---|
| Strom erneuerbar | 0,14 €/kWh | 21 | 0,05 | 4,5 |
| Strom Mix (nicht verwendet) | 0,12 €/kWh | 414 | 0,96 | 6 |
| Diesel | 0,75 €/l | 2.774 | 6,57 | 38,9 |
| eFuel | 2,50 €/l | 370 | 6,57 | 78,2 |
| H2 | 5,00 €/kg | 938 | 2,18 | 198,7 |

Weitere

| Parameter | Wert |
|---|---|
| CO2-Kostensatz | 670 €/t |
| Nutzenpunkte Primärenergie | 0,9 |
| Geldwert je Nutzenpunkt | 15,5 € |
| Ladeleistung Batterie | 1.200 kW |
| Wendezeit Umlaufbildung | 10 min |
| Mindesthaltezeit für Ladeabschnitt | 3 min |
| Rückfallwert Referenzgeschwindigkeit | 160 km/h |
| Routing: Faktor Oberleitung | 0,95 |

Störfall: Lkw-Kostensätze je 100 km (Energie 17,5, Personal 25,18, Kapital 22, Instandhaltung 12,86, CO2 1,8, Primärenergie 7,8, Emission 0,1 €), Lkw-Nutzlast 25 t, Containerwagen 19,7 m, 20 t Eigenmasse, 50 t Nutzlast, Wagenkosten 1,06 €/Wagen-h, Triebfahrzeugführer 57 €/h, Zugbereitstellung 23 €/Wagen, Störungsanteil 4,63 % der Zeit, Umleitungsgeschwindigkeit 60 km/h.

## B4 Gebietsbildung konkret

Ausgangsmenge: Strecken ohne Oberleitung und ohne Stromschiene im Zustand, und alle Zuggruppen, deren Route eine dieser Strecken enthält. Clusterbildung nach A6 mit beiden Relationen. Elektrifizierte Strecken der Routen gehören nicht zum Gebiet, zählen aber in der Betriebskostenrechnung der Zuggruppen mit. Eine ältere Skriptfassung startete nur von Güterzuggruppen; die Modellfassung startet von allen Zuggruppen. Teilgebiete nach identischer Zuggruppenmenge.

## B5 Betriebsleistungsgrößen je Zuggruppe

| Größe | Definition |
|---|---|
| Linienlänge L (km) | Summe der Streckenlängen der Route im Szenario |
| L_oo (km) | Teil von L ohne Oberleitung im Zustand |
| Anteil ABS / NBS | Teil von L mit `abs_nbs` ABS bzw. NBS |
| Züge je Tag n | Anzahl Züge der Zuggruppe |
| Zug-km je Jahr | L × n × 365 / 1000 (Tausend Zug-km) |
| Reisezeit T | Abfahrt erste bis Ankunft letzte Betriebsstelle, inkl. Halte |
| Zugstunden je Jahr | T × n × 365 / 1000 (Tausend Zug-h) |
| Halte h | Betriebsstellen mit Typ `stop` |
| Haltezeit gesamt | Summe (Abfahrt minus Ankunft) über Halte |
| Halte je Jahr | h × n × 365 |

## B6 Betriebskosten konkret

Zuordnung: sgv nach BVWP (Zuggruppe, nur Triebfahrzeug der BVWP-Ersatzformation); spnv und spfv nach Standi (Linie, Standi-Ersatzformation). Der BVWP-Zweig für spfv ist im Altcode vorhanden, aber durch die Parameterliste unerreichbar. Für sgv liefern battery und h2 kein Ergebnis.

Gemeinsame Externalitätenformeln je Fahrzeugmuster mit Energiemenge E:
- Energiekosten = Preis × E
- CO2 (t) = E × CO2-Faktor × 10^-3; CO2-Kosten = CO2 × 670 × 10^-3
- Schadstoffkosten = E × Schadstofffaktor × 10^-2
- Primärenergiekosten = E × Primärenergiefaktor × 0,9 × 0,9 × 15,5 × 10^-3 (Faktor 0,9 steht im Code zweimal, Teil C Nr. 5)
Elektro und Batterie nutzen die Faktoren für erneuerbaren Strom; eFuel nutzt die Dieselverbrauchsformel mit eFuel-Faktoren.

BVWP Güterverkehr (`BvwpSgv`):
- Kapitaldienst = `debt_service` × Zugstunden je Jahr
- Instandhaltung = `maintenance_cost_km` × Zug-km je Jahr
- Energie elektrisch (kWh) = 1,08 × m^-0,62 × Zug-km × 1000, m = Bruttomasse des Wagenpakets (t)
- Energie Diesel/eFuel (l) = 0,277 × m^-0,62 × Zug-km × 1000
- Gesamt = Kapitaldienst + Instandhaltung + Energie + CO2 + Schadstoffe + Primärenergie

BVWP Personenverkehr (`BvwpSpfv`, `BvwpSpnv`, nicht erreichbar): wie oben je Fahrzeug; Energie = Zug-km × `energy_per_km` (spfv differenziert nach Kernnetz, ABS mit `energy_abs_per_km`, NBS mit `energy_nbs_per_km`) + Zugstunden × `energy_consumption_hour`.

Standi Personenverkehr (`StandiSpnv`), je Linie:
- Umläufe U bei 10 min Wendezeit (A5)
- Kapitaldienst = U × Summe `debt_service` der Fahrzeuge
- zeitabhängige Instandhaltung = U × Summe (`maintenance_cost_duration_t` × Masse) / 1000
- laufleistungsabhängige Instandhaltung je Zuggruppe und Fahrzeug = (1 + z_IH × L_oo / L) × `maintenance_cost_km` × Zug-km, z_IH = `additional_maintenance_cost_withou_overhead`
- Fahrenergie je Zuggruppe und Fahrzeug = (1 + z_E × L_oo / L) × `energy_per_km` × Zug-km, z_E = `additional_energy_without_overhead`
- Halteenergie: I = 55,6 × (T minus Haltezeit) in Minuten, s = h minus 1; v_ref = 3,6 / (a × s) × (I minus Wurzel(I² minus 2 × a × s × L × 1000)), a = `energy_stop_a`; Rückfall 160 km/h; Energie je Halt = `energy_stop_b` × v_ref² × Masse × 10^-6; Halteenergie je Jahr = Energie je Halt × Halte je Jahr / 1000 (Verfahrensanleitung Standi S. 197)
- THG Fahrzeugherstellung = U × Summe `emission_production_vehicle_calc` × 670 / 1000
- Gesamt = alle Komponenten; Division durch Anzahl Zuggruppen der Linie, Speicherung je Zuggruppe

Barwert: Jahreswert über 2030 bis 2059 nach A4.

## B7 Infrastrukturkosten konkret

Rahmen (`BvwpCost`): Planung P = 0,18 × I; Barwert Planung über 5 Jahre ab 2020; Barwert Investition über 5 Jahre ab 2025; Barwert Instandhaltung M jährlich über 30 Jahre ab 2030; Kapitaldienst = Barwert Investition × 0,0428 (gespeichert, nicht in der Vergleichssumme); Vergleichswert Infrastruktur = Barwert Planung + Investition + Instandhaltung. Baudauer fix 5 Jahre; die BVWP-Tabelle zur kostenabhängigen Baudauer (`duration_build_rail_bvwp.csv`) ist vorhanden, wird nicht genutzt.

Oberleitung: je Strecke ohne Oberleitung Kosten je km = 200 + 200 + 5 + 737 × 30 / 60 = 773,5 T€, zweigleisig doppelt; I = Summe Länge × Satz; M = 0,014 × I.
Tankstellen (diesel, efuel, h2): Anzahl = aufgerundet(Gebietslänge / Abstand); I = Anzahl × Satz; M = 0,03 × I.
Ladestation I = 2.582, kleine Ladestation I = 1.200, jeweils M = 0,014 × I. Oberleitung im Bahnhof wie Oberleitung für die betreffende Strecke.

Batterie: A8 mit folgenden Festlegungen. Je Fahrplanlinie einmal; je Startbetriebsstelle ein Umlauf, dessen erste zwei Züge (Hin- und Rückfahrt); Mindesthaltezeit 3 min; Fahrzeit je Abschnitt = Länge / mittlere Reisegeschwindigkeit der Zuggruppe; Standzeit am Zugende bis Abfahrt des Folgezugs im Umlauf, sonst 1 h; Kapazität C = Summe `battery_capacity`; Fahrenergie im Abschnitt ohne Oberleitung (1 + z_E × L_oo / L) × `energy_per_km` × Länge; Halteenergie nach B6 je zugeordnetem Halt; Mehrfahrtproblem, wenn C / Defizit kleiner als Anzahl Züge im Umlauf / 2. Maßnahmenreihenfolge Einzelfahrtproblem: Ladepunkt am Endbahnhof der Hinfahrt (Oberleitung im Bahnhof, wenn dort Oberleitung an anderem Gleis, sonst Ladestation), dann Oberleitung auf Strecken vor der Problemstelle. Mehrfahrtproblem: Ladepunkte an Endbahnhöfen, Ladepunkte an Zwischenhalten ab 3 min, Oberleitung auf weiteren Strecken. Auswahl zusätzlicher Strecken: Kandidaten nach Anzahl befahrender Zuggruppen absteigend und Länge aufsteigend, bevorzugt mit Anschluss an Lademöglichkeit oder Oberleitungsnachbar; je Strecke Ladung = 1.200 kW × Länge / mittlere Liniengeschwindigkeit, gedeckelt auf C; Nachbarstrecken der Route werden nachgezogen. Maßnahmen gelten sofort für folgende Linien. Abschluss: kleine Ladestationen an Start- und Endbetriebsstellen ohne Lademöglichkeit.

Optimierte Elektrifizierung: A9 mit Basisteiloption Oberleitung und Alternative Batterie (ohne kleine Ladestationen), Teilgebiete aufsteigend nach Zug-km je Tag, Güterverkehr-Teilgebiete immer Oberleitung, Abschluss kleine Ladestationen. Ergebnis: Traktion je Zuggruppe (`TractionOptimisedElectrification`), Anteile Oberleitung/Batterie nach km und Infrastrukturkosten.

## B8 Entscheidung und Kennzahlen konkret

Je Gebiet und Traktion: Vergleichssumme = Vergleichswert Infrastruktur + Barwert Betriebskosten (Summe der Jahreswerte aller Zuggruppen). Minimum über die berechneten Traktionen. CO2 je Traktion aus `co2_emission` der Zuggruppen. Gespeichert je Gebiet: Gesamt-, Betriebs- und Infrastrukturkosten je Traktion, kosteneffiziente Traktion, Flags sgv/spnv/spfv; Teilgebiete nur Oberleitung und (ohne sgv) Batterie.
Je Szenario je kosteneffizienter Traktion: Anzahl Gebiete, Streckenkilometer, Zug-km je Tag, Infrastruktur- und Betriebskosten; Zerlegung optimierter Gebiete in Oberleitungs- und Batterieanteile (`oe_to_battery`, `oe_to_electrification`); Zug-km je Verkehrsart und Traktion; CO2 neu gegen CO2 Diesel.

## B9 Störfall konkret

Sperrmaßnahme zwischen zwei Betriebsstellen, Umrouten betroffener Zuggruppen (sgv, spfv) mit gesperrten Betriebsstellen und Zwangsfolgen. Betroffene Gebiete im Störfallszenario erhalten die umgeleiteten Güterzuggruppen; Oberleitung und optimierte Elektrifizierung sowie Zugkosten (electrification, diesel, efuel) werden neu gerechnet.
Kosten Umleitungsfall = Kosten der betroffenen Gebiete (gewählte Traktion) minus Barwert der regulären Betriebskosten der umgeleiteten Züge plus Barwert der Zugkosten im Störfall. Zugkosten im Störfall je Tag = reguläre Jahreskosten / 365 + Wagenkosten (Wagenzahl × 1,06 € × Einsatzstunden bei 60 km/h) + Personal (Stunden × 57 €) + Bereitstellung (23 € je Wagen), gewichtet mit 4,63 %.
Kosten Lkw-Fall = Kosten der Gebiete im Referenzszenario + Barwert der Lkw-Kosten: Lkw-Zahl = Züge × aufgerundet(Nutzlast Zug / 25 t), Nutzlast Zug = Wagenzahl × 50 t, Wagenzahl = min(Länge / 19,7 m, Bruttomasse / 70 t), Straßenentfernung über Openrouteservice, Kostensatz 87,34 €/100 km, gewichtet mit 4,63 %.

---

# Teil C: Mehrdeutigkeiten und Verdachtsfälle

Jeder Punkt braucht eine Entscheidung gegen den Thesis-Text, bevor er in der Neuentwicklung festgelegt wird. Die Entscheidung wird als Parameter oder Methodenvariante konfigurierbar gemacht, wo das sinnvoll ist, damit Alt- und Neurechnung vergleichbar bleiben.

1. **Elektrifizierung durch Szenario-Projekte wirkt nicht.** `Version._add_electrification` setzt `catenary = False` und schreibt einen Boolean in die Textspalte `electrified`. Alle Kostenformeln prüfen `catenary`. Ein Szenario-Projekt mit `elektrification = True` wird deshalb weiter als nicht elektrifiziert behandelt. Das betrifft auch die während der Batterie- und Optimierungsrechnung erzeugten Elektrifizierungsmaßnahmen, die über denselben Weg in den Zustand gelangen. Höchste Priorität bei der Verifikation. (`prosd/manage_db/version.py:195` bis `:200`)
2. **Laden an Zwischenhalten ohne Wirkung.** Nach einem Ladehalt wird `battery_status = min(battery_status, charge)` gesetzt; der Stand ändert sich nie. Vermutlich war `min(battery_capacity, charge)` gemeint. (`prosd/calculation_methods/cost.py:721`)
3. **Standzeit am Zugende in Minuten statt Stunden und mit falschem Vorzeichen.** `stand_time = arrival_last_ocp minus departure_next_segment` ist negativ; `.seconds` liefert den Rest eines Tages. Ladung mit `/ 60` statt `/ 3600`. (`prosd/calculation_methods/cost.py:734` bis `:738`)
4. **Investitionsbarwert nur vom letzten Teilprojekt.** `self.investment_cost_2015 = pc.investment_cost` statt `+=`. Gesamtkosten nicht betroffen, gespeicherte Investition schon. (`cost.py:333`, `:1247`, `:1254`)
5. **Primärenergiefaktor doppelt.** `UTILITY_POINT_PRIMARY_ENERGY` zweimal multipliziert (0,81 statt 0,9). (`use.py:116` und Folgezeilen)
6. **Batteriezuschlag je Abschnitt mit Linienanteil.** z_E wird im Abschnitt mit L_oo / L der gesamten Zuggruppe gewichtet, obwohl der Abschnitt vollständig ohne Oberleitung ist. (`cost.py:581`)
7. **Zeitabhängige Instandhaltung mit Masse des Basis-Fahrzeugmusters** statt der Traktionsvariante. (`use.py:460`)
8. **CO2 Diesel nur für optimierte Gebiete** aufsummiert; für andere Gebiete fehlt der Referenzwert. (`models.py:3295`)
9. **Kapitaldienst Infrastruktur ohne Verwendung.** Vergleichssumme enthält den vollen Investitionsbarwert statt der Annuität. Absicht klären; in der Neuentwicklung als Konfiguration der Vergleichssumme.
10. **Baudauer fix statt kostenabhängig.** Tabelle vorhanden, nicht genutzt. In der Neuentwicklung als Phasenmodell-Variante.
11. **spfv immer Standi.** bvwp-Zweig für Fernverkehr unerreichbar. Festlegen, dann als Methodenzuordnung konfigurieren.
12. **Einzelfahrtproblem auf der Hinfahrt ohne Lösung.** Gebiet erhält trotzdem Batteriekosten. Neuentwicklung: Durchführbarkeitsstatus und konfigurierbarer Umgang (A8 Nr. 6).
13. **Reihenfolgeabhängigkeit** der Linien in der Batterierechnung. Neuentwicklung: Reihenfolge explizit (A8 Nr. 7).
14. **Teilgebietsreihenfolge und Greedy-Entscheidung** ohne zweiten Durchlauf. Als Strategie dokumentieren (A9).
15. **Halteenergie mit Rückfallwert 160 km/h.** Alternative: Höchstgeschwindigkeit des Fahrzeugs. Als Parameter.
16. **Tageswerte als Jahreswerte** mit Faktor 365. Hochrechnungsfaktor als Parameter.
17. **Energieformel Güterverkehr** (1,08 und 0,277, Exponent minus 0,62) ohne Quellenangabe. Herkunft und Einheiten dokumentieren; Konstanten in den Parametersatz.
18. **Ersatzformationen.** Umlaufzahl und Fahrzeugkennwerte beziehen sich auf die Standi-Ersatzformation, Betriebsleistung auf die Originalformation. Festhalten.

---

# Teil D: Zielarchitektur und Umsetzungsplan

## D1 Grundsätze

- **Kern ohne Anwendungswissen.** Der Kern kennt Netz, Zustand, Verkehrsleistung, Technologieoption, Maßnahme, Kostenkomponente, Gebiet, Parametersatz. Er kennt weder „Oberleitung“ noch „BVWP“ noch Euro-Beträge. Alles Anwendungsspezifische kommt über Plugins und Konfiguration.
- **Keine Zahl im Code.** Jeder Kostensatz, Faktor, Zeitraum, Schwellwert und Rückfallwert liegt im Parametersatz mit Einheit, Preisjahr, Quelle und Gültigkeit. Code referenziert Parameter über Namen und schlägt fehl, wenn ein Parameter fehlt.
- **Rechnen im Speicher, ohne Nebenwirkungen.** Zustand ist unveränderlich; Änderungen erzeugen neue Zustände. Keine Datenbank in der Rechenlogik. Laden und Schreiben sind Adapter.
- **Registrierte, austauschbare Formeln.** Energie-, Kosten-, Platzierungs-, Cluster- und Entscheidungsfunktionen sind benannte Plugins, die per Konfiguration ausgewählt werden.
- **Nachvollziehbarkeit.** Jeder Lauf schreibt ein Manifest (Parametersatz mit Hash, Szenariodefinition, Plugin-Auswahl, Codeversion, Datenquellenstände) und speichert Zwischenergebnisse je Stufe.
- **Alte Ergebnisse reproduzierbar.** Ein Parametersatz und eine Plugin-Auswahl „altcode-kompatibel“ bilden das heutige Verhalten nach, inklusive der in Teil C entschiedenen Abweichungen als Schalter, damit Golden-Master-Vergleiche möglich sind.

## D2 Paketstruktur

```
traction_eval/                      # eigenständiges Paket mit pyproject.toml
  core/
    model/        Segment, Node, Place, Network, Service, ServiceBundle,
                  VehicleType, VehicleConfig, Scenario, Area, SubArea, Measure, Result
    state/        NetworkState (Netz + Overlays), apply(measure) -> NetworkState
    params/       ParameterSet, Laden aus YAML/TOML, Vererbung, Overrides,
                  Validierung (Einheit, Typ, Pflichtfelder), Hash, Provenienz
    finance/      present_value, phase_schedule, annuity, price_index
    registry/     Plugin-Registry und Protokolle (siehe D3)
    pipeline/     Stufen, Orchestrierung, Caching, Manifest
    results/      Ergebnisschema, Serialisierung (JSON, Parquet), Vergleich zweier Läufe
  methods/                          # generische Methoden, anwendungsneutral
    routing/      shortest_path mit austauschbaren Gewichtsfunktionen
    clustering/   connected_components(predicate, relations), identical_service_set
    energy/       per_km, per_hour, stop_energy_reference_speed, mass_power_law
    cost/         capital_service, maintenance_km, maintenance_time, externality
    cycles/       Umlaufbildung
    range/        Abschnittsbildung, Energiebilanz, Problemdiagnose, Platzierungsregeln
    optimise/     greedy_subarea, Schnittstelle für weitere Strategien
    decision/     min_total_cost, mit Nebenbedingungen
  applications/
    masterarbeit/
      config/     parameters/masterarbeit-2023.yaml, parameters/altcode-kompatibel.yaml,
                  scenario/*.yaml, technologies.yaml, methods.yaml
      plugins/    Technologieoptionen (electrification, battery, h2, efuel, diesel,
                  optimised_electrification), Kostenkomponenten BVWP und Standi,
                  Maßnahmentypen, Kategorie-Zuordnung
      adapters/   Loader aus der prosd-Datenbank, Writer in die prosd-Ergebnistabellen,
                  Export für Auswertung und Fixtures
      reports/    Kennzahlen, Karten, LaTeX (aus scripts/masterarbeit/auswertung übernommen)
  cli/            run, resume, compare, export, validate-params
tests/
  unit/           Formeln mit Handrechnung, Finanzmodul, Parametersystem
  properties/     Invarianten Gebietsbildung, Energiebilanz
  golden/         Fixture-Gebiete gegen eingefrorene Ergebnisse
```

## D3 Plugin-Schnittstellen

Protokolle (Signaturen skizziert; Einheiten und Typen im Code über typisierte Mengen):

```python
class EnergyModel(Protocol):
    name: str
    def energy(self, service: Service, vehicle: VehicleType, state: NetworkState,
               params: ParameterSet) -> Quantity: ...

class CostComponent(Protocol):
    name: str
    applies_to: set[str]          # Kategorien, z. B. {"sgv"} oder {"spnv", "spfv"}
    def annual_cost(self, bundle: ServiceBundle, option: TechnologyOption,
                    state: NetworkState, params: ParameterSet) -> CostBreakdown: ...

class MeasureGenerator(Protocol):
    name: str
    def generate(self, area: Area, state: NetworkState, bundles: list[ServiceBundle],
                 vehicles: VehicleCatalog, params: ParameterSet) -> MeasurePlan: ...
    # MeasurePlan: measures, feasibility, resulting_state, service_to_suboption

class ClusteringStrategy(Protocol):
    name: str
    def areas(self, state: NetworkState, services: list[Service],
              params: ParameterSet) -> list[Area]: ...
    def sub_areas(self, area: Area, services: list[Service]) -> list[SubArea]: ...

class PlacementRule(Protocol):          # Baustein der Reichweitenstrategie
    name: str
    def place(self, diagnosis: RangeDiagnosis, state: NetworkState,
              params: ParameterSet) -> tuple[list[Measure], RangeDiagnosis]: ...

class DecisionRule(Protocol):
    name: str
    def choose(self, results: dict[str, OptionResult], params: ParameterSet) -> Decision: ...

class TechnologyOption(Protocol):
    key: str
    energy_carrier: str
    vehicle_variant: str                # welcher Kennwertsatz des Fahrzeugtyps
    measure_generator: MeasureGenerator
    excluded_categories: set[str]
```

Alle Plugins werden über einen Registry-Eintrag mit Namen angemeldet; Konfigurationsdateien referenzieren Namen. Die Anwendung Masterarbeit registriert ihre Plugins beim Import, der Kern bleibt unverändert.

## D4 Parametersystem

Parameter liegen in YAML (oder TOML) mit Metadaten je Wert. Parametersätze können voneinander erben und Werte überschreiben; Sensitivitätsläufe sind Overrides auf der Kommandozeile oder in der Szenariodatei.

```yaml
# applications/masterarbeit/config/parameters/masterarbeit-2023.yaml
meta:
  name: masterarbeit-2023
  price_year: 2016
  currency: EUR
finance:
  discount_rate:        {value: 0.017, unit: "1/a", source: "BVWP 2030 Methodenhandbuch"}
  base_year:            {value: 2016,  unit: "a"}
  phases:
    planning: {start: 2020, duration: 5}
    build:    {start: 2025, duration: 5}
    operate:  {start: 2030, duration: 30}
  annuity_factor:       {value: 0.0428, unit: "1/a"}
  comparison_sum:       [planning_pv, investment_pv, maintenance_pv, operating_pv]
infrastructure:
  catenary:
    cost_per_km:        {value: 737,  unit: "kEUR/km", source: ""}
    lifetime:           {value: 60,   unit: "a"}
    power_supply_per_km:{value: 200,  unit: "kEUR/km"}
    civil_per_km:       {value: 200,  unit: "kEUR/km"}
    land_per_km:        {value: 5,    unit: "kEUR/km"}
    maintenance_share:  {value: 0.014,unit: "1/a"}
    track_factor:       {eingleisig: 1, zweigleisig: 2}
  charging_station:     {investment: {value: 2582, unit: "kEUR"}, maintenance_share: {value: 0.014}}
  small_charging_station: {investment: {value: 1200, unit: "kEUR"}, maintenance_share: {value: 0.014}}
  filling_station:
    h2:     {investment: {value: 6000, unit: "kEUR"}, spacing_km: 60, maintenance_share: 0.03}
    diesel: {investment: {value: 1000, unit: "kEUR"}, spacing_km: 40, maintenance_share: 0.03}
    efuel:  {investment: {value: 1000, unit: "kEUR"}, spacing_km: 40, maintenance_share: 0.03}
  planning_share:       {value: 0.18}
energy_carriers:
  electricity_renewable: {price: 0.14, unit: kWh, co2_g: 21,   pollutant_factor: 0.05, primary_energy_factor: 4.5}
  diesel:                {price: 0.75, unit: l,   co2_g: 2774, pollutant_factor: 6.57, primary_energy_factor: 38.9}
  efuel:                 {price: 2.50, unit: l,   co2_g: 370,  pollutant_factor: 6.57, primary_energy_factor: 78.2}
  h2:                    {price: 5.00, unit: kg,  co2_g: 938,  pollutant_factor: 2.18, primary_energy_factor: 198.7}
externalities:
  co2_cost_per_t:        {value: 670, unit: "EUR/t"}
  primary_energy_points: {value: 0.9}
  points_to_money:       {value: 15.5, unit: "EUR"}
  primary_energy_points_exponent: {value: 1, note: "Altcode: 2, siehe Teil C Nr. 5"}
range_model:
  charge_power_kw:       {value: 1200}
  min_dwell_for_charging_min: {value: 3}
  turnaround_min:        {value: 10}
  default_terminal_stand_time_h: {value: 1}
  reference_speed_fallback_kmh: {value: 160}
  placement_rules_single_trip: [terminal_charge_point, electrify_before_problem]
  placement_rules_multi_trip:  [terminal_charge_point, intermediate_charge_point, electrify_most_used]
routing:
  weight: length_prefer_catenary
  catenary_factor:       {value: 0.95}
timetable:
  days_per_year:         {value: 365}
freight_energy:
  electric: {a: 1.08,  exponent: -0.62, unit: "kWh per 1000 train-km"}
  diesel:   {a: 0.277, exponent: -0.62, unit: "l per 1000 train-km"}
```

Ein zweiter Satz `altcode-kompatibel.yaml` erbt davon und setzt die Schalter so, dass der Altcode nachgebildet wird (zum Beispiel `primary_energy_points_exponent: 2`, Ladehalte ohne Wirkung, Standzeitfaktor 60). Damit lassen sich Golden-Master-Vergleiche fahren und die Wirkung jeder Korrektur einzeln ausweisen.

Szenariodefinition:

```yaml
# applications/masterarbeit/config/scenario/s1_ausgangsszenario.yaml
name: Ausgangsszenario
parameters: masterarbeit-2023
sources:
  network: prosd-db            # Adapter-Name
  timetable: prosd-db
  vehicles: prosd-db
projects: [18]                 # Szenario-Maßnahmen (IDs in der Quelle)
technologies: [electrification, efuel, battery, optimised_electrification, diesel, h2]
exclusions:
  - {technologies: [battery, h2], when_category_present: sgv}
methods:
  cost_by_category: {sgv: bvwp, spnv: standi, spfv: standi}
  clustering: no_catenary_connected
  sub_areas: identical_service_set
  decision: min_comparison_sum
  infeasible_option: exclude     # oder: penalty, fallback_to: electrification
outputs: [prosd-db, parquet]
```

## D5 Datenfluss gegenüber dem bestehenden System

Der Loader liest einmal je Lauf aus der bestehenden PostGIS-Datenbank: Strecken, Bahnhöfe, Graph, Zuggruppen mit Fahrplan, Formationen, Fahrzeugmuster, Szenario-Projekte. Daraus entsteht das Domänenmodell als Datei (Parquet oder JSON), die auch ohne Datenbank als Eingabe dient. Der Writer schreibt am Ende in die bestehenden Tabellen (`master_areas`, `timetable_train_cost`, `projects_contents` für Maßnahmen, `traction_optimised_electrification`, Kennzahlenspalten), damit Dashboard und API unverändert funktionieren. Später kann der Writer durch ein eigenes Ergebnisschema ersetzt werden.

## D6 Tests

- Einheitstests je Formel aus Teil B mit Handrechnungsbeispielen (ein Fahrzeug, eine Strecke, ein Jahr).
- Finanzmodul gegen Referenzwerte (Barwert, Phasen, Annuität).
- Parametersystem: fehlende Parameter führen zu Fehlern, Vererbung und Overrides, Hash-Stabilität.
- Eigenschaftstests: Gebiete disjunkt und vollständig; Energiebilanz nie über Kapazität, Ladung monoton nicht fallend; Maßnahmen verändern nur Zustandskopien.
- Golden-Master: zwei bis drei kleine Gebiete aus der Produktionsdatenbank als Fixtures exportieren (ein reines Nahverkehrsgebiet, eines mit Güterverkehr, eines mit optimierter Elektrifizierung), heutige Ergebnisse einfrieren, mit Parametersatz `altcode-kompatibel` vergleichen. Jede Korrektur aus Teil C wird als eigener Schalter umgestellt und ihre Wirkung im Vergleichsbericht ausgewiesen.

## D7 Umsetzungsreihenfolge

1. Paketgerüst, Domänenmodell, Parametersystem mit den beiden Parametersätzen, Finanzmodul. Tests.
2. Loader aus der prosd-Datenbank in das Domänenmodell, Export als Datei. Fixtures erzeugen.
3. Betriebsleistungsgrößen und Umlaufbildung. Tests gegen Fixtures.
4. Kostenkomponenten BVWP und Standi als Plugins. Golden-Master für Betriebskosten.
5. Gebietsbildung und Teilgebiete. Eigenschaftstests.
6. Maßnahmengeneratoren Oberleitung, Tankstellen, Ladepunkte. Golden-Master Infrastrukturkosten ohne Batterie.
7. Reichweitenmodell mit Platzierungsregeln als Plugins. Golden-Master Batterie, dann Korrekturen aus Teil C Nr. 2, 3, 6 einzeln aktivieren und Wirkung ausweisen.
8. Kombinierte Optimierung. Golden-Master optimierte Elektrifizierung.
9. Entscheidung, Aggregation, Writer in die prosd-Tabellen, Manifest, CLI.
10. Auswertungsskripte (Karten, LaTeX) auf das neue Ergebnisschema umstellen.
11. Störfallbewertung als eigenes Modul.
12. Abschluss: Altcode in `prosd` auf Modelle, API und Importe reduzieren; Rechenlogik entfernen.

Voraussetzung für Schritt 2 und alle Golden-Master-Tests ist ein Zugriff auf einen Dump der Produktionsdatenbank oder ein Auszug mit mindestens einem Szenario und einigen Gebieten.

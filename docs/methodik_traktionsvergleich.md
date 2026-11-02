# Methodik des Traktionsvergleichs: allgemeines Verfahren und Anwendung Masterarbeit

Stand: rekonstruiert aus dem Code des Repos `pros` (Commit a5a5269), Oktober 2026, nach unabhängigem Review gegen den Code. Quellen sind `prosd/models.py` (MasterScenario, MasterArea, TimetableTrainGroup, TimetableTrainCost, TrainCycle, TimetableLine), `prosd/calculation_methods/use.py`, `prosd/calculation_methods/cost.py`, `prosd/calculation_methods/base.py`, `prosd/manage_db/version.py`, `prosd/graph/routing.py`, `prosd/graph/block_rw_lines.py` und `prosd/parameter.py`. Der Text der Masterarbeit lag bei der Rekonstruktion nicht vor; ebenso nicht die Datenbankinhalte (Fahrzeugkennwerte und ihre Einheiten) und die externen JSON-Korrekturlisten unter `example_data/railgraph/`. Jede Stelle, an der der Code mehrdeutig ist oder von der vermuteten Absicht abweicht, ist in Teil C gesammelt und muss gegen den Thesis-Text entschieden werden, bevor neu entwickelt wird.

Aufbau des Dokuments:
- Teil A beschreibt das Verfahren allgemein, ohne Bezug auf konkrete Traktionen, Kostensätze, Datenquellen oder Bewertungsrichtlinien. Das ist die Grundlage für den Kern der Neuentwicklung.
- Teil B beschreibt die Adaption auf die Masterarbeit: deutsches Schienennetz, Deutschlandtakt, sechs Traktionen, BVWP- und Standi-Verfahren, konkrete Formeln und Parameter, so wie der Altcode sie umsetzt.
- Teil C listet Verdachtsfälle und Mehrdeutigkeiten des Altcodes.
- Teil D enthält Zielarchitektur, Konfigurationskonzept und Umsetzungsplan.
- Teil E sammelt methodische Erweiterungen, die über die Rekonstruktion hinausgehen.

Gestaltungsgrundsätze für die Neuentwicklung: maximal modular, jede Kostengröße und jeder Faktor konfigurierbar, keine Zahl im Code, Methodik zuerst allgemein, dann adaptiert.

Entscheidungsstand: Die offenen Punkte wurden am 2026-11-01 als Entscheidungsstapel EKS-2026-010 vorgelegt und entschieden (Teil F). Wichtigste Festlegung: kompletter Neubau in einem eigenen Repo, kein Nachbau des Altcodes. Teil B beschreibt deshalb nur noch, was der Altcode tat; maßgeblich für die Neuentwicklung sind Teil A, Teil D und Teil F.

---

# Teil A: Allgemeines Verfahren

## A1 Grundidee

Gegeben ist ein Verkehrsnetz, auf dem ein Betriebsprogramm (eine Menge von Verkehrsleistungen mit festen Laufwegen und Fahrplänen) erbracht werden soll. Für einen Teil des Netzes stehen mehrere Technologieoptionen zur Verfügung, die sich in Infrastrukturbedarf und Betriebskosten unterscheiden. Das Verfahren zerlegt den relevanten Netzteil in Bewertungsgebiete, ermittelt je Gebiet und Option die Infrastrukturmaßnahmen, die die Option betriebsfähig machen, berechnet dafür Infrastruktur- und Betriebskosten über einen Betrachtungszeitraum, diskontiert sie auf ein Basisjahr und wählt je Gebiet die Option nach einer Entscheidungsregel. Gebietsergebnisse werden zu Szenariokennzahlen aggregiert.

Das Verfahren ist unabhängig davon, welche Technologien verglichen werden, welche Kostensätze gelten und nach welcher Richtlinie monetarisiert wird. Diese Festlegungen sind Konfiguration und Plugins der Anwendung (Teil B).

## A2 Bausteine

| Baustein | Rolle | Was die Anwendung festlegt |
|---|---|---|
| Netz | Gerichteter Graph aus Segmenten mit Attributen (Länge, Gleiszahl, Versorgungsmerkmale, Sperrung) und Knoten; Orte (Betriebsstellen) mit Segmentzuordnung und Versorgungsmerkmalen | Attributschema, Datenquelle |
| Infrastrukturzustand | Unveränderliches Netz plus Änderungsschicht (Overrides je Segment und Ort). Wird aus Szenario-Maßnahmen und Zwischenergebnissen abgeleitet. Jede Ableitung erzeugt einen neuen Zustand, der alte bleibt unverändert | Welche Maßnahmentypen welche Attribute setzen |
| Verkehrsleistung | Einheit des Betriebsprogramms mit Laufweg (geordnete Segmentfolge), Halten mit Zeiten, Fahrzeugkonfiguration, Kategorie, Häufigkeit je Zeiteinheit | Datenquelle, Kategorien, Hochrechnung auf das Jahr |
| Leistungsbündel | Gruppe von Verkehrsleistungen, die gemeinsam bewertet oder gemeinsam mit Fahrzeugen bedient wird (zum Beispiel beide Richtungen einer Linie), mit einer Verteilungsregel der Bündelkosten auf die Leistungen | Bündelungsregel, Verteilungsregel |
| Fahrzeugkonfiguration | Liste von Fahrzeugtypen mit Kennwerten je Technologieoption (Energie je km und je Stunde, Masse, Kapitaldienst, Instandhaltungssätze, Speicherkapazität, Zuschläge). Je Methodenkontext kann eine Ersatzkonfiguration gelten (Betriebsleistung aus der Originalkonfiguration, Kosten aus der Ersatzkonfiguration) | Kennwerttabellen, Ersatzregel |
| Technologieoption | Benannte Variante mit Auswahlregel für die Fahrzeugkennwerte, Energieträger, Maßnahmengenerator, Durchführbarkeitsprüfung, Ausschlussregeln auf Gebiets- und Teilgebietsebene | Liste der Optionen und ihre Plugins |
| Energieträger | Preis, Emissionsfaktoren, Primärenergiefaktor, Einheit, Preisjahr; Werte dürfen Zeitreihen sein | Tabelle je Energieträger |
| Kostenkomponente | Funktion von (Leistung oder Bündel oder Maßnahme, Option, Zustand, Parameter) nach Jahreswert oder Einmalwert mit Einheit und Preisbasis | Satz der Komponenten und ihre Formeln |
| Maßnahme | Infrastrukturänderung mit Wirkung auf den Zustand und Kostenwerten (Investition, laufende Kosten, Planung, Barwerte); kann Teilmaßnahmen enthalten; trägt die Regel, ob sie als Versorgung in Reichweitenbilanzen zählt | Maßnahmentypen und Kostenformeln |
| Gebietsbildung | Zerlegung des Netzteils in disjunkte Gebiete mit Segment- und Leistungsmenge; optional Teilgebiete; Zuordnungsregel für Leistungen, die in mehreren Teilgebieten liegen | Clusterkriterium, Teilgebietskriterium |
| Finanzmodul | Diskontierung, Preisbasis, Phasenmodell, Annuität, Restwert | Zinssatz, Basisjahr, Phasendauern |
| Entscheidungsregel | Abbildung der Optionsergebnisse eines Gebiets auf eine Wahl (Standard: minimale Vergleichssumme) mit Umgang mit nicht durchführbaren Optionen | Regel, Nebenbedingungen |
| Aggregation | Kennzahlen je Szenario aus Gebietsergebnissen | Kennzahlenliste |
| Validierung | Prüfregeln für Eingaben und Zwischenergebnisse mit festgelegtem Verhalten (abbrechen, überspringen und melden, Standardwert und melden) | Regeln und Schwellwerte |
| Parametersatz | Alle Zahlenwerte mit Einheit, Preisjahr, Quelle und Gültigkeit; versioniert, vererbbar, überschreibbar | Konkrete Werte |

## A3 Verfahrensgrundsätze

- **Bewertungsumfang Betriebskosten.** Betriebskosten einer Verkehrsleistung werden auf dem gesamten Laufweg berechnet, auch außerhalb des Gebiets, und die Technologieoption gilt für den gesamten Laufweg (kein Wechsel unterwegs). Dadurch sind Optionen je Gebiet vergleichbar; absolute Gebietskosten enthalten Anteile außerhalb des Gebiets.
- **Zeitbasis.** Das Betriebsprogramm beschreibt einen Normaltag; Jahreswerte entstehen über einen Hochrechnungsfaktor. Alle Fahrten einer Verkehrsleistung gelten als zeitlich identisch.
- **Zustände sind Werte.** Maßnahmen verändern nie einen bestehenden Zustand, sondern erzeugen einen neuen. Welche Zwischenergebnisse (Maßnahmen einer Option) in den Zustand für andere Optionen oder andere Gebiete übernommen werden, ist explizit konfiguriert; Standard ist keine Übernahme zwischen Optionen und Gebieten.
- **Wiederverwendung.** Ein Zwischenergebnis (Betriebskosten, Maßnahmenplan) darf nur wiederverwendet werden, wenn seine Eingaben (Leistung, Option, Zustands-Hash, Parametersatz-Hash) identisch sind.
- **Durchführbarkeit ist ein Ergebnis.** Kann eine Option für ein Gebiet nicht betriebsfähig gemacht werden, ist das ein Ergebnis mit Begründung, kein Fehler und keine stille Kostenschätzung.
- **Datenfehler sind keine Ergebnisse.** Fehlende Kennwerte, Längen null, fehlende Zuordnungen führen nach Validierungsregel zu Abbruch oder zu dokumentiertem Überspringen, nie zu stillen Nullwerten.

## A4 Ablauf als Pipeline

Jede Stufe hat definierte Ein- und Ausgaben, ist ohne Nebenwirkungen und einzeln testbar.

1. Laden: Netz, Betriebsprogramm, Fahrzeugkennwerte, Szenariodefinition, Korrekturlisten und Parametersatz in das Domänenmodell überführen.
2. Validieren: Eingaben gegen die Prüfregeln; Bericht ins Manifest.
3. Zustand bilden: Szenario-Maßnahmen auf das Netz anwenden.
4. Laufwege bestimmen: je Verkehrsleistung den Laufweg auf dem Zustand ermitteln oder aus der Quelle übernehmen (Routing ist ein Modul mit konfigurierbarer Gewichtsfunktion und Korrekturlisten).
5. Betriebsleistungsgrößen je Verkehrsleistung einmal vorberechnen (Längen nach Attributen, Fahrzeiten, Halte, Häufigkeit, Jahreswerte); Bündel und Fahrzeugbedarf bilden.
6. Gebiete bilden (A7), bei Bedarf Teilgebiete.
7. Je Gebiet und Option: Maßnahmen erzeugen (Maßnahmengenerator auf einer Kopie des Zustands), Infrastrukturkosten berechnen, Betriebskosten aller Leistungen des Gebiets unter dieser Option berechnen, Durchführbarkeit festhalten.
8. Je Gebiet: Barwerte bilden, Entscheidungsregel anwenden.
9. Aggregieren, Ergebnis mit Parametersatz, Szenariodefinition, Plugin-Auswahl, Codeversion, Datenstände und Validierungsbericht als Manifest speichern.

Zwischenergebnisse jeder Stufe sind serialisierbar, damit Läufe wiederaufgenommen und Teilstufen einzeln wiederholt werden können. Gebiete sind voneinander unabhängig und können parallel bearbeitet werden.

## A5 Finanzmodul

- Barwert eines Jahreswerts K_x über D Jahre ab Jahr S auf Basisjahr B mit Zinssatz p: Summe über x = 0 bis D minus 1 von K_x / (1 + p)^(S minus B + x). K_x darf konstant oder eine Zeitreihe sein.
- Einmalkosten E über eine Phase der Dauer D ab Jahr S: gleichmäßige Verteilung E / D je Jahr, dann Barwert wie oben.
- Phasenmodell für Maßnahmen: Planung (d_P), Bau (d_B), Betrieb (d_O), nacheinander ab einem Startjahr. Dauern sind Parameter oder Funktionen (zum Beispiel kostenabhängige Baudauer über eine Tabelle).
- Annuität einer Investition: Barwert × Annuitätsfaktor (Parameter) oder berechnet aus Zins und Lebensdauer.
- Restwert: Anlagen mit Lebensdauer über dem Betrachtungszeitraum werden anteilig angesetzt (Standard: linearer Anteil Betrachtungsdauer / Lebensdauer; Alternativen als Plugin).
- Preisbasis: jede Zahl trägt ihr Preisjahr; Umrechnung auf das Basisjahr über einen konfigurierbaren Index. Fehlt ein Index, wird die Zahl unverändert übernommen und das im Manifest vermerkt.
- Welche Komponenten in die Vergleichssumme eingehen (Investitionsbarwert oder Annuität, welche Externalitäten), ist Konfiguration der Entscheidungsregel.

## A6 Energie- und Betriebskostenmodelle

Betriebskosten je Verkehrsleistung und Option sind eine Summe konfigurierter Kostenkomponenten. Generische Komponenten:

| Komponente | Generische Form |
|---|---|
| Kapitaldienst Fahrzeuge | Fahrzeugbedarf × Kapitaldienst je Fahrzeug, oder Zugstunden × Satz je Stunde |
| Instandhaltung laufleistungsabhängig | Satz je km × Fahrzeug-km × (1 + Zuschlag × Anteil einer Betriebsbedingung, zum Beispiel Fahren ohne Versorgung) |
| Instandhaltung zeitabhängig | Fahrzeugbedarf × Satz je (Masse und Jahr) × Masse |
| Fahrenergie | Satz je km × km, optional differenziert nach Segmentklassen, mit Zuschlag analog zur Instandhaltung; oder massebasierte Potenzformel; oder Satz je Stunde × Stunden |
| Halteenergie | Energie je Halt (Funktion von Referenzgeschwindigkeit und Masse) × Halte je Jahr; Referenzgeschwindigkeit aus Reisezeit, Haltezeit, Haltezahl, Länge und Fahrzeugkennwert, mit konfigurierbarem Rückfall (Festwert oder Höchstgeschwindigkeit des Fahrzeugs) |
| Energiekosten | Energiemenge × Preis des Energieträgers (Zeitreihe erlaubt) |
| Emissionen | Energiemenge × Emissionsfaktor; Kosten = Menge × Kostensatz (Zeitreihe erlaubt) |
| Schadstoffe, Primärenergie, weitere Externalitäten | Energiemenge × Faktor × Monetarisierungssatz; beliebig viele Komponenten konfigurierbar |
| Emissionen Fahrzeugherstellung | Fahrzeugbedarf × Satz je Fahrzeug und Jahr × Kostensatz |
| Emissionen Infrastrukturherstellung | Maßnahmenmenge (km, Anlagen) × Satz × Kostensatz (optional) |

Welche Komponenten für welche Kategorie gelten und mit welchen Formelvarianten, ist eine Methodenkonfiguration. Formeln sind registrierte Funktionen. Bündelkosten werden über die Verteilungsregel des Bündels auf Leistungen verteilt (Standard: gleiche Anteile; Alternativen nach Zug-km oder Zugstunden).

Fahrzeugbedarf eines Bündels wird über eine Umlaufbildung bestimmt: Verkettung von Leistungen, deren Folgeleistung am Endort beginnt und frühestens nach einer Wendezeit abfährt. Wendezeit und optionaler Reservefaktor sind Parameter, die Umlaufbildung ein Modul.

## A7 Gebietsbildung

Clusterbildung über ein Segmentprädikat (zum Beispiel „ohne Versorgung“) und zwei Nachbarschaftsrelationen:
1. Segmente sind verbunden, wenn dieselbe Verkehrsleistung beide befährt.
2. Segmente sind verbunden, wenn sie an demselben Ort beginnen oder enden.
Gebiet = Zusammenhangskomponente der Segmente, die das Prädikat erfüllen, plus alle Verkehrsleistungen, die mindestens ein Segment des Gebiets befahren. Beide Relationen sind einzeln aktivierbar und werden transitiv geschlossen; weitere Relationen sind als Plugin ergänzbar. Segmente mit unbekanntem Attributwert werden nach Validierungsregel behandelt, nicht still ausgeschlossen.

Teilgebiete: Segmente eines Gebiets mit identischer Menge befahrender Verkehrsleistungen. Eine Leistung kann in mehreren Teilgebieten liegen; die Zuordnungsregel Leistung zu Teiloption (A10) muss das behandeln.

Invarianten, die getestet werden: Gebiete sind disjunkt; jedes Segment, das das Prädikat erfüllt und befahren wird, liegt in genau einem Gebiet; Teilgebiete partitionieren das Gebiet; jedes Segment eines Gebiets wird von mindestens einer Leistung befahren.

## A8 Infrastrukturmaßnahmen je Option

Jede Technologieoption bringt einen Maßnahmengenerator mit der Signatur: (Gebiet, Zustand, Bündel des Gebiets, Fahrzeugkennwerte, Parameter) nach (Maßnahmen, Durchführbarkeitsstatus, neuer Zustand, Zuordnung Leistung zu Teiloption). Generische Generatortypen:

- **Flächige Ausrüstung**: alle Segmente des Gebiets, die ein Prädikat erfüllen, erhalten ein Merkmal; Kosten = Summe über Segmente von Länge × Satz je km × Gleisfaktor.
- **Punktuelle Versorgung nach Dichte**: Anzahl Anlagen = aufgerundet(Gebietslänge / Abstand) × Satz je Anlage.
- **Punktuelle Versorgung an Orten**: Anlagen an bestimmten Orten (zum Beispiel Start- und Endorte ohne Versorgung) × Satz je Anlage.
- **Reichweitenbasierte Ergänzung** (A9): aus einer Energiebilanz abgeleitete Kombination punktueller und flächiger Maßnahmen.
- **Kombinierte Optimierung** (A10): Zerlegung in Teilgebiete, je Teilgebiet Wahl zwischen Teiloptionen.

Jede Maßnahme kennt ihre Phasen (A5), ihre Kostenwerte, ihre Wirkung auf den Zustand und ob sie in Reichweitenbilanzen als Versorgung zählt. Maßnahmen können Teilmaßnahmen enthalten; Kosten der Gesamtmaßnahme sind die Summe der Teilmaßnahmen.

## A9 Reichweitenmodell für speichernde Antriebe

Für Optionen, deren Fahrzeuge Energie speichern und unterwegs nachladen:

1. **Fahrtenfolge wählen** je Bündel: ein konfigurierbarer Selektor liefert die zu bilanzierenden Fahrten (Standard: je Startort ein Umlauf, dessen erste zwei Fahrten; Alternative: vollständiger Umlauf). Die Wendezeit ist dieselbe wie in der Umlaufbildung.
2. **Abschnittsbildung** je Fahrt: der Laufweg wird in Abschnitte geteilt an jedem Wechsel des Versorgungsmerkmals und an jedem Halt, der eine Mindesthaltezeit erreicht oder eine Ladeanlage hat. Je Abschnitt: Länge, Versorgung, Fahrzeit, Halte, letzter Halt mit Haltezeit und Ladeanlage. Die Segmentfolge ist so zu schneiden, dass das Segment, auf dem der Halt liegt, zum Abschnitt vor dem Halt gehört. Für den letzten Abschnitt ist die Standzeit die Zeit bis zur Abfahrt der Folgefahrt (konfigurierbarer Standardwert, wenn keine bekannt).
3. **Energiebedarf je Abschnitt** aus den Energiemodellen (A6), mit eindeutiger Zuordnung jedes Halts zu genau einem Abschnitt.
4. **Bilanz** entlang der Fahrtenfolge: Start mit nutzbarer Speicherkapazität (Nennkapazität × nutzbarer Anteil); unter Versorgung Laden mit Ladeleistung × Fahrzeit; an Ladeanlagen Laden mit Ladeleistung × Haltezeit; am Fahrtende Laden über die Standzeit, sofern Versorgung oder Ladeanlage vorhanden; ohne Versorgung Abzug des Abschnittsbedarfs; Deckelung auf Kapazität; Protokoll jedes negativen Zwischenstands. Ladezuwachs und Füllstand sind getrennte Größen.
5. **Problemtypen**: Einzelfolgeproblem (Speicher wird innerhalb der Fahrtenfolge leer) und Mehrfolgeproblem (Bilanz nach der Fahrtenfolge negativ und über die Zahl der Wiederholungen im Umlauf nicht tragfähig).
6. **Maßnahmenstrategie**: geordnete Liste von Platzierungsregeln, jede mit Vorbedingung (zum Beispiel „Problem liegt auf der Rückfahrt“), die nacheinander angewendet werden, bis der Bedarf gedeckt ist. Jede Regel liefert Maßnahmen und den Ladezuwachs, den sie bewirkt; jede Maßnahme wird vor der Abbruchprüfung in den Plan übernommen. Regeln sind Plugins; Reihenfolge und Vorbedingungen sind Konfiguration.
7. **Durchführbarkeit**: bleibt nach allen Regeln ein Problem, wird die Option für dieses Gebiet als nicht durchführbar markiert (A3).
8. **Reihenfolge der Bündel** innerhalb eines Gebiets ist konfiguriert und dokumentiert, weil frühere Maßnahmen späteren Bündeln zugutekommen.

## A10 Kombinierte Optimierung über Teilgebiete

Für eine Option, die je Teilgebiet zwischen Teiloptionen wählt:
1. Ausgangszustand: Gebiet vollständig mit der Basisteiloption ausrüsten; Betriebskosten aller Leistungen unter der Basisteiloption bestimmen.
2. Teilgebiete sortieren (Standard: aufsteigend nach Betriebsleistung).
3. Je Teilgebiet: Basisausrüstung des Teilgebiets zurücknehmen, jede zulässige Teiloption bewerten (Betriebskosten der Leistungen des Teilgebiets unter der Teiloption plus Maßnahmenkosten, als Barwert), die günstigste wählen, ihre Maßnahme in den Zustand übernehmen. Verworfene Teiloptionen hinterlassen keine Spuren im Zustand. Ausschlussregeln je Kategorie gelten auf Teilgebietsebene.
4. Zuordnung Leistung zu Teiloption: eine Leistung, die in mehreren Teilgebieten liegt, erhält die Teiloption nach einer konfigurierten Regel (Standard: Speicheroption, sobald ein Teilgebiet sie wählt, mit Neubewertung der Betriebskosten für die geänderte Zuordnung; Alternative: Mehrheits- oder Längenregel). Betriebskostendifferenzen einer Leistung dürfen nur einmal in die Entscheidung eingehen.
5. Nach allen Teilgebieten: Abschlussmaßnahmen (zum Beispiel Versorgung an Start- und Endorten).
6. Ergebnis: Gesamtmaßnahme mit Teilmaßnahmen, Zuordnung Leistung zu Teiloption, Anteile je Teiloption.

Der Greedy-Durchlauf ist die Standardstrategie. Die Schnittstelle erlaubt andere Strategien (mehrere Durchläufe, lokale Suche, exakte Verfahren über die additive Kostenstruktur) ohne Änderung der übrigen Pipeline.

## A11 Entscheidung und Aggregation

Je Gebiet und Option liegen vor: Infrastrukturkosten nach Komponenten, Betriebskosten nach Komponenten, Durchführbarkeit, physische Kennzahlen (ausgerüstete km, Anlagenzahl), Emissionen. Die Entscheidungsregel bildet daraus die gewählte Option. Standard: Minimum der konfigurierten Vergleichssumme über die durchführbaren Optionen. Umgang mit nicht durchführbaren Optionen: ausschließen, Strafkosten oder Rückfall auf eine andere Option (Konfiguration). Gibt es keine bewertbare Option, ist das ein ausgewiesenes Ergebnis.

Erweiterungen: Nebenbedingungen (Emissionsgrenze), Gewichtungen, Sensitivitätsläufe über Parametersätze, robuste Wahl (Option, die in den meisten Sätzen gewinnt), Break-even-Werte je Gebiet (bei welchem Parameterwert kippt die Entscheidung).

Aggregation je Szenario: je gewählter Option Anzahl Gebiete, Segment-km, Leistungs-km, Kosten nach Komponenten, Emissionen; Zerlegung kombinierter Optionen in ihre Teiloptionen; Vergleich gegen eine Referenzoption für alle Gebiete. Die Kennzahlenliste ist Konfiguration.

## A12 Störfallbewertung (Erweiterung)

Generisches Muster: Ein Störfall sperrt Segmente; betroffene Leistungen werden umgeleitet oder durch einen anderen Verkehrsträger ersetzt. Bewertet wird die Differenz der Gesamtkosten zwischen „Netz für Umleitung ertüchtigen“ und „Ersatz durch anderen Verkehrsträger“, gewichtet mit dem Zeitanteil des Störfalls. Kostensätze des Ersatzverkehrs und Zusatzkosten der Umleitung sind Parameter. Die Bewertung läuft auf Zustandskopien und verändert das Referenzergebnis nicht.

---

# Teil B: Anwendung Masterarbeit

Teil B beschreibt, was der Altcode tut. Abweichungen von der vermuteten Absicht stehen in Teil C.

## B1 Konkretisierung der Bausteine

| Baustein | Festlegung in der Masterarbeit |
|---|---|
| Netz | Deutsches Schienennetz (`RailwayLine`, `RailwayStation`): Länge, Gleiszahl (ein-/zweigleisig), Oberleitung (`catenary`), Stromschiene, ABS/NBS, Sperrung; Bahnhöfe mit Ladestation und kleiner Ladestation |
| Zustand | `Version`: Bestand plus Szenario-Projekte (`ProjectContent` mit `elektrification`, `closure`, `charging_station`, `small_charging_station`); eine Instanz für den gesamten Lauf (Teil C Nr. 19) |
| Verkehrsleistung | Zuggruppe des Deutschlandtakts (`TimetableTrainGroup`), Kategorien sgv, spnv, spfv |
| Leistungsbündel | Fahrplanlinie (`TimetableLine`), beide Richtungen; Verteilung der Linienkosten zu gleichen Teilen auf die Zuggruppen |
| Fahrzeugkonfiguration | Formation mit Ersatzformationen für BVWP und Standi; Fahrzeugmuster mit Traktionsvarianten |
| Technologieoptionen | electrification, battery, h2, efuel, diesel, optimised_electrification; Ausschluss: battery und h2 nicht für Gebiete mit sgv; sgv-Teilgebiete immer Oberleitung |
| Energieträger | Strom erneuerbar, Diesel, eFuel, H2 (Strommix definiert, nicht verwendet) |
| Kostenkomponenten | sgv nach BVWP (Zuggruppe, nur Triebfahrzeug), spnv und spfv nach Standi (Linie, alle Fahrzeuge) |
| Gebietsbildung | Prädikat `catenary is False and conductor_rail is False`, beide Relationen (Bahnhofsrelation nicht transitiv geschlossen, Teil C Nr. 22); Teilgebiete nach identischer Zuggruppenmenge |
| Finanzmodul | Basisjahr 2016, 1,7 %, Planung 5 Jahre ab 2020, Bau 5 Jahre ab 2025, Betrieb 30 Jahre ab 2030; Vergleichssumme = Barwert Planung + Barwert Investition + Barwert Instandhaltung + Barwert Betriebskosten |
| Entscheidungsregel | Minimum der Vergleichssumme über Traktionen mit beiden Kostenteilen; fehlen alle, Ergebnis „no calculated cost“ |
| Routing | Dijkstra über Streckengraph, Gewicht Länge in m, Oberleitung mit Faktor 0,95, gesperrte Strecken ausgeschlossen; Via-Punkte sind alle Zwischenbetriebsstellen mit Bahnhofszuordnung, auch Durchfahrten, abzüglich einer Ignorierliste je Zuggruppe (`blacklist_route_ignore_ocp.json`); Strecken ohne gültige Länge erhalten Gewicht 0 |

## B2 Eingangsdaten

Infrastruktur: je Strecke `id`, `length` (m), `number_tracks`, `catenary`, `conductor_rail`, `abs_nbs`, `closed`, Start-/Endknoten, Nachbarstrecken, Bahnhöfe. Je Bahnhof `id`, `name`, `db_kuerzel`, Strecken, `charging_station`, `small_charging_station`. Streckengraph: gerichteter networkx-Graph mit Teilknoten je Strecke und Richtung, Abbiegebeziehungen (Mindestwinkel 60 Grad), Bahnhofsknoten als Quelle/Ziel; gespeichert als Datei.
Fahrplan: railML des Deutschlandtakts mit Zuggruppen, Zügen, Zugteilen, Betriebsstellen mit Ankunft/Abfahrt und Typ (`stop` oder Durchfahrt), Mindestfahrzeiten, Kategorie, Formation. Zuordnung railML-Betriebsstelle zu Bahnhof über Kürzel; Betriebsstellen ohne Bahnhof werden im Routing übersprungen und in der Halteenergie über Fahrzeitanteile zugeordnet.
Fahrzeuge: Formation mit Fahrzeugliste; Fahrzeug mit `brutto_weight`, `length`, `engine`/`wagon`; Fahrzeugmuster mit den in B6 genutzten Feldern und Varianten je Traktion; `type_of_traction` (`Elektro`, `Batterie`, `Diesel`, `eFuel`, `H2`) wählt den Energieträger.
Szenario-Projekte: Maßnahmen mit den Flags aus B1; Teilmaßnahmen ersetzen die Hauptmaßnahme.
Korrekturlisten (nicht im Repo): `blacklist_route_ignore_ocp.json` (Routing), `recalculate_traingroups.json`, `blocked_scenarios/s-<id>.json` (Störfall), `catenary_too_long.json` (Protokoll).

## B3 Parametersatz „masterarbeit-2023“

Werte aus `parameter.py`, ergänzt um Konstanten, die im Code stehen (gekennzeichnet mit „Code“). In der Neuentwicklung liegen alle in einer Parameterdatei mit Einheit, Preisjahr und Quelle (Teil D). Die Spalte Quelle ist aus der Thesis zu ergänzen.

Zeit und Zins

| Parameter | Wert | Einheit |
|---|---|---|
| Basisjahr Barwert und Preisbasis | 2016 | Jahr |
| Diskontrate | 1,7 | % |
| Annuitätsfaktor Infrastruktur | 0,0428 | 1/Jahr |
| Startjahr Betrieb | 2030 | Jahr (die Spalten `start_year`, `operation_duration` des Szenarios werden ignoriert) |
| Planungsdauer | 5 | Jahre |
| Baudauer | 5 | Jahre |
| Betriebsdauer | 30 | Jahre |
| Hochrechnung Tag auf Jahr | 365 | Code |

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
| Gleisfaktor | 2 bei `zweigleisig`, sonst 1 (auch bei unbekannt) | Code |
| Ladestation | 2.582 | T€ |
| kleine Ladestation | 1.200 | T€ |
| Tankstelle H2 | 6.000 | T€, eine je 60 km |
| Tankstelle Diesel | 1.000 | T€, eine je 40 km |
| Tankstelle eFuel | 1.000 | T€, eine je 40 km |
| Schwellwert Bahnhofs-Oberleitung „zu lang“ | 1.000 | m, nur Protokoll, Code |
| unbenutzt: Oberleitung ein-/zweigleisig | 1.141 / 2.282 | T€/km, definiert, nicht verwendet |

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
| Nutzenpunkte Primärenergie | 0,9 (im Code quadriert, Teil C Nr. 5) |
| Geldwert je Nutzenpunkt | 15,5 € |
| Skalierungen Externalitäten | 10^-3 (CO2 g nach t, t nach T€), 10^-2 (Schadstoffe), Code |
| Standi-Konstanten Referenzgeschwindigkeit | 55,6 und 3,6; Energie je Halt × 10^-6; Code |
| Rückfallwert Referenzgeschwindigkeit | 160 km/h, Code |
| Energieformel Güterverkehr | 1,08 (kWh) bzw. 0,277 (l) × m^-0,62 × 1000, Code |
| Ladeleistung Batterie | 1.200 kW |
| Wendezeit Umlaufbildung | 10 min (`WAIT_TIME`); Umlaufauswahl in der Batterierechnung nutzt den Standard 5 min, Teil C Nr. 24 |
| Mindesthaltezeit für Ladeabschnitt | 3 min, Code |
| Standzeit am Zugende ohne Folgezug | 1 h, Code |
| Teiler Umlaufelemente zu Umläufen | 2, Code |
| Warnschwelle Überelektrifizierung | minus 100 kWh, nur Protokoll, Code |
| Routing: Faktor Oberleitung | 0,95, Code |
| Routing: Mindestwinkel Abbiegen | 60 Grad, Code |
| Laufsteuerung | `REROUTE_TRAINGROUP`, `DELETE_AREAS`, `CREATE_AREAS`, `OVERWRITE_INFRASTRUCTURE` |

Störfall: Lkw-Kostensätze je 100 km (Energie 17,5, Personal 25,18, Kapital 22, Instandhaltung 12,86, CO2 1,8, Primärenergie 7,8, Emission 0,1 €; Summe 87,24 €), Lkw-Nutzlast 25 t, Containerwagen 19,7 m, 20 t Eigenmasse, 50 t Nutzlast, Wagenkosten 1,06 €/Wagen-h, Triebfahrzeugführer 57 €/h, Zugbereitstellung 23 €/Wagen, Störungsanteil 4,63 % der Zeit, Umleitungsgeschwindigkeit 60 km/h.

## B4 Gebietsbildung konkret

Ausgangsmenge: Strecken mit `catenary is False and conductor_rail is False` im Zustand (Wert `None` fällt heraus) und alle Zuggruppen mit Zug und Kategorie, deren Route eine dieser Strecken enthält. Clusterbildung nach A7 mit beiden Relationen; die Bahnhofsrelation wird nur für die jeweils neu hinzugekommenen Strecken einmal geprüft, nicht transitiv geschlossen. Elektrifizierte Strecken der Routen gehören nicht zum Gebiet, zählen aber in der Betriebskostenrechnung mit (A3). Eine ältere Skriptfassung startete nur von Güterzuggruppen; die Modellfassung startet von allen Zuggruppen. Teilgebiete nach identischer Zuggruppenmenge; eine Gebietsstrecke ohne Zuggruppe führt zum Abbruch (`SubAreaError`).

## B5 Betriebsleistungsgrößen je Zuggruppe

Alle Zeitgrößen werden vom ersten Zug der Zuggruppe genommen und gelten für alle Züge.

| Größe | Definition |
|---|---|
| Linienlänge L (km) | Summe der Streckenlängen der Route im Szenario |
| L_oo (km) | Teil von L mit `catenary is False` im Zustand |
| Anteil ABS / NBS | Teil von L mit `abs_nbs` ABS bzw. NBS |
| Züge je Tag n | Anzahl Züge der Zuggruppe |
| Zug-km je Jahr | L × n × 365 / 1000 (Tausend Zug-km) |
| Reisezeit T | Abfahrt erste bis Ankunft letzte Betriebsstelle, inkl. Halte; Tageswechsel wird ignoriert (Teil C Nr. 31) |
| Zugstunden je Jahr | T × n × 365 / 1000 (Tausend Zug-h) |
| mittlere Reisegeschwindigkeit | L / T (inkl. Halte) |
| Liniengeschwindigkeit (Batterierechnung) | Linienlänge beider Richtungen / Summe der Mindestfahrzeiten ohne Halte |
| Halte h | Betriebsstellen mit Typ `stop` |
| Haltezeit gesamt | Summe (Abfahrt minus Ankunft) über Halte |
| Halte je Jahr | h × n × 365 |

## B6 Betriebskosten konkret

Zuordnung: sgv nach BVWP (Zuggruppe, nur Triebfahrzeug der BVWP-Ersatzformation, die genau aus Lok und Wagenpaket bestehen muss); spnv und spfv nach Standi (Linie, Standi-Ersatzformation). Der BVWP-Zweig für spfv ist vorhanden, aber durch die Parameterliste unerreichbar. Für sgv liefern battery und h2 kein Ergebnis.

Gemeinsame Externalitätenformeln je Fahrzeugmuster mit Energiemenge E:
- Energiekosten = Preis × E
- CO2 (t) = E × CO2-Faktor × 10^-3; CO2-Kosten = CO2 × 670 × 10^-3
- Schadstoffkosten = E × Schadstofffaktor × 10^-2
- Primärenergiekosten = E × Primärenergiefaktor × 0,9 × 0,9 × 15,5 × 10^-3 (Teil C Nr. 5)
Energieträgerwahl über `type_of_traction` des Fahrzeugmusters: Elektro und Batterie nutzen erneuerbaren Strom; Diesel, eFuel, H2 ihre Faktoren. Im BVWP-Zweig sind nur Elektro, Diesel und eFuel bekannt; andere Werte ergeben stille Nullkosten (Teil C Nr. 27).

BVWP Güterverkehr (`BvwpSgv`):
- Kapitaldienst = `debt_service` × Zugstunden je Jahr
- Instandhaltung = `maintenance_cost_km` × Zug-km je Jahr
- Energie elektrisch (kWh) = 1,08 × m^-0,62 × Zug-km × 1000, m = `brutto_weight` des Wagen-Eintrags der BVWP-Ersatzformation (t)
- Energie Diesel und eFuel (l) = 0,277 × m^-0,62 × Zug-km × 1000
- Gesamt = Kapitaldienst + Instandhaltung + Energie + CO2 + Schadstoffe + Primärenergie

BVWP Personenverkehr (`BvwpSpfv`, `BvwpSpnv`, nicht erreichbar): je Fahrzeug; Energie elektrisch = Zug-km × `energy_per_km` (spfv differenziert nach Kernnetz, ABS mit `energy_abs_per_km`, NBS mit `energy_nbs_per_km`) + Zugstunden × `energy_consumption_hour`; Energie Diesel und eFuel = `fuel_consumption_diesel_km` × Zug-km ohne Stundenterm.

Standi Personenverkehr (`StandiSpnv`), je Linie:
- Umläufe U bei 10 min Wendezeit (A6)
- Kapitaldienst = U × Summe `debt_service` der Fahrzeuge der Standi-Ersatzformation der ersten Zuggruppe der Linie
- zeitabhängige Instandhaltung = U × Summe (`maintenance_cost_duration_t` der Traktionsvariante × Masse des Basis-Fahrzeugmusters) / 1000, ebenfalls erste Zuggruppe (Teil C Nr. 7)
- laufleistungsabhängige Instandhaltung je Zuggruppe und Fahrzeug ihrer eigenen Ersatzformation = (1 + z_IH × L_oo / L) × `maintenance_cost_km` × Zug-km, z_IH = `additional_maintenance_cost_withou_overhead`
- Fahrenergie je Zuggruppe und Fahrzeug = (1 + z_E × L_oo / L) × `energy_per_km` der Traktionsvariante × Zug-km, z_E = `additional_energy_without_overhead`; für alle Traktionen dieselbe Formel, keine Dieselformel
- Halteenergie: I = 55,6 × (T minus Haltezeit) in Minuten, s = h minus 1; v_ref = 3,6 / (a × s) × (I minus Wurzel(I² minus 2 × a × s × L × 1000)), a = `energy_stop_a`; Rückfall 160 km/h nur bei negativer Wurzel (s = 0 oder a = 0 bricht ab, Teil C Nr. 15); Energie je Halt = `energy_stop_b` × v_ref² × Masse der Traktionsvariante × 10^-6; Halteenergie je Jahr = Energie je Halt × Halte je Jahr / 1000 (Verfahrensanleitung Standi S. 197)
- THG Fahrzeugherstellung = U × Summe `emission_production_vehicle_calc` × 670 / 1000, erste Zuggruppe
- Gesamt = alle Komponenten; Division durch Anzahl Zuggruppen der Linie, Speicherung je Zuggruppe als Integer in T€ (Teil C Nr. 30)

Barwert: Jahreswert über 2030 bis 2059 nach A5. Zuggruppen mit Routenlänge 0 brechen ab (`TraingroupNoLengthError`); Zuggruppen ohne Linie brechen im Standi-Zweig ab.

## B7 Infrastrukturkosten konkret

Rahmen (`BvwpCost`): Planung P = 0,18 × I; Barwert Planung über 5 Jahre ab 2020; Barwert Investition über 5 Jahre ab 2025; Barwert Instandhaltung M jährlich über 30 Jahre ab 2030; Kapitaldienst = Barwert Investition × 0,0428 (gespeichert, nicht in der Vergleichssumme); Vergleichswert Infrastruktur = Barwert Planung + Investition + Instandhaltung. Baudauer fix 5 Jahre; die BVWP-Tabelle (`duration_build_rail_bvwp.csv`) ist vorhanden, wird nicht aufgerufen.

Oberleitung: je Strecke mit `catenary == False` (bei `None` keine Kosten, `conductor_rail` nicht geprüft) Kosten je km = 200 + 200 + 5 + 737 × 30 / 60 = 773,5 T€, bei `zweigleisig` doppelt; I = Summe Länge × Satz; M = 0,014 × I. Die ausgewiesene Länge zählt zweigleisige Strecken doppelt.
Tankstellen (diesel, efuel, h2): Anzahl = aufgerundet(Gebietslänge / Abstand); I = Anzahl × Satz; M = 0,03 × I.
Ladestation I = 2.582, kleine Ladestation I = 1.200, jeweils M = 0,014 × I. Oberleitung im Bahnhof wie Oberleitung für die betreffende Strecke.

Batterie (`BvwpProjectBattery`), A9 mit folgenden Festlegungen:
- Je Fahrplanlinie einmal, in der Datenbankreihenfolge der Zuggruppen des Gebiets; je Startbetriebsstelle der erste gefundene Umlauf (Wendezeit 5 min, Teil C Nr. 24), davon die ersten zwei Züge; Umläufe mit nur einem Zug entfallen.
- Abschnittsgrenzen bei Wechsel von `catenary` und bei Halt ab 3 min oder mit `charging_station`; der Schnitt erfolgt vor dem Anhängen der Streckenstrecke mit dem Halt (Teil C Nr. 25); nur Strecken mit genau einem relevanten Halt werden geschnitten. Fahrzeit je Abschnitt = Länge / mittlere Reisegeschwindigkeit (inkl. Halte). Standzeit am Ende: bis Abfahrt des Folgezugs im Umlauf, sonst 1 h.
- Lademöglichkeit an einem Bahnhof: `charging_station` oder Oberleitung an einer Strecke des Bahnhofs. Kleine Ladestationen zählen nicht (Teil C Nr. 26).
- Kapazität C = Summe `battery_capacity` der Fahrzeuge des ersten Zuges. Fahrenergie im Abschnitt ohne Oberleitung (1 + z_E × L_oo / L) × `energy_per_km` × Länge; Halteenergie nach B6 je zugeordnetem Halt. Zuordnung der Halte: über die Strecken des Bahnhofs; liegt ein Halt an mehreren Abschnitten, gewinnt der Oberleitungsabschnitt mit kleinster Nummer, ohne Oberleitungsabschnitt wird der Halt nicht gezählt; Halte ohne Bahnhof über Fahrzeitanteil (Teil C Nr. 23).
- Bilanz: unter Oberleitung Laden 1.200 kW × Fahrzeit; an Ladehalten (Teil C Nr. 2); am Zugende (Teil C Nr. 3). Mehrfolgeproblem, wenn C / Defizit kleiner als ganzzahlig(Anzahl Elemente des ersten Umlaufs der Linie / 2).
- Einzelfolgeproblem: bei Problem auf der Rückfahrt Ladepunkt am Endbahnhof der Hinfahrt (Oberleitung im Bahnhof, wenn dort Oberleitung an anderer Strecke, sonst Ladestation), Ladezuwachs = Standzeit × 1.200 kW; verbleibendes Problem (Hin- oder Rückfahrt): Oberleitung auf Strecken vor der Problemstelle, Kandidaten auch bereits elektrifizierte Strecken (Teil C Nr. 29). Restproblem wird nur protokolliert (Teil C Nr. 12).
- Mehrfolgeproblem: Ladepunkte an Endbahnhöfen (Teil C Nr. 20), Ladepunkte an Zwischenhalten ab 3 min, Oberleitung auf oberleitungsfreien Strecken der Hinfahrt.
- Auswahl zusätzlicher Strecken: Kandidaten nach Anzahl befahrender Zuggruppen absteigend, Länge aufsteigend; bevorzugt mit Lademöglichkeit an einem Bahnhof (nur letzter Bahnhof wirksam, Teil C Nr. 21) oder Oberleitungsnachbar; je Strecke Ladezuwachs = 1.200 kW × Länge / Liniengeschwindigkeit (ohne Halte), gedeckelt auf C; Nachbarstrecken der Route werden nachgezogen.
- Alle Maßnahmen gelten sofort im gemeinsamen Zustand für folgende Linien, Traktionen und Gebiete (Teil C Nr. 19). Abschluss: kleine Ladestationen an Start- und Endbetriebsstellen ohne Lademöglichkeit (abschaltbar).

Optimierte Elektrifizierung (`BvwpProjectOptimisedElectrification`), A10 mit Basisteiloption Oberleitung und Alternative Batterie (ohne kleine Ladestationen), Teilgebiete aufsteigend nach Zug-km je Tag, sgv-Teilgebiete immer Oberleitung, Abschluss kleine Ladestationen. Die Batteriealternative eines Teilgebiets simuliert die vollständigen Linien seiner Zuggruppen; ihre Maßnahmen können außerhalb des Teilgebiets liegen und bleiben auch bei Verwerfen im Zustand (Teil C Nr. 28). Zuordnung Zuggruppe zu Traktion: einmal auf Batterie gesetzt, nie zurück (Teil C Nr. 28). Betriebskosten je Zuggruppe werden aus dem Cache genommen, wenn vorhanden (Teil C Nr. 19). Ergebnis: Traktion je Zuggruppe (`TractionOptimisedElectrification`), Anteile Oberleitung/Batterie nach km und Infrastrukturkosten.

## B8 Entscheidung und Kennzahlen konkret

Je Gebiet und Traktion: Vergleichssumme = Vergleichswert Infrastruktur (der Gebietsmaßnahme, Zuordnung über Flags, letzter Treffer gewinnt) + Barwert Betriebskosten (Summe der Integer-Jahreswerte aller Zuggruppen). Minimum über Traktionen mit beiden Werten; für sgv-Gebiete werden battery und h2 auch aus CO2 entfernt; ohne jede Traktion „no calculated cost“. Gespeichert je Gebiet als Integer: Gesamt-, Betriebs- und Infrastrukturkosten je Traktion, kosteneffiziente Traktion, Flags sgv/spnv/spfv; Teilgebiete nur Oberleitung und (ohne sgv) Batterie.
Je Szenario je kosteneffizienter Traktion: Anzahl Gebiete, Streckenkilometer, Zug-km je Tag, Infrastruktur- und Betriebskosten; Zerlegung optimierter Gebiete (`oe_to_battery`, `oe_to_electrification`); Zug-km je Verkehrsart und Traktion; CO2 neu gegen CO2 Diesel (Teil C Nr. 8).

## B9 Störfall konkret

Sperrmaßnahme zwischen zwei Betriebsstellen, Umrouten betroffener Zuggruppen (sgv, spfv) mit gesperrten Betriebsstellen und Zwangsfolgen aus `blocked_scenarios/s-<id>.json`. Betroffene Gebiete im Störfallszenario erhalten die umgeleiteten Güterzuggruppen dauerhaft (Teil C Nr. 32); Oberleitung und optimierte Elektrifizierung werden neu gerechnet, Zugkosten der umgeleiteten Züge für electrification, diesel, efuel (nur BVWP-Sätze).
Kosten Umleitungsfall = Kosten der betroffenen Gebiete (gewählte Traktion) minus Barwert der regulären BVWP-Betriebskosten der umgeleiteten Züge für Traktion electrification (unabhängig von der gewählten Traktion) plus Barwert der Zugkosten im Störfall. Zugkosten im Störfall je Tag = reguläre Jahreskosten / 365 + Wagenkosten (Wagenzahl × 1,06 € × Einsatzstunden bei 60 km/h) + Personal (Stunden × 57 €) + Bereitstellung (23 € je Wagen), gewichtet mit 4,63 %.
Kosten Lkw-Fall = Kosten der Gebiete im Referenzszenario + Barwert der Lkw-Kosten: Lkw-Zahl = Züge × aufgerundet(Nutzlast Zug / 25 t), Nutzlast Zug = Wagenzahl × 50 t, Wagenzahl = min(abgerundet(Länge / 19,7 m), aufgerundet(Bruttomasse / (20 + 50) t)), Straßenentfernung über Openrouteservice mit CSV-Cache, Kostensatz 87,24 €/100 km, gewichtet mit 4,63 %.

## B10 Laufsteuerung und Zustand im Altcode

Diese Eigenschaften bestimmen das Ergebnis mit, sind aber keine Methodik. Sie werden in Teil C als Verdachtsfälle geführt und in der Neuentwicklung durch A3 ersetzt.
- Eine `Version`-Instanz für den gesamten Lauf; Maßnahmen aus Batterie- und Optimierungsrechnung bleiben für folgende Traktionen und Gebiete wirksam.
- Betriebskosten (`TimetableTrainCost`) und Gebietsmaßnahmen (`ProjectContent`) werden während der Rechnung in die Datenbank geschrieben und bei Wiederholung ungeprüft wiederverwendet; Lookup der Maßnahme über Namensmuster; bei Mehrfachtreffern werden alle gelöscht.
- Routen je Szenario persistent, Neuberechnung nur über Flags.
- Nebenwirkungen auf Dateien: Pfad-JSONs beim Routing, `catenary_too_long.json`.
- Alle Kosten- und Emissionsspalten sind Integer (T€ bzw. t).
- Reihenfolgen (Zuggruppen eines Gebiets, Gebiete eines Szenarios) kommen aus der Datenbank.

---

# Teil C: Mehrdeutigkeiten und Verdachtsfälle

Priorität A: beeinflusst Ergebnisse wahrscheinlich erheblich. B: beeinflusst Ergebnisse begrenzt oder nur Nebenwerte. C: Robustheit, Datenqualität.

Entscheidungsstand 2026-11-01 (Teil F): Die Neuentwicklung ist ein Neubau ohne Nachbildung des Altcodes. Die Punkte 1, 2, 3, 4, 5, 8, 20, 21, 22, 23, 24, 25 und 30 wurden als Rechenfehler eingestuft und werden korrigiert (EK-2026-072). Die Punkte 6, 9, 10, 11, 12, 13, 15, 26 und 28 sind durch eigene Karten entschieden (EK-2026-062 bis 071). Die Punkte 19, 27, 29, 31 bis 37 entfallen durch die Architektur (Zustände als Werte, Validierung, keine Datenbank in der Rechnung). Die Punkte 14, 16, 17 und 18 bleiben als dokumentierte Annahmen und Parameter. Der Abgleich einzelner Formeln mit dem Thesis-Text (vor allem 5, 9, 17) steht weiterhin aus, ändert aber am Vorgehen nichts mehr.

Rechenkern und Formeln
1. **(A) Elektrifizierung wirkt nicht im Zustand.** `Version._add_electrification` setzt `catenary = False` und schreibt einen Boolean in die Textspalte `electrified`; alle Kostenformeln prüfen `catenary`. Szenario-Projekte mit `elektrification = True` und alle im Lauf erzeugten Elektrifizierungsmaßnahmen bleiben wirkungslos; `remove_electrification_for_rw_lines` ist damit ebenfalls wirkungslos, und bereits „elektrifizierte“ Strecken können im selben Lauf erneut gewählt und bekostet werden. (`prosd/manage_db/version.py:195` bis `:201`)
2. **(A) Laden an Zwischenhalten ohne Wirkung.** `battery_status = min(battery_status, charge)`; gemeint war vermutlich `min(battery_capacity, charge)`. (`cost.py:721`)
3. **(A) Standzeit am Zugende falsch.** `stand_time = arrival_last_ocp minus departure_next_segment` ist negativ, `.seconds` liefert den Tagesrest; Ladung mit `/ 60` statt `/ 3600`; für den letzten Zug wird die Abfahrt desselben Zuges statt der nächsten Hinfahrt genommen; `charge_while_stop` nutzt dieselbe negative Standzeit. (`cost.py:732` bis `:738`, `:1059`)
4. **(B) Investitionsbarwert nur vom letzten Teilprojekt.** `=` statt `+=`; Gesamtkosten nicht betroffen. (`cost.py:333`, `:1247`, `:1254`)
5. **(B) Primärenergiefaktor quadriert.** 0,9 × 0,9 statt 0,9. (`use.py:115`, `:124`, `:133`, `:487`, `:496`, `:505`, `:514`)
6. **(B) Batteriezuschlag je Abschnitt mit Linienanteil** L_oo / L, obwohl der Abschnitt vollständig ohne Oberleitung ist. (`cost.py:581`)
7. **(B) Zeitabhängige Instandhaltung mit Masse des Basis-Fahrzeugmusters** statt der Traktionsvariante; Halteenergie nutzt dagegen die Variante. (`use.py:459`, `:544`)
8. **(B) CO2 Diesel nur für optimierte Gebiete** aufsummiert. (`models.py:3295` bis `:3299`)
9. **(B) Kapitaldienst Infrastruktur ohne Verwendung.** Vergleichssumme enthält den vollen Investitionsbarwert statt der Annuität. Absicht klären; in der Neuentwicklung Konfiguration der Vergleichssumme.
10. **(B) Baudauer fix statt kostenabhängig.** Tabelle vorhanden, Funktionen `duration_building` und `_duration_year` nie aufgerufen. (`cost.py:80` bis `:110`)
11. **(B) spfv immer Standi.** bvwp-Zweig für Fernverkehr unerreichbar. Festlegen, dann als Methodenzuordnung konfigurieren.
12. **(A) Kein Durchführbarkeitsstatus.** Bleibt nach allen Platzierungsregeln ein Problem, wird es nur geloggt; das Gebiet erhält Batteriekosten aus den erzeugten Maßnahmen. (`cost.py:839` bis `:843`)
13. **(B) Reihenfolgeabhängigkeit der Linien** in der Batterierechnung; Reihenfolge ist die Datenbankreihenfolge von `area.traingroups`, nicht sortiert. (`cost.py:288`)
14. **(B) Teilgebietsreihenfolge und Greedy-Entscheidung** ohne zweiten Durchlauf. Als Strategie dokumentieren (A10).
15. **(C) Halteenergie mit Rückfallwert 160 km/h** nur bei negativer Wurzel; s = 0 (eine Haltestelle) oder `energy_stop_a` 0 oder leer bricht unbehandelt ab. (`use.py:536` bis `:539`, `cost.py:611` bis `:615`)
16. **(B) Tageswerte als Jahreswerte** mit Faktor 365; alle Zeitgrößen vom ersten Zug. Hochrechnungsfaktor als Parameter.
17. **(B) Energieformel Güterverkehr** (1,08 und 0,277, Exponent minus 0,62, Faktor 1000) ohne Quellenangabe; Kommentare deuten auf kWh und l, während Standi-Energien in Tausend kWh vorliegen; Einheitenkonsistenz ohne Thesis nicht verifizierbar. (`use.py:302`, `:307`)
18. **(B) Ersatzformationen.** Umlaufzahl, Kapitaldienst, zeitabhängige Instandhaltung, THG Herstellung und Batteriekapazität nur aus der Formation der ersten Zuggruppe bzw. des ersten Zuges; Betriebsleistung aus der Originalformation. (`use.py:378`, `:439`, `:457`, `:469`; `cost.py:1138` bis `:1149`)

Zustand, Cache, Reihenfolge
19. **(A) Gemeinsamer Zustand und Datenbank-Cache.** Eine `Version` für alle Gebiete und Traktionen; Maßnahmen aus Batterie und Optimierung (auch verworfene Teilgebietsalternativen) bleiben für folgende Traktionen desselben Gebiets und alle folgenden Gebiete wirksam. Betriebskosten werden je (Zuggruppe, Szenario, Traktion, Methode) ungeprüft aus der Datenbank wiederverwendet, unabhängig vom Zustand; `traingroup_to_traction` wird in `calc_operating_cost` nicht ausgewertet; Maßnahmen-Lookup über Namensmuster. Ergebnisse hängen von Gebiets- und Traktionsreihenfolge und vom Datenbankzustand vor dem Lauf ab. (`models.py:3176` bis `:3192`, `:3941` bis `:3998`, `:4016` bis `:4035`; `cost.py:357`, `:1266` bis `:1269`, `:1338` bis `:1342`)

Reichweitenmodell
20. **(A) Ladepunkt an Endbahnhöfen geht verloren.** In `_create_infrastructure_endpoints` wird bei gedecktem Bedarf zurückgegeben, bevor die gerade erzeugte Maßnahme angehängt wird; sie fehlt in Kosten und Zustand. (`cost.py:891` bis `:896`)
21. **(A) Bahnhofsprüfung überschrieben.** In `_electrify_additional_railwaylines` wird `add_line` je Bahnhof überschrieben; nur der letzte Bahnhof der Strecke zählt. (`cost.py:965` bis `:967`)
22. **(B) Füllstand statt Zuwachs.** `_create_infrastructure_point` gibt `min(C, Ladung + Füllstand)` zurück; Aufrufer addieren erneut den Füllstand oder ziehen den Füllstand als Zuwachs vom Bedarf ab. (`cost.py:914`, `:798`, `:892`, `:929`)
23. **(B) Halte an Abschnittsgrenzen.** Zuordnung zum Oberleitungsabschnitt mit kleinster Nummer; liegen beide Nachbarabschnitte ohne Oberleitung, wird der Halt nicht gezählt; Halte ohne Bahnhof über Fahrzeitanteil, dabei wird eine km-Länge erneut durch 1000 geteilt, der Anteil ist nahezu 0 und die Zuordnung greift praktisch nie. (`cost.py:641` bis `:653`, `:677`, `:680`)
24. **(B) Wendezeit 5 statt 10 Minuten** bei der Umlaufauswahl der Batterierechnung (`get_train_cycles()` ohne Argument), während Folgezugsuche und Umlaufzahl 10 Minuten nutzen. (`models.py:2709`, `:2738`; `cost.py:298`, `:452` bis `:462`, `:752` bis `:755`)
25. **(B) Abschnittsgrenze um eine Strecke verschoben.** Der Schnitt erfolgt vor dem Anhängen der Strecke mit dem Halt; die Ankunftsstrecke landet im Abschnitt nach dem Halt. Strecken mit zwei relevanten Halten werden nicht geschnitten. `stop_duration.seconds` ignoriert Tageswechsel. (`cost.py:426`, `:433`, `:442` bis `:447`)
26. **(B) Kleine Ladestationen zählen nicht als Lademöglichkeit.** Weder in der Bilanz noch bei der Prüfung vorhandener Versorgung; ein Bahnhof mit kleiner Ladestation aus einem früheren Gebiet erhält wieder eine. (`cost.py:215` bis `:229`, `:431`, `:477` bis `:479`)
27. **(C) Stille Nullkosten bei unbekannter Traktion** im BVWP-Zweig (`Batterie`, `H2` fallen in den `else`-Zweig). (`use.py:136` bis `:142`)
28. **(A) Teilgebietsalternative verändert Zustand und Zuordnung dauerhaft.** Die Batteriealternative eines Teilgebiets simuliert die ganzen Linien, legt Maßnahmen auch außerhalb des Teilgebiets an und schreibt sie in den Zustand, auch wenn Oberleitung gewählt wird; `traingroup_to_traction` wird nur auf Batterie gesetzt, nie zurück; da Betriebskosten linienweit gecacht sind, geht dieselbe Betriebskostendifferenz in jede Teilgebietsentscheidung ein, die die Zuggruppe enthält. (`cost.py:860` bis `:863`, `:1338`, `:1343` bis `:1344`)
29. **(B) Kandidaten für Zusatz-Oberleitung im Einzelfolgefall** umfassen bereits elektrifizierte Strecken; sie kosten 0, ihr Ladezuwachs wird aber angerechnet. (`cost.py:813` bis `:816`)

Daten, Einheiten, Robustheit
30. **(B) Integer-Speicherung.** Jahreswerte je Zuggruppe und alle Gebiets- und Szenariokosten sowie CO2 als Integer (T€, t), abgeschnitten vor Summierung und Diskontierung. (`models.py:1867` bis `:1876`, `:3401` bis `:3420`, `:2955` bis `:3006`)
31. **(C) Reisezeit über Mitternacht.** Zeiten werden mit `date.today()` kombiniert; Fahrten über Tageswechsel liefern negative Reisezeit, `travel_speed_average` nimmt `.seconds` davon. (`models.py:2134` bis `:2139`, `:2264`)
32. **(B) Störfall verändert Gebiete dauerhaft.** Umgeleitete Zuggruppen werden an `area.traingroups` gehängt und committet; die Rücksetzung greift nur für die Gebiete der letzten Zuggruppe und ohne Commit. (`block_rw_lines.py:159` bis `:165`, `:251` bis `:252`)
33. **(C) Ungebundene Variablen und Division durch null.** `sequence_in_rw_lines` nach `IndexError` (`cost.py:1000` bis `:1005`); `path`, `first_ocp`, `last_ocp` im Routing (`routing.py:50` bis `:61`, `:88` bis `:98`); `travel_speed_average` bei Reisezeit 0 (`models.py:2264`); `average_speed` bei Mindestfahrzeit 0 (`cost.py:985`); leere Kandidatenliste (`cost.py:951`); `maintenance_cost_running` durch Zug-km (`use.py:450`).
34. **(C) Datenfilter still.** Gebietsbildung schließt Strecken mit `catenary`/`conductor_rail` `None` aus; Oberleitungskosten übergehen `None`; Routing gibt Strecken ohne gültige Länge Gewicht 0; Zuggruppen ohne Linie werden in der Batterierechnung übersprungen. (`version.py:167` bis `:171`; `cost.py:151`, `:304` bis `:305`; `routing.py:281` bis `:294`)
35. **(C) Barwert der Komponenten mit `cost_is_sum=True`.** In `calc_barwert` werden Energie, CO2, Schadstoffe, Primärenergie und THG durch die Dauer geteilt, die übrigen nicht; in der Thesis-Pipeline unbenutzt, Falle für Golden-Master. (`use.py:200` bis `:209`)
36. **(C) Unbenutzte Parameter und Reste.** `COST_OVERHEAD_ONE_TRACK`/`TWO_TRACKS`, `ENERGY_*_ELECTRO_CASUAL`, `ProjectGroup.query.get(4)` (`cost.py:886`), `bvwp_project.py` mit Importen nicht existierender Klassen.
37. **(C) Szenariospalten ignoriert.** `MasterScenario.start_year` und `operation_duration` werden nicht gelesen; es gelten die Parameter. (`models.py:2952` bis `:2953`)

---

# Teil D: Zielarchitektur und Umsetzungsplan

## D1 Grundsätze

- **Kern ohne Anwendungswissen.** Der Kern kennt Netz, Zustand, Verkehrsleistung, Bündel, Technologieoption, Maßnahme, Kostenkomponente, Gebiet, Parametersatz. Er kennt weder „Oberleitung“ noch „BVWP“ noch Euro-Beträge. Alles Anwendungsspezifische kommt über Plugins und Konfiguration.
- **Keine Zahl im Code.** Jeder Kostensatz, Faktor, Zeitraum, Schwellwert, Rückfallwert und jede Formelkonstante (auch 55,6, 3,6, 365, Skalierungen) liegt im Parametersatz mit Einheit, Preisjahr, Quelle und Gültigkeit. Code referenziert Parameter über Namen und schlägt fehl, wenn ein Parameter fehlt.
- **Typisierte Größen.** Zahlen tragen Einheiten als eigene leichte Typen (NewType je Einheit, Umrechnung nur über benannte Funktionen, statische Prüfung mit mypy; EK-2026-076). Der Parameterlader prüft die Einheitenangabe jeder Zahl. `pint` wird höchstens in Tests zur Gegenprobe eingesetzt. Einheitenfehler wie in Teil C Nr. 3, 23 scheitern damit vor dem Rechnen.
- **Rechnen im Speicher, ohne Nebenwirkungen.** Zustand ist unveränderlich; Änderungen erzeugen neue Zustände. Keine Datenbank, keine Dateien in der Rechenlogik. Laden und Schreiben sind Adapter.
- **Registrierte, austauschbare Formeln.** Energie-, Kosten-, Platzierungs-, Cluster-, Umlauf-, Routing-, Phasen-, Verteilungs- und Entscheidungsfunktionen sind benannte Plugins, die per Konfiguration ausgewählt werden.
- **Nachvollziehbarkeit.** Jeder Lauf hat eine Lauf-ID und schreibt ein Manifest (Parametersatz mit Hash, Szenariodefinition, Korrekturlisten mit Hash, Plugin-Auswahl, Codeversion, Datenstände, Validierungsbericht); Zwischenergebnisse je Stufe werden gespeichert; mehrere Läufe existieren nebeneinander.
- **Neubau, kein Nachbau.** Der Altcode wird nicht nachgebildet (EK-2026-060). Es gibt keinen Parametersatz `altcode-kompatibel` und keinen Golden-Master gegen alte Ergebnisse. Richtig ist, was Teil A, Teil F und die Handrechnungstests festlegen. Ein Plausibilitätsvergleich mit den veröffentlichten Thesis-Ergebnissen ist optional und dient nur der Einordnung.
- **Eigenes Repo und eigenes Frontend.** Das Paket `traction_eval` entsteht in einem eigenen Repo (EK-2026-059). Ergebnisse werden in einem eigenen Schema mit Lauf-ID gehalten und über ein eigenständiges Frontend dargestellt (EK-2026-075); es gibt keinen Writer in die prosd-Tabellen. `pros` ist nur noch eine mögliche Datenquelle für den Loader.

## D2 Paketstruktur

```
traction_eval/                      # eigenständiges Paket mit pyproject.toml
  core/
    model/        Segment, Node, Place, Network, Service, ServiceBundle,
                  VehicleType, VehicleConfig, Scenario, Area, SubArea, Measure, Result
    state/        NetworkState (Netz + Overlays), apply(measures) -> NetworkState, hash
    params/       ParameterSet, Laden aus YAML/TOML, Vererbung, Overrides, Zeitreihen,
                  Validierung (Einheit, Typ, Pflichtfelder), Hash, Provenienz
    units/        Quantity-Typen und Einheitenprüfung
    finance/      present_value, phase_schedule, annuity, residual_value, price_index
    registry/     Plugin-Registry und Protokolle (D3)
    pipeline/     Stufen, Orchestrierung, Caching nach Eingabe-Hash, Parallelisierung je Gebiet, Manifest
    validation/   Prüfregeln, Schwellwerte, Bericht
    results/      Ergebnisschema mit Komponenten und Maßnahmenlisten, Serialisierung (JSON, Parquet),
                  Vergleich zweier Läufe
  methods/                          # generische Methoden, anwendungsneutral
    routing/      shortest_path mit austauschbaren Gewichtsfunktionen, Korrekturlisten
    clustering/   connected_components(predicate, relations, transitive), identical_service_set
    energy/       per_km, per_hour, stop_energy_reference_speed, mass_power_law
    cost/         capital_service, maintenance_km, maintenance_time, externality, production_emissions
    cycles/       Umlaufbildung, Fahrtenfolge-Selektoren
    allocation/   Verteilung Bündel -> Leistung, Zuordnung Leistung -> Teiloption
    range/        Abschnittsbildung, Energiebilanz, Problemdiagnose, Platzierungsregeln
    optimise/     greedy_subarea, Schnittstelle für weitere Strategien
    decision/     min_total_cost, mit Nebenbedingungen, robuste Wahl, Break-even
    disruption/   Störfallbewertung
  applications/
    masterarbeit/
      config/     parameters/masterarbeit-2026.yaml, scenario/*.yaml, technologies.yaml,
                  methods.yaml, corrections/*.json
      plugins/    Technologieoptionen, Kostenkomponenten BVWP und Standi, Maßnahmentypen,
                  Kategorie-Zuordnung, Ersatzformationsregel
      adapters/   Loader für Netz (nach dem Netzmodell des raildashboard), railML des dritten
                  Zielfahrplans, Fahrzeugkennwerte; optional Loader aus der prosd-Datenbank
      reports/    Kennzahlen, Karten, Berichte (Ersatz für scripts/masterarbeit/auswertung)
  results/        Ergebnisschema mit Lauf-ID (Datei und Datenbank), Abfrage-API für das Frontend
  cli/            run, resume, compare, export, validate-params, validate-data
frontend/         eigenständiges Frontend für Szenarien, Gebiete, Optionen, Maßnahmen und Karten
tests/
  unit/           Formeln mit Handrechnung, Finanzmodul, Parametersystem, Einheiten
  properties/     Invarianten Gebietsbildung, Energiebilanz, Zustandsunveränderlichkeit
  fixtures/       kleine Netz- und Fahrplanausschnitte aus den neuen Eingangsdaten
  example/        durchgerechnetes Minimalbeispiel (zwei Strecken, eine Linie, zwei Optionen)
```

Routing: Das Routing-Modul folgt dem Ansatz des raildashboard (Routing über das Schienennetz mit Betriebsstellensuche, EK-2026-074). Der Abgleich mit dem Netzmodell und dem Routing-Code des raildashboard-Repos ist der erste Schritt der Umsetzung, damit Netzschema, Betriebsstellen und Streckenattribute (einschließlich Streckengeschwindigkeit) gemeinsam genutzt werden können.

## D3 Plugin-Schnittstellen

Protokolle (Signaturen skizziert; Einheiten über typisierte Mengen):

```python
class RouteWeight(Protocol):
    name: str
    def weight(self, segment: Segment, state: NetworkState, params: ParameterSet) -> float | None: ...

class CycleBuilder(Protocol):
    name: str
    def cycles(self, bundle: ServiceBundle, params: ParameterSet) -> list[Cycle]: ...

class TripSequenceSelector(Protocol):     # welche Fahrten die Reichweitenbilanz betrachtet
    name: str
    def select(self, bundle: ServiceBundle, cycles: list[Cycle], params: ParameterSet) -> list[TripSequence]: ...

class EnergyModel(Protocol):
    name: str
    def energy(self, ctx: EnergyContext, vehicle: VehicleType, params: ParameterSet) -> Quantity: ...
    # EnergyContext: Leistung oder Abschnitt, Länge, Zeit, Halte, Attributanteile, Zustand

class CostComponent(Protocol):
    name: str
    applies_to: set[str]                  # Kategorien
    level: Literal["service", "bundle"]
    def annual_cost(self, subject: Service | ServiceBundle, option: TechnologyOption,
                    state: NetworkState, fleet: FleetDemand, params: ParameterSet) -> CostBreakdown: ...

class BundleAllocation(Protocol):         # Bündelkosten -> Leistungen
    name: str
    def allocate(self, bundle: ServiceBundle, cost: CostBreakdown) -> dict[ServiceId, CostBreakdown]: ...

class PhaseModel(Protocol):
    name: str
    def schedule(self, measure: Measure, params: ParameterSet) -> PhaseSchedule: ...

class PriceIndex(Protocol):
    name: str
    def to_base_year(self, value: Money, price_year: int, base_year: int) -> Money: ...

class ClusteringStrategy(Protocol):
    name: str
    def areas(self, state: NetworkState, services: list[Service], params: ParameterSet) -> list[Area]: ...
    def sub_areas(self, area: Area, services: list[Service]) -> list[SubArea]: ...

class MeasureGenerator(Protocol):
    name: str
    def generate(self, area: Area | SubArea, state: NetworkState, bundles: list[ServiceBundle],
                 vehicles: VehicleCatalog, params: ParameterSet) -> MeasurePlan: ...
    # MeasurePlan: measures, feasibility (ok | infeasible mit Begründung), resulting_state,
    #              service_to_suboption, physical_metrics

class RangeDiagnoser(Protocol):
    name: str
    def diagnose(self, sequence: TripSequence, state: NetworkState, vehicles: VehicleConfig,
                 params: ParameterSet) -> RangeDiagnosis: ...

class PlacementRule(Protocol):
    name: str
    def applies(self, diagnosis: RangeDiagnosis) -> bool: ...          # Vorbedingung
    def place(self, diagnosis: RangeDiagnosis, state: NetworkState,
              params: ParameterSet) -> tuple[list[Measure], Quantity]: ...   # Maßnahmen, Ladezuwachs

class SubOptionAssignment(Protocol):      # Leistung in mehreren Teilgebieten
    name: str
    def assign(self, choices: dict[SubAreaId, SubOption], service: Service) -> SubOption: ...

class DecisionRule(Protocol):
    name: str
    def choose(self, results: dict[OptionKey, OptionResult], infeasible_policy: InfeasiblePolicy,
               params: ParameterSet) -> Decision: ...

class Aggregator(Protocol):
    name: str
    def aggregate(self, decisions: list[AreaDecision], params: ParameterSet) -> ScenarioMetrics: ...

class DisruptionModel(Protocol):
    name: str
    def evaluate(self, case: DisruptionCase, reference: ScenarioResult, params: ParameterSet) -> DisruptionResult: ...

class TechnologyOption(Protocol):
    key: str
    energy_carrier: str
    vehicle_variant: str
    measure_generator: MeasureGenerator
    excluded_categories_area: set[str]       # Option nicht, wenn Kategorie im Gebiet
    forced_suboption_by_category: dict[str, SubOption]   # z. B. sgv -> Basisteiloption
```

Alle Plugins werden über einen Registry-Eintrag mit Namen angemeldet; Konfigurationsdateien referenzieren Namen. Die Anwendung registriert ihre Plugins beim Import, der Kern bleibt unverändert.

## D4 Parametersystem

Parameter liegen in YAML (oder TOML) mit Metadaten je Wert. Parametersätze erben voneinander und überschreiben Werte; Sensitivitätsläufe sind Overrides auf der Kommandozeile oder in der Szenariodatei. Werte dürfen Zeitreihen sein (`{series: {2030: 0.14, 2040: 0.12}}`, Interpolation konfigurierbar).

```yaml
# applications/masterarbeit/config/parameters/masterarbeit-2023.yaml
meta:
  name: masterarbeit-2023
  price_year: 2016
  currency: EUR
finance:
  discount_rate:        {value: 0.017, unit: "1/a", source: ""}
  base_year:            {value: 2016,  unit: "a"}
  phases:
    model: fixed_durations           # Alternative: bvwp_cost_dependent_build
    planning: {start: 2020, duration: 5}
    build:    {start: 2025, duration: 5}
    operate:  {start: 2030, duration: 30}
  annuity_factor:       {value: 0.0428, unit: "1/a"}
  residual_value:       {model: linear_lifetime_share}
  comparison_sum:       [planning_pv, investment_pv, maintenance_pv, operating_pv]
timetable:
  days_per_year:        {value: 365}
  turnaround:           {value: 10, unit: min}
  fleet_reserve_factor: {value: 1.0}
infrastructure:
  catenary:
    cost_per_km:        {value: 737,  unit: "kEUR/km", source: ""}
    lifetime:           {value: 60,   unit: "a"}
    power_supply_per_km:{value: 200,  unit: "kEUR/km"}
    civil_per_km:       {value: 200,  unit: "kEUR/km"}
    land_per_km:        {value: 5,    unit: "kEUR/km"}
    maintenance_share:  {value: 0.014,unit: "1/a"}
    track_factor:       {default: 1, by_value: {zweigleisig: 2}}
    station_catenary_warn_length: {value: 1000, unit: m}
  charging_station:       {investment: {value: 2582, unit: kEUR}, maintenance_share: {value: 0.014}, counts_as_supply: true}
  small_charging_station: {investment: {value: 1200, unit: kEUR}, maintenance_share: {value: 0.014}, counts_as_supply: false}
  filling_station:
    h2:     {investment: {value: 6000, unit: kEUR}, spacing: {value: 60, unit: km}, maintenance_share: {value: 0.03}}
    diesel: {investment: {value: 1000, unit: kEUR}, spacing: {value: 40, unit: km}, maintenance_share: {value: 0.03}}
    efuel:  {investment: {value: 1000, unit: kEUR}, spacing: {value: 40, unit: km}, maintenance_share: {value: 0.03}}
  planning_share:       {value: 0.18}
energy_carriers:
  electricity_renewable: {price: {value: 0.14, unit: "EUR/kWh", price_year: 2016}, co2: {value: 21, unit: "g/kWh"}, pollutant_factor: 0.05, primary_energy_factor: 4.5}
  electricity_mix:       {price: {value: 0.12, unit: "EUR/kWh"}, co2: {value: 414, unit: "g/kWh"}, pollutant_factor: 0.96, primary_energy_factor: 6, note: "definiert, nicht verwendet"}
  diesel:                {price: {value: 0.75, unit: "EUR/l"},   co2: {value: 2774, unit: "g/l"},  pollutant_factor: 6.57, primary_energy_factor: 38.9}
  efuel:                 {price: {value: 2.50, unit: "EUR/l"},   co2: {value: 370, unit: "g/l"},   pollutant_factor: 6.57, primary_energy_factor: 78.2}
  h2:                    {price: {value: 5.00, unit: "EUR/kg"},  co2: {value: 938, unit: "g/kg"},  pollutant_factor: 2.18, primary_energy_factor: 198.7}
externalities:
  co2_cost:              {value: 670, unit: "EUR/t"}
  pollutant_scale:       {value: 1.0e-2}
  primary_energy_points: {value: 0.9}
  primary_energy_points_exponent: {value: 1, note: "Altcode 2, Teil C Nr. 5"}
  points_to_money:       {value: 15.5, unit: EUR}
standi:
  reference_speed_constants: {k1: 55.6, k2: 3.6}
  stop_energy_scale:     {value: 1.0e-6}
  reference_speed_fallback: {mode: fixed, value: {value: 160, unit: "km/h"}}   # Alternative: vehicle_vmax
  time_maintenance_mass_source: variant        # Altcode: base
  bundle_vehicle_source: all_services          # Altcode: first_service
  bundle_allocation: equal_share
bvwp:
  freight_energy:
    electric: {a: 1.08,  exponent: -0.62, scale: 1000, unit: "kWh/train-km", note: "Einheit offen, Teil C Nr. 17"}
    diesel:   {a: 0.277, exponent: -0.62, scale: 1000, unit: "l/train-km"}
range_model:
  charge_power:          {value: 1200, unit: kW}
  usable_capacity_share: {value: 1.0}
  min_dwell_for_charging:{value: 3, unit: min}
  default_terminal_stand_time: {value: 1, unit: h}
  trip_sequence: first_two_trips_per_start_place    # Alternative: full_cycle
  cycle_turnaround_source: timetable.turnaround     # Altcode: 5 min
  bundle_order: by_running_km_desc                  # Altcode: database_order
  cycles_per_multi_check_divisor: {value: 2}
  overelectrification_warn: {value: -100, unit: kWh}
  section_cut: before_stop_segment_end              # Altcode: after
  stop_assignment_fallback: travel_time_share
  placement_rules_single_trip:
    - {rule: terminal_charge_point, when: problem_on_return_trip}
    - {rule: electrify_before_problem}
  placement_rules_multi_trip:
    - {rule: terminal_charge_point}
    - {rule: intermediate_charge_point}
    - {rule: electrify_most_used}
  candidate_filter_single_trip: unsupplied_only     # Altcode: all
routing:
  weight: length_prefer_supply
  supply_factor:         {value: 0.95}
  min_turn_angle:        {value: 60, unit: deg}
  corrections: corrections/blacklist_route_ignore_ocp.json
disruption:
  truck_cost_per_100km: {energy: 17.5, personnel: 25.18, capital: 22, maintenance: 12.86, co2: 1.8, primary_energy: 7.8, emission: 0.1, unit: "EUR/100km"}
  truck_payload:        {value: 25, unit: t}
  wagon: {length: {value: 19.7, unit: m}, tare: {value: 20, unit: t}, payload: {value: 50, unit: t}, cost_per_hour: {value: 1.06, unit: EUR}}
  driver_cost_per_hour: {value: 57, unit: EUR}
  provision_per_wagon:  {value: 23, unit: EUR}
  disturbance_share:    {value: 0.0463}
  detour_speed:         {value: 60, unit: "km/h"}
  deducted_operating_cost_option: electrification
```

Das YAML oben zeigt die Struktur mit den Altwerten der Thesis als Startpunkt. Für den Neubau gelten folgende Abweichungen aus Teil F: `finance.comparison_sums` führt zwei Summen (`investment_pv` und `annuity`), beide werden ausgewiesen, `decision.uses` wählt eine (EK-2026-062); `finance.phases.model: by_measure_type` mit Baudauer je Maßnahmentyp (EK-2026-071); `standi.reference_speed_fallback: {mode: vehicle_vmax_and_line_speed}` (EK-2026-070); `small_charging_station: {counts_as_supply: true, charge_power: …, max_per_place: 1}` (EK-2026-068); `range_model.section_additional_energy: full_on_unsupplied` (EK-2026-069); `range_model.bundle_order: by_running_km_desc` (EK-2026-066); `optimisation.suboption_assignment: sticky_with_single_valuation` (EK-2026-067); `methods.infeasible_option: exclude` (EK-2026-064); `clustering.relations.shared_place.transitive: true` (EK-2026-073). Die Hinweise `note: "Altcode …"` in den Einträgen dienen nur der Dokumentation der Herkunft; es gibt keinen Parametersatz, der das Altverhalten nachbildet. Die Konstanten der Energieformel Güterverkehr (`bvwp.freight_energy`) und die Baudauern je Maßnahmentyp brauchen Quellen aus der Thesis beziehungsweise neue Festlegungen, bevor der Satz als `masterarbeit-2026` gilt.

Szenariodefinition:

```yaml
# applications/masterarbeit/config/scenario/s1_ausgangsszenario.yaml
name: Ausgangsszenario
parameters: masterarbeit-2023
sources:
  network:   {adapter: prosd-db, snapshot: "2024-11-01"}
  timetable: {adapter: prosd-db, version: "Deutschlandtakt 3. Gutachterentwurf"}
  vehicles:  {adapter: prosd-db}
corrections: [corrections/blacklist_route_ignore_ocp.json]
projects: [18]
technologies: [electrification, efuel, battery, optimised_electrification, diesel, h2]
exclusions:
  - {technologies: [battery, h2], when_category_present: sgv}
  - {suboption: electrification, forced_for_category: sgv}
methods:
  cost_by_category: {sgv: bvwp, spnv: standi, spfv: standi}
  clustering: {strategy: unsupplied_connected, relations: [shared_service, shared_place], transitive: true}
  sub_areas: identical_service_set
  optimisation: greedy_subarea
  decision: min_comparison_sum
  infeasible_option: exclude
  state_sharing: none
validation:
  unknown_attribute: error          # oder: treat_as_false_and_report
  zero_length_route: error
  service_without_bundle: skip_and_report
outputs: [prosd-db, parquet]
```

## D8 Netz- und Routingmodell nach dem raildashboard (Ergebnis Schritt 0)

Sichtung des Repos `JonasPrade/raildashboard` (Stand 2026-11-01, Commit 5769f3a). Dort gibt es zwei Ebenen, die für `traction_eval` beide relevant sind.

**Geometrie-Routing über OpenStreetMap.** Ein GraphHopper-Dienst mit OpenRailRouting (geofabrik, v1.1, GraphHopper 11) läuft auf dem OSM-Extrakt Deutschland (`germany-latest.osm.pbf`), Profil `rail_default` mit Abbiegekosten für Züge. Codierte Attribute im Graphen: `gauge`, `voltage`, `electrified`, `frequency`, `max_speed`, `rail_access`, `rail_average_speed`, `railway_class`, `railway_service`, `preferred_direction`. Das Backend (`services/route_service.py`, `services/routing_client.py`) schickt Wegpunkte als Koordinaten (Betriebsstellen oder freie Punkte) und übernimmt nur Linie, Distanz und Dauer; Routen werden je Projekt mit `graph_version` und `cache_key` als Geography gespeichert. Pfaddetails je Teilstück (GraphHopper-Parameter `details`, zum Beispiel `electrified`, `voltage`, `max_speed`) fragt das raildashboard nicht ab, der Dienst kann sie aber liefern.

**Topologisches Netz aus RINF.** Tabellen nach dem ERA-Datenmodell: `operational_point` (Betriebsstellen mit `op_id`, Name, Typ, Koordinaten), `section_of_line` (Abschnitt zwischen zwei Betriebsstellen mit Länge und Streckennummer), `sol_track` (Gleise je Abschnitt) und `sol_track_parameter` (RINF-Parameter je Gleis, darunter Elektrifizierung, Spannung, Höchstgeschwindigkeit). Dazu ein pgRouting-Dijkstra über `section_of_line` nach Länge (`routing/core.py`), bisher nur für die Migration der alten Projekte genutzt. Die Dokumentation vermerkt, dass die deutschen RINF-Daten keine Geometrie je Abschnitt liefern und der Import von Gleisen und Gleisparametern noch unvollständig ist.

**Zuordnung zum Fahrplan.** Die railML-Betriebsstellen des Deutschlandtakts tragen DB-Kürzel; RINF-`op_id` enthält dasselbe Kürzel mit Länderpräfix. Die alte `pros`-Datenbank verknüpfte `railway_stations.db_kuerzel` entsprechend.

**Entscheidung (EK-2026-077, 2026-11-02): OSM als einzige Netzgrundlage mit Korrekturschicht.** RINF wird nicht verwendet. Das Netzmodell von `traction_eval` entsteht in drei Schichten:

1. **Gepinnter OSM-Extrakt.** Ein Geofabrik-Extrakt Deutschland (oder ein Ausschnitt) mit Datum; Datei oder Prüfsumme im Manifest. Derselbe Extrakt speist den GraphHopper-Dienst mit OpenRailRouting (Konfiguration wie im raildashboard, Profil `rail_default`).
2. **Abgeleitetes Segmentmodell.** Ein Extraktionsschritt (osmium-Filter auf `railway=rail|construction|proposed` mit `usage=main|branch` sowie Betriebsstellenknoten `railway=station|halt|junction|service_station|yard|crossover` mit `railway:ref`) bildet Segmente: alle Gleise einer VzG-Streckennummer (`railway:ref` am Weg) zwischen zwei aufeinanderfolgenden Betriebsstellen. Kennung = (Streckennummer, Von-Kürzel, Bis-Kürzel), stabil über Extrakte. Attribute je Segment aus den zugehörigen Wegen: Länge aus der Geometrie, Gleiszahl als Anzahl paralleler Gleise, Elektrifizierung (`electrified`: contact_line, rail, no), `voltage`, `frequency`, `maxspeed` (für die Streckengeschwindigkeit nach EK-2026-070), `gauge`, `usage`, Lebenszyklus (`proposed:*`, `construction:*`) für geplante Elektrifizierung und Neubaustrecken. Betriebsstellen tragen das DS100-Kürzel aus `railway:ref` und werden darüber den railML-Betriebsstellen zugeordnet.
3. **Manuelle Korrekturschicht (Diff).** Eine versionierte Konfigurationsdatei je Szenario oder global, die vor dem Domänenmodell angewendet wird: Overrides je Segment (einzelne Attribute, zum Beispiel Elektrifizierung oder Gleiszahl), Zusammenlegen oder Ausschließen von Segmenten, ergänzte Segmente mit eigener Geometrie (Neubaustrecken, die in OSM fehlen), Zuordnungen Betriebsstelle zu Kürzel, Ignorierlisten für das Routing. Jeder Eintrag trägt Begründung und Datum. Die Schicht erscheint mit Hash im Manifest; ein Lauf ohne sie ist ebenfalls möglich, damit die Wirkung der Korrekturen ausgewiesen werden kann.

Routing: Zuggruppen werden mit allen Zwischenbetriebsstellen als Zwangspunkten (EK-2026-074) über GraphHopper geroutet; die zurückgegebene Linie wird über die passierten Betriebsstellen auf die Segmentfolge abgebildet. Validierung: Segmente ohne `electrified`-Tag, Betriebsstellen ohne Kürzel und Routen, die ein Segment nur teilweise nutzen, werden ausgewiesen; der Lauf startet nur, wenn die Lücken durch die Korrekturschicht erklärt oder als akzeptiert markiert sind.

Risiken: OSM ist nicht amtlich; Attributlücken und Fehler werden durch Validierung und Korrekturschicht abgefangen. Die Gleiszahl ist eine Ableitung aus parallelen Wegen. Abzweig- und Überleitstellen tragen in OSM nicht immer ein Kürzel; die Korrekturschicht ergänzt sie. RINF kann später als Gegenprobe für Elektrifizierung und Geschwindigkeit dienen, ohne Teil des Modells zu sein.

## D5 Datenfluss

Eingangsdaten (EK-2026-061): Netz nach dem Netzmodell des raildashboard, railML des dritten Zielfahrplans des Deutschlandtakts, Fahrzeugkennwerte, Szenario-Maßnahmen, Korrekturlisten. Jonas stellt die Daten bereit. Der Loader überführt sie einmal je Lauf in das Domänenmodell und legt es als Datei ab (Parquet oder JSON); diese Datei ist die reproduzierbare Eingabe eines Laufs und zugleich Quelle für Fixtures. Ein Loader aus der alten prosd-Datenbank bleibt optional für Fahrzeugmuster und Formationen, falls diese nicht neu erhoben werden.

Ergebnisse (EK-2026-075): eigenes Ergebnisschema mit Lauf-ID, das je Szenario, Gebiet und Option Kosten nach Komponenten, Maßnahmen mit Geometriebezug, Durchführbarkeit, physische Kennzahlen, Emissionen und das Manifest hält. Es wird als Datei geschrieben und in eine eigene Datenbank geladen, aus der ein eigenständiges Frontend liest (Szenarienvergleich, Gebietskarte mit gewählter Option, Kostenzerlegung, Maßnahmenliste, Sensitivität). Es gibt keinen Writer in die prosd-Tabellen; das alte Dashboard zeigt weiter die Thesis-Ergebnisse, bis es abgelöst wird. Gestaltung des Frontends nach dem Design-System der Initiative Deutschlandtakt, wie beim raildashboard.

## D6 Tests

- Einheitstests je Formel aus Teil B mit Handrechnungsbeispielen (ein Fahrzeug, eine Strecke, ein Jahr), inklusive Einheiten.
- Finanzmodul gegen Referenzwerte (Barwert, Phasen, Annuität, Restwert, Zeitreihen).
- Parametersystem: fehlende Parameter führen zu Fehlern, Vererbung und Overrides, Hash-Stabilität, Zeitreihen-Interpolation.
- Eigenschaftstests: Gebiete disjunkt und vollständig, transitiv geschlossen; Energiebilanz nie über Kapazität, Ladezuwachs nie negativ, Maßnahmen verändern nur Zustandskopien; Entscheidungen unabhängig von Gebiets- und Optionsreihenfolge bei `state_sharing: none`.
- Minimalbeispiel: zwei Strecken, eine Linie mit zwei Zuggruppen, zwei Optionen, von Hand durchgerechnet und als Dokumentationsbeispiel und Test geführt.
- Fixtures aus den neuen Eingangsdaten: zwei bis drei kleine Netzausschnitte mit Fahrplan (ein reines Nahverkehrsgebiet, eines mit Güterverkehr, eines mit Teilgebieten), Ergebnisse nach Freigabe eingefroren als Regressionsschutz für spätere Änderungen. Kein Vergleich mit dem Altcode.
- Plausibilität: Vergleich der Szenariokennzahlen mit den veröffentlichten Thesis-Ergebnissen (Größenordnung, Verteilung der Traktionen), dokumentiert, nicht als Test.

## D7 Umsetzungsreihenfolge

0. Erledigt (D8): Netzmodell und Routing des raildashboard gesichtet, Netzgrundlage OSM mit Korrekturschicht entschieden. Offen: railML des dritten Zielfahrplans und Fahrzeugkennwerte von Jonas.
1. Eigenes Repo `traction_eval`, Paketgerüst, Domänenmodell, Einheiten, Parametersystem mit `masterarbeit-2026`, Finanzmodul mit beiden Vergleichssummen, Validierung. Tests.
2. Netz-Pipeline: OSM-Extrakt pinnen, osmium-Filter, Segmentbildung, Korrekturschicht, Validierungsbericht; GraphHopper-Dienst nach raildashboard-Vorlage; Loader für railML und Fahrzeugkennwerte; Export des Domänenmodells als Datei. Fixtures aus den neuen Daten erzeugen.
3. Routing nach dem Ansatz des raildashboard, Betriebsleistungsgrößen, Umlaufbildung, Bündelverteilung. Tests gegen Fixtures. Minimalbeispiel.
4. Kostenkomponenten BVWP (Güterverkehr) und Standi (Personenverkehr) als Plugins. Handrechnungstests.
5. Gebietsbildung (transitiv über Zuggruppen und Bahnhöfe) und Teilgebiete. Eigenschaftstests.
6. Maßnahmengeneratoren Oberleitung, Tankstellen, Ladepunkte; Phasenmodell mit Baudauer je Maßnahmentyp.
7. Reichweitenmodell mit Fahrtenfolge-Selektor, Diagnose und Platzierungsregeln als Plugins; Durchführbarkeitsstatus.
8. Kombinierte Optimierung mit Zuordnungsregel (Einmalbewertung).
9. Entscheidung (Ausschluss nicht durchführbarer Optionen), Aggregation, Ergebnisschema mit Lauf-ID, Manifest, CLI, Parallelisierung je Gebiet.
10. Eigenständiges Frontend: Szenarienvergleich, Gebietskarte, Kostenzerlegung, Maßnahmen, Sensitivität; Abfrage-API auf dem Ergebnisschema.
11. Störfallbewertung als eigenes Modul auf Zustandskopien.
12. Erweiterungen aus Teil E (Rückfall je Linie, Zeitreihen, Sensitivität) nach Bedarf.
13. Abschluss: Altcode in `pros` einfrieren oder archivieren; Thesis-Ansichten des alten Dashboards durch das neue Frontend ablösen.

Voraussetzung für Schritt 0 ist der Zugriff auf das raildashboard-Repo in der Arbeitsumgebung; für Schritt 2 die Eingangsdaten von Jonas.

---

# Teil E: Methodische Erweiterungen (über die Rekonstruktion hinaus)

Diese Punkte sind durch die Architektur vorbereitet (A5, A6, A9, A11), aber keine Nachbildung des Altcodes. Reihenfolge nach erwartetem Nutzen.

1. **Zeitreihen für Preise und Faktoren.** Energiepreise, CO2-Kostenpfad, Batteriekosten über den Betrachtungszeitraum; Finanzmodul diskontiert jahresweise.
2. **Sensitivität und Robustheit.** Parameterfächer, robuste Entscheidungsregel, Break-even-Werte je Gebiet (Strompreis, Dieselpreis, Oberleitungskosten, CO2-Preis).
3. **Reichweitenmodell.** Nutzbarer Kapazitätsanteil, Degradationsreserve, Ladeleistungskurve, Nebenverbraucher, Bilanz über den vollen Umlauf.
4. **Fahrzeugbedarf.** Reservefaktor, Umläufe über Linien hinweg.
5. **Externe Effekte der Infrastruktur.** THG der Herstellung von Oberleitung und Ladeanlagen als Kostenkomponente.
6. **Restwert und Lebensdauern** als explizite Methode für alle Anlagen und Fahrzeuge.
7. **Optimierung.** Exakte Verfahren über Teilgebiete (dynamische Programmierung oder ganzzahlige Optimierung) als Alternative zum Greedy-Durchlauf; Mehrfachdurchläufe.
8. **Validierung mit Plausibilitätsgrenzen** je Kennzahl (Kosten je km, Energie je km, Geschwindigkeiten), Verletzungen im Manifest.
9. **Ergebnisvisualisierung** im eigenständigen Frontend (Karten je Option, Kostenzerlegung je Gebiet, Break-even-Karten).
10. **Rückfall je Linie** bei nicht durchführbarer Batterieoption: die nicht fahrbare Linie erhält Oberleitung auf ihrem Laufweg, die übrigen fahren Batterie (EK-2026-064, Option C).

---

# Teil F: Getroffene Entscheidungen (Stapel EKS-2026-010, 2026-11-01)

Maßgeblich sind die Karten im gemeinsamen Vault (Projektnotiz „Traktionsvergleich Neuentwicklung“); hier die Kurzfassung.

| Karte | Frage | Entscheidung |
|---|---|---|
| EK-2026-059 | Ablage des Pakets | eigenes Repo `traction_eval`; `pros` nur Datenquelle |
| EK-2026-060 | Nachbildung vor Erweiterung | kompletter Neubau, kein Nachbau; kein altcode-kompatibler Satz, kein Golden-Master |
| EK-2026-061 | Testdaten | Eingangsdaten von Jonas auf Basis des dritten Zielfahrplans; Fixtures daraus |
| EK-2026-062 | Vergleichssumme | Investitionsbarwert und Annuität beide ausweisen; Entscheidungsregel wählt per Konfiguration |
| EK-2026-063 | Methode Fernverkehr | Standi wie bisher |
| EK-2026-064 | nicht durchführbare Option | ausschließen und ausweisen; Rückfall je Linie als zweiter Schritt |
| EK-2026-065 | Fahrtenfolge Batterie | Hin- und Rückfahrt mit Mehrfolgeprüfung; voller Umlauf als Sensitivität |
| EK-2026-066 | Reihenfolge Linien | absteigend nach Zug-km je Tag |
| EK-2026-067 | Zuggruppen in mehreren Teilgebieten | Batterie bleibt, Betriebskostendifferenz zählt einmal |
| EK-2026-068 | kleine Ladestation | zählt als Versorgung mit eigener Ladeleistung, höchstens eine je Bahnhof |
| EK-2026-069 | Batteriezuschlag | voller Zuschlag auf Abschnitten ohne Oberleitung |
| EK-2026-070 | Rückfall Referenzgeschwindigkeit | Fahrzeug-Höchstgeschwindigkeit, zusätzlich begrenzt durch Streckengeschwindigkeit, sofern im Netz vorhanden |
| EK-2026-071 | Baudauer | je Maßnahmentyp als Parameter |
| EK-2026-072 | 13 Rechenfehler | alle korrigieren |
| EK-2026-073 | Gebietsbildung | transitiv über Zuggruppen und Bahnhöfe; Bahnhofsrelation ausdrücklich gewollt |
| EK-2026-074 | Via-Punkte Routing | alle Zwischenbetriebsstellen mit Bahnhof; Routing-Modul nach dem Ansatz des raildashboard |
| EK-2026-075 | Ergebnisse | eigenes Ergebnisschema mit Lauf-ID und eigenständiges Frontend; kein Writer in prosd |
| EK-2026-076 | Einheiten | eigene leichte Einheitentypen mit statischer Prüfung; pint nur in Tests |
| EK-2026-077 | Netzsegment | OSM als einzige Netzgrundlage (gepinnter Extrakt, Segment je VzG-Strecke und Betriebsstellenpaar, Elektrifizierung aus OSM, GraphHopper mit OpenRailRouting) mit manueller versionierter Korrekturschicht; RINF nur optionale Gegenprobe |

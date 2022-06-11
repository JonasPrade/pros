from bs4 import BeautifulSoup as bs
import logging
import os
import requests


class ElementNotInPrinsException(Exception):
    def __init__(self, message):
        super().__init__(message)


class ProjectNotFound(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoBoolPossible(Exception):
    def __init__(self, message):
        super().__init__(message)


class Bvwp:
    def __init__(self, project_id):
        self._URL_PRINS = "https://bvwp-projekte.de/schiene_2018/"
        self.project_id = str(project_id)
        FOLDERPATH = '/Users/jonas/PycharmProjects/pros/example_data/bvwp_data/'
        FILENAME = 'Bundesverkehrswegeplan 2030 – Projekt ' + self.project_id + '.html'

        self.filepath = FOLDERPATH + FILENAME

        self.soup = self._import_from_prins()

        # basic data
        self.tables = self.soup.find_all('table')

    def _import_from_prins(self):
        if not os.path.exists(self.filepath):
            self._download_project()

        with open(self.filepath, 'r', encoding='utf-8') as f:
            text = f.read()

        # converts it to beautiful self.soup
        soup = bs(text, 'html.parser')
        return soup

    def _download_project(self):
        url_project = self._URL_PRINS + self.project_id + "/" +  self.project_id + ".html"
        html = requests.get(url_project)

        if html.status_code == 200:
            open(self.filepath, 'wb').write(html.content)
        else:
            raise ProjectNotFound("Could not find the project, url: " + url_project)

    def _get_element_by_prev(self, type_of_element, text):
        next_element = None
        elements = self.soup.find_all(str(type_of_element))
        for index, element in enumerate(elements):
            if text in element.text:
                next_element = element.nextSibling
                break

        if next_element is None:
            raise ElementNotInPrinsException("Couldn't find the next Element " + str(text))

        return next_element

    def _get_all_elements_to_next_same(self, element_start_tag, element_end_tag, element_text):
        """
        Gets all all elements between to elements of same type (for example all <p> between <h2>).
        This is necessary, because Prins refuses to use <div>
        :param element_start_tag: Type of the element between all elements are selected (for example h2)
        :param element_end_tag: Defines the tag of the element before the searches stops (f.e "h1")
        :param element_text: The text for the starting element
        :return:
        """
        elements_between = []
        possible_starting_elements = self.soup.find_all(str(element_start_tag))
        for index, element in enumerate(possible_starting_elements):
            if element_text in element.text:
                selected_element = element.nextSibling
                while selected_element.name != element_end_tag:
                    if selected_element != '\n':
                        elements_between.append(selected_element)
                    selected_element = selected_element.nextSibling
                break

        if not elements_between:
            raise ElementNotInPrinsException("There were no elements between after the given term:" + str(element_text))

        return elements_between

    def _get_table_nr(self, table_title, column_first_text=0, row_first_text=1):
        """
        a function that checks a given string with the first text element of an table. This is necessary to return the index and to get the table_content independ if on table is missing (which can be the case for some projects)
        :param table_title:
        :param column_first_text: usually 0 (so first column), but some titles don't have a string in first row, first column, so this variable can shift the column where the function is comparing the string
        :param row_first_text: usually 1 (so second row), reason same as column_first_text
        :return:
        """
        tbl_nr = None
        for index, table in enumerate(self.tables):
            try:
                if table_title in table.contents[row_first_text].contents[column_first_text].text:
                    tbl_nr = index
                    break
            except (IndexError, AttributeError):
                continue

        if tbl_nr is None:
            raise ElementNotInPrinsException("Couldn't find table in Prins beginning with" + str(table_title))

        return tbl_nr

    def _convert(self, input_float):
        input_float = str(input_float)

        if input_float=='-':
            input_float = None
        else:
            try:
                # converts a float 12.452,234 to a float that python accepts
                input_float = input_float.replace('.', '')
                input_float = float(input_float.replace(',', '.'))
            except ValueError:
                if input_float == '2) s 110':
                    input_float = None
                    logging.info("there is an missing info, look to 1.10 in Prins of this project")
                else:
                    logging.warning('There was an error while converting a string to an float')

        return input_float

    def _yesno_to_bool(self, inputstring):
        """
        Converts the (german) yes and no to bool
        :param inputstring: string as input. Must be "ja" or "nein"
        :return:
        """
        output_bool = None
        if "ja" in inputstring:
            output_bool = True
        elif "nein" in inputstring:
            output_bool = False
        else:
            raise NoBoolPossible("Couldn't convert to a Bool:" + str(inputstring))

        return output_bool

    def _list_to_string(self, input_list):
        """
        transforms a list of html elements to an string
        :param input_list: list
        :return:
        """
        output_string = ''
        for e in input_list:
            output_string += e.text
        return output_string


class BvwpRail(Bvwp):
    def __init__(self, project_name):
        super().__init__(project_name)

        logging.info("Starting with project: " + project_name)

        tbl_nm = ('Basisdaten', 'Projektnummer')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1])
            # self.bvwp_id = self.soup.find_all('table')[tbl_nr].contents[1].contents[1].text  #  actual not needed
            # because Bvwp class only works with id
            self.title = self.soup.find_all('table')[tbl_nr].contents[3].contents[1].text
            self.content = self.soup.find_all('table')[tbl_nr].contents[7].contents[1].text  # TODO: Add algorithmus to get the important project content (electrification, vmax, nbs, etc for the bools)
            self.length = float(self.soup.find_all('table')[tbl_nr].contents[9].contents[1].text[:-3].replace(',', '.'))
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # prio bvwp
        tbl_nm = ('Dringlichkeit BVWP', 'Dringlichkeitseinstufung')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1])
            self.prio_bvwp = self.soup.find_all('table')[tbl_nr].contents[1].contents[1].text
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # cost
        tbl_nm = ('Kostenübersicht', 'Kostenbestandteile (netto ohne Mehrwertsteuer)')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1])
            self.building_cost = self._convert(self.soup.find_all('table')[tbl_nr].contents[3].contents[1].text)
            self.maintenance_cost = self._convert(self.soup.find_all('table')[tbl_nr].contents[5].contents[1].text)
            self.planning_cost = self._convert(self.soup.find_all('table')[tbl_nr].contents[7].contents[1].text)
            self.planning_cost_incurred = self._convert(self.soup.find_all('table')[tbl_nr].contents[9].contents[1].text)
            self.total_budget_relevant_cost = self._convert(self.soup.find_all('table')[tbl_nr].contents[11].contents[1].text)
            self.total_budget_relevant_cost_incurred = self._convert(self.soup.find_all('table')[tbl_nr].contents[13].contents[1].text)
            self.valuation_relevant_cost = self._convert(self.soup.find_all('table')[tbl_nr].contents[15].contents[1].text)
            self.valuation_relevant_cost_pricelevel_2012 = self._convert(self.soup.find_all('table')[tbl_nr].contents[17].contents[1].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # rating
        tbl_nm = ('Bewertungsergebnisse', 'Bewertungsergebnisse')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1])
            self.nkv = self._convert(self.soup.find_all('table')[tbl_nr].contents[3].contents[1].text)
            self.environmental_impact = self.soup.find_all('table')[tbl_nr].contents[5].contents[1].text
            self.regional_significance = self.soup.find_all('table')[tbl_nr].contents[7].contents[1].text
            self.bottleneck_elimination = self._yesno_to_bool(self.soup.find_all('table')[tbl_nr].contents[9].contents[1].text)
            self.traveltime_reductions = self._convert(self.soup.find_all('table')[4].contents[11].contents[1].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        h_nm = ('Dringlichkeitseinstufung', 'Begründung der Dringlichkeitseinstufung')
        try:
            priority_reason_list = self._get_all_elements_to_next_same(element_start_tag='h2', element_end_tag='h2', element_text=h_nm[1])
            self.priority_reason = self._list_to_string(priority_reason_list)
        except ElementNotInPrinsException:
            logging.warning("No element found with starting h2 " + h_nm[0])
        finally:
            h_nm = []

        h_nm = ('Projektbegründung', 'Projektbegründung/Notwendigkeit des Projektes')
        try:
            project_reason_list = self._get_all_elements_to_next_same(element_start_tag='h2', element_end_tag='h1', element_text=h_nm[1])
            self.project_reason = self._list_to_string(project_reason_list)
        except ElementNotInPrinsException:
            logging.warning("No element found with starting h2 " + h_nm[0])
        finally:
            h_nm = []


        tbl_nm = ('Länder, Kreise und Wahlkreise', 'Länderübergreifendes Projekt')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1])
            self.states = self.soup.find_all('table')[tbl_nr].contents[3].contents[1].contents
            self.counties = self.soup.find_all('table')[tbl_nr].contents[5].contents[1].contents
            self.constituencies = self.soup.find_all('table')[tbl_nr].contents[7].contents[1].contents
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        h_nm = ('Alternativenprüfung', '1.4 Alternativenprüfung')
        try:
            alternatives = self._get_all_elements_to_next_same(element_start_tag='h1', element_end_tag='h1',
                                                                      element_text=h_nm[1])
            self.alternatives = self._list_to_string(alternatives)
        except ElementNotInPrinsException:
            logging.warning("No element found with starting h2 " + h_nm[0])
        finally:
            h_nm = []

        # Vermeidung der Überlastung im Schienennetz
        tbl_nm = ("Kilometer Schiene mit einer Überlastung", "Anzahl Kilometer Schiene mit einer Überlastung")
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], column_first_text=1)
            self.congested_rail_reference_6to9_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[7].contents[1].text.split("km")[0])
            self.congested_rail_reference_6to9_perc = self._convert(self.soup.find_all('table')[tbl_nr].contents[7].contents[1].text.split("km")[1][2:-2])
            self.congested_rail_plancase_6to9_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[7].contents[2].text.split("km")[0])
            self.congested_rail_plancase_6to9_perc = self._convert(self.soup.find_all('table')[tbl_nr].contents[7].contents[2].text.split("km")[1][2:-2])

            self.congested_rail_reference_9to16_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[9].contents[1].text.split("km")[0])
            self.congested_rail_reference_9to16_perc = self._convert(self.soup.find_all('table')[tbl_nr].contents[9].contents[1].text.split("km")[1][2:-2])
            self.congested_rail_plancase_9to16_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[9].contents[2].text.split("km")[0])
            self.congested_rail_plancase_9to16_perc = self._convert(self.soup.find_all('table')[tbl_nr].contents[9].contents[2].text.split("km")[1][2:-2])

            self.congested_rail_reference_16to19_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[11].contents[1].text.split("km")[0])
            self.congested_rail_reference_16to19_perc = self._convert(self.soup.find_all('table')[tbl_nr].contents[11].contents[1].text.split("km")[1][2:-2])
            self.congested_rail_plancase_16to19_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[11].contents[2].text.split("km")[0])
            self.congested_rail_plancase_16to19_perc = self._convert(self.soup.find_all('table')[tbl_nr].contents[11].contents[2].text.split("km")[1][2:-2])

            self.congested_rail_reference_19to22_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[13].contents[1].text.split("km")[0])
            self.congested_rail_reference_19to22_perc = self._convert(self.soup.find_all('table')[tbl_nr].contents[13].contents[1].text.split("km")[1][2:-2])
            self.congested_rail_plancase_19to22_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[13].contents[2].text.split("km")[0])
            self.congested_rail_plancase_19to22_perc = self._convert(self.soup.find_all('table')[tbl_nr].contents[13].contents[2].text.split("km")[1][2:-2])

            self.congested_rail_reference_22to6_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[15].contents[1].text.split("km")[0])
            self.congested_rail_reference_22to6_perc = self._convert(self.soup.find_all('table')[tbl_nr].contents[15].contents[1].text.split("km")[1][2:-2])
            self.congested_rail_plancase_22to6_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[15].contents[2].text.split("km")[0])
            self.congested_rail_plancase_22to6_perc = self._convert(self.soup.find_all('table')[tbl_nr].contents[15].contents[2].text.split("km")[1][2:-2])

            self.congested_rail_reference_day_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[17].contents[1].text.split("km")[0])
            self.congested_rail_reference_day_perc = self._convert(self.soup.find_all('table')[tbl_nr].contents[17].contents[1].text.split("km")[1][2:-2])
            self.congested_rail_plancase_day_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[17].contents[2].text.split("km")[0])
            self.congested_rail_plancase_day_perc = self._convert(self.soup.find_all('table')[tbl_nr].contents[17].contents[2].text.split("km")[1][2:-2])

        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # Auswirkung auf Verspätung und Betriebsstabilität
        tbl_nm = ('außerplanmäßige Wartezeiten', 'Entwicklung von außerplanmäßigen Wartezeiten (vergleichbar mit Stauwartezeiten) im deutschen Netz')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], column_first_text=1)
            self.unscheduled_waiting_period_reference_case = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[3].contents[1].text[:-8])
            self.unscheduled_waiting_period_plan_case = self._convert(self.soup.find_all('table')[tbl_nr].contents[5].contents[1].text[:-8])
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        tbl_nm = ('Zuverlässigkeit', 'Veränderung der Zuverlässigkeit')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], row_first_text=0)
            self.punctuality_cargo_reference_case = self._convert(self.soup.find_all('table')[tbl_nr].contents[2].contents[1].text) / 100
            self.delta_punctuality_cargo_relativ = self._convert(self.soup.find_all('table')[tbl_nr].contents[4].contents[1].text)
            self.delta_punctuality_cargo_absolut = self._convert(self.soup.find_all('table')[tbl_nr].contents[6].contents[1].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # changing in travel time
        element_nm = ("ausgewählte Fahrzeitverkürzungen", "Ausgewählte Fahrzeitverkürzung im Maßnahmenbereich")
        try:
            self.change_travel_time_examples = self._list_to_string(self._get_all_elements_to_next_same(
                element_start_tag="h2", element_end_tag="h1", element_text=element_nm[1]))
        except ElementNotInPrinsException:
            logging.warning("Couldn't find any elements after " + element_nm[0])

        # Auswirkungen auf den Personenverkehr
        tbl_nm = ('Auswirkungen Personenverkehr', 'Auswirkungen des Projektes auf den Personenverkehr')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], row_first_text=0)
            self.relocation_car_to_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[4].contents[1].text)
            self.relocation_rail_to_car = self._convert(self.soup.find_all('table')[tbl_nr].contents[6].contents[1].text)
            self.relocation_air_to_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[8].contents[1].text)
            self.induced_traffic = self._convert(self.soup.find_all('table')[tbl_nr].contents[10].contents[1].text)
            self.delta_car_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[12].contents[1].text)
            self.delta_rail_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[14].contents[1].text)
            self.delta_rail_running_time = self._convert(self.soup.find_all('table')[tbl_nr].contents[16].contents[1].text)
            self.delta_rail_km_of_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[20].contents[1].text)  # verbleibender Verkehr im SPNV
            self.delta_rail_km_car_to_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[22].contents[1].text)
            self.delta_rail_km_rail_to_car = self._convert(self.soup.find_all('table')[tbl_nr].contents[24].contents[1].text)
            self.delta_rail_km_air_to_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[26].contents[1].text)
            self.delta_rail_km_induced = self._convert(self.soup.find_all('table')[tbl_nr].contents[28].contents[1].text)
            self.delta_travel_time_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[32].contents[1].text)
            self.delta_travel_time_car_to_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[34].contents[1].text)
            self.delta_travel_time_rail_to_car = self._convert(self.soup.find_all('table')[tbl_nr].contents[36].contents[1].text)
            self.delta_travel_time_air_to_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[38].contents[1].text)
            self.delta_travel_time_induced = self._convert(self.soup.find_all('table')[tbl_nr].contents[40].contents[1].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # Auswirkungen auf den Güterverkehr
        tbl_nm = ('Auswirkungen Güterverkehr', 'Auswirkungen des Projektes auf den Güterverkehr')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], row_first_text=0)
            self.relocation_truck_to_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[4].contents[1].text)
            self.relocation_ship_to_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[6].contents[1].text)
            self.delta_truck_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[8].contents[1].text)
            self.delta_truck_count = self._convert(self.soup.find_all('table')[tbl_nr].contents[10].contents[1].text)
            self.delta_rail_cargo_count = self._convert(self.soup.find_all('table')[tbl_nr].contents[12].contents[1].text)
            self.delta_rail_cargo_running_time = self._convert(self.soup.find_all('table')[tbl_nr].contents[14].contents[1].text)
            self.delta_rail_cargo_km_lkw_to_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[18].contents[1].text)
            self.delta_rail_cargo_km_ship_to_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[20].contents[1].text)
            self.delta_rail_cargo_time_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[24].contents[1].text)
            self.delta_rail_cargo_time_lkw_to_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[26].contents[1].text)
            self.delta_rail_cargo_time_ship_to_rail = self._convert(self.soup.find_all('table')[tbl_nr].contents[28].contents[1].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # Abgasemissionen
        tbl_nm = ('Veränderung Abgasemssionen', 'Veränderung der Abgasemissionen (Summe Personen- und Güterverkehr über alle Verkehrsmittel, Planfall - Bezugsfall)')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], row_first_text=0)
            self.delta_nox = self._convert(self.soup.find_all('table')[tbl_nr].contents[2].contents[1].text)
            self.delta_co = self._convert(self.soup.find_all('table')[tbl_nr].contents[4].contents[1].text)
            self.delta_co2 = self._convert(self.soup.find_all('table')[tbl_nr].contents[6].contents[1].text)
            self.delta_hc = self._convert(self.soup.find_all('table')[tbl_nr].contents[8].contents[1].text)
            self.delta_pm = self._convert(self.soup.find_all('table')[tbl_nr].contents[10].contents[1].text)
            self.delta_so2 = self._convert(self.soup.find_all('table')[tbl_nr].contents[12].contents[1].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # Nutzen-Kosten-Analyse
        # # passenger
        tbl_nm = ('Nutzen Personenverkehr', 'Nutzenkomponenten des Personenverkehrs')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], row_first_text=0)
            self.use_change_operating_cost_car_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[4].contents[2].text)
            self.use_change_operating_cost_car_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[4].contents[3].text)
            self.use_change_operating_cost_rail_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[6].contents[2].text)
            self.use_change_operating_cost_rail_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[6].contents[3].text)
            self.use_change_operating_cost_air_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[8].contents[2].text)
            self.use_change_operating_cost_air_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[8].contents[3].text)
            self.use_change_pollution_car_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[12].contents[2].text)
            self.use_change_pollution_car_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[12].contents[3].text)
            self.use_change_pollution_rail_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[14].contents[2].text)
            self.use_change_pollution_rail_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[14].contents[3].text)
            self.use_change_pollution_air_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[16].contents[2].text)
            self.use_change_pollution_air_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[16].contents[3].text)
            self.use_change_safety_car_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[20].contents[2].text)
            self.use_change_safety_car_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[20].contents[3].text)
            self.use_change_safety_rail_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[22].contents[2].text)
            self.use_change_safety_rail_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[22].contents[3].text)
            self.use_change_travel_time_rail_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[26].contents[2].text)
            self.use_change_travel_time_rail_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[26].contents[3].text)
            self.use_change_travel_time_induced_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[28].contents[2].text)
            self.use_change_travel_time_induced_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[28].contents[3].text)
            self.use_change_travel_time_pkw_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[30].contents[2].text)
            self.use_change_travel_time_pkw_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[30].contents[3].text)
            self.use_change_travel_time_air_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[32].contents[2].text)
            self.use_change_travel_time_air_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[32].contents[3].text)
            self.use_change_travel_time_less_2min_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[34].contents[2].text)
            self.use_change_travel_time_less_2min_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[34].contents[3].text)
            self.use_change_implicit_benefit_induced_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[38].contents[2].text)
            self.use_change_implicit_benefit_induced_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[38].contents[3].text)
            self.use_change_implicit_benefit_pkw_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[40].contents[2].text)
            self.use_change_implicit_benefit_pkw_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[40].contents[3].text)
            self.use_change_implicit_benefit_air_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[42].contents[2].text)
            self.use_change_implicit_benefit_air_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[42].contents[3].text)
            self.use_sum_passenger_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[44].contents[2].text)
            self.use_sum_passenger_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[44].contents[2].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None


        # # use cargo
        tbl_nm = ('Nutzen Güterverkehr', 'Nutzenkomponenten des Güterverkehrs')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], row_first_text=0)
            self.use_change_operating_cost_truck_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[4].contents[2].text)
            self.use_change_operating_cost_truck_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[4].contents[3].text)
            self.use_change_operating_cost_rail_cargo_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[6].contents[2].text)
            self.use_change_operating_cost_rail_cargo_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[6].contents[3].text)
            self.use_change_operating_cost_ship_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[8].contents[2].text)
            self.use_change_operating_cost_ship_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[8].contents[3].text)
            self.use_change_pollution_truck_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[12].contents[2].text)
            self.use_change_pollution_truck_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[12].contents[3].text)
            self.use_change_pollution_rail_cargo_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[14].contents[2].text)
            self.use_change_pollution_rail_cargo_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[14].contents[3].text)
            self.use_change_pollution_ship_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[16].contents[2].text)
            self.use_change_pollution_ship_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[16].contents[3].text)
            self.use_change_safety_truck_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[20].contents[2].text)
            self.use_change_safety_truck_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[20].contents[3].text)
            self.use_change_safety_rail_cargo_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[22].contents[2].text)
            self.use_change_safety_rail_cargo_present_value = self._convert(
                self.soup.find_all('table')[22].contents[tbl_nr].contents[3].text)
            self.use_change_safety_ship_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[24].contents[2].text)
            self.use_change_safety_ship_present_value = self._convert(self.soup.find_all('table')[tbl_nr].contents[24].contents[3].text)
            self.use_change_running_time_rail_yearly = self._convert(self.soup.find_all('table')[tbl_nr].contents[28].contents[2].text)
            self.use_change_running_time_rail_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[28].contents[3].text)
            self.use_change_running_time_lkw_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[30].contents[2].text)
            self.use_change_running_time_lkw_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[30].contents[3].text)
            self.use_change_running_time_ship_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[32].contents[2].text)
            self.use_change_running_time_ship_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[32].contents[3].text)
            self.use_change_implicit_benefit_truck_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[36].contents[2].text)
            self.use_change_implicit_benefit_truck_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[36].contents[3].text)
            self.use_change_implicit_benefit_ship_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[38].contents[2].text)
            self.use_change_implicit_benefit_ship_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[38].contents[3].text)
            self.use_change_reliability_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[42].contents[2].text)
            self.use_change_reliability_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[42].contents[3].text)
            self.use_sum_cargo_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[44].contents[2].text)
            self.use_sum_cargo_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[44].contents[3].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # # sonstige Nutzenkomponenten
        tbl_nm = ('Sonstige Nutzen', 'Sonstige Nutzenkomponenten')
        try:
            tbl_nr = self._get_table_nr('Sonstige Nutzenkomponenten', row_first_text=0)
            self.use_change_maintenance_costs_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[2].contents[2].text)
            self.use_change_maintenance_costs_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[2].contents[3].text)
            self.use_change_lcc_infrastructure_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[4].contents[2].text)
            self.use_change_lcc_infrastructure_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[4].contents[3].text)
            self.use_change_noise_intown_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[8].contents[2].text)
            self.use_change_noise_intown_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[8].contents[2].text)
            self.use_change_noise_outtown_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[10].contents[2].text)
            self.use_change_noise_outtown_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[10].contents[3].text)
            self.sum_use_change_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[18].contents[2].text)
            self.sum_use_change_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[18].contents[3].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # # use-calulation cost#
        tbl_nm = ('Bewertungsrelevante Kosten', 'Bewertungsrelevante Kosten')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1])
            self.valuation_relevant_cost_pricelevel_2012_planning_cost = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[3].contents[1].text)
            self.valuation_relevant_cost_pricelevel_2012_infrastructure_cost = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[5].contents[1].text)
            self.valuation_relevant_cost_pricelevel_2012_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[7].contents[2].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # # Principles of present value calculation
        tbl_nm = ('Barwertermittlung', 'Grundlagen der Barwertermittlung')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1])
            self.duration_of_outstanding_planning = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[3].contents[1].text[:-6])
            self.duration_of_build = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[5].contents[1].text[:-6])
            self.duration_operating = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[7].contents[1].text[:-6])
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # Environmental and nature protection assessment
        tbl_nm = ('Nutzensumme Umwelt', 'Umweltbeitrag Teil 1: Nutzensumme Umwelt 	[Mio. Euro Barwert]')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1])
            self.sum_use_environment = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[1].contents[1].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        tbl_nm = ('Umweltbetroffenheit', 'Umweltbeitrag Teil 2: Umwelt-Betroffenheit 	[gering/mittel/hoch] oder "Projekt '
                                     'planfestgestellt"')
        try:
            tbl_nr = self._get_table_nr('Umweltbeitrag Teil 2: Umwelt-Betroffenheit 	[gering/mittel/hoch] oder "Projekt '
                                         'planfestgestellt"')
            self.sum_environmental_affectedness = str(
                self.soup.find_all('table')[tbl_nr].contents[1].contents[1].text)
            self.sum_environmental_affectedness_text = str(
                self.soup.find_all('table')[tbl_nr].contents[3].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # # environmental data
        # # #  Monetizable metrics
        tbl_nm = ('Umweltbeitrag monetarisiert', 'Umweltbeitrag Teil 1')
        try:
            table_monetizable_metrics = self._get_element_by_prev(type_of_element='h3', text='Umweltbeitrag Teil 1')
            self.noise_new_affected = table_monetizable_metrics.contents[7].contents[2].contents[0].text
            self.noise_relieved = table_monetizable_metrics.contents[9].contents[2].contents[0].text
            self.change_noise_outtown = table_monetizable_metrics.contents[11].contents[2].contents[0].text
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        tbl_nm = ('Umweltbeitrag nicht monetarisiert', 'Umweltbeitrag Teil 2')
        try:
            table_non_monetizable_metrics = self._get_element_by_prev(type_of_element='h3', text='Umweltbeitrag Teil 2')
            self.area_nature_high_importance = self._convert(table_non_monetizable_metrics.contents[5].contents[5].text)
            self.area_nature_high_importance_per_km = self._convert(table_non_monetizable_metrics.contents[5].contents[9].text)
            self.area_nature_high_importance_rating = table_non_monetizable_metrics.contents[5].contents[13].text
            self.natura2000_rating = table_non_monetizable_metrics.contents[7].contents[13].text
            self.natura2000_not_excluded = self._convert(table_non_monetizable_metrics.contents[9].contents[5].text)
            self.natura2000_probably = self._convert(table_non_monetizable_metrics.contents[11].contents[5].text)
            self.ufr_250 = self._convert(table_non_monetizable_metrics.contents[13].contents[5].text)
            self.ufr_250_per_km = self._convert(table_non_monetizable_metrics.contents[13].contents[9].text)
            self.ufr_250_rating = table_non_monetizable_metrics.contents[13].contents[13].text
            self.bfn_rating = table_non_monetizable_metrics.contents[15].contents[13].text
            self.ufr_1000_undissacted_large_area = self._convert(table_non_monetizable_metrics.contents[17].contents[5].text)
            self.ufr_1000_undissacted_large_area_per_km = self._convert(table_non_monetizable_metrics.contents[17].contents[9].text)
            self.ufr_1000_undissacted_large_mammals = self._convert(table_non_monetizable_metrics.contents[19].contents[5].text)
            self.ufr_1000_undissacted_large_mammals_per_km = self._convert(table_non_monetizable_metrics.contents[19].contents[9].text)
            self.count_undissacted_area = self._convert(table_non_monetizable_metrics.contents[21].contents[5].text)
            self.count_reconnect_area = self._convert(table_non_monetizable_metrics.contents[23].contents[5].text)
            self.land_consumption = self._convert(table_non_monetizable_metrics.contents[25].contents[5].text)
            self.flooding_area = self._convert(table_non_monetizable_metrics.contents[27].contents[5].text)
            self.flooding_area_per_km = self._convert(table_non_monetizable_metrics.contents[27].contents[9].text)
            self.water_protection_area = self._convert(table_non_monetizable_metrics.contents[29].contents[5].text)
            self.water_protection_area_per_km = self._convert(table_non_monetizable_metrics.contents[29].contents[9].text)
            self.uzvr = self._convert(table_non_monetizable_metrics.contents[31].contents[5].text)
            self.priority_area_landscape_protection = self._convert(table_non_monetizable_metrics.contents[33].contents[5].text)
            self.priority_area_landscape_protection_per_km = self._convert(table_non_monetizable_metrics.contents[33].contents[9].text)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        element_nm = ("Weitere Sachverhalte Umwelt", "Zusätzliche bewertungsrelevante Sachverhalte")
        try:
            self.environment_additional_informations = self._list_to_string(self._get_all_elements_to_next_same(element_start_tag="h2", element_end_tag="h1", element_text=element_nm[1]))
        except ElementNotInPrinsException:
            logging.warning("Could not find any elements after:" + element_nm[0])

        # spatial significance
        element_nm = ("Raumordnung", "Raumordnerische Beurteilung")
        try:
            self._sp_sig = self._get_all_elements_to_next_same(element_start_tag="h1", element_end_tag="h1", element_text=element_nm[1])[0]
        except ElementNotInPrinsException:
            logging.warning("Could not find any elements after:" + element_nm[0])

        element_nm = ("Gesamtergebnis Raumordnung", "Gesamtergebnis")
        try:
            self.sp_sig_overall_result = self._sp_sig.findChildren("h3")[0].text
        except ElementNotInPrinsException:
            logging.warning("Could not find any elements after: " +  element_nm[0])

        element_nm = ("Begründung Raumordnung", "Begründung Raumordnung")
        try:
            self.sp_sig_reasons = self._list_to_string(self._sp_sig.findChildren("ul"))
        except ElementNotInPrinsException:
            logging.warning("Could not find any elements: " + element_nm[0])

        element_nm = ("Raumordnung Straßenpersonenverkehr", "An- und Verbindungsqualitäten im Straßenpersonenverkehr")
        try:
            self.sp_sig_road = self._get_all_elements_to_next_same(element_start_tag="h3", element_end_tag="h3", element_text=element_nm[1])
        except ElementNotInPrinsException:
            logging.warning("Could not find any elements " + element_nm[0])

        element_nm = ("Erreichbarkeitsdefizite", "Räumliche Ausprägungen von Erreichbarkeitsdefiziten")
        try:
            self.sp_sig_accessibility_deficits = self._get_all_elements_to_next_same(element_start_tag="h3", element_end_tag="h3", element_text=element_nm[1])
        except ElementNotInPrinsException:
            logging.warning("Could not find any elements " + element_nm[0])

        element_nm = ("Zusammenfassung Raumordnung", "Zusammenfassung der Projektwirkungen")
        try:
            self.sp_sig_conclusion = self._get_all_elements_to_next_same(element_start_tag="h3", element_end_tag="h3", element_text=element_nm[1])
        except ElementNotInPrinsException:
            logging.warning("Could not find any elements " + element_nm[0])

        self.complementary_consideration = self._get_element_by_prev(type_of_element='h1', text='Ergänzende Betrachtungen').text

        logging.info("Ended with project: " + project_name)


if __name__ == '__main__':
    project_name = '2-007-V01'
    project = BvwpRail(project_name)


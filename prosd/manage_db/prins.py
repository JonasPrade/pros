from bs4 import BeautifulSoup as bs
import logging
import os
import requests
import sqlalchemy


# from prosd import models, app, db


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

        # a dict for updating the db with the data of the prins
        self.db_dict = {}

    def _import_from_prins(self):
        if not os.path.exists(self.filepath):
            self._download_project()

        with open(self.filepath, 'r', encoding='utf-8') as f:
            text = f.read()

        # converts it to beautiful self.soup
        soup = bs(text, 'html.parser')
        return soup

    def _download_project(self):
        url_project = self._URL_PRINS + self.project_id + "/" + self.project_id + ".html"
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
                    if selected_element == None:
                        logging.warning(
                            'Breaked a search between elements because of an None-element (maybe ending div) ' + str(
                                element_text))
                        break  # can happen if a div ends, but then the searched process should be over too
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

        if input_float == '-' or input_float == '- ':
            input_float = None
        else:
            try:
                # converts a float 12.452,234 to a float that python accepts
                input_float = input_float.replace('.', '')
                input_float = float(input_float.replace(',', '.'))
            except ValueError:
                if input_float == '2) s 110' or input_float == '1) s 110':
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

    def _str_to_list(self, input_str, sep=', '):
        """
        transforms a str seperated by an sep_value to an list
        :param input_str: str
        :param sep: seperator element, usual ", " (yes with an blank after the comma)
        :return:
        """
        list = input_str.split(sep)

        return list


class BvwpRail(Bvwp):
    def __init__(self, project_name):
        super().__init__(project_name)

        logging.info("Starting with project: " + project_name)

        self.dict_project_content = {}

        tbl_nm = ('Basisdaten', 'Projektnummer')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1])
            # self.bvwp_id = self.soup.find_all('table')[tbl_nr].contents[1].contents[1].text  #  actual not needed
            # because Bvwp class only works with id
            self.title = self.soup.find_all('table')[tbl_nr].contents[3].contents[1].text
            self.content = self.soup.find_all('table')[tbl_nr].contents[7].contents[
                1].text
            self.length = self._convert(self.soup.find_all('table')[tbl_nr].contents[9].contents[1].text[:-3].replace(',', '.'))
            add_dict = {
                "name": self.title,
                "description": self.content,
                "length": self.length,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # prio calculation_methods
        tbl_nm = ('Dringlichkeit BVWP', 'Dringlichkeitseinstufung')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1])
            self.prio_bvwp = self.soup.find_all('table')[tbl_nr].contents[1].contents[1].text
            add_dict = {
                "priority": self.prio_bvwp,
            }
            self.dict_project_content.update(add_dict)
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
            self.planning_cost_incurred = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[9].contents[1].text)
            self.total_budget_relevant_cost = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[11].contents[1].text)
            self.total_budget_relevant_cost_incurred = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[13].contents[1].text)
            self.valuation_relevant_cost = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[15].contents[1].text)
            self.valuation_relevant_cost_pricelevel_2012 = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[17].contents[1].text)

            add_dict = {
                "bvwp_planned_cost": self.building_cost,
                "bvwp_planned_maintenance_cost": self.maintenance_cost,
                "bvwp_planned_planning_cost": self.planning_cost,
                "bvwp_planned_planning_cost_incurred": self.planning_cost_incurred,
                "bvwp_total_budget_relevant_cost": self.total_budget_relevant_cost,
                "bvwp_total_budget_relevant_cost_incurred": self.total_budget_relevant_cost_incurred,
                "bvwp_valuation_relevant_cost": self.valuation_relevant_cost,
                "bvwp_valuation_relevant_cost_pricelevel_2012": self.valuation_relevant_cost_pricelevel_2012,
            }
            self.dict_project_content.update(add_dict)
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
            self.bottleneck_elimination = self._yesno_to_bool(
                self.soup.find_all('table')[tbl_nr].contents[9].contents[1].text)
            self.traveltime_reductions = self._convert(self.soup.find_all('table')[4].contents[11].contents[1].text)
            add_dict = {
                "nkv": self.nkv,
                "bvwp_environmental_impact": self.environmental_impact,
                "bvwp_regional_significance": self.regional_significance,
                "bottleneck_elimination": self.bottleneck_elimination,
                "traveltime_reduction": self.traveltime_reductions,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        h_nm = ('Dringlichkeitseinstufung', 'Begründung der Dringlichkeitseinstufung')
        try:
            priority_reason_list = self._get_all_elements_to_next_same(element_start_tag='h2', element_end_tag='h2',
                                                                       element_text=h_nm[1])
            self.priority_reason = self._list_to_string(priority_reason_list)
            add_dict = {
                "reason_priority": self.priority_reason,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("No element found with starting h2 " + h_nm[0])
        finally:
            h_nm = []

        h_nm = ('Projektbegründung', 'Projektbegründung/Notwendigkeit des Projektes')
        try:
            project_reason_list = self._get_all_elements_to_next_same(element_start_tag='h2', element_end_tag='h1',
                                                                      element_text=h_nm[1])
            self.project_reason = self._list_to_string(project_reason_list)
            add_dict = {
                "reason_project": self.project_reason,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("No element found with starting h2 " + h_nm[0])
        finally:
            h_nm = []

        tbl_nm = ('Länder, Kreise und Wahlkreise', 'Länderübergreifendes Projekt')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1])
            self.states = self._str_to_list(self.soup.find_all('table')[tbl_nr].contents[3].contents[1].contents[0])
            counties = self._str_to_list(self.soup.find_all('table')[tbl_nr].contents[5].contents[1].contents[0],
                                         sep='; ')
            self.counties = []
            for county in counties:
                try:
                    county_name, county_type = county.split(',', 1)
                    self.counties.append((county_name.strip(), county_type.strip()))
                except ValueError:
                    self.counties.append((county, None))

            constituencies = self._str_to_list(self.soup.find_all('table')[tbl_nr].contents[7].contents[1].contents[0], sep=';')
            self.constituencies = []
            for c in constituencies:
                c_name, c_id = c.split('(', 1)
                c_name = c_name.strip()
                c_id = int(c_id.replace(")",""))
                self.constituencies.append((c_name, c_id))
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
            add_dict = {
                "bvwp_alternatives": self.alternatives
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("No element found with starting h2 " + h_nm[0])
        finally:
            h_nm = []

        # Vermeidung der Überlastung im Schienennetz
        tbl_nm = ("Kilometer Schiene mit einer Überlastung", "Anzahl Kilometer Schiene mit einer Überlastung")
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], column_first_text=1)
            self.congested_rail_reference_6to9_km = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[7].contents[1].text.split("km")[0])
            self.congested_rail_reference_6to9_perc = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[7].contents[1].text.split("km")[1][2:-2])
            self.congested_rail_plancase_6to9_km = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[7].contents[2].text.split("km")[0])
            self.congested_rail_plancase_6to9_perc = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[7].contents[2].text.split("km")[1][2:-2])

            self.congested_rail_reference_9to16_km = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[9].contents[1].text.split("km")[0])
            self.congested_rail_reference_9to16_perc = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[9].contents[1].text.split("km")[1][2:-2])
            self.congested_rail_plancase_9to16_km = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[9].contents[2].text.split("km")[0])
            self.congested_rail_plancase_9to16_perc = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[9].contents[2].text.split("km")[1][2:-2])

            self.congested_rail_reference_16to19_km = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[11].contents[1].text.split("km")[0])
            self.congested_rail_reference_16to19_perc = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[11].contents[1].text.split("km")[1][2:-2])
            self.congested_rail_plancase_16to19_km = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[11].contents[2].text.split("km")[0])
            self.congested_rail_plancase_16to19_perc = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[11].contents[2].text.split("km")[1][2:-2])

            self.congested_rail_reference_19to22_km = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[13].contents[1].text.split("km")[0])
            self.congested_rail_reference_19to22_perc = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[13].contents[1].text.split("km")[1][2:-2])
            self.congested_rail_plancase_19to22_km = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[13].contents[2].text.split("km")[0])
            self.congested_rail_plancase_19to22_perc = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[13].contents[2].text.split("km")[1][2:-2])

            self.congested_rail_reference_22to6_km = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[15].contents[1].text.split("km")[0])
            self.congested_rail_reference_22to6_perc = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[15].contents[1].text.split("km")[1][2:-2])
            self.congested_rail_plancase_22to6_km = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[15].contents[2].text.split("km")[0])
            self.congested_rail_plancase_22to6_perc = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[15].contents[2].text.split("km")[1][2:-2])

            self.congested_rail_reference_day_km = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[17].contents[1].text.split("km")[0])
            self.congested_rail_reference_day_perc = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[17].contents[1].text.split("km")[1][2:-2])
            self.congested_rail_plancase_day_km = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[17].contents[2].text.split("km")[0])
            self.congested_rail_plancase_day_perc = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[17].contents[2].text.split("km")[1][2:-2])
            add_dict = {
                "bvwp_congested_rail_reference_6to9_km": self.congested_rail_reference_6to9_km,
                "bvwp_congested_rail_reference_6to9_perc": self.congested_rail_reference_6to9_perc,
                "bvwp_congested_rail_plancase_6to9_km": self.congested_rail_plancase_6to9_km,
                "bvwp_congested_rail_plancase_6to9_perc": self.congested_rail_plancase_6to9_perc,

                "bvwp_congested_rail_reference_9to16_km": self.congested_rail_reference_9to16_km,
                "bvwp_congested_rail_reference_9to16_perc": self.congested_rail_reference_9to16_perc,
                "bvwp_congested_rail_plancase_9to16_km": self.congested_rail_plancase_9to16_km,
                "bvwp_congested_rail_plancase_9to16_perc": self.congested_rail_plancase_9to16_perc,

                "bvwp_congested_rail_reference_16to19_km": self.congested_rail_reference_16to19_km,
                "bvwp_congested_rail_reference_16to19_perc": self.congested_rail_reference_16to19_perc,
                "bvwp_congested_rail_plancase_16to19_km": self.congested_rail_plancase_16to19_km,
                "bvwp_congested_rail_plancase_16to19_perc": self.congested_rail_plancase_16to19_perc,

                "bvwp_congested_rail_reference_19to22_km": self.congested_rail_reference_19to22_km,
                "bvwp_congested_rail_reference_19to22_perc": self.congested_rail_reference_19to22_perc,
                "bvwp_congested_rail_plancase_19to22_km": self.congested_rail_plancase_19to22_km,
                "bvwp_congested_rail_plancase_19to22_perc": self.congested_rail_plancase_19to22_perc,

                "bvwp_congested_rail_reference_22to6_km": self.congested_rail_reference_22to6_km,
                "bvwp_congested_rail_reference_22to6_perc": self.congested_rail_reference_22to6_perc,
                "bvwp_congested_rail_plancase_22to6_km": self.congested_rail_plancase_22to6_km,
                "bvwp_congested_rail_plancase_22to6_perc": self.congested_rail_plancase_22to6_perc,

                "bvwp_congested_rail_reference_day_km": self.congested_rail_reference_day_km,
                "bvwp_congested_rail_reference_day_perc": self.congested_rail_reference_day_perc,
                "bvwp_congested_rail_plancase_day_km": self.congested_rail_plancase_day_km,
                "bvwp_congested_rail_plancase_day_perc": self.congested_rail_plancase_day_perc,
            }
            self.dict_project_content.update(add_dict)

        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # Auswirkung auf Verspätung und Betriebsstabilität
        tbl_nm = ('außerplanmäßige Wartezeiten',
                  'Entwicklung von außerplanmäßigen Wartezeiten (vergleichbar mit Stauwartezeiten) im deutschen Netz')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], column_first_text=1)
            self.unscheduled_waiting_period_reference_case = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[3].contents[1].text[:-8])
            self.unscheduled_waiting_period_plan_case = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[5].contents[1].text[:-8])

            add_dict = {
                "bvwp_unscheduled_waiting_period_reference": self.unscheduled_waiting_period_reference_case,
                "bvwp_unscheduled_waiting_period_plancase": self.unscheduled_waiting_period_plan_case,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        tbl_nm = ('Zuverlässigkeit', 'Veränderung der Zuverlässigkeit')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], row_first_text=0)
            punctuality_cargo_reference = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[2].contents[1].text)
            if punctuality_cargo_reference:
                self.punctuality_cargo_reference = punctuality_cargo_reference/100
            else:
                self.punctuality_cargo_reference = None
            self.delta_punctuality_cargo_relativ = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[4].contents[1].text)
            self.delta_punctuality_cargo_absolut = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[6].contents[1].text)
            add_dict = {
                "bvwp_punctuality_cargo_reference": self.punctuality_cargo_reference,
                "bvwp_delta_punctuality_relativ": self.delta_punctuality_cargo_relativ,
                "bvwp_delta_punctuality_absolut": self.delta_punctuality_cargo_absolut,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # changing in travel time
        element_nm = ("ausgewählte Fahrzeitverkürzungen", "Ausgewählte Fahrzeitverkürzung im Maßnahmenbereich")
        try:
            self.change_traveltime_examples = self._list_to_string(self._get_all_elements_to_next_same(
                element_start_tag="h2", element_end_tag="h1", element_text=element_nm[1]))
            add_dict = {
                "bvwp_traveltime_examples": self.change_traveltime_examples
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Couldn't find any elements after " + element_nm[0])

        # Auswirkungen auf den Personenverkehr
        tbl_nm = ('Auswirkungen Personenverkehr', 'Auswirkungen des Projektes auf den Personenverkehr')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], row_first_text=0)
            self.relocation_car_to_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[4].contents[1].text)
            self.relocation_rail_to_car = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[6].contents[1].text)
            self.relocation_air_to_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[8].contents[1].text)
            self.induced_traffic = self._convert(self.soup.find_all('table')[tbl_nr].contents[10].contents[1].text)
            self.delta_car_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[12].contents[1].text)
            self.delta_rail_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[14].contents[1].text)
            self.delta_rail_running_time = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[16].contents[1].text)
            self.delta_km_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[20].contents[1].text)  # verbleibender Verkehr im SPNV
            self.delta_km_car_to_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[22].contents[1].text)
            self.delta_km_rail_to_car = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[24].contents[1].text)
            self.delta_km_air_to_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[26].contents[1].text)
            self.delta_rail_km_induced = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[28].contents[1].text)
            self.delta_travel_time_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[32].contents[1].text)
            self.delta_travel_time_car_to_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[34].contents[1].text)
            self.delta_travel_time_rail_to_car = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[36].contents[1].text)
            self.delta_travel_time_air_to_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[38].contents[1].text)
            self.delta_travel_time_induced = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[40].contents[1].text)

            add_dict = {
                "relocation_car_to_rail": self.relocation_car_to_rail,
                "relocation_rail_to_car": self.relocation_rail_to_car,
                "relocation_air_to_rail": self.relocation_air_to_rail,
                "induced_traffic": self.induced_traffic,
                "delta_car_km": self.delta_car_km,
                "delta_km_rail": self.delta_rail_km,
                "delta_rail_running_time": self.delta_rail_running_time,
                "delta_rail_km_rail": self.delta_km_rail,
                "delta_rail_km_car_to_rail": self.delta_km_car_to_rail,
                "delta_rail_km_rail_to_car": self.delta_km_rail_to_car,
                "delta_rail_km_air_to_rail": self.delta_km_air_to_rail,
                "delta_rail_km_induced": self.delta_rail_km_induced,
                "delta_travel_time_rail": self.delta_travel_time_rail,
                "delta_travel_time_car_to_rail": self.delta_travel_time_car_to_rail,
                "delta_travel_time_rail_to_car": self.delta_travel_time_rail_to_car,
                "delta_travel_time_air_to_rail": self.delta_travel_time_air_to_rail,
                "delta_travel_time_induced": self.delta_travel_time_induced,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # Auswirkungen auf den Güterverkehr
        tbl_nm = ('Auswirkungen Güterverkehr', 'Auswirkungen des Projektes auf den Güterverkehr')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], row_first_text=0)
            self.relocation_truck_to_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[4].contents[1].text)
            self.relocation_ship_to_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[6].contents[1].text)
            self.delta_truck_km = self._convert(self.soup.find_all('table')[tbl_nr].contents[8].contents[1].text)
            self.delta_truck_count = self._convert(self.soup.find_all('table')[tbl_nr].contents[10].contents[1].text)
            self.delta_rail_cargo_count = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[12].contents[1].text)
            self.delta_rail_cargo_running_time = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[14].contents[1].text)
            self.delta_rail_cargo_km_lkw_to_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[18].contents[1].text)
            self.delta_rail_cargo_km_ship_to_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[20].contents[1].text)
            self.delta_rail_cargo_time_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[24].contents[1].text)
            self.delta_rail_cargo_time_lkw_to_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[26].contents[1].text)
            self.delta_rail_cargo_time_ship_to_rail = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[28].contents[1].text)
            add_dict = {
                "relocation_truck_to_rail": self.relocation_truck_to_rail,
                "relocation_ship_to_rail": self.relocation_ship_to_rail,
                "delta_truck_km": self.delta_truck_km,
                "delta_truck_count": self.delta_truck_count,
                "delta_rail_cargo_count": self.delta_rail_cargo_count,
                "delta_rail_cargo_running_time": self.delta_rail_cargo_running_time,
                "delta_rail_cargo_km_lkw_to_rail": self.delta_rail_cargo_km_lkw_to_rail,
                "delta_rail_cargo_km_ship_to_rail": self.delta_rail_cargo_km_ship_to_rail,
                "delta_rail_cargo_time_rail": self.delta_rail_cargo_time_rail,
                "delta_rail_cargo_time_lkw_to_rail": self.delta_rail_cargo_time_lkw_to_rail,
                "delta_rail_cargo_time_ship_to_rail": self.delta_rail_cargo_time_ship_to_rail,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # Abgasemissionen
        tbl_nm = ('Veränderung Abgasemssionen',
                  'Veränderung der Abgasemissionen (Summe Personen- und Güterverkehr über alle Verkehrsmittel, Planfall - Bezugsfall)')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], row_first_text=0)
            self.delta_nox = self._convert(self.soup.find_all('table')[tbl_nr].contents[2].contents[1].text)
            self.delta_co = self._convert(self.soup.find_all('table')[tbl_nr].contents[4].contents[1].text)
            self.delta_co2 = self._convert(self.soup.find_all('table')[tbl_nr].contents[6].contents[1].text)
            self.delta_hc = self._convert(self.soup.find_all('table')[tbl_nr].contents[8].contents[1].text)
            self.delta_pm = self._convert(self.soup.find_all('table')[tbl_nr].contents[10].contents[1].text)
            self.delta_so2 = self._convert(self.soup.find_all('table')[tbl_nr].contents[12].contents[1].text)
            add_dict = {
                "delta_nox": self.delta_nox,
                "delta_co": self.delta_co,
                "delta_co2": self.delta_co2,
                "delta_hc": self.delta_hc,
                "delta_pm": self.delta_pm,
                "delta_so2": self.delta_so2,
            }
            self.dict_project_content.update(add_dict)
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
            self.use_change_operating_cost_car_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[4].contents[2].text)
            self.use_change_operating_cost_car_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[4].contents[3].text)
            self.use_change_operating_cost_rail_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[6].contents[2].text)
            self.use_change_operating_cost_rail_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[6].contents[3].text)
            self.use_change_operating_cost_air_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[8].contents[2].text)
            self.use_change_operating_cost_air_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[8].contents[3].text)
            self.use_change_pollution_car_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[12].contents[2].text)
            self.use_change_pollution_car_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[12].contents[3].text)
            self.use_change_pollution_rail_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[14].contents[2].text)
            self.use_change_pollution_rail_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[14].contents[3].text)
            self.use_change_pollution_air_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[16].contents[2].text)
            self.use_change_pollution_air_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[16].contents[3].text)
            self.use_change_safety_car_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[20].contents[2].text)
            self.use_change_safety_car_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[20].contents[3].text)
            self.use_change_safety_rail_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[22].contents[2].text)
            self.use_change_safety_rail_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[22].contents[3].text)
            self.use_change_travel_time_rail_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[26].contents[2].text)
            self.use_change_travel_time_rail_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[26].contents[3].text)
            self.use_change_travel_time_induced_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[28].contents[2].text)
            self.use_change_travel_time_induced_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[28].contents[3].text)
            self.use_change_travel_time_pkw_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[30].contents[2].text)
            self.use_change_travel_time_pkw_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[30].contents[3].text)
            self.use_change_travel_time_air_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[32].contents[2].text)
            self.use_change_travel_time_air_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[32].contents[3].text)
            self.use_change_travel_time_less_2min_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[34].contents[2].text)
            self.use_change_travel_time_less_2min_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[34].contents[3].text)
            self.use_change_implicit_benefit_induced_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[38].contents[2].text)
            self.use_change_implicit_benefit_induced_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[38].contents[3].text)
            self.use_change_implicit_benefit_pkw_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[40].contents[2].text)
            self.use_change_implicit_benefit_pkw_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[40].contents[3].text)
            self.use_change_implicit_benefit_air_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[42].contents[2].text)
            self.use_change_implicit_benefit_air_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[42].contents[3].text)
            self.use_sum_passenger_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[44].contents[2].text)
            self.use_sum_passenger_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[44].contents[3].text)

            add_dict = {
                "use_change_operation_cost_car_yearly": self.use_change_operating_cost_car_yearly,
                "use_change_operation_cost_car_present_value": self.use_change_operating_cost_car_present_value,
                "use_change_operating_cost_rail_yearly": self.use_change_operating_cost_rail_yearly,
                "use_change_operating_cost_rail_present_value": self.use_change_operating_cost_rail_present_value,
                "use_change_operating_cost_air_yearly": self.use_change_operating_cost_air_yearly,
                "use_change_operating_cost_air_present_value": self.use_change_operating_cost_air_present_value,
                "use_change_pollution_car_yearly": self.use_change_pollution_car_yearly,
                "use_change_pollution_car_present_value": self.use_change_pollution_car_present_value,
                "use_change_pollution_rail_yearly": self.use_change_pollution_rail_yearly,
                "use_change_pollution_rail_present_value": self.use_change_pollution_rail_present_value,
                "use_change_pollution_air_yearly": self.use_change_pollution_air_yearly,
                "use_change_pollution_air_present_value": self.use_change_pollution_air_present_value,
                "use_change_safety_car_yearly": self.use_change_safety_car_yearly,
                "use_change_safety_car_present_value": self.use_change_safety_car_present_value,
                "use_change_safety_rail_yearly": self.use_change_safety_rail_yearly,
                "use_change_safety_rail_present_value": self.use_change_safety_rail_present_value,

                "use_change_travel_time_rail_yearly": self.use_change_travel_time_rail_yearly,
                "use_change_travel_time_induced_yearly": self.use_change_travel_time_induced_yearly,
                "use_change_travel_time_pkw_yearly": self.use_change_travel_time_pkw_yearly,
                "use_change_travel_time_air_yearly": self.use_change_travel_time_air_yearly,
                "use_change_travel_time_less_2min_yearly": self.use_change_travel_time_less_2min_yearly,
                "use_change_implicit_benefit_induced_yearly": self.use_change_implicit_benefit_induced_yearly,
                "use_change_implicit_benefit_pkw_yearly": self.use_change_implicit_benefit_pkw_yearly,
                "use_change_implicit_benefit_air_yearly": self.use_change_implicit_benefit_air_yearly,
                "use_sum_passenger_yearly": self.use_sum_passenger_yearly,
                "use_change_travel_time_rail_present_value": self.use_change_travel_time_rail_present_value,
                "use_change_travel_time_induced_present_value": self.use_change_travel_time_induced_present_value,
                "use_change_travel_time_pkw_present_value": self.use_change_travel_time_pkw_present_value,
                "use_change_travel_time_air_present_value": self.use_change_travel_time_air_present_value,
                "use_change_travel_time_less_2min_present_value": self.use_change_travel_time_less_2min_present_value,
                "use_change_implicit_benefit_induced_present_value": self.use_change_implicit_benefit_induced_present_value,
                "use_change_implicit_benefit_pkw_present_value": self.use_change_implicit_benefit_pkw_present_value,
                "use_change_implicit_benefit_air_present_value": self.use_change_implicit_benefit_air_present_value,
                "use_sum_passenger_present_value": self.use_sum_passenger_present_value,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        # # use cargo
        tbl_nm = ('Nutzen Güterverkehr', 'Nutzenkomponenten des Güterverkehrs')
        try:
            tbl_nr = self._get_table_nr(tbl_nm[1], row_first_text=0)
            self.use_change_operating_cost_truck_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[4].contents[2].text)
            self.use_change_operating_cost_truck_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[4].contents[3].text)
            self.use_change_operating_cost_rail_cargo_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[6].contents[2].text)
            self.use_change_operating_cost_rail_cargo_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[6].contents[3].text)
            self.use_change_operating_cost_ship_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[8].contents[2].text)
            self.use_change_operating_cost_ship_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[8].contents[3].text)
            self.use_change_pollution_truck_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[12].contents[2].text)
            self.use_change_pollution_truck_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[12].contents[3].text)
            self.use_change_pollution_rail_cargo_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[14].contents[2].text)
            self.use_change_pollution_rail_cargo_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[14].contents[3].text)
            self.use_change_pollution_ship_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[16].contents[2].text)
            self.use_change_pollution_ship_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[16].contents[3].text)
            self.use_change_safety_truck_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[20].contents[2].text)
            self.use_change_safety_truck_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[20].contents[3].text)
            self.use_change_safety_rail_cargo_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[22].contents[2].text)
            self.use_change_safety_rail_cargo_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[22].contents[3].text)
            self.use_change_safety_ship_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[24].contents[2].text)
            self.use_change_safety_ship_present_value = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[24].contents[3].text)
            self.use_change_running_time_rail_cargo_yearly = self._convert(
                self.soup.find_all('table')[tbl_nr].contents[28].contents[2].text)
            self.use_change_running_time_rail_cargo_present_value = self._convert(
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

            add_dict = {
                "use_change_operating_cost_truck_yearly": self.use_change_operating_cost_truck_yearly,
                "use_change_operating_cost_rail_cargo_yearly": self.use_change_operating_cost_rail_cargo_yearly,
                "use_change_operating_cost_ship_yearly": self.use_change_operating_cost_ship_yearly,
                "use_change_pollution_truck_yearly": self.use_change_pollution_truck_yearly,
                "use_change_pollution_rail_cargo_yearly": self.use_change_pollution_rail_cargo_yearly,
                "use_change_pollution_ship_yearly": self.use_change_pollution_ship_yearly,
                "use_change_safety_truck_yearly": self.use_change_safety_truck_yearly,
                "use_change_safety_rail_cargo_yearly": self.use_change_safety_rail_cargo_yearly,
                "use_change_safety_ship_yearly": self.use_change_safety_ship_yearly,
                "use_change_running_time_rail_yearly": self.use_change_running_time_rail_cargo_yearly,
                "use_change_running_time_lkw_yearly": self.use_change_running_time_lkw_yearly,
                "use_change_running_time_ship_yearly": self.use_change_running_time_ship_yearly,
                "use_change_implicit_benefit_truck_yearly": self.use_change_implicit_benefit_truck_yearly,
                "use_change_implicit_benefit_ship_yearly": self.use_change_implicit_benefit_ship_yearly,
                "use_change_reliability_yearly": self.use_change_reliability_yearly,
                "use_sum_cargo_yearly": self.use_sum_cargo_yearly,

                "use_change_operating_cost_truck_present_value": self.use_change_operating_cost_truck_present_value,
                "use_change_operating_cost_rail_cargo_present_value": self.use_change_operating_cost_rail_cargo_present_value,
                "use_change_operating_cost_ship_present_value": self.use_change_operating_cost_ship_present_value,
                "use_change_pollution_truck_present_value": self.use_change_pollution_truck_present_value,
                "use_change_pollution_rail_cargo_present_value": self.use_change_pollution_rail_cargo_present_value,
                "use_change_pollution_ship_present_value": self.use_change_pollution_ship_present_value,
                "use_change_safety_truck_present_value": self.use_change_safety_truck_present_value,
                "use_change_safety_rail_cargo_present_value": self.use_change_safety_rail_cargo_present_value,
                "use_change_safety_ship_present_value": self.use_change_safety_ship_present_value,
                "use_change_running_time_rail_present_value": self.use_change_running_time_rail_cargo_present_value,
                "use_change_running_time_lkw_present_value": self.use_change_running_time_lkw_present_value,
                "use_change_running_time_ship_present_value": self.use_change_running_time_ship_present_value,
                "use_change_implicit_benefit_truck_present_value": self.use_change_implicit_benefit_truck_present_value,
                "use_change_implicit_benefit_ship_present_value": self.use_change_implicit_benefit_ship_present_value,
                "use_change_reliability_present_value": self.use_change_reliability_present_value,
                "use_sum_cargo_present_value": self.use_sum_cargo_present_value,
            }
            self.dict_project_content.update(add_dict)
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

            add_dict = {
                "use_change_maintenance_cost_yearly": self.use_change_maintenance_costs_yearly,
                "use_change_lcc_infrastructure_yearly": self.use_change_lcc_infrastructure_yearly,
                "use_change_noise_intown_yearly": self.use_change_noise_intown_yearly,
                "use_change_noise_outtown_yearly": self.use_change_noise_outtown_yearly,
                "sum_use_change_yearly": self.sum_use_change_yearly,

                "use_change_maintenance_cost_present_value": self.use_change_maintenance_costs_present_value,
                "use_change_lcc_infrastructure_present_value": self.use_change_lcc_infrastructure_present_value,
                "use_change_noise_intown_present_value": self.use_change_noise_intown_present_value,
                "use_change_noise_outtown_present_value": self.use_change_noise_outtown_present_value,
                "sum_use_change_present_value": self.sum_use_change_present_value,
            }
            self.dict_project_content.update(add_dict)
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

            add_dict = {
                "bvwp_valuation_relevant_cost_pricelevel_2012_planning_cost": self.valuation_relevant_cost_pricelevel_2012_planning_cost,
                "bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cos": self.valuation_relevant_cost_pricelevel_2012_infrastructure_cost,
                "bvwp_valuation_relevant_cost_pricelevel_2012_present_value": self.valuation_relevant_cost_pricelevel_2012_present_value,
            }
            self.dict_project_content.update(add_dict)
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
            add_dict = {
                "bvwp_duration_of_outstanding_planning": self.duration_of_outstanding_planning,
                "bvwp_duration_of_build": self.duration_of_build,
                "bvwp_duration_operating": self.duration_operating,
            }
            self.dict_project_content.update(add_dict)
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
            add_dict = {
                "bvwp_sum_use_environment": self.sum_use_environment,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        tbl_nm = (
        'Umweltbetroffenheit', 'Umweltbeitrag Teil 2: Umwelt-Betroffenheit 	[gering/mittel/hoch] oder "Projekt '
                               'planfestgestellt"')
        try:
            tbl_nr = self._get_table_nr(
                'Umweltbeitrag Teil 2: Umwelt-Betroffenheit 	[gering/mittel/hoch] oder "Projekt '
                'planfestgestellt"')
            self.sum_environmental_affectedness = str(
                self.soup.find_all('table')[tbl_nr].contents[1].contents[1].text)
            self.sum_environmental_affectedness_text = str(
                self.soup.find_all('table')[tbl_nr].contents[3].text)

            add_dict = {
                "bvwp_sum_environmental_affectedness": self.sum_environmental_affectedness,
                "bvwp_sum_environmental_affectedness_text": self.sum_environmental_affectedness_text,
            }
            self.dict_project_content.update(add_dict)
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
            self.noise_new_affected = self._convert(table_monetizable_metrics.contents[7].contents[2].contents[0].text)
            self.noise_relieved = self._convert(table_monetizable_metrics.contents[9].contents[2].contents[0].text)
            self.change_noise_outtown = self._convert(table_monetizable_metrics.contents[11].contents[2].contents[0].text)
            add_dict = {
                "noise_new_affected": self.noise_new_affected,
                "noise_relieved": self.noise_relieved,
                "change_noise_outtown": self.change_noise_outtown,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        tbl_nm = ('Umweltbeitrag nicht monetarisiert', 'Umweltbeitrag Teil 2')
        try:
            table_non_monetizable_metrics = self._get_element_by_prev(type_of_element='h3', text='Umweltbeitrag Teil 2')
            self.area_nature_high_importance = self._convert(table_non_monetizable_metrics.contents[5].contents[5].text)
            self.area_nature_high_importance_per_km = self._convert(
                table_non_monetizable_metrics.contents[5].contents[9].text)
            self.area_nature_high_importance_rating = table_non_monetizable_metrics.contents[5].contents[13].text
            self.natura2000_rating = table_non_monetizable_metrics.contents[7].contents[13].text
            self.natura2000_not_excluded = self._convert(table_non_monetizable_metrics.contents[9].contents[5].text)
            self.natura2000_probably = self._convert(table_non_monetizable_metrics.contents[11].contents[5].text)
            self.ufr_250 = self._convert(table_non_monetizable_metrics.contents[13].contents[5].text)
            self.ufr_250_per_km = self._convert(table_non_monetizable_metrics.contents[13].contents[9].text)
            self.ufr_250_rating = table_non_monetizable_metrics.contents[13].contents[13].text
            self.bfn_rating = table_non_monetizable_metrics.contents[15].contents[13].text
            self.ufr_1000_undissacted_large_area = self._convert(
                table_non_monetizable_metrics.contents[17].contents[5].text)
            self.ufr_1000_undissacted_large_area_per_km = self._convert(
                table_non_monetizable_metrics.contents[17].contents[9].text)
            self.ufr_1000_undissacted_large_mammals = self._convert(
                table_non_monetizable_metrics.contents[19].contents[5].text)
            self.ufr_1000_undissacted_large_mammals_per_km = self._convert(
                table_non_monetizable_metrics.contents[19].contents[9].text)
            self.count_undissacted_area = self._convert(table_non_monetizable_metrics.contents[21].contents[5].text)
            self.count_reconnect_area = self._convert(table_non_monetizable_metrics.contents[23].contents[5].text)
            self.land_consumption = self._convert(table_non_monetizable_metrics.contents[25].contents[5].text)
            self.flooding_area = self._convert(table_non_monetizable_metrics.contents[27].contents[5].text)
            self.flooding_area_per_km = self._convert(table_non_monetizable_metrics.contents[27].contents[9].text)
            self.flooding_area_rating = table_non_monetizable_metrics.contents[27].contents[13].text
            self.water_protection_area = self._convert(table_non_monetizable_metrics.contents[29].contents[5].text)
            self.water_protection_area_per_km = self._convert(
                table_non_monetizable_metrics.contents[29].contents[9].text)
            self.water_protection_rating = table_non_monetizable_metrics.contents[29].contents[13].text
            self.uzvr = self._convert(table_non_monetizable_metrics.contents[31].contents[5].text)
            self.uvzr_rating = table_non_monetizable_metrics.contents[31].contents[13].text
            self.priority_area_landscape_protection = self._convert(
                table_non_monetizable_metrics.contents[33].contents[5].text)
            self.priority_area_landscape_protection_per_km = self._convert(
                table_non_monetizable_metrics.contents[33].contents[9].text)
            self.priority_area_landscape_protection_rating = table_non_monetizable_metrics.contents[33].contents[13].text

            add_dict = {
                "area_nature_high_importance": self.area_nature_high_importance,
                "area_nature_high_importance_per_km": self.area_nature_high_importance_per_km,
                "area_nature_high_importance_rating": self.area_nature_high_importance_rating,
                "natura2000_rating": self.natura2000_rating,
                "natura2000_not_excluded": self.natura2000_not_excluded,
                "natura2000_probably": self.natura2000_probably,
                "ufr_250": self.ufr_250,
                "ufr_250_per_km": self.ufr_250_per_km,
                "ufra_250_rating": self.ufr_250_rating,
                "bfn_rating": self.bfn_rating,
                "ufr_1000_undissacted_large_area": self.ufr_1000_undissacted_large_area,
                "ufr_1000_undissacted_large_area_per_km": self.ufr_1000_undissacted_large_area_per_km,
                "ufr_1000_undissacted_large_mammals": self.ufr_1000_undissacted_large_mammals,
                "ufr_1000_undissacted_large_mammals_per_km": self.ufr_1000_undissacted_large_mammals_per_km,
                "count_undissacted_area": self.count_undissacted_area,
                "count_reconnect_area": self.count_reconnect_area,
                "land_consumption": self.land_consumption,
                "flooding_area": self.flooding_area,
                "flooding_area_per_km": self.flooding_area_per_km,
                "flooding_area_rating": self.flooding_area_rating,
                "water_protection_area": self.water_protection_area,
                "water_protection_area_per_km": self.water_protection_area_per_km,
                "water_protection_area_rating": self.water_protection_rating,
                "uzvr": self.uzvr,
                "uvzr_rating": self.uvzr_rating,
                "priortiy_area_landscape_protection": self.priority_area_landscape_protection,
                "priority_area_landscape_protection_per_km": self.priority_area_landscape_protection_per_km,
                "priority_area_landscape_protection_rating": self.priority_area_landscape_protection_rating,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Could not find table " + tbl_nm[0] + " in Prins")
        finally:
            tbl_nm = None
            tbl_nr = None

        element_nm = ("Weitere Sachverhalte Umwelt", "Zusätzliche bewertungsrelevante Sachverhalte")
        try:
            self.environment_additional_informations = self._list_to_string(
                self._get_all_elements_to_next_same(element_start_tag="h2", element_end_tag="h1",
                                                    element_text=element_nm[1]))
            add_dict = {
                "environmental_additional_informations": self.environment_additional_informations
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Could not find any elements after:" + element_nm[0])

        # spatial significance
        element_nm = ("Raumordnung", "Raumordnerische Beurteilung")
        spatial_significance_blacklist = [
            'Eine raumordnerische Analyse wurde nicht durchgeführt.',
            'Das Projekt weist keine signifikante raumordnerische Wirkung auf.'
        ]
        try:
            self._sp_sig = self._get_all_elements_to_next_same(element_start_tag="h1", element_end_tag="h1",
                                                               element_text=element_nm[1])[0]
        except ElementNotInPrinsException:
            logging.warning("Could not find any elements after:" + element_nm[0])

        if not self._sp_sig.text in spatial_significance_blacklist:

            element_nm = ("Gesamtergebnis Raumordnung", "Gesamtergebnis")
            try:
                self.sp_sig_overall_result = self._sp_sig.findChildren("h3")[0].text
                add_dict = {
                    "spatial_significance_overall_result": self.sp_sig_overall_result,
                }
                self.dict_project_content.update(add_dict)
            except ElementNotInPrinsException:
                logging.warning("Could not find any elements after: " + element_nm[0])

            element_nm = ("Begründung Raumordnung", "Begründung Raumordnung")
            try:
                self.sp_sig_reasons = self._list_to_string(self._sp_sig.findChildren("ul"))
                add_dict = {
                    "spatial_significance_reasons": self.sp_sig_reasons,
                }
                self.dict_project_content.update(add_dict)
            except ElementNotInPrinsException:
                logging.warning("Could not find any elements: " + element_nm[0])

            element_nm = ("Raumordnung Straßenpersonenverkehr", "An- und Verbindungsqualitäten im Straßenpersonenverkehr")
            try:
                self.sp_sig_road = self._list_to_string(self._get_all_elements_to_next_same(element_start_tag="h3", element_end_tag="h3",
                                                                       element_text=element_nm[1]))
                add_dict = {
                    "spatial_significance_street": self.sp_sig_road
                }
                self.dict_project_content.update(add_dict)
            except ElementNotInPrinsException:
                logging.warning("Could not find any elements " + element_nm[0])

            element_nm = ("Erreichbarkeitsdefizite", "Räumliche Ausprägungen von Erreichbarkeitsdefiziten")
            try:
                self.sp_sig_accessibility_deficits = self._list_to_string(
                    self._get_all_elements_to_next_same(element_start_tag="h3", element_end_tag="h2",
                                                        element_text=element_nm[1]))
                add_dict = {
                    "spatial_significance_accessibility_deficits": self.sp_sig_accessibility_deficits,
                }
                self.dict_project_content.update(add_dict)

            except ElementNotInPrinsException:
                logging.warning("Could not find any elements " + element_nm[0])

            element_nm = ("Zusammenfassung Raumordnung", "Zusammenfassung der Projektwirkungen")
            try:
                self.sp_sig_conclusion = self._list_to_string(
                    self._get_all_elements_to_next_same(element_start_tag="h2", element_end_tag="h1",
                                                        element_text=element_nm[1]))
                add_dict = {
                    "spatial_significance_conclusion": self.sp_sig_conclusion,
                }
                self.dict_project_content.update(add_dict)
            except ElementNotInPrinsException:
                logging.warning("Could not find any elements " + element_nm[0])
        else:
            logging.warning('No spatial significance found')
            self.sp_sig_overall_result = self._sp_sig.text

        element_nm = ("Ergänzende Betrachtungen", "Ergänzende Betrachtungen")
        try:
            self.complementary_consideration = self._list_to_string(self._get_all_elements_to_next_same(element_start_tag='h1', element_end_tag='h1',element_text=element_nm[1]))
            add_dict = {
                "bvwp_additional_informations": self.complementary_consideration,
            }
            self.dict_project_content.update(add_dict)
        except ElementNotInPrinsException:
            logging.warning("Could not find any elements " + element_nm[0])


    def update_db(self, all_states, all_counties, all_constituencies):
        """
        Creates a dictionary for updating the corresponding ProjectContent
        :param all_states: get the table states of the db.
        :param all_counties: get the model of the DB Table Counties
        :param all_constituencies: get the model of the DB Table Constituencies
        :return:
        """

        dict_project_content = self.dict_project_content

        """
        dict_project_content = {
            # ignores project_number: project_id because the BVWP class is called with that
            "name": self.title,
            "description": self.content,
            "length": self.length,
            "priority": self.prio_bvwp,
            "reason_priority": self.priority_reason,
            "reason_project": self.project_reason,
            "bvwp_alternatives": self.alternatives,

            # Financial
            "bvwp_planned_cost": self.building_cost,
            "bvwp_planned_maintenance_cost": self.maintenance_cost,
            "bvwp_planned_planning_cost": self.planning_cost,
            "bvwp_planned_planning_cost_incurred": self.planning_cost_incurred,
            "bvwp_total_budget_relevant_cost": self.total_budget_relevant_cost,
            "bvwp_total_budget_relevant_cost_incurred": self.total_budget_relevant_cost_incurred,
            "bvwp_valuation_relevant_cost": self.valuation_relevant_cost,
            "bvwp_valuation_relevant_cost_pricelevel_2012": self.valuation_relevant_cost_pricelevel_2012,
            "bvwp_valuation_relevant_cost_pricelevel_2012_planning_cost": self.valuation_relevant_cost_pricelevel_2012_planning_cost,
            "bvwp_valuation_relevant_cost_pricelevel_2012_infrastructure_cos": self.valuation_relevant_cost_pricelevel_2012_infrastructure_cost,
            "bvwp_valuation_relevant_cost_pricelevel_2012_present_value": self.valuation_relevant_cost_pricelevel_2012_present_value,
            "nkv": self.nkv,

            # environmental
            "bvwp_environmental_impact": self.environmental_impact,
            "delta_nox": self.delta_nox,
            "delta_co": self.delta_co,
            "delta_co2": self.delta_co2,
            "delta_hc": self.delta_hc,
            "delta_pm": self.delta_pm,
            "delta_so2": self.delta_so2,

            "bvwp_sum_use_environment": self.sum_use_environment,
            "bvwp_sum_environmental_affectedness": self.sum_environmental_affectedness,
            "bvwp_sum_environmental_affectedness_text": self.sum_environmental_affectedness_text,
            "noise_new_affected": self.noise_new_affected,
            "noise_relieved": self.noise_relieved,
            "change_noise_outtown": self.change_noise_outtown,

            "area_nature_high_importance": self.area_nature_high_importance,
            "area_nature_high_importance_per_km": self.area_nature_high_importance_per_km,
            "area_nature_high_importance_rating": self.area_nature_high_importance_rating,
            "natura2000_rating": self.natura2000_rating,
            "natura2000_not_excluded": self.natura2000_not_excluded,
            "natura2000_probably": self.natura2000_probably,
            "ufr_250": self.ufr_250,
            "ufr_250_per_km": self.ufr_250_per_km,
            "ufra_250_rating": self.ufr_250_rating,
            "bfn_rating": self.bfn_rating,
            "ufr_1000_undissacted_large_area": self.ufr_1000_undissacted_large_area,
            "ufr_1000_undissacted_large_area_per_km": self.ufr_1000_undissacted_large_area_per_km,
            "ufr_1000_undissacted_large_mammals": self.ufr_1000_undissacted_large_mammals,
            "ufr_1000_undissacted_large_mammals_per_km": self.ufr_1000_undissacted_large_mammals_per_km,
            "count_undissacted_area": self.count_undissacted_area,
            "count_reconnect_area": self.count_reconnect_area,
            "land_consumption": self.land_consumption,
            "flooding_area": self.flooding_area,
            "flooding_area_per_km": self.flooding_area_per_km,
            "flooding_area_rating": self.flooding_area_rating,
            "water_protection_area": self.water_protection_area,
            "water_protection_area_per_km": self.water_protection_area_per_km,
            "water_protection_area_rating": self.water_protection_rating,
            "uzvr": self.uzvr,
            "uvzr_rating": self.uvzr_rating,
            "priortiy_area_landscape_protection": self.priority_area_landscape_protection,
            "priority_area_landscape_protection_per_km": self.priority_area_landscape_protection_per_km,
            "priority_area_landscape_protection_rating": self.priority_area_landscape_protection_rating,
            "environmental_additional_informations": self.environment_additional_informations,

            # regional significance
            "bvwp_regional_significance": self.regional_significance,
            "spatial_significance_overall_result": self.sp_sig_overall_result,
            "spatial_significance_reasons": self.sp_sig_reasons,
            "spatial_significance_street": self.sp_sig_road,
            "spatial_significance_accessibility_deficits": self.sp_sig_accessibility_deficits,
            "spatial_significance_conclusion": self.sp_sig_conclusion,

            # capacity
            "bottleneck_elimination": self.bottleneck_elimination,
            "bvwp_congested_rail_reference_6to9_km": self.congested_rail_reference_6to9_km,
            "bvwp_congested_rail_reference_6to9_perc": self.congested_rail_reference_6to9_perc,
            "bvwp_congested_rail_plancase_6to9_km": self.congested_rail_plancase_6to9_km,
            "bvwp_congested_rail_plancase_6to9_perc": self.congested_rail_plancase_6to9_perc,

            "bvwp_congested_rail_reference_9to16_km": self.congested_rail_reference_9to16_km,
            "bvwp_congested_rail_reference_9to16_perc": self.congested_rail_reference_9to16_perc,
            "bvwp_congested_rail_plancase_9to16_km": self.congested_rail_plancase_9to16_km,
            "bvwp_congested_rail_plancase_9to16_perc": self.congested_rail_plancase_9to16_perc,

            "bvwp_congested_rail_reference_16to19_km": self.congested_rail_reference_16to19_km,
            "bvwp_congested_rail_reference_16to19_perc": self.congested_rail_reference_16to19_perc,
            "bvwp_congested_rail_plancase_16to19_km": self.congested_rail_plancase_16to19_km,
            "bvwp_congested_rail_plancase_16to19_perc": self.congested_rail_plancase_16to19_perc,

            "bvwp_congested_rail_reference_19to22_km": self.congested_rail_reference_19to22_km,
            "bvwp_congested_rail_reference_19to22_perc": self.congested_rail_reference_19to22_perc,
            "bvwp_congested_rail_plancase_19to22_km": self.congested_rail_plancase_19to22_km,
            "bvwp_congested_rail_plancase_19to22_perc": self.congested_rail_plancase_19to22_perc,

            "bvwp_congested_rail_reference_22to6_km": self.congested_rail_reference_22to6_km,
            "bvwp_congested_rail_reference_22to6_perc": self.congested_rail_reference_22to6_perc,
            "bvwp_congested_rail_plancase_22to6_km": self.congested_rail_plancase_22to6_km,
            "bvwp_congested_rail_plancase_22to6_perc": self.congested_rail_plancase_22to6_perc,

            "bvwp_congested_rail_reference_day_km": self.congested_rail_reference_day_km,
            "bvwp_congested_rail_reference_day_perc": self.congested_rail_reference_day_perc,
            "bvwp_congested_rail_plancase_day_km": self.congested_rail_plancase_day_km,
            "bvwp_congested_rail_plancase_day_perc": self.congested_rail_plancase_day_perc,

            "bvwp_unscheduled_waiting_period_reference": self.unscheduled_waiting_period_reference_case,
            "bvwp_unscheduled_waiting_period_plancase": self.unscheduled_waiting_period_plan_case,

            "bvwp_punctuality_cargo_reference": self.punctuality_cargo_reference,
            "bvwp_delta_punctuality_relativ": self.delta_punctuality_cargo_relativ,
            "bvwp_delta_punctuality_absolut": self.delta_punctuality_cargo_absolut,

            # travel time
            "traveltime_reduction": self.traveltime_reductions,
            "bvwp_traveltime_examples": self.change_traveltime_examples,

            # traffic forecast
            # # passenger
            "relocation_car_to_rail": self.relocation_car_to_rail,
            "relocation_rail_to_car": self.relocation_rail_to_car,
            "relocation_air_to_rail": self.relocation_air_to_rail,
            "induced_traffic": self.induced_traffic,
            "delta_car_km": self.delta_car_km,
            "delta_rail_km": self.delta_rail_km,
            "delta_rail_running_time": self.delta_rail_running_time,
            "delta_rail_km_rail": self.delta_km_rail,
            "delta_rail_km_car_to_rail": self.delta_km_car_to_rail,
            "delta_rail_km_rail_to_car": self.delta_km_rail_to_car,
            "delta_rail_km_air_to_rail": self.delta_km_air_to_rail,
            "delta_rail_km_induced": self.delta_rail_km_induced,
            "delta_travel_time_rail": self.delta_travel_time_rail,
            "delta_travel_time_car_to_rail": self.delta_travel_time_car_to_rail,
            "delta_travel_time_rail_to_car": self.delta_travel_time_rail_to_car,
            "delta_travel_time_air_to_rail": self.delta_travel_time_air_to_rail,
            "delta_travel_time_induced": self.delta_travel_time_induced,

            # # cargo
            "relocation_truck_to_rail": self.relocation_truck_to_rail,
            "relocation_ship_to_rail": self.relocation_ship_to_rail,
            "delta_truck_km": self.delta_truck_km,
            "delta_truck_count": self.delta_truck_count,
            "delta_rail_cargo_count": self.delta_rail_cargo_count,
            "delta_rail_cargo_running_time": self.delta_rail_cargo_running_time,
            "delta_rail_cargo_km_lkw_to_rail": self.delta_rail_cargo_km_lkw_to_rail,
            "delta_rail_cargo_km_ship_to_rail": self.delta_rail_cargo_km_ship_to_rail,
            "delta_rail_cargo_time_rail": self.delta_rail_cargo_time_rail,
            "delta_rail_cargo_time_lkw_to_rail": self.delta_rail_cargo_time_lkw_to_rail,
            "delta_rail_cargo_time_ship_to_rail": self.delta_rail_cargo_time_ship_to_rail,

            # benefit - cost - calculation
            ## passenger
            "use_change_operation_cost_car_yearly": self.use_change_operating_cost_car_yearly,
            "use_change_operation_cost_car_present_value": self.use_change_operating_cost_car_present_value,
            "use_change_operating_cost_rail_yearly": self.use_change_operating_cost_rail_yearly,
            "use_change_operating_cost_rail_present_value": self.use_change_operating_cost_rail_present_value,
            "use_change_operating_cost_air_yearly": self.use_change_operating_cost_air_yearly,
            "use_change_operating_cost_air_present_value": self.use_change_operating_cost_air_present_value,
            "use_change_pollution_car_yearly": self.use_change_pollution_car_yearly,
            "use_change_pollution_car_present_value": self.use_change_pollution_car_present_value,
            "use_change_pollution_rail_yearly": self.use_change_pollution_rail_yearly,
            "use_change_pollution_rail_present_value": self.use_change_pollution_rail_present_value,
            "use_change_pollution_air_yearly": self.use_change_pollution_air_yearly,
            "use_change_pollution_air_present_value": self.use_change_pollution_air_present_value,
            "use_change_safety_car_yearly": self.use_change_safety_car_yearly,
            "use_change_safety_car_present_value": self.use_change_safety_car_present_value,
            "use_change_safety_rail_yearly": self.use_change_safety_car_yearly,
            "use_change_safety_rail_present_value": self.use_change_safety_rail_present_value,
            
            "use_change_travel_time_rail_yearly": self.use_change_travel_time_rail_yearly,
            "use_change_travel_time_induced_yearly": self.use_change_travel_time_induced_yearly,
            "use_change_travel_time_pkw_yearly": self.use_change_travel_time_pkw_yearly,
            "use_change_travel_time_air_yearly": self.use_change_travel_time_air_yearly,
            "use_change_travel_time_less_2min_yearly": self.use_change_travel_time_less_2min_yearly,
            "use_change_implicit_benefit_induced_yearly": self.use_change_implicit_benefit_induced_yearly,
            "use_change_implicit_benefit_pkw_yearly": self.use_change_implicit_benefit_pkw_yearly,
            "use_change_implicit_benefit_air_yearly": self.use_change_implicit_benefit_air_yearly,
            "use_sum_passenger_yearly": self.use_sum_passenger_yearly,
            
            "use_change_travel_time_rail_present_value": self.use_change_travel_time_rail_present_value,
            "use_change_travel_time_induced_present_value": self.use_change_travel_time_induced_present_value,
            "use_change_travel_time_pkw_present_value": self.use_change_travel_time_pkw_present_value,
            "use_change_travel_time_air_present_value": self.use_change_travel_time_air_present_value,
            "use_change_travel_time_less_2min_present_value": self.use_change_travel_time_less_2min_present_value,
            "use_change_implicit_benefit_induced_present_value": self.use_change_implicit_benefit_induced_present_value,
            "use_change_implicit_benefit_pkw_present_value": self.use_change_implicit_benefit_pkw_present_value,
            "use_change_implicit_benefit_air_present_value": self.use_change_implicit_benefit_air_present_value,
            "use_sum_passenger_present_value": self.use_sum_passenger_present_value,

            ## cargo
            "use_change_operating_cost_truck_yearly": self.use_change_operating_cost_truck_yearly,
            "use_change_operating_cost_rail_cargo_yearly": self.use_change_operating_cost_rail_cargo_yearly,
            "use_change_operating_cost_ship_yearly": self.use_change_operating_cost_ship_yearly,
            "use_change_pollution_truck_yearly": self.use_change_pollution_truck_yearly,
            "use_change_pollution_rail_cargo_yearly": self.use_change_pollution_rail_cargo_yearly,
            "use_change_pollution_ship_yearly": self.use_change_pollution_ship_yearly,
            "use_change_safety_truck_yearly": self.use_change_safety_truck_yearly,
            "use_change_safety_rail_cargo_yearly": self.use_change_safety_rail_cargo_yearly,
            "use_change_safety_ship_yearly": self.use_change_safety_ship_yearly,
            "use_change_running_time_rail_yearly": self.use_change_running_time_rail_cargo_yearly,
            "use_change_running_time_lkw_yearly": self.use_change_running_time_lkw_yearly,
            "use_change_running_time_ship_yearly": self.use_change_running_time_ship_yearly,
            "use_change_implicit_benefit_truck_yearly": self.use_change_implicit_benefit_truck_yearly,
            "use_change_implicit_benefit_ship_yearly": self.use_change_implicit_benefit_ship_yearly,
            "use_change_reliability_yearly": self.use_change_reliability_yearly,
            "use_sum_cargo_yearly": self.use_sum_cargo_yearly,

            "use_change_operating_cost_truck_present_value": self.use_change_operating_cost_truck_present_value,
            "use_change_operating_cost_rail_cargo_present_value": self.use_change_operating_cost_rail_cargo_present_value,
            "use_change_operating_cost_ship_present_value": self.use_change_operating_cost_ship_present_value,
            "use_change_pollution_truck_present_value": self.use_change_pollution_truck_present_value,
            "use_change_pollution_rail_cargo_present_value": self.use_change_pollution_rail_cargo_present_value,
            "use_change_pollution_ship_present_value": self.use_change_pollution_ship_present_value,
            "use_change_safety_truck_present_value": self.use_change_safety_truck_present_value,
            "use_change_safety_rail_cargo_present_value": self.use_change_safety_rail_cargo_present_value,
            "use_change_safety_ship_present_value": self.use_change_safety_ship_present_value,
            "use_change_running_time_rail_present_value": self.use_change_running_time_rail_cargo_present_value,
            "use_change_running_time_lkw_present_value": self.use_change_running_time_lkw_present_value,
            "use_change_running_time_ship_present_value": self.use_change_running_time_ship_present_value,
            "use_change_implicit_benefit_truck_present_value": self.use_change_implicit_benefit_truck_present_value,
            "use_change_implicit_benefit_ship_present_value": self.use_change_implicit_benefit_ship_present_value,
            "use_change_reliability_present_value": self.use_change_reliability_present_value,
            "use_sum_cargo_present_value": self.use_sum_cargo_present_value,
            
            # # other use
            "use_change_maintenance_cost_yearly": self.use_change_maintenance_costs_yearly,
            "use_change_lcc_infrastructure_yearly": self.use_change_lcc_infrastructure_yearly,
            "use_change_noise_intown_yearly": self.use_change_noise_intown_yearly,
            "use_change_noise_outtown_yearly": self.use_change_noise_outtown_yearly,
            "sum_use_change_yearly": self.sum_use_change_yearly,

            "use_change_maintenance_cost_present_value": self.use_change_maintenance_costs_present_value,
            "use_change_lcc_infrastructure_present_value": self.use_change_lcc_infrastructure_present_value,
            "use_change_noise_intown_present_value": self.use_change_noise_intown_present_value,
            "use_change_noise_outtown_present_value": self.use_change_noise_outtown_present_value,
            "sum_use_change_present_value": self.sum_use_change_present_value,

            # duration
            "bvwp_duration_of_outstanding_planning": self.duration_of_outstanding_planning,
            "bvwp_duration_of_build": self.duration_of_build,
            "bvwp_duration_operating": self.duration_operating,

            #additional informations
            "bvwp_additional_informations": self.complementary_consideration,

        }
        """

        # create a list of all states that are touched witht that project
        pc_states = []
        for state in all_states:
            if state.name_short_2 in self.states:
                pc_states.append(state)

        pc_counties = []
        for county in self.counties:
            county_db = None
            if county[1]:
                try:
                    county_db = all_counties.query.filter(
                        all_counties.name_short.like('%' + county[0] + '%'),
                        all_counties.type.like('%' + county[1] + '%')).one()
                except sqlalchemy.exc.NoResultFound:
                    logging.warning('County not found ' + county[0] + '; ' + county[1])
            else:
                try:
                    county_db = all_counties.query.filter(
                        all_counties.name.like('%' + county[0] + '%')).one()
                except sqlalchemy.exc.NoResultFound:
                    logging.warning('County not found ' + county[0])

            if county_db:
                pc_counties.append(county_db)

        pc_constituencies = []
        for c in self.constituencies:
            c_db = all_constituencies.query.filter(all_constituencies.id==c[1]).one()
            pc_constituencies.append(c_db)

        return dict_project_content, pc_states, pc_counties, pc_constituencies


if __name__ == '__main__':
    project_name = '2-007-V01'
    project = BvwpRail(project_name)

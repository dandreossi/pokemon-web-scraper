#!/usr/bin/python3
"""
Scrapes Serebii.net for Pokémon statistics.
"""
import argparse
import bs4
import json
import logging
import re
import requests

FORMAT = '%(asctime)s %(levelname)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)

OUTPUT_FILE = 'pokemon.json'


def setup_arg_parser():
    """
    Set up command-line argument parser.
    :return: An ArgumentParser object.
    """
    arg_parser = argparse.ArgumentParser(description='A Pokémon web scraper')
    arg_parser.add_argument('-s', '--save', action='store_true', help='save the output to JSON')
    arg_parser.add_argument('-f', '--first', default=1, type=int, help='the ID of the first Pokémon to retrieve')
    arg_parser.add_argument('-l', '--last', default=1, type=int, help='the ID of the last Pokémon to retrieve')
    arg_parser.add_argument('-v', '--verbose', action='store_true', help='print the Pokémon\'s statistics to console')
    return arg_parser.parse_args()


def scrape_pokemon(first_id: int, last_id: int, args):
    """
    Orchestrates scraping data based on a given Pokémon ID range.
    """
    data_list = []

    for poke_id in range(first_id, last_id + 1):
        data = extract_statistics(poke_id)
        data_list.append(data)

        if args.verbose or not args.save:
            display_formatted(data)
        else:
            logging.info('Scraped %s %s', data['number'], data['name'])

    if args.save:
        logging.info('Saving to %s', OUTPUT_FILE)
        save_to_json(data_list)
    else:
        logging.info('All Pokémon retrieved! To save to JSON, use the --save flag')


def extract_statistics(poke_id: int) -> object:
    """
    Scrapes the Serebii.net with a given Pokémon ID.
    """
    url = 'https://serebii.net/pokedex-sv/{}.shtml'.format(str(poke_id).zfill(3))
    data = requests.get(url)
    soup = bs4.BeautifulSoup(data.text, 'html.parser')

    try:
        all_divs = soup.find_all('div', attrs={'align': 'center'})
        center_panel_info = all_divs[1].findAll('td', {'class': 'fooinfo'})

        height = center_panel_info[6].text.split('\r\n\t\t\t')
        weight = center_panel_info[7].text.split('\r\n\t\t\t')

        if center_panel_info[6].find('td', string='Standard'):
            height = center_panel_info[6].find('td', string='Standard').findNext('td').text.replace('"', '" ').split(" ")
            weight = center_panel_info[7].find('td', string='Standard').findNext('td').text.replace('lbs', 'lbs ').split(" ")

        base_stats_td = all_divs[1].find('td', string=re.compile("Base Stats - Total.*")).find_next_siblings('td')

        # Extract level-up moves
        level_up_moves = []
        standard_level_table = soup.find('a', {'name': 'standardlevel'}).find_parent('table')
        if standard_level_table:
            rows = standard_level_table.find_all('tr')[2:]  # Skip header rows
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    level = cols[0].text.strip()
                    move = cols[1].text.strip()
                    level_up_moves.append(f"{level}: {move}")

        # Extract TM/HM moves
        tm_hm_moves = []
        tm_hm_table = soup.find('a', {'name': 'tmhm'}).find_parent('table')
        if tm_hm_table:
            rows = tm_hm_table.find_all('tr')[2:]  # Skip header rows
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    tm_hm = cols[0].text.strip()
                    move = cols[1].text.strip()
                    tm_hm_moves.append(f"{tm_hm}: {move}")

        # Extract egg moves
        egg_moves = []
        try:
            egg_table = soup.find('a', {'name': 'eggmoves'}).find_parent('table')
        except AttributeError:
            egg_table = None
        if egg_table:
            rows = egg_table.find_all('tr')[2:]
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    egg_move = cols[0].text.strip()
                    egg_moves.append(egg_move)

        # Extract abilities
        abilities = []
        abilities_table = soup.find('table', {'class': 'dextable'})
        if abilities_table:
            abilities_rows = abilities_table.find_all('tr')
            for row in abilities_rows:
                if 'Abilities' in row.text:
                    abilities_cells = row.find_all('td')
                    for cell in abilities_cells:
                        if 'Hidden Ability' in cell.text:
                            abilities.append(cell.text.strip() + ' (Hidden)')
                        else:
                            abilities.append(cell.text.strip())

    except Exception:
        logging.error('There was an error trying to identify HTML elements on the webpage. URL: %s', url)
        raise

    extracted_pokemon = {
        "name": center_panel_info[1].text,
        "number": '#{}'.format(str(poke_id).zfill(3)),
        "classification": center_panel_info[5].text,
        "height": height,
        "weight": weight,
        "hit_points": int(base_stats_td[0].text),
        "abilities": abilities,
        "attack": int(base_stats_td[1].text),
        "defense": int(base_stats_td[2].text),
        "special": int(base_stats_td[3].text),
        "speed": int(base_stats_td[4].text),
        "level_up_moves": level_up_moves,
        "tm_hm_moves": tm_hm_moves,
        "egg_moves": egg_moves
    }

    return extracted_pokemon


def display_formatted(poke_object):
    """
    Prints a given Pokémon object.
    """
    print('Name\t\t', poke_object['name'])
    print('Number\t\t', poke_object['number'])
    print('Classification\t', poke_object['classification'])
    print('Height\t\t', ' '.join(poke_object['height']))
    print('Weight\t\t', ' '.join(poke_object['weight']))
    print('HP\t\t', poke_object['hit_points'])
    print('Abilities\t', ', '.join(poke_object['abilities']))
    print('Attack\t\t', poke_object['attack'])
    print('Defense\t\t', poke_object['defense'])
    print('Special\t\t', poke_object['special'])
    print('Speed\t\t', poke_object['speed'])
    print('Level-up Moves\t\t', poke_object['level_up_moves'])
    print('TM/HM Moves\t\t', poke_object['tm_hm_moves'])
    print('Egg Moves\t\t', poke_object['egg_moves'])
    print('-' * 20)


def save_to_json(data: list):
    """
    Save data to file.
    """
    with open(OUTPUT_FILE, mode='w', encoding='utf-8') as output_file:
        json.dump(data, output_file, indent=4)


def validate_input(first_id_input: int, last_id_input: int):
    """
    Check if the user-supplied input is valid.
    """
    if first_id_input >= 1026 or last_id_input >= 1026:
        logging.error('Error: This Pokémon is not yet supported!')
        exit()
    if last_id_input < first_id_input:
        last_id_input = first_id_input
    return first_id_input, last_id_input


if __name__ == '__main__':
    try:
        args = setup_arg_parser()
        logging.info('Extracting data from Serebii.net')
        first_id, last_id = validate_input(args.first, args.last)
        scrape_pokemon(first_id, last_id, args)
    except Exception as ex:
        logging.error(ex)
        raise

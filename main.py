import json
import os
import re
import argparse
import subprocess



def text_color(color_theme:str):
    """
    Help changing the color theme for specific events
    :param color_theme: what type of color do we need?
    :return: the color code
    """
    color_dict = {
        'base': '\033[97m',  # white
        'ERROR': '\033[93m',  # yellow
        'backup': '\033[96m',  # cyan
        'WARNING': '\033[92m'  # Green
    }
    try:
        return color_dict[color_theme]
    except:
        return color_dict['base']


def is_obsidian_md(file_path):
    """
    Find if the file is a .md file (files use by obsidian for keeping the text)
    also ensure the files are not from the backup folder
    :param file_path: files to look if its a .md files
    :return:
    """
    # First, check if the file has a .md extension
    if file_path.find('\\backup') != -1:
        return False

    if file_path.endswith('.md'):
        return True

    # If no extension, check the content
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            # Check for markdown patterns
            markdown_patterns = [
                r'#',  # headings
                r'\[.*?\]\(.*?\)',  # links
                r'^[\*\-\+]\s+',  # lists
                r'!\[.*?\]\(.*?\)',  # images
                r'\*\*.*?\*\*',  # bold text
                r'\*.*?\*',  # italic text
                r'```',  # code blocks
                r'\[\[.*?\]\]',  # Obsidian wiki-style links
                r'^---\s*\n.*?\n---\s*\n',  # YAML front matter
                r'#\w+',  # tags
            ]
            for pattern in markdown_patterns:
                if re.search(pattern, content, re.MULTILINE):
                    return True
    except Exception as e:
        print(f"{text_color('ERROR')}Error reading file {file_path}: {e}{text_color('base')}")

    return False


def get_file_name(file_path: str):
    """
    I just dislike using multiple time the os. what ever and prefer using a function with a bether name
    :param file_path:  The path of the file we want the name
    :return:  Name of the file
    """
    return os.path.basename(file_path)


def back_up_original_obsidian_files(vault_directory: str, file_to_backup: list):
    """
    Will back up the version of the file the modified obsidian file the program see.
    it will overwrite them if a backup is all ready there
    :param vault_directory: directory to look for links
    :param file_to_backup: file to use to make the linking
    :return: None
    """
    backup_path: str = f'{vault_directory}\\backup'
    if not os.path.isdir(backup_path):
        os.mkdir(backup_path)

    for e in file_to_backup:
        if e.find('\\backup') != -1:
            continue
        with open(e, 'r', encoding='utf-8') as f:
            file_data = f.read()
            f.close()

        if file_data == '':  # if empty do not back up
            continue
        file_name = get_file_name(e)
        with open(f'{backup_path}\\{file_name}', 'w', encoding='utf-8') as f:
            f.write(file_data)
        print(f'{text_color("backup")}backup for file {e} done {text_color("base")}')


def find_all_files(directory, file_to_ignore: str = ''):
    """
    Finds all files in the given directory and its subdirectories.

    Parameters:
    directory (str): The root directory to search for files.
    file_to_ignore: ignore a specific file

    Returns:
    list: A list of paths to all the files found.
    """
    all_files = []

    for root, dirs, files in os.walk(directory):
        # Skip directories that start with a .
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            if file == file_to_ignore:
                continue
            all_files.append(os.path.join(root, file))

    return all_files


def replace_key_value(obsidian_files: list, path_to_vault_translation_link: str, link_translation_text: dict) -> None:
    """
    Look through all the .md files and try to find any known words or series of words inside the word link list
    replace them by the value wanted.
    :param obsidian_files: all the files to look into
    :param path_to_vault_translation_link: path to the linking file
    :param link_translation_text: dictionary made with the linking file
    :return:
    """
    special_char = ['@','/','\'']
    for e in obsidian_files:
        if e == path_to_vault_translation_link:
            continue

        with open(e, 'r') as f:
            data = f.read()
        if data == '':
            continue

        for key, value in link_translation_text.items():

            # Find special character for regex and add \\ to them so they become understandable
            key = next((key[:key.find(s)] + '\\' + key[key.find(s):] for s in special_char if key.find(s) != -1), key)

            pattern = rf'{key}'
            matches = re.finditer(pattern, data)

            # List of positions to replace
            positions_to_replace = [
                (match.start(), match.end()) for match in matches
                if not (
                    (match.start() > 0 and data[match.start()-1] in ['#', '[']) or
                    (match.start() > 1 and data[match.start()-1] == ' ' and data[match.start()-2] == '#') or
                    (match.end() < len(data) and data[match.end()] == ']')
                )
            ]

            # Replace all valid positions
            data = ''.join(
                [data[last_end:start] + value for (last_end, (start, end)) in zip([0] + [e for s, e in positions_to_replace], positions_to_replace)]
                + [data[positions_to_replace[-1][1]:]] if positions_to_replace else [data]
            )

        with open(e, 'w') as f:
            f.write(data)


def get_link_translation(path_to_vault_translation_link:str) -> dict:
    """
    Create the dictionary link for the words and the link we want to put insted
    :param path_to_vault_translation_link: path to the file olding the data for the links and words
    :return: dictionary of word (key) and links (value)
    """
    link_translation_text = {}  # Key: word to detect, Value : what it should be change for
    remove_end_space = r'\s$'
    remove_beginning_space = r'^\s+'

    with open(path_to_vault_translation_link, 'r', encoding='utf-8') as translation:
        read = translation.read().splitlines()  # use to know what we will transform as a link
        for e in read:
            split = e.split(':')
            if len(split) < 1:
                continue
            split = [re.sub(remove_end_space, '', re.sub(remove_beginning_space, '', s)) for s in split]

            link_translation_text[split[0]] = split[1]
    return link_translation_text


def configuration_file_detection() -> bool:
    conf_path:str = '.\\configuration\\conf.json'
    if os.path.isfile(conf_path):
        with open(conf_path,'r', encoding='utf-8') as f:
            data = json.load(f)
            f.close()
        if os.path.isdir(data['vault_path']) and (os.path.isfile(data['translation_path'])):
            return True

    return False


def conf_creation():
    if not configuration_file_detection():
        print('no configuration file, creating one.')
        conf = {
            'vault_path': '',
            'translation_path': '',
            'obsidian.exe_path': ''
        }
        with open('.\\configuration\\conf.json', 'w', encoding='utf-8') as f:
            json.dump(conf, f)


def arg_parse():
    parser = argparse.ArgumentParser(description='This is a way to make it simpler to make reference in a obsidian')
    parser.add_argument('-o', '--open', nargs='?', const=True, help=f'Put this if you want to open '
        f'obsidian and work on the project at the same time\n{text_color("WARNING")} '
        f'if you want to use this function you need to add the path of obsidian '
        f'in the config file OR give it as an argument (will be save in the conf.json file) {text_color("base")}', required=False)

    parser.add_argument('-v', '--vault', type=str, help='Path where is the vault we need to interact with\n'
                                                        'if not use the program will use the last path used in its configuration json file\n'
                                                        'you also could change it directly in the json file', required=False)

    parser.add_argument('-t', '--translation_link', type=str, help='Path to the translation link file\n'
                                                                  'if not use it will use the path in the configuration json file\n'
                                                                  'you could also just change the path in the configuration file', required=False)
    return parser


def get_path(args):
    """
    Try to get the path for the Vault in the directory
    :param args: the arguments received by the program
    :return: path for the files
    """
    with open('.\\configuration\\conf.json', 'r', encoding='utf-8') as f:
        conf: dict = json.load(f)
        f.close()
    vault_directory_path = args.vault if args.vault is not None and os.path.isdir(args.vault) else conf['vault_path']

    path_to_vault_translation_link = args.translation_link if args.translation_link is not None and os.path.isfile(args.translation_link) else conf['translation_path']

    path_to_obsidian = args.open if type(args.open) == str and args.open is not None and os.path.isfile(args.open) else conf['obsidian.exe_path']

    conf_verifier = conf.copy()

    if vault_directory_path != conf['vault_path']:
        conf['vault_path'] = vault_directory_path

    if path_to_vault_translation_link != conf['translation_path']:
        conf['translation_path'] = path_to_vault_translation_link

    if path_to_obsidian != conf['obsidian.exe_path']:
        conf['obsidian.exe_path'] = path_to_obsidian


    if conf_verifier != conf:
        with open('.\\configuration\\conf.json', 'w', encoding='utf-8') as f:
            json.dump(conf, f)
            f.close()

    return vault_directory_path, path_to_vault_translation_link, path_to_obsidian


def ensure_path_are_ok(vault_directory_path:str, path_to_vault_translation_link:str):
    if not os.path.isdir(vault_directory_path):
        raise Exception(f'{text_color("ERROR")}Not a directory or does not exist {vault_directory_path}'
                        f'\nIf you have try to use the configuration file it might be empty. Try using -v :PATH:{text_color("base")}')

    if not os.path.isfile(path_to_vault_translation_link):
        raise Exception(f'{text_color("ERROR")}This is not a file. Retry to input the correct file path {path_to_vault_translation_link}'
                        f'\nIf you have try to use the configuration file it might be empty try using -t :PATH:{text_color("base")}')


def start_obsidian(path_to_obsidian):
    process = subprocess.Popen(path_to_obsidian)
    print(f'program launched with PID {process.pid}')
    process.wait()
    print(f"program with pid {process.pid} closed")


def main():
    args = arg_parse().parse_args()

    conf_creation()

    vault_directory_path, path_to_vault_translation_link, path_to_obsidian = get_path(args)

    ensure_path_are_ok(vault_directory_path, path_to_vault_translation_link)

    # open obsidian if asked
    if args.open is not None:
        if not os.path.isfile(path_to_obsidian):
            raise Exception(f"{text_color('ERROR')}Path to local obsidian is not working {path_to_obsidian}.\n"
                            f"Look in your config file if you have the correct path enter.\n"
                            f"You can also add the path next to the -o and it will be updated {text_color('base')}")
        start_obsidian(path_to_obsidian)

    all_files = find_all_files(vault_directory_path, file_to_ignore=path_to_vault_translation_link)  # all files from the directory

    link_translation_text = get_link_translation(path_to_vault_translation_link)

    back_up_original_obsidian_files(vault_directory_path,all_files)  # Try to ensure the process does not fuck up everything

    obsidian_files = [file for file in all_files if is_obsidian_md(file)]  # get all the obsidian files inside the vault directory

    replace_key_value(obsidian_files, path_to_vault_translation_link, link_translation_text)


if __name__ == '__main__':
    main()


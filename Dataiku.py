import sublime, sublime_plugin

import requests
from requests.auth import HTTPBasicAuth
import os
import base64
import json

temp_dir = os.path.abspath(os.path.join(sublime.cache_path(),'Dataiku'))
print("DataikuSublimeText -", "Temp directory:", temp_dir)

settings = None
def plugin_loaded():
    global settings
    settings = sublime.load_settings("Dataiku.sublime-settings")

def stringToBase64(s):
    return base64.b64encode(s.encode()).decode()

def base64ToString(b):
    return base64.b64decode(b.encode()).decode()

def recipeTypeToExtension(recipe_type):
    if "py" in recipe_type:
        return 'py'
    elif "sql" in recipe_type or recipe_type == "hive" or recipe_type == "impala":
        return 'sql'
    elif recipe_type in ["r", "sparkr"]:
        return 'r'
    elif recipe_type == "shaker":
        return 'json'
    else:
        return 'txt'


# Wrapper to make API call to a DSS instance
def api_dss(base_url, key, action, params = {}, method = 'get', data = {}):
    if not base_url.endswith('/'):
        base_url = base_url + '/'
    if not action.endswith('/'):
        action = action + '/'
    url = '%spublic/api/%s' % (base_url, action)
    headers = {'content-type': 'application/json'}
    if method == 'get':
        r = requests.request(method, url, params=params, auth=HTTPBasicAuth(key, ''), timeout=2)
    elif method == 'put':
        r = requests.request(method, url, data=data, params=params, auth=HTTPBasicAuth(key, ''), headers=headers, timeout=10)
    else:
        raise ValueError('Method should be get or put.')
    if r.status_code < 300:
        return r.json()
    else:
        sublime.error_message('API error when callin: ' + method + ' ' + r.url)
        raise ValueError('API error when calling ' + r.url + '\n' + r.text)


def browse_instances(window):
    commands = []

    dss_instances = settings.get("instances", [])

    if dss_instances:
        for instance in dss_instances:
            commands.append({
                "caption": instance.get('name'),
                "command": "dataiku_recipes",
                "args": {
                    "instance": instance
                }
            })

    commands.append({
        "caption": "Edit DSS instances",
        "command": "open_file",
        "args": {
            "file": "${packages}/User/Dataiku.sublime-settings"
        }
    })

    def show_quick_panel():
        window.show_quick_panel([ x['caption'] for x in commands ], on_select)

    def on_select(picked):
        if picked == -1:
            return
        window.run_command(commands[picked]['command'], commands[picked]['args'])

    sublime.set_timeout(show_quick_panel, 10)


def browse_recipes(window, instance):
    commands = []

    dss_url = instance.get('base_url', '')
    dss_key = instance.get('api_key', '')
    list_of_project_keys_to_exclude = instance.get('list_of_project_keys_to_exclude', [])
    keep_only_code_recipes = instance.get('keep_only_code_recipes', True)

    projects = api_dss(dss_url, dss_key, 'projects')
    projects_keys = [project['projectKey'] for project in projects if project['projectKey'] not in list_of_project_keys_to_exclude]

    for project_key in projects_keys:
        for recipe in api_dss(dss_url, dss_key, "projects/%s/recipes/" % project_key):

            if keep_only_code_recipes == True and recipeTypeToExtension(recipe.get('type')) not in ['py', 'sql', 'r']:
                continue

            commands.append({
                "caption": "%s - %s (%s)" % (project_key, recipe.get('name'), recipe.get('type')),
                "command": "dataiku_recipe",
                "args": {
                    "instance": instance,
                    "project_key": project_key,
                    "recipe_name": recipe.get('name')
                }
            })

    def show_quick_panel():
        window.show_quick_panel([ x['caption'] for x in commands ], on_select)

    def on_select(picked):
        if picked == -1:
            return
        window.run_command(commands[picked]['command'], commands[picked]['args'])

    sublime.set_timeout(show_quick_panel, 10)


def open_recipe(window, instance, project_key, recipe_name):
    dss_url = instance.get('base_url', '')
    dss_key = instance.get('api_key', '')

    recipe = api_dss(dss_url, dss_key, "projects/%s/recipes/%s" % (project_key, recipe_name))
    
    recipe_type = recipe.get('recipe').get('type', '')

    local_file = os.path.abspath(os.path.join( temp_dir,
                                                stringToBase64(dss_url),
                                                stringToBase64(dss_key),
                                                project_key,
                                                recipe_name+'.'+recipeTypeToExtension(recipe_type)
                                                ))
    print("DataikuSublimeText -", "Opening recipe in",local_file)

    if not os.path.exists(os.path.dirname(local_file)):
        os.makedirs(os.path.dirname(local_file))

    with open(local_file, 'w', encoding="utf-8") as file_:
        file_.write(recipe.get('payload', 'ERROR. Unable to download the recipe.'))

    sublime.set_timeout(lambda:window.open_file(local_file), 0)


# External Commands
class DataikuInstancesCommand(sublime_plugin.WindowCommand):
    def run(self):
        browse_instances(self.window)

class DataikuRecipesCommand(sublime_plugin.WindowCommand):
    def run(self, instance):
        browse_recipes(self.window, instance)

class DataikuRecipeCommand(sublime_plugin.WindowCommand):
    def run(self, instance, project_key, recipe_name):
        open_recipe(self.window, instance, project_key, recipe_name)

class RecipeEditListener(sublime_plugin.EventListener):
    def on_post_save(self, view):
        """
        When a recipe is saved, save it back to the DSS instance.
        """
        file = view.file_name()

        if temp_dir in file:
            print("DataikuSublimeText -", "Sending saved document %s" % file)
            recipe_name = file.split(os.sep)[-1]
            project_key = file.split(os.sep)[-2]
            dss_key = base64ToString(file.split(os.sep)[-3])
            dss_url = base64ToString(file.split(os.sep)[-4])
            print("DataikuSublimeText -", dss_url, dss_key, project_key, recipe_name)
            with open(file, 'r', encoding="utf-8") as file_:
                content = file_.read()
            #print("DataikuSublimeText -", content)
            recipe_name_no_ext =  os.path.splitext(recipe_name)[0]
            recipe = api_dss(dss_url, dss_key, "projects/%s/recipes/%s" % (project_key, recipe_name_no_ext))
            recipe['payload'] = content
            print("DataikuSublimeText -", api_dss(dss_url, dss_key, "projects/%s/recipes/%s" % (project_key, recipe_name_no_ext), method = 'put', data = json.dumps(recipe)))


    def on_close(self, view):
        """
        When a recipe is closed, delete the local temp file.
        """
        file = view.file_name()

        if file and temp_dir in file:
            print("DataikuSublimeText -", "Removing closed document:", file)
            os.remove(file)

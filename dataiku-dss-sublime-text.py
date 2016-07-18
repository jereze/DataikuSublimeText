import sublime, sublime_plugin

import requests
from requests.auth import HTTPBasicAuth
import os
import base64
import json

settings = sublime.load_settings("dss_instances.sublime-settings")
temp_dir = os.path.join(sublime.cache_path(),'Dataiku')

def stringToBase64(s):
    return base64.b64encode(s.encode()).decode()

def base64ToString(b):
    return base64.b64decode(b.encode()).decode()

#Parameters: action (the URL), params, method (GET or PUT), data for PUT
def api_dss(base_url, key, action, params = {}, method = 'get', data = {}):
    if not base_url.endswith('/'):
        base_url = base_url + '/'
    if not action.endswith('/'):
        action = action + '/'
    url = '%spublic/api/%s' % (base_url, action)
    headers = {'content-type': 'application/json'}
    if method == 'get':
        r = requests.request(method, url, params=params, auth=HTTPBasicAuth(key, ''))
    elif method == 'put':
        r = requests.request(method, url, data=data, params=params, auth=HTTPBasicAuth(key, ''), headers=headers)
    else:
        raise ValueError('Method should be get or put.')
        #todo: support other methods
    #print 'API call: ' + r.url
    #print r.text
    if r.status_code < 300:
        return r.json()
    else:
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
            "file": "${packages}/User/dss_instances.sublime-settings"
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

    projects = api_dss(dss_url, dss_key, 'projects')
    projects_keys = [project['projectKey'] for project in projects]

    for project_key in projects_keys:
        for recipe in api_dss(dss_url, dss_key, "projects/%s/recipes/" % project_key):

            commands.append({
                "caption": "%s - %s" % (project_key, recipe.get('name')),
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
    if "python" in recipe_type:
        ext = '.py'
    elif "sql" in recipe_type:
        ext = '.sql'
    elif "r" in recipe_type:
        ext = '.r'
    else:
        ext = '.txt'

    local_file = os.path.normpath(os.path.join(temp_dir,stringToBase64(dss_url),stringToBase64(dss_key),project_key,recipe_name+ext))
    print(local_file)

    if not os.path.exists(os.path.dirname(local_file)):
        os.makedirs(os.path.dirname(local_file))

    with open(local_file, 'w') as file_:
        file_.write(recipe.get('payload', 'ERROR. Unable to download the recipe.'))

    sublime.set_timeout(lambda:window.open_file(local_file), 0)


# External Commands
class DataikuInstancesCommand(sublime_plugin.WindowCommand):
    def run(self):
        browse_instances(self.window)

class DataikuRecipesCommand(sublime_plugin.WindowCommand):
    def run(self, instance):
        print(instance)
        browse_recipes(self.window, instance)

class DataikuRecipeCommand(sublime_plugin.WindowCommand):
    def run(self, instance, project_key, recipe_name):
        print(instance, project_key, recipe_name)
        open_recipe(self.window, instance, project_key, recipe_name)

class RecipeEditListener(sublime_plugin.EventListener):
    def on_post_save(self, view):
        """
        When a recipe is saved, save it back to the DSS instance.
        """
        file = view.file_name()
        print(file)

        if temp_dir in file:
            print("This is a file managed by Dataiku Plugin")
            recipe_name = file.split(os.sep)[-1]
            project_key = file.split(os.sep)[-2]
            dss_key = base64ToString(file.split(os.sep)[-3])
            dss_url = base64ToString(file.split(os.sep)[-4])
            print(dss_url, dss_key, project_key, recipe_name)
            with open(file, 'r') as file_:
                content = file_.read()
            #print(content)
            recipe_name_no_ext =  os.path.splitext(recipe_name)[0]
            recipe = api_dss(dss_url, dss_key, "projects/%s/recipes/%s" % (project_key, recipe_name_no_ext))
            recipe['payload'] = content
            print(api_dss(dss_url, dss_key, "projects/%s/recipes/%s" % (project_key, recipe_name_no_ext), method = 'put', data = json.dumps(recipe)))


    def on_close(self, view):
        """
        When a remote file is closed delete the local temp file and directory.
        We also no longer keep a record of it in our remote files list.
        """
        file = view.file_name()
        print(file)
        if temp_dir in file:
            print("This is a file managed by Dataiku Plugin")
            os.remove(file)

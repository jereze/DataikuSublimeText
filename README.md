DataikuSublimeText
==================

Sublime Text plugin to edit [Dataiku DSS](https://www.dataiku.com/dss/) recipes and plugins remotely.

![Preview](https://raw.githubusercontent.com/jereze/DataikuSublimeText/master/preview.gif)

## Requirements

* Sublime Text 3
* Dataiku DSS 3.1 or further (4.0 for plugins edition)
* Access to Dataiku DSS Public API (with a valid [API key](https://doc.dataiku.com/dss/latest/api/public/keys.html))

Note: From DSS 4.0, you have to generate a `Personal API key` on a User profile. Before, a `Global API key` was required.

## Configuration and usage

In Sublime Text, once installed with [Package Control](https://packagecontrol.io/), open the Command Palette (`ctrl+shift+p` on Win/Linux, `cmd+shift+p` on MacOS) and type `dataiku`. You will have two options:

* __Configure DSS instances__: use this to configure the instances you can edit remotely.
* __Edit DSS recipes__: use this to choose a recipe to open in the editor. You will have to select first a DSS instance if more than one are available.
* __Edit DSS plugins__: use this to choose a plugin file to open in the editor. You will have to select first a DSS instance if more than one are available.

Find out more in the [guide](https://www.dataiku.com/learn/guide/tips/dataiku-dss-sublime-text.html) on Dataiku website.

## Need help?

Ask your question on [answers.dataiku.com](https://answers.dataiku.com). Or, [open an issue](https://github.com/jereze/DataikuSublimeText/issues).

## Contributors

* @jereze
* @ThmsLa

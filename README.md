# ToDo Pyramid App

This is the Pyramid app for the Python Web Shootout.

Try it out here: <http://demo.todo.sixfeetup.com>

## Install

You can follow the instructions in the [Pyramid docs on installation][install].

Once you have Python and virtualenv installed, you can do the following:

```
$ mkdir ~/.virtualenvs
$ cd ~/.virtualenvs
$ virtualenv -p python2.7 todopyramid
$ cd todopyramid
$ source bin/activate
```

This creates the new virtual environment, now you can install the app.

```
(todopyramid)$ cd ~/Desktop
(todopyramid)$ git clone https://github.com/indypy/todopyramid.git
(todopyramid)$ cd todopyramid
(todopyramid)$ pip install -r requirements.txt -e .
```

This gives us the end result of the finished app. If it is the first time you are running the app, you will need to initialize the database.

```
(todopyramid)$ initialize_todopyramid_db development.ini
```

It can now be started up by doing the following.

```
(todopyramid)$ pserve development.ini
```

Now go to <http://localhost:6543> and enjoy!

## How the sausage was made

The above install directions tell you how to get the finished application started. Here we will document how the app was created from scratch.

### First steps

Started by creating a virtualenv and installing Pyramid into it.

```
(todopyramid)$ pip install pyramid
```

This gives us a starting point and the `pcreate` command to create a new app. In this case, we used the `alchemy` scaffold.

```
(todopyramid)$ cd ~/Desktop
(todopyramid)$ pcreate -s alchemy todopyramid
```

Since we are responsible developers, the first thing we should do is put this code into version control.

```
(todopyramid)$ cd todopyramid
(todopyramid)$ git init
(todopyramid)$ git add .
(todopyramid)$ git commit -m 'initial package from pcreate alchemy scaffold'
```

Before we start up the app for the first time, we need to install the new package that we've created, and all of its dependencies.

```
(todopyramid)$ python2.7 setup.py develop
```

Now that we've installed some more packages, we need to freeze the list of packages.

```
(todopyramid)$ pip freeze > requirements.txt
(todopyramid)$ git add requirements.txt
(todopyramid)$ git commit -m 'committing first version of requirements file'
```

Now let's initialize the database. In our example, we will be using SQLite.

```
(todopyramid)$ initialize_todopyramid_db development.ini
```

We don't want to check in the database, add it to the `.gitignore` file.

```
(todopyramid)$ echo "todopyramid.sqlite" > .gitignore
(todopyramid)$ git add .gitignore
(todopyramid)$ git commit -m 'ignore the SQLite database'
```

Now we can start up the app and see what it looks like.

```
(todopyramid)$ pserve development.ini
```

This will include all the boilerplate code from the alchemy template.

### Remove boilerplate

For our purposes, we won't need some of the boilerplate code that has been added. We'll just get rid of it.

```
(todopyramid)$ git rm static/*
(todopyramid)$ touch static/.gitignore
(todopyramid)$ git add static/.gitignore
(todopyramid)$ git rm templates/*
(todopyramid)$ git commit -m 'removing boilerplate templates'
```

We've put a `.gitignore` in the `static` dir so that the directory stays in place. We'll add templates to the `templates` dir soon, so it isn't necessary for that dir.

### Let's get fancy

Now we are ready to start adding our customizations. First thing we want to do is add in Bootstrap to ease creation of layouts. Since we will be using [Deform][deform] to create forms later on, we will use the [deform_bootstrap][deform_bootstrap] package.

Add it to the `setup.py`

```
requires = [
    # ...
    'deform_bootstrap',
]
```

Then we need to pull in its dependencies (which includes Deform itself). Then update the `requirements.txt` file.

```
(todopyramid)$ python2.7 setup.py develop
(todopyramid)$ pip freeze > requirements.txt
```

Then add the static resources to the `__init__.py`

```
# Adding the static resources from Deform
config.add_static_view('deform_static', 'deform:static', cache_max_age=3600)
config.add_static_view('deform_bootstrap_static', 'deform_bootstrap:static', cache_max_age=3600)
```

Now we need to get our template structure in place. We'll add a `todopyramid/layouts.py` with the following (see the [Creating a Custom UX for Pyramid][customux] tutorial for more details):

```
ifrom pyramid.renderers import get_renderer
from pyramid.decorator import reify


class Layouts(object):

    @reify
    def global_template(self):
        renderer = get_renderer("templates/global_layout.pt")
        return renderer.implementation().macros['layout']
```

Add the `global_layout.pt` with at least the following (look at the source code for the complete template):

```
<!DOCTYPE html>
 <!-- The layout macro below is what is referenced in the layouts.Laytouts.global_template -->
<html lang="en" metal:define-macro="layout">
  <head>

    <!-- Styles from Deform Bootstrap -->
    <link rel="stylesheet" href="${request.static_url('deform_bootstrap:static/deform_bootstrap.css')}" type="text/css" media="screen" charset="utf-8" />
    <link rel="stylesheet" href="${request.static_url('deform_bootstrap:static/chosen_bootstrap.css')}" type="text/css" media="screen" charset="utf-8" />
    <link rel="stylesheet" href="${request.static_url('deform:static/css/ui-lightness/jquery-ui-1.8.11.custom.css')}" type="text/css" media="screen" charset="utf-8" />
  </head>

  <body>
    <div class="container">
        <!-- This is where our subsequent templates will fill in content -->
        <div metal:define-slot="content">
          Site content goes here
        </div>
    </div>

    <!-- The javascript resources from Deform -->
    <script src="${request.static_url('deform:static/scripts/jquery-1.7.2.min.js')}"></script>
    <script src="${request.static_url('deform_bootstrap:static/jquery-ui-1.8.18.custom.min.js')}"></script>
    <script src="${request.static_url('deform_bootstrap:static/jquery-ui-timepicker-addon-0.9.9.js')}"></script>
    <script src="${request.static_url('deform:static/scripts/deform.js')}"></script>
    <script src="${request.static_url('deform_bootstrap:static/deform_bootstrap.js')}"></script>
    <script src="${request.static_url('deform_bootstrap:static/bootstrap.min.js')}"></script>
    <script src="${request.static_url('deform_bootstrap:static/bootstrap-datepicker.js')}"></script>
    <script src="${request.static_url('deform_bootstrap:static/bootstrap-typeahead.js')}"></script>
    <script src="${request.static_url('deform_bootstrap:static/jquery.form-2.96.js')}"></script>
    <script src="${request.static_url('deform_bootstrap:static/jquery.maskedinput-1.3.js')}"></script>
  </body>
</html>
```

Now we have to modify our boilerplate view to use the layout in `todopyramid/views.py`, notice that we've also changed the view name and template name to reflect what this view does, showing the `home` page.

```
from .layouts import Layouts


class ToDoViews(Layouts):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(route_name='home', renderer='templates/home.pt')
    def home_view(request):
        # view code here
        return {}
```

Now we can add a `todopyramid/templates/home.pt` to our app with the following

```
<metal: master use-macro="view.global_template">
  <div metal:fill-slot="content">
    <h1>Home</h1>
    <p>Welcome to the Pyramid version of the ToDo app.</p>
  </div>
</metal:master>
```

Now subsequent templates can be set up in the same manner.

### Authentication

Our app will need to authorize users in order to be able to add a ToDo list. Pyramid, having no opinions on the matter, leaves us with a myriad of options. One quick way is to utilize the [Mozilla Persona][persona] login system. There just so happens to be a plugin for this called [pyramid_persona][pyramid_persona]

Following the documentation for the personas plugin, we add it to the dependencies of our app, build the latest version and include the plugin in our config.

We also override the default forbidden view in order to integrate a login form into our global template layout.

### Not Found

In order to keep up appearances, we add a custom Not Found view that integrates into our global layout. This is quite simple using the [pyramid.view.notfound_view_config][notfound]

### Models

Now that we have created the shell for our app, it is time to create some models. We will be utilizing [SQLAlchemy][sqlalchemy] in this case since it fits the needs of our application.

We will create a `TodoItem` and `Tag` model to start out with. This will give us the basis for our todo list.

[install]: http://pyramid.readthedocs.org/en/latest/narr/install.html
[deform]: http://docs.pylonsproject.org/projects/deform/en/latest/
[deform_bootstrap]: http://pypi.python.org/pypi/deform_bootstrap
[customux]: http://docs.pylonsproject.org/projects/pyramid_tutorials/en/latest/humans/creatingux/step05/index.html
[persona]: https://login.persona.org/
[pyramid_persona]: https://pyramid_persona.readthedocs.org/en/latest/
[notfound]: http://docs.pylonsproject.org/projects/pyramid/en/latest/api/view.html#pyramid.view.notfound_view_config
[sqlalchemy]: http://www.sqlalchemy.org/

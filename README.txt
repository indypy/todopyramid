# ToDo Pyramid App

This is the Pyramid app for the Python Web Shootout.

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

This creates the new virtual environemnt, now you can install the app.

```
(todopyramid)$ cd ~/Desktop
(todopyramid)$ git clone https://github.com/indypy/todopyramid.git
(todopyramid)$ cd todopyramid
(todopyramid)$ pip install -r requirements.txt
```

This gives us the end result of the finished app. It can now be started up by doing the following.

```
(todopyramid)$ pserve production.ini
```

Now go to <http://localhost:6543> and enjoy!

## How the sausage was made

The above install directions tell you how to get the finished application started. here we will document how the app was created from scratch.

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
(todopyramid)$ git status | awk -F'#\t' '{print $2}' | xargs git add
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

For our purposes, we won't need some of the boilerplate code that has been added.

[install]: http://pyramid.readthedocs.org/en/latest/narr/install.html

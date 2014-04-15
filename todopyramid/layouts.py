from pyramid.renderers import get_renderer
from pyramid.decorator import reify

#i18n/l10n is another topic to be handled for menu items
class SiteMenu(list):
    """mutable, ordered list of navbar menu items"""
    
    def __init__(self, request):
        """Set some common variables needed for each view.
        """
        self.request = request        
    
    def populate(self, menu_items):
        for k,v in menu_items.items():
            self.add_item(k,v)
    
    def add_item(self, title, route):
        new_item = {'title':title, 'route':route}
        self.append(new_item)
        
        
#ToDoPyramid currently highlights navbar item 'todos' for multiple routes
#Original version implemented navbar highlighting by setting a section variable 
menu_items = [        
        {'route': 'home', 'title': 'Home', 'routes': ['home']},
        {'route': 'todos', 'title': 'List', 'routes': ['todos', 'taglist']},
        {'route': 'tags', 'title': 'Tags', 'routes': ['tags']},
        {'route': 'account', 'title': 'Account', 'routes': ['account']},
        {'route': 'about', 'title': 'About', 'routes': ['about']}
]

class Layouts(object):
    """This is the main layout for our application. This currently
    just sets up the global layout template. See the views module and
    their associated templates to see how this gets used.
    """
    
    site_menu = menu_items
    
    def __init__(self, request):
        """Set some common variables needed for each view.
        """
        self.request = request


    @reify
    def global_template(self):
        renderer = get_renderer("todopyramid:templates/global_layout.pt")
        return renderer.implementation().macros['layout']
    
    
    @reify
    def navbar(self):
        """return navbar menu items and help to find current navbar item
        
        site menu concept inspired by
        http://docs.pylonsproject.org/projects/pyramid-tutorials/en/latest/humans/creatingux/step07/index.html
        
        concept can be extended by components registering routes and adding their items to navbar menu
        TodoPyramid adds Home, Todos, Tags, Account, About to this registry 
        When another TodoPyramid add-on component is activated by configuration it could add their menu item into this registry as well
        
        catching the matched route name inspired by
        http://stackoverflow.com/questions/13552992/get-current-route-instead-of-route-path-in-pyramid
        """
        def is_active_item(request, item):
            """if we have a match between menu route and matched route set a boolean variable 'current' to true, else to false"""
            if not request.matched_route:
                item['active'] = False
                return item
            activate_item = True if request.matched_route.name in item['routes'] else False
            item['active'] = activate_item
            return item
        
        def menu_url(request, item):
            item['url'] = request.route_url(item['route'])
            return item
        
        def process_item(request, item):
            item = menu_url(request, item)
            item = is_active_item(request, item)
            return item
        
        return [process_item(self.request, item) for item in self.site_menu]

         

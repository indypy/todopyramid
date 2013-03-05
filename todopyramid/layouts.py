from pyramid.renderers import get_renderer
from pyramid.decorator import reify


class Layouts(object):
    """This is the main layout for our application. This currently
    just sets up the global layout template. See the views module and
    their associated templates to see how this gets used.
    """

    @reify
    def global_template(self):
        renderer = get_renderer("templates/global_layout.pt")
        return renderer.implementation().macros['layout']

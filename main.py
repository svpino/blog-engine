import webapp2
import logging
import os
import urllib2

from app.handlers import * 

application = webapp2.WSGIApplication([
    webapp2.Route(r'/', DefaultHandler, name='home'),
    webapp2.Route(r'/about', AboutHandler),
    webapp2.Route(r'/archive', ArchiveHandler),
    webapp2.Route(r'/rss', RSSHandler, name='rss'),
    webapp2.Route(r'/<year:\d{4}>/<month:\d{2}>/', handler=DefaultHandler),
    webapp2.Route(r'/<year:\d{4}>/<month:\d{2}>/<day:\d{2}>/<page>', handler=PostHandler, name='post'),
], debug=True)

application.error_handlers[404] = DefaultHandler().handle_404
application.error_handlers[500] = DefaultHandler().handle_500

